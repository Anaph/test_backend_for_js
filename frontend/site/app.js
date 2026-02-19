const statusEl = document.getElementById('status');
const tokenEl = document.getElementById('token');
const userIdEl = document.getElementById('userId');
const authForm = document.getElementById('authForm');
const connectBtn = document.getElementById('connectBtn');
const canvas = document.getElementById('canvas');
const ctx = canvas?.getContext('2d') ?? null;

let ws = null;
let drawing = false;
let lastBlob = null;

const setStatus = (text) => {
  if (statusEl) statusEl.textContent = `Статус: ${text}`;
};

authForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  setStatus('получение JWT...');

  const res = await fetch('/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userIdEl?.value || 'frontend-dev' })
  });

  const data = await res.json();
  if (tokenEl) tokenEl.value = data.access_token || '';
  setStatus('JWT получен');
});

async function drawLoop() {
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
  ws.onmessage = async (event) => {
    lastBlob = event.data;
    await drawLoop();
  };
});
