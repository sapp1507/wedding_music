#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE="$ROOT_DIR/.env.server"
EXAMPLE_FILE="$ROOT_DIR/.env.server.example"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"

random_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 36 | tr -d '\n'
    else
        date +%s%N | sha256sum | cut -d ' ' -f 1
    fi
}

replace_env_value() {
    key="$1"
    value="$2"
    escaped_value=$(printf '%s\n' "$value" | sed 's/[\/&]/\\&/g')
    sed -i "s/^${key}=.*/${key}=${escaped_value}/" "$ENV_FILE"
}

if [ ! -f "$ENV_FILE" ]; then
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    replace_env_value DJANGO_SECRET_KEY "$(random_secret)"
    replace_env_value SONG_REQUEST_SECRET "$(random_secret)"
    replace_env_value DJANGO_SUPERUSER_PASSWORD "$(random_secret)"
    replace_env_value POSTGRES_PASSWORD "$(random_secret)"
    echo "Created .env.server with generated secrets."
fi

COMMAND="${1:-up}"

case "$COMMAND" in
    up)
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
        ;;
    down)
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
        ;;
    logs)
        if [ "${2:-}" ]; then
            docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f "$2"
        else
            docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f
        fi
        ;;
    restart)
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
        ;;
    *)
        echo "Usage: ./scripts/deploy.sh [up|down|logs|restart]"
        exit 1
        ;;
esac

ADMIN_URL=$(grep '^PUBLIC_URL=' "$ENV_FILE" | cut -d '=' -f 2-)/admin/
ADMIN_USERNAME=$(grep '^DJANGO_SUPERUSER_USERNAME=' "$ENV_FILE" | cut -d '=' -f 2-)
ADMIN_PASSWORD=$(grep '^DJANGO_SUPERUSER_PASSWORD=' "$ENV_FILE" | cut -d '=' -f 2-)

if [ "$COMMAND" = "up" ] || [ "$COMMAND" = "restart" ]; then
    echo ""
    echo "Application is starting."
    echo "Public URL: $(grep '^PUBLIC_URL=' "$ENV_FILE" | cut -d '=' -f 2-)"
    echo "Admin URL:  $ADMIN_URL"
    echo "Admin user: $ADMIN_USERNAME"
    echo "Admin pass: $ADMIN_PASSWORD"
    echo ""
    echo "Use './scripts/deploy.sh logs backend' to watch migrations and admin creation."
fi
