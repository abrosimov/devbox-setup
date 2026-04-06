function klocal-use --description "Point klocal and mlops-be at a specific installer worktree's kubeconfig"
    set -l symlink ~/.kube/localcluster.yaml
    set -l target
    set -l installer_root

    if test (count $argv) -eq 0
        # No args: show current state
        if test -L $symlink
            set -l real (realpath $symlink)
            echo "klocal    → $real"
            # Derive installer root from kubeconfig path (strip /install/cluster-kubeconfig.yaml)
            set -l root (string replace '/install/cluster-kubeconfig.yaml' '' $real)
            if test -d "$root"
                echo "installer → $root"
            end
        else if test -e $symlink
            echo "klocal: $symlink (not a symlink)"
        else
            echo "Not configured. Run from an installer worktree:"
            echo "  klocal-use ."
            echo "  klocal-use /path/to/oi-platform-installer/<branch>"
        end
        return 0
    end

    set -l arg $argv[1]

    switch $arg
        case .
            set installer_root (pwd)
            set target $installer_root/install/cluster-kubeconfig.yaml
        case '*'
            if test -d "$arg"
                set installer_root $arg
                set target $arg/install/cluster-kubeconfig.yaml
            else if test -f "$arg"
                set target $arg
            else
                echo "klocal-use: not a file or directory: $arg"
                return 1
            end
    end

    if not test -f "$target"
        echo "klocal-use: kubeconfig not found: $target"
        return 1
    end

    set target (realpath $target)
    test -n "$installer_root"; and set installer_root (realpath $installer_root)

    # Update kubeconfig symlink
    ln -sfn $target $symlink
    echo "klocal    → $target"

    # Update OI_PLATFORM_INSTALLER_ROOT in mlops-be .env files (all worktrees)
    if test -n "$installer_root"
        set -l mlops_project ~/Work/mlops-be
        if test -d $mlops_project
            for envfile in $mlops_project/*/.env
                if test -f $envfile
                    if grep -q '^OI_PLATFORM_INSTALLER_ROOT=' $envfile
                        sed -i '' "s|^OI_PLATFORM_INSTALLER_ROOT=.*|OI_PLATFORM_INSTALLER_ROOT=$installer_root|" $envfile
                        echo "updated   → $envfile"
                    end
                end
            end
        end
    end
end
