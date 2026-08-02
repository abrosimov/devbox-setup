function agy --wraps agy
    set -l profile $MNEMOSYNE_PERISTASEOS
    if test -z "$profile"
        set profile "default"
    end
    env OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 OTEL_SERVICE_NAME=agy-$profile command agy $argv
end
