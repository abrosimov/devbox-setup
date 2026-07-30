# Completions for otelbox (telemetry SSH tunnel + browser UIs)
complete -c otelbox -f

complete -c otelbox -n __fish_use_subcommand -a up -d 'Open the tunnel, then both UIs'
complete -c otelbox -n __fish_use_subcommand -a down -d 'Close the tunnel'
complete -c otelbox -n __fish_use_subcommand -a status -d 'Tunnel and forwarded-port state'
complete -c otelbox -n __fish_use_subcommand -a signoz -d 'Ensure the tunnel, open SigNoz only'
complete -c otelbox -n __fish_use_subcommand -a clickstack -d 'Ensure the tunnel, open ClickStack only'
complete -c otelbox -n __fish_use_subcommand -a help -d 'Show usage'

complete -c otelbox -n '__fish_seen_subcommand_from up' -l no-open -d 'Open the tunnel, print the URLs instead of launching a browser'
