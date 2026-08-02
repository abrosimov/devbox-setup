from __future__ import annotations

import fcntl
import json
import os
import stat
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest
from ai_config import (
    CandidateValidationError,
    ReadBackValidationError,
    TransactionStatus,
    write_validated_file,
)
from ai_config.transaction import (
    ConcurrentModificationError,
    FileExpectation,
    FileWrite,
    MultiFileTransactionError,
    MultiFileTransactionResult,
    TransactionDefinitionError,
    TransactionLockError,
    write_validated_files,
)

if TYPE_CHECKING:
    from pathlib import Path

OLD_DOCUMENT = b'{"valid": "old"}\n'
NEW_DOCUMENT = b'{"valid": "new"}\n'


def validate_document(content: bytes) -> None:
    if not content.startswith(b'{"valid":'):
        message = "invalid test document"
        raise ValueError(message)


def assert_no_temporary_files(directory: Path) -> None:
    assert not list(directory.glob(".*.tmp"))


class InjectedReplaceError(OSError):
    pass


class SimulatedCrash(BaseException):
    pass


@dataclass(slots=True)
class ReplaceFailingFileSystem:
    target: Path

    def replace(self, source: Path, destination: Path, /) -> None:
        if destination == self.target:
            message = "injected replace failure"
            raise InjectedReplaceError(message)
        source.replace(destination)

    def read_bytes(self, path: Path, /) -> bytes:
        return path.read_bytes()


@dataclass(slots=True)
class ReadBackFailingFileSystem:
    target: Path
    target_replacements: int = 0

    def replace(self, source: Path, destination: Path, /) -> None:
        source.replace(destination)
        if destination == self.target:
            self.target_replacements += 1

    def read_bytes(self, path: Path, /) -> bytes:
        if path == self.target and self.target_replacements == 1:
            message = "injected read-back failure"
            raise OSError(message)
        return path.read_bytes()


@dataclass(slots=True)
class CorruptingReadBackFileSystem:
    target: Path
    target_replacements: int = 0

    def replace(self, source: Path, destination: Path, /) -> None:
        source.replace(destination)
        if destination == self.target:
            self.target_replacements += 1

    def read_bytes(self, path: Path, /) -> bytes:
        if path == self.target and self.target_replacements == 1:
            return b"invalid read-back"
        return path.read_bytes()


@dataclass(slots=True)
class FailOnceBeforeReplaceFileSystem:
    target: Path
    failed: bool = False

    def replace(self, source: Path, destination: Path, /) -> None:
        if destination == self.target and not self.failed:
            self.failed = True
            message = "injected multi-file replace failure"
            raise InjectedReplaceError(message)
        source.replace(destination)

    def read_bytes(self, path: Path, /) -> bytes:
        return path.read_bytes()


@dataclass(slots=True)
class CorruptingMultiFileReadBack:
    target: Path
    target_installed: bool = False

    def replace(self, source: Path, destination: Path, /) -> None:
        source.replace(destination)
        if destination == self.target:
            self.target_installed = True

    def read_bytes(self, path: Path, /) -> bytes:
        if path == self.target and self.target_installed:
            return b"invalid read-back"
        return path.read_bytes()


@dataclass(slots=True)
class CrashAfterTargetReplaceFileSystem:
    target: Path
    crashed: bool = False

    def replace(self, source: Path, destination: Path, /) -> None:
        source.replace(destination)
        if destination == self.target and not self.crashed:
            self.crashed = True
            raise SimulatedCrash

    def read_bytes(self, path: Path, /) -> bytes:
        return path.read_bytes()


@dataclass(slots=True)
class CrashAfterCommitMarkerFileSystem:
    journal_path: Path
    crashed: bool = False

    def replace(self, source: Path, destination: Path, /) -> None:
        should_crash = (
            destination == self.journal_path
            and b'"status":"committed"' in source.read_bytes()
            and not self.crashed
        )
        source.replace(destination)
        if should_crash:
            self.crashed = True
            raise SimulatedCrash

    def read_bytes(self, path: Path, /) -> bytes:
        return path.read_bytes()


@dataclass(slots=True)
class RecordingFileSystem:
    replacements: list[tuple[Path, Path]] = field(default_factory=list)

    def replace(self, source: Path, destination: Path, /) -> None:
        self.replacements.append((source, destination))
        source.replace(destination)

    def read_bytes(self, path: Path, /) -> bytes:
        return path.read_bytes()


class TestValidatedFileTransaction:
    def test_create_returns_created_and_creates_private_tree(self, tmp_path: Path) -> None:
        target = tmp_path / "private" / "nested" / "settings.json"

        result = write_validated_file(target, NEW_DOCUMENT, validate=validate_document)

        assert result.status is TransactionStatus.CREATED
        assert result.changed is True
        assert result.backup_path is None
        assert target.read_bytes() == NEW_DOCUMENT
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
        assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(target.parent.parent.stat().st_mode) == 0o700
        assert_no_temporary_files(target.parent)

    def test_update_creates_one_private_backup(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        state_directory = tmp_path / "state"
        target.write_bytes(OLD_DOCUMENT)

        first = write_validated_file(
            target,
            NEW_DOCUMENT,
            validate=validate_document,
            create_backup=True,
            state_directory=state_directory,
        )
        second = write_validated_file(
            target,
            OLD_DOCUMENT,
            validate=validate_document,
            create_backup=True,
            state_directory=state_directory,
        )

        backup_path = first.backup_path
        assert backup_path is not None
        assert first.status is TransactionStatus.UPDATED
        assert second.status is TransactionStatus.UPDATED
        assert first.backup_path == backup_path
        assert second.backup_path == backup_path
        assert target.read_bytes() == OLD_DOCUMENT
        assert backup_path.read_bytes() == NEW_DOCUMENT
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
        assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
        assert list((state_directory / "backups").glob("*.bak")) == [backup_path]
        assert not list(tmp_path.glob("*.bak"))
        assert_no_temporary_files(tmp_path)

    def test_identical_candidate_is_a_no_op_without_backup(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        state_directory = tmp_path / "state"
        target.write_bytes(NEW_DOCUMENT)
        target.chmod(0o600)
        original_stat = target.stat()

        result = write_validated_file(
            target,
            NEW_DOCUMENT,
            validate=validate_document,
            create_backup=True,
            state_directory=state_directory,
        )

        assert result.status is TransactionStatus.UNCHANGED
        assert result.changed is False
        assert result.backup_path is None
        assert target.stat().st_ino == original_stat.st_ino
        assert not state_directory.exists()
        assert_no_temporary_files(tmp_path)

    def test_invalid_candidate_does_not_create_parent_or_change_target(
        self,
        tmp_path: Path,
    ) -> None:
        missing_parent = tmp_path / "missing"
        target = missing_parent / "settings.json"

        with pytest.raises(CandidateValidationError):
            write_validated_file(target, b"invalid", validate=validate_document)

        assert not missing_parent.exists()

    def test_invalid_candidate_leaves_existing_target_unchanged(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        state_directory = tmp_path / "state"
        target.write_bytes(OLD_DOCUMENT)

        with pytest.raises(CandidateValidationError):
            write_validated_file(
                target,
                b"invalid",
                validate=validate_document,
                create_backup=True,
                state_directory=state_directory,
            )

        assert target.read_bytes() == OLD_DOCUMENT
        assert not state_directory.exists()
        assert_no_temporary_files(tmp_path)

    def test_replace_failure_leaves_target_unchanged_and_removes_temporary_file(
        self,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "settings.json"
        target.write_bytes(OLD_DOCUMENT)

        with pytest.raises(InjectedReplaceError):
            write_validated_file(
                target,
                NEW_DOCUMENT,
                validate=validate_document,
                file_system=ReplaceFailingFileSystem(target),
            )

        assert target.read_bytes() == OLD_DOCUMENT
        assert_no_temporary_files(tmp_path)

    @pytest.mark.parametrize(
        "file_system_type",
        [ReadBackFailingFileSystem, CorruptingReadBackFileSystem],
    )
    def test_read_back_failure_restores_private_backup_atomically(
        self,
        tmp_path: Path,
        file_system_type: type[ReadBackFailingFileSystem | CorruptingReadBackFileSystem],
    ) -> None:
        target = tmp_path / "settings.json"
        state_directory = tmp_path / "state"
        target.write_bytes(OLD_DOCUMENT)
        file_system = file_system_type(target)

        with pytest.raises(ReadBackValidationError) as caught:
            write_validated_file(
                target,
                NEW_DOCUMENT,
                validate=validate_document,
                create_backup=True,
                state_directory=state_directory,
                file_system=file_system,
            )

        backups = list((state_directory / "backups").glob("*.bak"))
        assert len(backups) == 1
        backup_path = backups[0]
        assert caught.value.target == target
        assert caught.value.restored is True
        assert caught.value.restoration_error is None
        assert target.read_bytes() == OLD_DOCUMENT
        assert backup_path.read_bytes() == OLD_DOCUMENT
        assert stat.S_IMODE(target.stat().st_mode) == 0o644
        assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
        assert file_system.target_replacements == 2
        assert_no_temporary_files(tmp_path)

    def test_failed_read_back_of_new_file_restores_absence(self, tmp_path: Path) -> None:
        target = tmp_path / "settings.json"
        file_system = CorruptingReadBackFileSystem(target)

        with pytest.raises(ReadBackValidationError) as caught:
            write_validated_file(
                target,
                NEW_DOCUMENT,
                validate=validate_document,
                file_system=file_system,
            )

        assert caught.value.restored is True
        assert not target.exists()
        assert_no_temporary_files(tmp_path)


class TestMultiFileTransaction:
    def test_live_and_base_inside_state_commit_together(self, tmp_path: Path) -> None:
        state_directory = tmp_path / "state"
        live_target = tmp_path / "live" / "settings.json"
        base_target = state_directory / "base.json"
        live_target.parent.mkdir()
        live_target.write_bytes(OLD_DOCUMENT)
        live_target.chmod(0o600)

        result = write_validated_files(
            engine="claude",
            state_directory=state_directory,
            writes=(
                FileWrite(live_target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),
                FileWrite(base_target, NEW_DOCUMENT, None, validate_document),
            ),
        )

        assert result.changed is True
        assert live_target.read_bytes() == NEW_DOCUMENT
        assert base_target.read_bytes() == NEW_DOCUMENT
        assert stat.S_IMODE(live_target.stat().st_mode) == 0o600
        assert stat.S_IMODE(base_target.stat().st_mode) == 0o600
        assert not (state_directory / "claude.journal.json").exists()

    def test_create_and_update_commit_with_modes_private_state_and_same_filesystem_stages(
        self,
        tmp_path: Path,
    ) -> None:
        state_directory = tmp_path / "state"
        repo_target = tmp_path / "repo" / "settings.json"
        live_target = tmp_path / "live" / "settings.json"
        repo_target.parent.mkdir()
        repo_target.write_bytes(OLD_DOCUMENT)
        repo_target.chmod(0o644)
        file_system = RecordingFileSystem()

        result = write_validated_files(
            engine="claude",
            state_directory=state_directory,
            writes=(
                FileWrite(
                    target=repo_target,
                    candidate=NEW_DOCUMENT,
                    expected=OLD_DOCUMENT,
                    validate=validate_document,
                    mode=0o644,
                ),
                FileWrite(
                    target=live_target,
                    candidate=NEW_DOCUMENT,
                    expected=None,
                    validate=validate_document,
                ),
            ),
            file_system=file_system,
        )

        assert isinstance(result, MultiFileTransactionResult)
        assert result.changed is True
        assert result.recovered is False
        assert [item.status for item in result.files] == [
            TransactionStatus.UPDATED,
            TransactionStatus.CREATED,
        ]
        assert repo_target.read_bytes() == NEW_DOCUMENT
        assert live_target.read_bytes() == NEW_DOCUMENT
        assert stat.S_IMODE(repo_target.stat().st_mode) == 0o644
        assert stat.S_IMODE(live_target.stat().st_mode) == 0o600
        assert stat.S_IMODE(state_directory.stat().st_mode) == 0o700
        assert stat.S_IMODE((state_directory / "claude.lock").stat().st_mode) == 0o600
        assert not (state_directory / "claude.journal.json").exists()
        backups = list((state_directory / "backups").glob("*.bak"))
        assert len(backups) == 1
        assert backups[0].read_bytes() == OLD_DOCUMENT
        assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600
        assert stat.S_IMODE(backups[0].parent.stat().st_mode) == 0o700
        assert not list(tmp_path.rglob("*.stage"))
        assert not list(tmp_path.glob("*.bak"))
        assert all(
            source.parent == destination.parent for source, destination in file_system.replacements
        )

    def test_all_candidates_are_validated_before_transaction_state_or_targets_are_written(
        self,
        tmp_path: Path,
    ) -> None:
        state_directory = tmp_path / "state"
        first_target = tmp_path / "first" / "settings.json"
        second_target = tmp_path / "second" / "settings.json"

        with pytest.raises(CandidateValidationError):
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(
                    FileWrite(first_target, NEW_DOCUMENT, None, validate_document),
                    FileWrite(second_target, b"invalid", None, validate_document),
                ),
            )

        assert not state_directory.exists()
        assert not first_target.parent.exists()
        assert not second_target.parent.exists()

    @pytest.mark.parametrize("mode", [0, 0o640, 0o777])
    def test_unsupported_mode_is_rejected_before_state_creation(
        self,
        tmp_path: Path,
        mode: int,
    ) -> None:
        state_directory = tmp_path / "state"
        target = tmp_path / "settings.json"

        with pytest.raises(TransactionDefinitionError):
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(FileWrite(target, NEW_DOCUMENT, None, validate_document, mode),),
            )

        assert not state_directory.exists()
        assert not target.exists()

    def test_expected_content_mismatch_fails_under_lock_before_journal_write(
        self,
        tmp_path: Path,
    ) -> None:
        state_directory = tmp_path / "state"
        target = tmp_path / "settings.json"
        target.write_bytes(OLD_DOCUMENT)

        with pytest.raises(ConcurrentModificationError):
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(FileWrite(target, NEW_DOCUMENT, NEW_DOCUMENT, validate_document),),
            )

        assert target.read_bytes() == OLD_DOCUMENT
        assert (state_directory / "claude.lock").exists()
        assert not (state_directory / "claude.journal.json").exists()
        assert not (state_directory / "backups").exists()

    def test_expectation_mismatch_fails_before_journal_write(self, tmp_path: Path) -> None:
        state_directory = tmp_path / "state"
        guarded = tmp_path / "guarded.json"
        target = tmp_path / "settings.json"
        guarded.write_bytes(NEW_DOCUMENT)

        with pytest.raises(ConcurrentModificationError):
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(FileWrite(target, NEW_DOCUMENT, None, validate_document),),
                expectations=(FileExpectation(guarded, OLD_DOCUMENT),),
            )

        assert not target.exists()
        assert not (state_directory / "claude.journal.json").exists()
        assert not (state_directory / "backups").exists()

    @pytest.mark.parametrize(
        "relative_target",
        [
            "claude.lock",
            "claude.journal.json",
            ".claude.journal.json.tmp",
            "backups/target.bak",
            ".base.deadbeef.stage",
        ],
    )
    def test_transaction_internal_targets_are_rejected(
        self,
        tmp_path: Path,
        relative_target: str,
    ) -> None:
        state_directory = tmp_path / "state"
        target = state_directory / relative_target

        with pytest.raises(TransactionDefinitionError):
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(FileWrite(target, NEW_DOCUMENT, None, validate_document),),
            )

        assert not state_directory.exists()

    @pytest.mark.parametrize(
        "file_system_type",
        [FailOnceBeforeReplaceFileSystem, CorruptingMultiFileReadBack],
    )
    def test_failure_rolls_back_every_target_and_cleans_stages(
        self,
        tmp_path: Path,
        file_system_type: type[FailOnceBeforeReplaceFileSystem | CorruptingMultiFileReadBack],
    ) -> None:
        state_directory = tmp_path / "state"
        first_target = tmp_path / "first.json"
        second_target = tmp_path / "second.json"
        first_target.write_bytes(OLD_DOCUMENT)
        second_target.write_bytes(OLD_DOCUMENT)
        first_target.chmod(0o640)
        second_target.chmod(0o600)
        file_system = file_system_type(second_target)

        with pytest.raises(MultiFileTransactionError) as caught:
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(
                    FileWrite(first_target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),
                    FileWrite(second_target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),
                ),
                file_system=file_system,
            )

        assert caught.value.rolled_back is True
        assert caught.value.rollback_errors == ()
        assert first_target.read_bytes() == OLD_DOCUMENT
        assert second_target.read_bytes() == OLD_DOCUMENT
        assert stat.S_IMODE(first_target.stat().st_mode) == 0o640
        assert stat.S_IMODE(second_target.stat().st_mode) == 0o600
        assert len(list((state_directory / "backups").glob("*.bak"))) == 2
        assert not (state_directory / "claude.journal.json").exists()
        assert not list(tmp_path.glob(".*.stage"))
        assert not list(state_directory.glob("*.tmp"))

    def test_unfinished_installing_journal_is_private_value_free_and_recovered(
        self,
        tmp_path: Path,
    ) -> None:
        state_directory = tmp_path / "state"
        first_target = tmp_path / "first.json"
        second_target = tmp_path / "second.json"
        first_target.write_bytes(OLD_DOCUMENT)
        second_target.write_bytes(OLD_DOCUMENT)
        first_target.chmod(0o640)

        with pytest.raises(SimulatedCrash):
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(
                    FileWrite(first_target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),
                    FileWrite(second_target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),
                ),
                file_system=CrashAfterTargetReplaceFileSystem(first_target),
            )

        journal_path = state_directory / "claude.journal.json"
        journal = journal_path.read_bytes()
        parsed = json.loads(journal)
        assert parsed["status"] == "installing"
        assert OLD_DOCUMENT.strip() not in journal
        assert NEW_DOCUMENT.strip() not in journal
        assert stat.S_IMODE(journal_path.stat().st_mode) == 0o600
        stages = list(tmp_path.glob(".*.stage"))
        assert len(stages) == 1
        assert stat.S_IMODE(stages[0].stat().st_mode) == 0o600
        assert first_target.read_bytes() == NEW_DOCUMENT
        assert second_target.read_bytes() == OLD_DOCUMENT

        recovered = write_validated_files(
            engine="claude",
            state_directory=state_directory,
            writes=(),
        )

        assert recovered.recovered is True
        assert recovered.changed is False
        assert recovered.files == ()
        assert first_target.read_bytes() == OLD_DOCUMENT
        assert second_target.read_bytes() == OLD_DOCUMENT
        assert stat.S_IMODE(first_target.stat().st_mode) == 0o640
        assert not journal_path.exists()
        assert not list(tmp_path.glob(".*.stage"))

    def test_failure_removes_a_new_target_and_restores_an_existing_target(
        self,
        tmp_path: Path,
    ) -> None:
        state_directory = tmp_path / "state"
        new_target = tmp_path / "new.json"
        existing_target = tmp_path / "existing.json"
        existing_target.write_bytes(OLD_DOCUMENT)

        with pytest.raises(MultiFileTransactionError) as caught:
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(
                    FileWrite(new_target, NEW_DOCUMENT, None, validate_document),
                    FileWrite(existing_target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),
                ),
                file_system=FailOnceBeforeReplaceFileSystem(existing_target),
            )

        assert caught.value.rolled_back is True
        assert not new_target.exists()
        assert existing_target.read_bytes() == OLD_DOCUMENT
        assert len(list((state_directory / "backups").glob("*.bak"))) == 1
        assert not (state_directory / "claude.journal.json").exists()

    def test_committed_journal_recovery_keeps_installed_content(self, tmp_path: Path) -> None:
        state_directory = tmp_path / "state"
        target = tmp_path / "settings.json"
        target.write_bytes(OLD_DOCUMENT)
        journal_path = state_directory / "claude.journal.json"

        with pytest.raises(SimulatedCrash):
            write_validated_files(
                engine="claude",
                state_directory=state_directory,
                writes=(FileWrite(target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),),
                file_system=CrashAfterCommitMarkerFileSystem(journal_path),
            )

        assert target.read_bytes() == NEW_DOCUMENT
        assert json.loads(journal_path.read_bytes())["status"] == "committed"

        recovered = write_validated_files(
            engine="claude",
            state_directory=state_directory,
            writes=(),
        )

        assert recovered.recovered is True
        assert target.read_bytes() == NEW_DOCUMENT
        assert not journal_path.exists()

    def test_non_blocking_engine_lock_reports_contention(self, tmp_path: Path) -> None:
        state_directory = tmp_path / "state"
        state_directory.mkdir(mode=0o700)
        lock_path = state_directory / "claude.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(TransactionLockError):
                write_validated_files(
                    engine="claude",
                    state_directory=state_directory,
                    writes=(),
                    wait_for_lock=False,
                )
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def test_backup_slot_is_reused_for_each_target(self, tmp_path: Path) -> None:
        state_directory = tmp_path / "state"
        target = tmp_path / "settings.json"
        target.write_bytes(OLD_DOCUMENT)

        first = write_validated_files(
            engine="claude",
            state_directory=state_directory,
            writes=(FileWrite(target, NEW_DOCUMENT, OLD_DOCUMENT, validate_document),),
        )
        second = write_validated_files(
            engine="claude",
            state_directory=state_directory,
            writes=(FileWrite(target, OLD_DOCUMENT, NEW_DOCUMENT, validate_document),),
        )

        backup_path = first.files[0].backup_path
        assert backup_path is not None
        assert second.files[0].backup_path == backup_path
        assert backup_path.read_bytes() == NEW_DOCUMENT
        assert list((state_directory / "backups").glob("*.bak")) == [backup_path]
