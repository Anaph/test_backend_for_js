type TokenResponse = {
  access_token?: string;
};

const statusEl = document.getElementById('status') as HTMLParagraphElement | null;
const tokenEl = document.getElementById('token') as HTMLTextAreaElement | null;
const userIdEl = document.getElementById('userId') as HTMLInputElement | null;
const authForm = document.getElementById('authForm') as HTMLFormElement | null;
const connectBtn = document.getElementById('connectBtn') as HTMLButtonElement | null;
const canvas = document.getElementById('canvas') as HTMLCanvasElement | null;
const ctx = canvas?.getContext('2d') ?? null;

let ws: WebSocket | null = null;
let drawing = false;
let lastBlob: Blob | null = null;

const setStatus = (text: string): void => {
  if (statusEl) statusEl.textContent = `Статус: ${text}`;
};

authForm?.addEventListener('submit', async (e: SubmitEvent) => {
  e.preventDefault();
  setStatus('получение JWT...');

  const res = await fetch('/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userIdEl?.value || 'frontend-dev' })
  });

  const data = (await res.json()) as TokenResponse;
  if (tokenEl) tokenEl.value = data.access_token || '';
  setStatus('JWT получен');
});

async function drawLoop(): Promise<void> {
  if (drawing || !lastBlob || !canvas || !ctx) return;
  drawing = true;

  try {
    const bitmap = await createImageBitmap(lastBlob);
    if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
    }
    ctx.drawImage(bitmap, 0, 0);
    bitmap.close();
  } finally {
    drawing = false;
  }
}

connectBtn?.addEventListener('click', () => {
  ws?.close();

  const token = tokenEl?.value.trim() || '';
  if (!token) {
    setStatus('нет токена');
    return;
  }

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/stream/ws?token=${encodeURIComponent(token)}`);
  ws.binaryType = 'blob';

  ws.onopen = () => setStatus('подключено');
  ws.onclose = () => setStatus('отключено');
  ws.onerror = () => setStatus('ошибка');
  ws.onmessage = async (event: MessageEvent<Blob>) => {
    lastBlob = event.data;
    await drawLoop();
  };
});
