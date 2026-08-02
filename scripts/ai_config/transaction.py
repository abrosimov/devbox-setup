from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType
    from typing import IO, Self

PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
_ENGINE_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_UNSUPPORTED_DIRECTORY_FSYNC_ERRORS = {
    errno.EBADF,
    errno.EINVAL,
    errno.ENOTSUP,
}


class BytesValidator(Protocol):
    def __call__(self, candidate: bytes, /) -> None: ...


class TransactionFileSystem(Protocol):
    def replace(self, source: Path, destination: Path, /) -> None: ...

    def read_bytes(self, path: Path, /) -> bytes: ...


class TransactionError(Exception):
    pass


class CandidateValidationError(TransactionError):
    pass


class TransactionDefinitionError(TransactionError):
    pass


class TransactionLockError(TransactionError):
    pass


class ConcurrentModificationError(TransactionError):
    pass


class ReadBackValidationError(TransactionError):
    def __init__(
        self,
        target: Path,
        *,
        restored: bool,
        restoration_error: OSError | None = None,
    ) -> None:
        self.target = target
        self.restored = restored
        self.restoration_error = restoration_error
        message = f"written file failed read-back validation: {target}"
        super().__init__(message)


class MultiFileTransactionError(TransactionError):
    def __init__(
        self,
        engine: str,
        *,
        rolled_back: bool,
        rollback_errors: tuple[OSError, ...],
        cleanup_errors: tuple[OSError, ...],
    ) -> None:
        self.engine = engine
        self.rolled_back = rolled_back
        self.rollback_errors = rollback_errors
        self.cleanup_errors = cleanup_errors
        message = f"multi-file transaction failed for engine: {engine}"
        super().__init__(message)


class JournalRecoveryError(TransactionError):
    def __init__(self, engine: str, errors: tuple[Exception, ...]) -> None:
        self.engine = engine
        self.errors = errors
        message = f"cannot recover unfinished transaction for engine: {engine}"
        super().__init__(message)


class TransactionCleanupError(TransactionError):
    def __init__(self, engine: str, errors: tuple[OSError, ...]) -> None:
        self.engine = engine
        self.errors = errors
        message = f"committed transaction cleanup failed for engine: {engine}"
        super().__init__(message)


class TransactionStatus(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class TransactionResult:
    target: Path
    status: TransactionStatus
    backup_path: Path | None

    @property
    def changed(self) -> bool:
        return self.status is not TransactionStatus.UNCHANGED


@dataclass(frozen=True, slots=True)
class FileWrite:
    target: Path
    candidate: bytes
    expected: bytes | None
    validate: BytesValidator
    mode: int = PRIVATE_FILE_MODE


@dataclass(frozen=True, slots=True)
class FileExpectation:
    target: Path
    expected: bytes | None


@dataclass(frozen=True, slots=True)
class MultiFileTransactionResult:
    engine: str
    files: tuple[TransactionResult, ...]
    recovered: bool

    @property
    def changed(self) -> bool:
        return any(result.changed for result in self.files)


class LocalTransactionFileSystem:
    def replace(self, source: Path, destination: Path, /) -> None:
        source.replace(destination)

    def read_bytes(self, path: Path, /) -> bytes:
        return path.read_bytes()


class _JournalStatus(StrEnum):
    PREPARING = "preparing"
    INSTALLING = "installing"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling-back"


class _EntryStatus(StrEnum):
    PENDING = "pending"
    PREPARED = "prepared"
    INSTALLED = "installed"


class _OriginalStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"


class _ModeStatus(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"

    @property
    def mode(self) -> int:
        if self is _ModeStatus.PRIVATE:
            return PRIVATE_FILE_MODE
        return 0o644


@dataclass(slots=True)
class _JournalEntry:
    target_path: Path
    staged_path: Path
    backup_path: Path | None
    original_status: _OriginalStatus
    original_mode: int | None
    mode_status: _ModeStatus
    status: _EntryStatus = _EntryStatus.PENDING


@dataclass(slots=True)
class _Journal:
    status: _JournalStatus
    entries: tuple[_JournalEntry, ...]


@dataclass(frozen=True, slots=True)
class _NormalisedWrite:
    target: Path
    candidate: bytes
    expected: bytes | None
    validate: BytesValidator
    mode: int


@dataclass(frozen=True, slots=True)
class _CurrentWrite:
    write: _NormalisedWrite
    original: bytes | None
    current_mode: int | None


class _EngineLock:
    def __init__(self, path: Path, *, wait: bool) -> None:
        self._path = path
        self._wait = wait
        self._descriptor: int | None = None

    def __enter__(self) -> Self:
        _create_private_directories(self._path.parent)
        self._path.parent.chmod(PRIVATE_DIRECTORY_MODE)
        descriptor = os.open(self._path, os.O_CREAT | os.O_RDWR, PRIVATE_FILE_MODE)
        try:
            os.fchmod(descriptor, PRIVATE_FILE_MODE)
            operation = fcntl.LOCK_EX
            if not self._wait:
                operation |= fcntl.LOCK_NB
            fcntl.flock(descriptor, operation)
        except BlockingIOError as error:
            os.close(descriptor)
            message = f"transaction lock is held: {self._path}"
            raise TransactionLockError(message) from error
        except Exception:
            os.close(descriptor)
            raise
        self._descriptor = descriptor
        return self

    def __exit__(
        self,
        _exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        descriptor = self._descriptor
        if descriptor is None:
            return
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
            self._descriptor = None


def write_validated_file(
    target: Path,
    candidate: bytes,
    *,
    validate: BytesValidator,
    mode: int = PRIVATE_FILE_MODE,
    create_backup: bool = False,
    state_directory: Path | None = None,
    file_system: TransactionFileSystem | None = None,
) -> TransactionResult:
    _validate_candidate(candidate, validate)
    _validate_mode(mode)
    if create_backup and state_directory is None:
        message = "state_directory is required when create_backup is enabled"
        raise TransactionDefinitionError(message)
    active_file_system = file_system if file_system is not None else LocalTransactionFileSystem()
    target_existed = target.exists()
    original = active_file_system.read_bytes(target) if target_existed else None

    current_mode = stat.S_IMODE(target.stat().st_mode) if target_existed else None
    if original == candidate and current_mode == mode:
        return TransactionResult(
            target=target,
            status=TransactionStatus.UNCHANGED,
            backup_path=None,
        )

    _create_private_directories(target.parent)
    backup_path = (
        _create_backup(target, original, state_directory, active_file_system)
        if create_backup
        else None
    )
    _atomic_replace_bytes(target, candidate, active_file_system, mode=mode)

    try:
        _read_back_and_validate(target, candidate, validate, active_file_system)
    except Exception as error:
        restored, restoration_error = _restore_original(
            target=target,
            original=original,
            backup_path=backup_path,
            file_system=active_file_system,
            mode=current_mode if current_mode is not None else mode,
        )
        raise ReadBackValidationError(
            target,
            restored=restored,
            restoration_error=restoration_error,
        ) from error

    status = TransactionStatus.UPDATED if target_existed else TransactionStatus.CREATED
    return TransactionResult(target=target, status=status, backup_path=backup_path)


def write_validated_files(
    *,
    engine: str,
    state_directory: Path,
    writes: Sequence[FileWrite],
    expectations: Sequence[FileExpectation] = (),
    file_system: TransactionFileSystem | None = None,
    wait_for_lock: bool = True,
) -> MultiFileTransactionResult:
    _validate_engine_name(engine)
    normalised_writes = _normalise_and_validate_writes(writes, state_directory, engine)
    normalised_expectations = _normalise_expectations(expectations, normalised_writes)
    active_file_system = file_system if file_system is not None else LocalTransactionFileSystem()
    state_path = state_directory.absolute()
    lock_path = state_path / f"{engine}.lock"
    journal_path = state_path / f"{engine}.journal.json"

    with _EngineLock(lock_path, wait=wait_for_lock):
        recovered = _recover_journal(engine, journal_path, active_file_system)
        _validate_expectations(normalised_expectations, active_file_system)
        current_writes = _read_expected_writes(normalised_writes, active_file_system)
        return _execute_multi_file_transaction(
            engine=engine,
            journal_path=journal_path,
            current_writes=current_writes,
            recovered=recovered,
            file_system=active_file_system,
            state_directory=state_path,
        )


def _execute_multi_file_transaction(
    *,
    engine: str,
    journal_path: Path,
    current_writes: tuple[_CurrentWrite, ...],
    recovered: bool,
    file_system: TransactionFileSystem,
    state_directory: Path,
) -> MultiFileTransactionResult:
    unchanged = {
        current.write.target: TransactionResult(
            target=current.write.target,
            status=TransactionStatus.UNCHANGED,
            backup_path=None,
        )
        for current in current_writes
        if _current_matches_candidate(current)
    }
    changed_writes = tuple(
        current for current in current_writes if not _current_matches_candidate(current)
    )
    if not changed_writes:
        return MultiFileTransactionResult(
            engine=engine,
            files=tuple(unchanged[current.write.target] for current in current_writes),
            recovered=recovered,
        )

    journal = _new_journal(changed_writes, state_directory)
    installation_started = False
    try:
        _write_journal(journal_path, journal, file_system)
        _prepare_entries(journal_path, journal, changed_writes, file_system)
        journal.status = _JournalStatus.INSTALLING
        _write_journal(journal_path, journal, file_system)
        installation_started = True
        _install_entries(journal_path, journal, file_system)
        _validate_installed_files(changed_writes, file_system)
        journal.status = _JournalStatus.COMMITTED
        _write_journal(journal_path, journal, file_system)
    except Exception as error:
        rollback_errors = (
            _rollback_entries(journal.entries, file_system) if installation_started else ()
        )
        if installation_started:
            journal.status = _JournalStatus.ROLLING_BACK
            _try_write_journal(journal_path, journal, file_system)
        cleanup_errors = _cleanup_transaction(journal_path, journal.entries)
        if rollback_errors:
            _try_write_journal(journal_path, journal, file_system)
        elif not cleanup_errors:
            cleanup_errors += _remove_journal(journal_path)
        raise MultiFileTransactionError(
            engine,
            rolled_back=not rollback_errors,
            rollback_errors=rollback_errors,
            cleanup_errors=cleanup_errors,
        ) from error

    cleanup_errors = _cleanup_transaction(journal_path, journal.entries)
    if not cleanup_errors:
        cleanup_errors += _remove_journal(journal_path)
    if cleanup_errors:
        raise TransactionCleanupError(engine, cleanup_errors)

    changed = {
        current.write.target: TransactionResult(
            target=current.write.target,
            status=(
                TransactionStatus.UPDATED
                if current.original is not None
                else TransactionStatus.CREATED
            ),
            backup_path=(
                _backup_path(state_directory, current.write.target)
                if current.original is not None
                else None
            ),
        )
        for current in changed_writes
    }
    results = unchanged | changed
    return MultiFileTransactionResult(
        engine=engine,
        files=tuple(results[current.write.target] for current in current_writes),
        recovered=recovered,
    )


def _validate_engine_name(engine: str) -> None:
    if _ENGINE_NAME_PATTERN.fullmatch(engine) is None:
        message = "engine must use letters, digits, dots, underscores, or hyphens"
        raise TransactionDefinitionError(message)


def _normalise_and_validate_writes(
    writes: Sequence[FileWrite],
    state_directory: Path,
    engine: str,
) -> tuple[_NormalisedWrite, ...]:
    normalised: list[_NormalisedWrite] = []
    for write in writes:
        _validate_candidate(write.candidate, write.validate)
        _validate_mode(write.mode)
        normalised.append(
            _NormalisedWrite(
                target=write.target.absolute(),
                candidate=write.candidate,
                expected=write.expected,
                validate=write.validate,
                mode=write.mode,
            ),
        )
    targets = [write.target for write in normalised]
    if len(targets) != len(set(targets)):
        message = "transaction targets must be unique"
        raise TransactionDefinitionError(message)
    state_path = state_directory.absolute()
    protected_paths = {
        state_path / f"{engine}.lock",
        state_path / f"{engine}.journal.json",
        _journal_temporary_path(state_path / f"{engine}.journal.json"),
    }
    invalid_target = next(
        (
            target
            for target in targets
            if target in protected_paths
            or target.is_relative_to(state_path / "backups")
            or _is_staged_transaction_path(target, state_path)
        ),
        None,
    )
    if invalid_target is not None:
        message = f"transaction target collides with transaction state: {invalid_target}"
        raise TransactionDefinitionError(message)
    return tuple(normalised)


def _normalise_expectations(
    expectations: Sequence[FileExpectation],
    writes: tuple[_NormalisedWrite, ...],
) -> tuple[FileExpectation, ...]:
    normalised = tuple(
        FileExpectation(target=expectation.target.absolute(), expected=expectation.expected)
        for expectation in expectations
    )
    targets = [expectation.target for expectation in normalised]
    if len(targets) != len(set(targets)):
        message = "transaction expectations must be unique"
        raise TransactionDefinitionError(message)
    write_targets = {write.target for write in writes}
    overlap = next((target for target in targets if target in write_targets), None)
    if overlap is not None:
        message = f"transaction target has both a write and expectation: {overlap}"
        raise TransactionDefinitionError(message)
    return normalised


def _validate_expectations(
    expectations: tuple[FileExpectation, ...],
    file_system: TransactionFileSystem,
) -> None:
    for expectation in expectations:
        try:
            current = file_system.read_bytes(expectation.target)
        except FileNotFoundError:
            current = None
        if current != expectation.expected:
            message = f"transaction source changed after planning: {expectation.target}"
            raise ConcurrentModificationError(message)


def _is_staged_transaction_path(target: Path, state_directory: Path) -> bool:
    return (
        target.is_relative_to(state_directory)
        and target.name.startswith(".")
        and target.name.endswith(".stage")
    )


def _read_expected_writes(
    writes: tuple[_NormalisedWrite, ...],
    file_system: TransactionFileSystem,
) -> tuple[_CurrentWrite, ...]:
    current_writes: list[_CurrentWrite] = []
    for write in writes:
        original = file_system.read_bytes(write.target) if write.target.exists() else None
        if original != write.expected:
            message = f"transaction target changed after planning: {write.target}"
            raise ConcurrentModificationError(message)
        current_mode = stat.S_IMODE(write.target.stat().st_mode) if original is not None else None
        current_writes.append(
            _CurrentWrite(write=write, original=original, current_mode=current_mode),
        )
    return tuple(current_writes)


def _current_matches_candidate(current: _CurrentWrite) -> bool:
    return (
        current.original == current.write.candidate and current.current_mode == current.write.mode
    )


def _new_journal(
    changed_writes: tuple[_CurrentWrite, ...],
    state_directory: Path,
) -> _Journal:
    entries = tuple(
        _JournalEntry(
            target_path=current.write.target,
            staged_path=_new_staged_path(current.write.target),
            backup_path=(
                _backup_path(state_directory, current.write.target)
                if current.original is not None
                else None
            ),
            original_status=(
                _OriginalStatus.PRESENT if current.original is not None else _OriginalStatus.ABSENT
            ),
            original_mode=current.current_mode,
            mode_status=_mode_status(current.write.mode),
        )
        for current in changed_writes
    )
    return _Journal(status=_JournalStatus.PREPARING, entries=entries)


def _prepare_entries(
    journal_path: Path,
    journal: _Journal,
    changed_writes: tuple[_CurrentWrite, ...],
    file_system: TransactionFileSystem,
) -> None:
    for entry, current in zip(journal.entries, changed_writes, strict=True):
        _create_private_directories(entry.target_path.parent)
        if entry.backup_path is not None and current.original is not None:
            _create_private_directories(entry.backup_path.parent)
            entry.backup_path.parent.chmod(PRIVATE_DIRECTORY_MODE)
            _atomic_replace_bytes(entry.backup_path, current.original, file_system)
        _write_file(entry.staged_path, current.write.candidate, mode=current.write.mode)
        _fsync_directory(entry.staged_path.parent)
        entry.status = _EntryStatus.PREPARED
        _write_journal(journal_path, journal, file_system)


def _install_entries(
    journal_path: Path,
    journal: _Journal,
    file_system: TransactionFileSystem,
) -> None:
    for entry in journal.entries:
        file_system.replace(entry.staged_path, entry.target_path)
        _fsync_directory(entry.target_path.parent)
        entry.status = _EntryStatus.INSTALLED
        _write_journal(journal_path, journal, file_system)


def _validate_installed_files(
    changed_writes: tuple[_CurrentWrite, ...],
    file_system: TransactionFileSystem,
) -> None:
    for current in changed_writes:
        _read_back_and_validate(
            current.write.target,
            current.write.candidate,
            current.write.validate,
            file_system,
        )


def _read_back_and_validate(
    target: Path,
    candidate: bytes,
    validate: BytesValidator,
    file_system: TransactionFileSystem,
) -> None:
    read_back = file_system.read_bytes(target)
    validate(read_back)
    if read_back != candidate:
        message = "read-back content differs from candidate"
        raise ValueError(message)


def _recover_journal(
    engine: str,
    journal_path: Path,
    file_system: TransactionFileSystem,
) -> bool:
    journal_temporary = _journal_temporary_path(journal_path)
    try:
        _unlink_and_sync(journal_temporary)
    except OSError as error:
        raise JournalRecoveryError(engine, (error,)) from error
    if not journal_path.exists():
        return False
    try:
        journal = _read_journal(journal_path, file_system)
    except (OSError, TypeError, UnicodeError, ValueError) as error:
        raise JournalRecoveryError(engine, (error,)) from error

    errors: tuple[Exception, ...] = ()
    if journal.status in {_JournalStatus.INSTALLING, _JournalStatus.ROLLING_BACK}:
        rollback_errors = _rollback_entries(journal.entries, file_system)
        errors += rollback_errors
    errors += _cleanup_transaction(journal_path, journal.entries)
    if not errors:
        errors += _remove_journal(journal_path)
    if errors:
        raise JournalRecoveryError(engine, errors)
    return True


def _rollback_entries(
    entries: tuple[_JournalEntry, ...],
    file_system: TransactionFileSystem,
) -> tuple[OSError, ...]:
    errors: list[OSError] = []
    for entry in reversed(entries):
        try:
            if entry.original_status is _OriginalStatus.PRESENT:
                original = _read_entry_backup(entry, file_system)
                _atomic_replace_bytes(
                    entry.target_path,
                    original,
                    file_system,
                    mode=_entry_original_mode(entry),
                )
            else:
                _unlink_and_sync(entry.target_path)
        except OSError as error:
            errors.append(error)
    return tuple(errors)


def _read_entry_backup(
    entry: _JournalEntry,
    file_system: TransactionFileSystem,
) -> bytes:
    if entry.backup_path is None:
        message = f"journal backup is missing for: {entry.target_path}"
        raise OSError(message)
    return file_system.read_bytes(entry.backup_path)


def _entry_original_mode(entry: _JournalEntry) -> int:
    if entry.original_mode is None:
        message = f"journal original mode is missing for: {entry.target_path}"
        raise OSError(message)
    return entry.original_mode


def _cleanup_transaction(
    journal_path: Path,
    entries: tuple[_JournalEntry, ...],
) -> tuple[OSError, ...]:
    errors: list[OSError] = []
    for path in (
        *(entry.staged_path for entry in entries),
        _journal_temporary_path(journal_path),
    ):
        try:
            _unlink_and_sync(path)
        except OSError as error:
            errors.append(error)
    return tuple(errors)


def _remove_journal(journal_path: Path) -> tuple[OSError, ...]:
    try:
        _unlink_and_sync(journal_path)
    except OSError as error:
        return (error,)
    return ()


def _try_write_journal(
    journal_path: Path,
    journal: _Journal,
    file_system: TransactionFileSystem,
) -> None:
    try:
        _write_journal(journal_path, journal, file_system)
    except OSError:
        return


def _write_journal(
    journal_path: Path,
    journal: _Journal,
    file_system: TransactionFileSystem,
) -> None:
    content = _serialise_journal(journal)
    temporary_path = _journal_temporary_path(journal_path)
    temporary_path.unlink(missing_ok=True)
    _write_private_file(temporary_path, content)
    try:
        file_system.replace(temporary_path, journal_path)
        _fsync_directory(journal_path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def _serialise_journal(journal: _Journal) -> bytes:
    entries: list[dict[str, str]] = []
    for entry in journal.entries:
        serialised = {
            "mode_status": entry.mode_status.value,
            "original_status": entry.original_status.value,
            "staged_path": str(entry.staged_path),
            "status": entry.status.value,
            "target_path": str(entry.target_path),
        }
        if entry.backup_path is not None:
            serialised["backup_path"] = str(entry.backup_path)
        if entry.original_mode is not None:
            serialised["original_mode"] = str(entry.original_mode)
        entries.append(serialised)
    document: dict[str, object] = {
        "entries": entries,
        "status": journal.status.value,
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _read_journal(
    journal_path: Path,
    file_system: TransactionFileSystem,
) -> _Journal:
    source = file_system.read_bytes(journal_path).decode()
    document: object = json.loads(source)
    mapping = _as_mapping(document, "journal must be an object")
    if set(mapping) != {"entries", "status"}:
        message = "journal has unexpected fields"
        raise ValueError(message)
    status = _JournalStatus(_required_string(mapping, "status"))
    raw_entries = mapping["entries"]
    if not isinstance(raw_entries, list):
        message = "journal entries must be an array"
        raise TypeError(message)
    entries = tuple(
        _parse_journal_entry(entry, journal_path.parent)
        for entry in cast("list[object]", raw_entries)
    )
    targets = [entry.target_path for entry in entries]
    if len(targets) != len(set(targets)):
        message = "journal targets must be unique"
        raise ValueError(message)
    return _Journal(status=status, entries=entries)


def _parse_journal_entry(value: object, state_directory: Path) -> _JournalEntry:
    mapping = _as_mapping(value, "journal entry must be an object")
    required = {"mode_status", "original_status", "staged_path", "status", "target_path"}
    allowed = required | {"backup_path", "original_mode"}
    if not required.issubset(mapping) or not set(mapping).issubset(allowed):
        message = "journal entry has unexpected fields"
        raise ValueError(message)
    target_path = Path(_required_string(mapping, "target_path"))
    staged_path = Path(_required_string(mapping, "staged_path"))
    original_status = _OriginalStatus(_required_string(mapping, "original_status"))
    mode_status = _ModeStatus(_required_string(mapping, "mode_status"))
    entry_status = _EntryStatus(_required_string(mapping, "status"))
    original_mode = _required_mode(mapping, "original_mode") if "original_mode" in mapping else None
    backup_path = (
        Path(_required_string(mapping, "backup_path")) if "backup_path" in mapping else None
    )
    _validate_journal_paths(
        target_path,
        staged_path,
        backup_path,
        original_status,
        original_mode,
        state_directory,
    )
    return _JournalEntry(
        target_path=target_path,
        staged_path=staged_path,
        backup_path=backup_path,
        original_status=original_status,
        original_mode=original_mode,
        mode_status=mode_status,
        status=entry_status,
    )


def _as_mapping(value: object, message: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise TypeError(message)
    return cast("dict[object, object]", value)


def _required_string(mapping: dict[object, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        message = f"journal field must be a string: {key}"
        raise TypeError(message)
    return value


def _required_mode(mapping: dict[object, object], key: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.isdecimal():
        message = f"journal field must be a decimal mode string: {key}"
        raise TypeError(message)
    mode = int(value)
    if not 0 <= mode <= 0o7777:
        message = f"journal field contains an invalid mode: {key}"
        raise ValueError(message)
    return mode


def _validate_journal_paths(
    target_path: Path,
    staged_path: Path,
    backup_path: Path | None,
    original_status: _OriginalStatus,
    original_mode: int | None,
    state_directory: Path,
) -> None:
    if not target_path.is_absolute() or not staged_path.is_absolute():
        message = "journal paths must be absolute"
        raise ValueError(message)
    valid_staged_name = (
        staged_path.parent == target_path.parent
        and staged_path.name.startswith(f".{target_path.name}.")
        and staged_path.name.endswith(".stage")
    )
    if not valid_staged_name:
        message = "journal staged path is invalid"
        raise ValueError(message)
    expected_backup = _backup_path(state_directory, target_path)
    if original_status is _OriginalStatus.PRESENT and backup_path != expected_backup:
        message = "journal backup path is invalid"
        raise ValueError(message)
    if original_status is _OriginalStatus.ABSENT and backup_path is not None:
        message = "journal has a backup for an absent target"
        raise ValueError(message)
    if original_status is _OriginalStatus.PRESENT and original_mode is None:
        message = "journal has no mode for a present target"
        raise ValueError(message)
    if original_status is _OriginalStatus.ABSENT and original_mode is not None:
        message = "journal has a mode for an absent target"
        raise ValueError(message)


def _validate_candidate(candidate: bytes, validate: BytesValidator) -> None:
    try:
        validate(candidate)
    except Exception as error:
        message = "candidate failed validation"
        raise CandidateValidationError(message) from error


def _validate_mode(mode: int) -> None:
    if mode not in {PRIVATE_FILE_MODE, 0o644}:
        message = "file mode must be 0o600 or 0o644"
        raise TransactionDefinitionError(message)


def _mode_status(mode: int) -> _ModeStatus:
    if mode == PRIVATE_FILE_MODE:
        return _ModeStatus.PRIVATE
    return _ModeStatus.PUBLIC


def _create_private_directories(parent: Path) -> None:
    missing: list[Path] = []
    current = parent
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=PRIVATE_DIRECTORY_MODE)


def _create_backup(
    target: Path,
    original: bytes | None,
    state_directory: Path | None,
    file_system: TransactionFileSystem,
) -> Path | None:
    if original is None:
        return None
    if state_directory is None:
        message = "state directory is required"
        raise TransactionDefinitionError(message)
    backup_path = _backup_path(state_directory.absolute(), target.absolute())
    _create_private_directories(backup_path.parent)
    backup_path.parent.chmod(PRIVATE_DIRECTORY_MODE)
    _atomic_replace_bytes(backup_path, original, file_system)
    return backup_path


def _backup_path(state_directory: Path, target: Path) -> Path:
    digest = hashlib.sha256(os.fsencode(target)).hexdigest()
    return state_directory / "backups" / f"{digest}.bak"


def _new_staged_path(target: Path) -> Path:
    return target.with_name(f".{target.name}.{uuid.uuid4().hex}.stage")


def _journal_temporary_path(journal_path: Path) -> Path:
    return journal_path.with_name(f".{journal_path.name}.tmp")


def _atomic_replace_bytes(
    target: Path,
    content: bytes,
    file_system: TransactionFileSystem,
    *,
    mode: int = PRIVATE_FILE_MODE,
) -> None:
    temporary_path = _write_temporary_file(target, content, mode=mode)
    try:
        file_system.replace(temporary_path, target)
        _fsync_directory(target.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_temporary_file(target: Path, content: bytes, *, mode: int) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            _write_and_sync(stream, content, mode=mode)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path


def _write_private_file(path: Path, content: bytes) -> None:
    _write_file(path, content, mode=PRIVATE_FILE_MODE)


def _write_file(path: Path, content: bytes, *, mode: int) -> None:
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        PRIVATE_FILE_MODE,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            _write_and_sync(stream, content, mode=mode)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _write_and_sync(stream: IO[bytes], content: bytes, *, mode: int) -> None:
    os.fchmod(stream.fileno(), mode)
    written = stream.write(content)
    if written != len(content):
        message = "temporary file write was incomplete"
        raise OSError(message)
    stream.flush()
    descriptor = stream.fileno()
    os.fsync(descriptor)


def _restore_original(
    *,
    target: Path,
    original: bytes | None,
    backup_path: Path | None,
    file_system: TransactionFileSystem,
    mode: int,
) -> tuple[bool, OSError | None]:
    try:
        if backup_path is not None:
            _atomic_replace_bytes(
                target,
                file_system.read_bytes(backup_path),
                file_system,
                mode=mode,
            )
        elif original is not None:
            _atomic_replace_bytes(target, original, file_system, mode=mode)
        else:
            _unlink_and_sync(target)
    except OSError as error:
        return False, error
    return True, None


def _unlink_and_sync(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    _fsync_directory(path.parent)


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError as error:
        if error.errno in _UNSUPPORTED_DIRECTORY_FSYNC_ERRORS:
            return
        raise
    try:
        try:
            os.fsync(descriptor)
        except OSError as error:
            if error.errno not in _UNSUPPORTED_DIRECTORY_FSYNC_ERRORS:
                raise
    finally:
        os.close(descriptor)
