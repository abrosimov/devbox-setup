# Completions for claude-fix-perms (permissions injector)
complete -c claude-fix-perms -f

complete -c claude-fix-perms -l with-git -d 'Add git write permissions'
complete -c claude-fix-perms -l go -d 'Add Go toolchain permissions'
complete -c claude-fix-perms -l python -d 'Add Python toolchain permissions'
complete -c claude-fix-perms -l node -d 'Add Node toolchain permissions'
complete -c claude-fix-perms -l all -d 'Shortcut for --go --python --node'
complete -c claude-fix-perms -l no-detect -d 'Skip auto-detection'
