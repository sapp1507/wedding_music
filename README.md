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
- Django admin умеет быстро менять `approved` и экспортировать CSV;
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

Перед этим нужно войти в Django admin на `http://127.0.0.1:8000/admin/`, потому что API модерации использует session auth.

## API

- `GET /api/songs/moments/` - варианты момента
- `POST /api/songs/` - создать заявку
- `GET /api/songs/public/` - публичный список одобренных треков
- `GET /api/songs/` - все заявки, staff only
- `PATCH /api/songs/{id}/approve/` - модерация, staff only
- `GET /api/songs/export/` - CSV export, staff only
