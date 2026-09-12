set shell := ["bash", "-uc"]

## Typical flow: just otel-up → use Claude Code → just otel-parse → just otel-costs → just otel-down.

# List all
default:
    @just --list

# Start the OTel collector (docker compose, detached)
[group('otel')]
otel-up:
    docker compose -f otel/docker-compose.yml up -d

# Stop and remove the OTel collector
[group('otel')]
otel-down:
    docker compose -f otel/docker-compose.yml down

# Restart the OTel collector
[group('otel')]
otel-restart: otel-down otel-up

# Show OTel collector container status
[group('otel')]
otel-status:
    docker compose -f otel/docker-compose.yml ps

# Follow the OTel collector's logs
[group('otel')]
otel-logs:
    docker compose -f otel/docker-compose.yml logs -f

# Validate the collector config without starting it
[group('otel')]
otel-check:
    docker compose -f otel/docker-compose.yml config -q

# Parse captured logs into per-prompt token/cost aggregates
[group('otel')]
otel-parse *ARGS:
    python3 otel/parse_prompt_costs.py {{ARGS}}

# Print the last parsed per-prompt cost summary
[group('otel')]
otel-costs:
    cat otel/output/prompt_costs.json

# Delete captured telemetry output (logs, metrics, parsed costs)
[group('otel')]
otel-clean:
    rm -f otel/output/otel-logs.jsonl otel/output/otel-metrics.jsonl otel/output/prompt_costs.json
