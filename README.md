# FastAPI MJPEG-over-WebSocket backend + frontend

Тестовый проект для JS-разработчика:
- backend на FastAPI выдаёт JWT и стримит MJPEG-кадры в WebSocket;
- frontend написан на чистом HTML/CSS/TypeScript;
- Python раздаёт собранный frontend из папки `./sites` на том же порте.

## Сборка фронтенда (TS -> ./sites)

```bash
cd frontend
npm install
npm run build
```

После сборки статический сайт будет в `./sites` (в корне проекта).

## Запуск backend + frontend (один порт)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

После запуска:
- UI: `http://127.0.0.1:8000/`
- health: `http://127.0.0.1:8000/health`
- token API: `POST http://127.0.0.1:8000/auth/token`
- stream WS: `ws://127.0.0.1:8000/stream/ws?token=<JWT>`

## Frontend source (TypeScript)

Исходники лежат в `frontend/src/main.ts`.
Проверка типов:

```bash
cd frontend
npm run typecheck
```

## Переменные окружения backend
Смотрите `.env.example`.
