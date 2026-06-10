function __proj_current_project
    set -q AION_AUTOPOIESEON; or return 1
    set -l rel (string replace "$AION_AUTOPOIESEON/" '' -- $PWD)
    test "$rel" = "$PWD"; and return 1
    set -l project (string split '/' -- $rel)[1]
    echo "$project"
end
