function agy --wraps agy
    set -l profile $MNEMOSYNE_PERISTASEOS
    if test -z "$profile"
        set profile "default"
    end
    # LANGFUSE_USER_ID is quoted below: unquoted, an unset variable expands to
    # nothing and the assignment vanishes from argv, shifting `command` along.
    #
    # CC_LANGFUSE_TRACE_TAGS carries the engine identity. The vendored hook is
    # shared with Claude Code and hardcodes the "claude-code" tag regardless of
    # who invoked it, so without this tag agy and Claude Code traces are
    # indistinguishable in Langfuse.
    env \
        OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
        OTEL_SERVICE_NAME=agy-$profile \
        OTEL_RESOURCE_ATTRIBUTES=otelbox.telemetry.class=llm \
        CC_LANGFUSE_BASE_URL=http://127.0.0.1:14318 \
        CC_LANGFUSE_PUBLIC_KEY=otelbox-local-public \
        CC_LANGFUSE_SECRET_KEY=otelbox-local-secret \
        CC_LANGFUSE_CAPTURE_IMAGES=false \
        CC_LANGFUSE_STATE_DIR=$HOME/.gemini/antigravity-cli/state \
        CC_LANGFUSE_TRACE_TAGS='["engine:agy"]' \
        LANGFUSE_TRACING_ENVIRONMENT=$profile \
        LANGFUSE_USER_ID="$LANGFUSE_USER_ID" \
        command agy $argv
end
