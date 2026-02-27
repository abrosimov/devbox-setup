# Completions for proj function
complete -c proj -f

# Subcommands
complete -c proj -n '__fish_use_subcommand' -a clone -d 'Bare-clone a repo'
complete -c proj -n '__fish_use_subcommand' -a ls -d 'List projects'

# Project names as cd shortcuts
complete -c proj -n '__fish_use_subcommand' -a '(set -q PROJECTS_DIR; and test -d "$PROJECTS_DIR"; and for d in $PROJECTS_DIR/*/; basename $d; end)'
