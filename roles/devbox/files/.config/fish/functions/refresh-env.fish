function refresh-env --description 'Re-load env + PATH from conf.d/_init_*.fish without restarting fish'
    for f in $__fish_config_dir/conf.d/_init_*.fish
        test -r $f; and source $f
    end
    echo "refreshed: MNEMOSYNE_PERISTASEOS=$MNEMOSYNE_PERISTASEOS  AION_AUTOPOIESEON=$AION_AUTOPOIESEON"
end
