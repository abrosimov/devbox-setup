fish_add_path -g -p /opt/homebrew/bin 
fish_add_path -g -p $GOROOT/bin
fish_add_path -g -a $GOPATH/bin
fish_add_path -g -a $FLUTTER_PATH/bin
fish_add_path -g -a $HOME/.local/bin
fish_add_path -g -a $HOME/bin
fish_add_path -g -a $GEM_HOME/bin

if test -d $HOME/.cargo
  fish_add_path -g -a $HOME/.cargo/bin
end
