set -gx EDITOR vim 
set -gx GOPATH $HOME/go
set -gx GOROOT /usr/local/go
set -gx FLUTTER_PATH $HOME/flutter
set -gx GEM_HOME $HOME/.programming/ruby/gems

if test -d /opt/homebrew
  /opt/homebrew/bin/brew shellenv | source
end
