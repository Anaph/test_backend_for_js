# FastAPI MJPEG-over-WebSocket backend + frontend

Тестовый проект для JS-разработчика:
- backend на FastAPI выдаёт JWT и стримит MJPEG-кадры в WebSocket;
- frontend написан на чистом HTML/CSS/TypeScript;
- сайт раздаётся самим Python backend на **том же порте**.

## Backend + Frontend запуск (один процесс, один порт)

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

## Как это устроено

- Python раздаёт папку `frontend/site` как статический сайт.
- API и WebSocket работают в том же приложении FastAPI.
- Если существует `VIDEO_FILE` (по умолчанию `assets/big_buck_bunny.mp4`), используется зацикленное видео.
- Иначе синтетика: на белом фоне движутся случайные геометрические фигуры со случайным цветом/размером/скоростью.

## Frontend source (TypeScript)

Исходники лежат в `frontend/src/main.ts`.
Проверка типов:

```bash
cd frontend
npm install
npm run typecheck
```

## Переменные окружения backend
Смотрите `.env.example`.
