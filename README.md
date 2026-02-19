# FastAPI MJPEG-over-WebSocket backend + frontend

Тестовый проект для JS-разработчика:
- backend на FastAPI выдаёт JWT и стримит MJPEG-кадры в WebSocket;
- frontend на чистом HTML/CSS/TypeScript показывает поток в `<canvas>`;
- сборка фронта: **Vite** (компактно и современно).

## Backend

### Функционал
- `POST /auth/token` — выдача JWT;
- `WS /stream/ws?token=<JWT>` — MJPEG поток (каждый WS binary message = JPEG-кадр);
- если есть `VIDEO_FILE`, используется зацикленное видео;
- иначе синтетика: на белом фоне движутся случайные геометрические фигуры со случайным цветом/размером/скоростью.

### Запуск
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Frontend (чистый HTML+CSS+TypeScript)

### Запуск в dev-режиме
```bash
cd frontend
npm install
npm run dev
```

Проверка типов:
```bash
npm run typecheck
```

Vite поднимет фронт на `http://127.0.0.1:5173` и проксирует `/auth` и `/stream` на backend `:8000`.

### Использование
1. Нажмите «Получить JWT».
2. Нажмите «Подключиться к стриму».
3. MJPEG-кадры будут отображаться в `<canvas>`.

## Переменные окружения backend
Смотрите `.env.example`.
