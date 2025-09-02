function fish_title
    set current_dir (pwd)
    if test "$current_dir" = "$HOME"
        echo "~"
    else
        basename "$current_dir"
    end
end
