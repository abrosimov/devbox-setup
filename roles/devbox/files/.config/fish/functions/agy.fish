function agy --wraps agy
    set -l profile $MNEMOSYNE_PERISTASEOS
    if test -z "$profile"
        set profile "default"
    end
    env \
        OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
        OTEL_SERVICE_NAME=agy-$profile \
        CC_LANGFUSE_BASE_URL=http://127.0.0.1:14318 \
        CC_LANGFUSE_PUBLIC_KEY=otelbox-local-public \
        CC_LANGFUSE_SECRET_KEY=otelbox-local-secret \
        CC_LANGFUSE_CAPTURE_IMAGES=false \
        CC_LANGFUSE_STATE_DIR=$HOME/.gemini/antigravity-cli/state \
        LANGFUSE_TRACING_ENVIRONMENT=$profile \
        command agy $argv
end
