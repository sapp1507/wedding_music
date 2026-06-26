#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE="$ROOT_DIR/.env.server"
EXAMPLE_FILE="$ROOT_DIR/.env.server.example"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
NGINX_GENERATED_DIR="$ROOT_DIR/docker/nginx/generated"
NGINX_CONFIG="$NGINX_GENERATED_DIR/default.conf"

random_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32 | tr -d '\n'
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

append_env_value_if_missing() {
    key="$1"
    value="$2"
    if ! grep -q "^${key}=" "$ENV_FILE"; then
        printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    fi
}

env_value() {
    key="$1"
    default="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        grep "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2-
    else
        printf '%s' "$default"
    fi
}

render_nginx_config() {
    mode="$1"
    app_domain=$(env_value APP_DOMAIN localhost)
    backend_port=$(env_value BACKEND_PORT 8000)

    mkdir -p "$NGINX_GENERATED_DIR"
    if [ "$mode" = "https" ]; then
        template="$ROOT_DIR/docker/nginx/https.conf.template"
    else
        template="$ROOT_DIR/docker/nginx/http.conf.template"
    fi

    sed \
        -e "s/__APP_DOMAIN__/${app_domain}/g" \
        -e "s/__BACKEND_PORT__/${backend_port}/g" \
        "$template" > "$NGINX_CONFIG"
}

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

issue_certificate() {
    app_domain=$(env_value APP_DOMAIN localhost)
    email=$(env_value LETSENCRYPT_EMAIL "")

    if [ "$app_domain" = "localhost" ] || [ "$app_domain" = "127.0.0.1" ]; then
        echo "ENABLE_HTTPS=1 requires a real public domain in APP_DOMAIN."
        exit 1
    fi
    if [ -z "$email" ] || [ "$email" = "admin@example.com" ]; then
        echo "Set LETSENCRYPT_EMAIL in .env.server before enabling HTTPS."
        exit 1
    fi

    staging_flag=""
    if [ "$(env_value LETSENCRYPT_STAGING 0)" = "1" ]; then
        staging_flag="--staging"
    fi

    if compose run --rm --entrypoint sh certbot -c "test -f /etc/letsencrypt/live/$app_domain/fullchain.pem"; then
        echo "Certificate for $app_domain already exists."
        return
    fi

    compose run --rm certbot certonly \
        --webroot \
        -w /var/www/certbot \
        -d "$app_domain" \
        --email "$email" \
        --agree-tos \
        --no-eff-email \
        $staging_flag
}

renew_certificate() {
    compose run --rm certbot renew --webroot -w /var/www/certbot
    compose exec nginx nginx -s reload || true
}

if [ ! -f "$ENV_FILE" ]; then
    cp "$EXAMPLE_FILE" "$ENV_FILE"
    replace_env_value DJANGO_SECRET_KEY "$(random_secret)"
    replace_env_value SONG_REQUEST_SECRET "$(random_secret)"
    replace_env_value DJANGO_SUPERUSER_PASSWORD "$(random_secret)"
    replace_env_value POSTGRES_PASSWORD "$(random_secret)"
    echo "Created .env.server with generated secrets."
fi

append_env_value_if_missing APP_HTTP_PORT "$(env_value APP_PORT 80)"
append_env_value_if_missing APP_HTTPS_PORT "443"
append_env_value_if_missing ENABLE_HTTPS "0"
append_env_value_if_missing LETSENCRYPT_EMAIL "admin@example.com"
append_env_value_if_missing GUNICORN_WORKERS "1"

COMMAND="${1:-up}"

case "$COMMAND" in
    up)
        render_nginx_config http
        compose up -d --build --remove-orphans postgres backend nginx
        if [ "$(env_value ENABLE_HTTPS 0)" = "1" ]; then
            issue_certificate
            render_nginx_config https
            compose up -d --build --remove-orphans nginx
        fi
        ;;
    down)
        compose down --remove-orphans
        ;;
    logs)
        if [ "${2:-}" ]; then
            compose logs -f "$2"
        else
            compose logs -f
        fi
        ;;
    restart)
        render_nginx_config http
        compose up -d --build --remove-orphans postgres backend nginx
        if [ "$(env_value ENABLE_HTTPS 0)" = "1" ]; then
            issue_certificate
            render_nginx_config https
            compose up -d --build --remove-orphans nginx
        fi
        ;;
    cert)
        render_nginx_config http
        compose up -d --build --remove-orphans postgres backend nginx
        issue_certificate
        render_nginx_config https
        compose up -d --build --remove-orphans nginx
        ;;
    renew)
        renew_certificate
        ;;
    *)
        echo "Usage: ./scripts/deploy.sh [up|down|logs|restart|cert|renew]"
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
    echo "Nginx service: nginx"
    echo "Use './scripts/deploy.sh logs backend' to watch migrations and admin creation."
    echo "Use './scripts/deploy.sh logs nginx' to watch the public reverse proxy."
fi
