# wedding_music

Небольшой pet-project для сбора музыкальных заявок на свадьбу.

Стек:

- Django + Django REST Framework
- Vue 3 + Vite
- PostgreSQL через `DATABASE_URL`
- Django admin для просмотра, модерации и CSV export

## Возможности

- гости отправляют имя, трек, исполнителя, ссылку, момент и комментарий;
- заявка не принимается, если нет ни названия трека, ни ссылки;
- новые заявки по умолчанию ждут модерации;
- публичный список показывает только одобренные треки;
- отдельная страница `/dj` без авторизации показывает DJ, что включать;
- staff-пользователи входят на Vue-странице модерации и одобряют треки;
- форма умеет пробовать определить название и исполнителя по ссылке;
- Django admin тоже умеет быстро менять `approved` и экспортировать CSV;
- API export доступен staff-пользователям по `/api/songs/export/`;
- добавление можно закрыть секретным токеном `SONG_REQUEST_SECRET`.

## Быстрый старт

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres
```

Если PostgreSQL не нужен для локальной пробы, не задавайте `DATABASE_URL`: Django использует SQLite.

Backend:

```bash
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py createsuperuser
../.venv/bin/python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Форма будет доступна на `http://localhost:5173`.

Если задан `SONG_REQUEST_SECRET`, раздавайте гостям ссылку вида:

```text
http://127.0.0.1:5173/?secret=secret-link-token
```

Для Vue-экрана модерации откройте:

```text
http://127.0.0.1:5173/admin-list
```

Войти можно прямо на этой странице логином staff/superuser-пользователя.

Для DJ выдайте отдельную ссылку:

```text
http://127.0.0.1:5173/dj
```

Она не требует авторизации и не показывается в навигации гостевого сайта.

## API

- `GET /api/songs/moments/` - варианты момента
- `POST /api/songs/` - создать заявку
- `POST /api/songs/preview-link/` - определить название и исполнителя по ссылке
- `GET /api/songs/public/` - публичный список одобренных треков
- `GET /api/songs/` - все заявки, staff only
- `PATCH /api/songs/{id}/approve/` - модерация, staff only
- `GET /api/songs/export/` - CSV export, staff only
- `GET /api/auth/me/` - текущий пользователь
- `POST /api/auth/login/` - вход staff-пользователя
- `POST /api/auth/logout/` - выход

## Запуск на сервере в Docker

Самый простой запуск:

```bash
./scripts/deploy.sh up
```

Скрипт при первом запуске создаст `.env.server`, сгенерирует секреты, соберёт контейнеры, применит миграции, соберёт static files и создаст суперпользователя.

В production compose внешний вход один: сервис `nginx`. Он отдаёт Vue-приложение и проксирует `/api/`, `/admin/`, `/static/` в Django backend. PostgreSQL и backend наружу не публикуются.

В конце запуска будет выведено:

```text
Public URL: ...
Admin URL:  ...
Admin user: ...
Admin pass: ...
```

Эти же данные пишутся в лог backend-контейнера при создании пользователя:

```bash
./scripts/deploy.sh logs backend
```

Админка доступна по `/admin/`. Сменить пароль можно штатно в Django admin: `Users` → нужный пользователь → `Password`.

Если пользователь уже существует, пароль при рестарте не сбрасывается, чтобы смена пароля в админке не терялась. Для принудительного сброса пароля из `.env.server` выставьте:

```env
DJANGO_SUPERUSER_FORCE_PASSWORD=1
```

и выполните:

```bash
./scripts/deploy.sh restart
```

После успешного сброса верните `DJANGO_SUPERUSER_FORCE_PASSWORD=0`.

### Настройка домена и портов

Перед запуском можно отредактировать `.env.server`. Если файла ещё нет:

```bash
cp .env.server.example .env.server
```

Основные параметры:

```env
APP_DOMAIN=music.example.com
APP_HOST=0.0.0.0
APP_HTTP_PORT=80
APP_HTTPS_PORT=443
BACKEND_PORT=8000
PUBLIC_URL=https://music.example.com
ENABLE_HTTPS=1
LETSENCRYPT_EMAIL=you@example.com

DJANGO_ALLOWED_HOSTS=music.example.com,127.0.0.1,localhost,backend
CSRF_TRUSTED_ORIGINS=https://music.example.com
CORS_ALLOWED_ORIGINS=https://music.example.com
```

Если на сервере уже есть внешний nginx/caddy/traefik, встроенный nginx приложения можно оставить на локальном HTTP-порту:

```env
APP_HOST=127.0.0.1
APP_HTTP_PORT=18080
APP_HTTPS_PORT=18443
ENABLE_HTTPS=0
PUBLIC_URL=https://music.example.com
```

и внешний reverse proxy направляет трафик на `http://127.0.0.1:18080`.

`APP_HTTP_PORT` и `APP_HTTPS_PORT` - внешние порты nginx-контейнера. Для обычного сервера ставьте `80` и `443`. `BACKEND_PORT` - внутренний порт Django/gunicorn внутри docker-сети, обычно его менять не нужно. PostgreSQL в `docker-compose.prod.yml` не публикует порт на хост и доступен только контейнерам этого приложения во внутренней сети Docker. Поэтому он не мешает установленному на сервере PostgreSQL или другим compose-проектам.

### HTTPS и сертификат

Автоматическая выдача нормального браузерного сертификата работает через Let's Encrypt. Для этого нужны условия:

- `APP_DOMAIN` - реальный домен, не `localhost`;
- DNS A/AAAA-запись домена указывает на сервер;
- порты `80` и `443` открыты снаружи;
- в `.env.server` указан настоящий `LETSENCRYPT_EMAIL`;
- `PUBLIC_URL`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` используют `https://...`.

После настройки `.env.server` достаточно:

```bash
./scripts/deploy.sh up
```

Если `ENABLE_HTTPS=1`, скрипт сначала поднимет nginx в HTTP-режиме для ACME challenge, выпустит сертификат через certbot, затем переключит nginx на HTTPS и редирект с HTTP на HTTPS.

Для ручного выпуска или перевыпуска сертификата:

```bash
./scripts/deploy.sh cert
```

Для renew можно поставить cron:

```cron
0 4 * * * cd /path/to/wedding_music && ./scripts/deploy.sh renew
```

Для локального dev-only PostgreSQL из `docker-compose.yml` порт вынесен в переменную:

```bash
POSTGRES_PORT=55433 docker compose up -d postgres
```

### Управление

```bash
./scripts/deploy.sh up       # собрать и запустить
./scripts/deploy.sh restart  # пересобрать и перезапустить
./scripts/deploy.sh logs     # смотреть все логи
./scripts/deploy.sh logs nginx
./scripts/deploy.sh cert     # выпустить сертификат и включить HTTPS
./scripts/deploy.sh renew    # обновить сертификат
./scripts/deploy.sh down     # остановить
```
