from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator, Literal

import cv2
import jwt
import numpy as np
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
STREAM_FPS = float(os.getenv("STREAM_FPS", "24"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))
VIDEO_FILE = os.getenv("VIDEO_FILE", "assets/big_buck_bunny.mp4")
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "1280"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", "720"))
SYNTHETIC_SHAPES_COUNT = int(os.getenv("SYNTHETIC_SHAPES_COUNT", "12"))
SHAPE_MIN_SIZE = int(os.getenv("SHAPE_MIN_SIZE", "25"))
SHAPE_MAX_SIZE = int(os.getenv("SHAPE_MAX_SIZE", "120"))
SHAPE_MIN_SPEED = float(os.getenv("SHAPE_MIN_SPEED", "2.0"))
SHAPE_MAX_SPEED = float(os.getenv("SHAPE_MAX_SPEED", "8.0"))


SITE_DIR = Path("sites")


class TokenRequest(BaseModel):
    user_id: str = "js-test"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    websocket_url: str
    codec: str = "mjpeg"


@dataclass
class MovingShape:
    kind: Literal["circle", "rectangle", "triangle"]
    x: float
    y: float
    vx: float
    vy: float
    size: int
    color: tuple[int, int, int]


def create_access_token(user_id: str) -> tuple[str, int]:
    expires_at_dt = datetime.now(tz=timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    expires_at = int(expires_at_dt.timestamp())
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": expires_at,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _encode_mjpeg(frame: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
    )
    if not ok:
        raise RuntimeError("Failed to encode frame to MJPEG")
    return encoded.tobytes()


def _rand_velocity(rng: np.random.Generator) -> tuple[float, float]:
    speed = float(rng.uniform(SHAPE_MIN_SPEED, SHAPE_MAX_SPEED))
    angle = float(rng.uniform(0, 2 * np.pi))
    return speed * float(np.cos(angle)), speed * float(np.sin(angle))


def _make_random_shapes(rng: np.random.Generator) -> list[MovingShape]:
    min_size = min(SHAPE_MIN_SIZE, SHAPE_MAX_SIZE)
    max_size = max(SHAPE_MIN_SIZE, SHAPE_MAX_SIZE)
    shapes: list[MovingShape] = []

    for _ in range(max(1, SYNTHETIC_SHAPES_COUNT)):
        size = int(rng.integers(min_size, max_size + 1))
        x = float(rng.uniform(size, max(size + 1, FRAME_WIDTH - size)))
        y = float(rng.uniform(size, max(size + 1, FRAME_HEIGHT - size)))
        vx, vy = _rand_velocity(rng)
        color = (
            int(rng.integers(0, 256)),
            int(rng.integers(0, 256)),
            int(rng.integers(0, 256)),
        )
        kind = rng.choice(np.array(["circle", "rectangle", "triangle"]))
        shapes.append(MovingShape(kind=kind, x=x, y=y, vx=vx, vy=vy, size=size, color=color))

    return shapes


def _draw_shape(canvas: np.ndarray, shape: MovingShape) -> None:
    cx, cy, s, color = int(shape.x), int(shape.y), shape.size, shape.color

    if shape.kind == "circle":
        cv2.circle(canvas, (cx, cy), s, color, -1)
    elif shape.kind == "rectangle":
        cv2.rectangle(canvas, (cx - s, cy - s), (cx + s, cy + s), color, -1)
    else:
        pts = np.array(
            [
                [cx, cy - s],
                [cx - s, cy + s],
                [cx + s, cy + s],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(canvas, [pts], color)


def _move_shape(shape: MovingShape) -> None:
    shape.x += shape.vx
    shape.y += shape.vy

    if shape.x - shape.size < 0:
        shape.x = shape.size
        shape.vx *= -1
    elif shape.x + shape.size > FRAME_WIDTH:
        shape.x = FRAME_WIDTH - shape.size
        shape.vx *= -1

    if shape.y - shape.size < 0:
        shape.y = shape.size
        shape.vy *= -1
    elif shape.y + shape.size > FRAME_HEIGHT:
        shape.y = FRAME_HEIGHT - shape.size
        shape.vy *= -1


async def _mjpeg_frames_from_video(path: str, fps: float) -> AsyncGenerator[bytes, None]:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {path}")

    frame_interval = 1.0 / max(fps, 1.0)

    try:
        while True:
            has_frame, frame = cap.read()
            if not has_frame:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            yield _encode_mjpeg(frame)
            await asyncio.sleep(frame_interval)
    finally:
        cap.release()


async def _mjpeg_synthetic_fallback(fps: float) -> AsyncGenerator[bytes, None]:
    frame_interval = 1.0 / max(fps, 1.0)
    rng = np.random.default_rng()
    shapes = _make_random_shapes(rng)

    while True:
        canvas = np.full((FRAME_HEIGHT, FRAME_WIDTH, 3), 255, dtype=np.uint8)

        for shape in shapes:
            _move_shape(shape)
            _draw_shape(canvas, shape)

        yield _encode_mjpeg(canvas)
        await asyncio.sleep(frame_interval)


async def mjpeg_frames() -> AsyncGenerator[bytes, None]:
    video_path = Path(VIDEO_FILE)
    if video_path.exists():
        async for frame in _mjpeg_frames_from_video(str(video_path), STREAM_FPS):
            yield frame
    else:
        async for frame in _mjpeg_synthetic_fallback(STREAM_FPS):
            yield frame


app = FastAPI(title="MJPEG-over-WebSocket backend")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "codec": "mjpeg",
            "video_file": VIDEO_FILE,
            "video_exists": Path(VIDEO_FILE).exists(),
        }
    )


@app.post("/auth/token", response_model=TokenResponse)
def issue_token(payload: TokenRequest) -> TokenResponse:
    token, expires_at = create_access_token(payload.user_id)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        websocket_url="/stream/ws?token=<JWT>",
    )


@app.websocket("/stream/ws")
async def stream_ws(websocket: WebSocket, token: str = Query(...)) -> None:
    verify_token(token)
    await websocket.accept()
    try:
        async for frame in mjpeg_frames():
            await websocket.send_bytes(frame)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close(code=1011)


if SITE_DIR.exists():
    app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
