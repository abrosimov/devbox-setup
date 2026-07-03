abbr -a co git checkout
abbr -a st git status
abbr -a gd git diff
abbr -a am git commit --amend
abbr -a br git branch

abbr -a cob git checkout -b
abbr -a add git add
abbr -a gdc git diff --cached

# Safer branch switching: `sw` refuses to detach HEAD unless given --detach,
# so `sw <sha>` errors instead of silently detaching (unlike `co <sha>`).
# `restore` splits the file-restore half out of the overloaded `checkout`.
abbr -a sw git switch
abbr -a swc git switch -c
abbr -a restore git restore

# Branchless: current branch, same name on origin. push.autoSetupRemote sets the
# upstream on first push; pull.ff=only stops loudly instead of a surprise merge.
abbr -a pull git pull
abbr -a push git push

abbr -a merge git merge

abbr -a gl git log
abbr -a glp git log -p

abbr -a code claude --model claude-opus-4-5
abbr -a code_smart claude --model claude-opus-4-6

abbr -a code_continue claude --model claude-opus-4-5
abbr -a code_smart_continue claude --model claude-opus-4-6

abbr -a vi nvim
abbr -a vim nvim
abbr -a vimdiff nvim -d
abbr -a vd nvim -d

abbr -a dc docker compose
abbr -a -- - "cd -"

abbr -a kss kitty-save-session

abbr -a g gcx

abbr -a stash git stash # TODO: In the video on YT there was a nice hack for git stash.

abbr -a --set-cursor gg "git grep -n '%'"
abbr -a --set-cursor ci "git commit -m '%'"
