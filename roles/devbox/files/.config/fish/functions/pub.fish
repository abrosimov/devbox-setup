function pub --description "Thirty-minute sliding WARP traffic-only lease with a twelve-hour cap"
    if not command -q pub-lease
        echo "pub: unavailable; Cloudflare WARP is not configured for this profile" >&2
        return 127
    end
    command pub-lease $argv
end
