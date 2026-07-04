#!/usr/bin/env python3
"""
⭕❌ GATO web — interfaz gráfica sobre el canvas de frontpage.sh/million
Abre http://localhost:8787 : click en una casilla = compra el pixel en el canvas
real (modo --live) y el bot responde. Botón "nuevo tablero" arma otra partida
en 9 pixeles vírgenes nuevos.

  python3 server.py            # dry-run (lee canvas real, simula compras)
  python3 server.py --live     # compras reales con USDC vía mppx
"""
import argparse, json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from gato import api, find_virgin_board, read_board, buy_pixel, winner, bot_move, X_RGB, O_RGB

S = {'cells': None, 'overlay': {}, 'spent': 0.0, 'total': 0.0, 'live': False,
     'email': 'javier@t-bit.io', 'origin': (494, 465), 'spacing': 3, 'busy': False}
LOCK = threading.Lock()


def new_board():
    S['cells'] = find_virgin_board(S['origin'], S['spacing'])
    S['overlay'] = {}
    S['spent'] = 0.0


def state():
    board = read_board(S['cells'], S['overlay'])
    return {'board': board, 'cells': S['cells'], 'spent': round(S['spent'], 3),
            'total': round(S['total'], 3), 'winner': winner(board), 'live': S['live'],
            'canvasUrl': 'https://www.frontpage.sh/million'}


def best_move(b, player):
    """Minimax genérico: mejor jugada para X o para O."""
    other = 'O' if player == 'X' else 'X'
    def score(b, turn):
        w = winner(b)
        if w == player: return 1
        if w == other: return -1
        if w == 'empate': return 0
        vals = [score(b[:i] + [turn] + b[i+1:], other if turn == player else player)
                for i in range(9) if b[i] == ' ']
        return max(vals) if turn == player else min(vals)
    moves = [(score(b[:i] + [player] + b[i+1:], other), i) for i in range(9) if b[i] == ' ']
    import random
    best = max(moves)[0]
    return random.choice([i for s, i in moves if s == best])


def autostep():
    """Una jugada automática: la IA mueve por quien tenga el turno."""
    board = read_board(S['cells'], S['overlay'])
    if winner(board):
        return state()
    turn = 'X' if board.count('X') <= board.count('O') else 'O'
    mv = best_move(board, turn)
    usd = buy_pixel(*S['cells'][mv], X_RGB if turn == 'X' else O_RGB, S['email'], S['live'])
    S['spent'] += usd; S['total'] += usd
    if not S['live']: S['overlay'][mv] = turn
    return state()


def play(cell):
    board = read_board(S['cells'], S['overlay'])
    if winner(board) or not (0 <= cell <= 8) or board[cell] != ' ':
        return state()
    usd = buy_pixel(*S['cells'][cell], X_RGB, S['email'], S['live'])
    S['spent'] += usd; S['total'] += usd
    if not S['live']: S['overlay'][cell] = 'X'
    board = read_board(S['cells'], S['overlay'])
    if not winner(board):
        bm = bot_move(board)
        usd = buy_pixel(*S['cells'][bm], O_RGB, S['email'], S['live'])
        S['spent'] += usd; S['total'] += usd
        if not S['live']: S['overlay'][bm] = 'O'
    return state()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', len(b))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == '/':
            b = HTML.encode()
            self.send_response(200)
            self.send_header('content-type', 'text/html; charset=utf-8')
            self.send_header('content-length', len(b))
            self.end_headers()
            self.wfile.write(b)
        elif self.path == '/state':
            with LOCK: self._json(state())
        else:
            self._json({'error': 'not found'}, 404)

    def do_POST(self):
        n = int(self.headers.get('content-length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        with LOCK:
            if self.path == '/move':
                self._json(play(int(body.get('cell', -1))))
            elif self.path == '/autostep':
                self._json(autostep())
            elif self.path == '/new':
                new_board(); self._json(state())
            else:
                self._json({'error': 'not found'}, 404)


HTML = r'''<!doctype html><html><head><meta charset="utf-8"><title>⭕❌ Gato × frontpage.sh</title>
<style>
  :root { --teal:#77bfbe; --purple:#9755ff; --coral:#ff8270; --ink:#1c2430; }
  * { box-sizing:border-box; font-family:ui-rounded,'SF Pro Rounded',system-ui,sans-serif; }
  body { margin:0; min-height:100vh; display:flex; flex-direction:column; align-items:center;
         justify-content:center; background:#f2f0ea; color:var(--ink); }
  h1 { margin:.2em 0 0; font-size:1.6rem; } .sub { opacity:.6; font-size:.85rem; margin-bottom:1rem; }
  #board { display:grid; grid-template-columns:repeat(3,96px); gap:8px; }
  .cell { height:96px; font-size:3rem; font-weight:800; border:none; border-radius:14px;
          background:#fff; box-shadow:0 2px 6px rgba(0,0,0,.08); cursor:pointer; transition:.15s; }
  .cell:hover:enabled { transform:scale(1.05); background:#fdfdfd; }
  .cell:disabled { cursor:default; }
  .X { color:var(--coral); } .O { color:var(--purple); }
  #status { margin:1rem 0 .4rem; font-size:1.05rem; min-height:1.4em; font-weight:600; }
  #meta { font-size:.8rem; opacity:.65; margin-bottom:1rem; text-align:center; line-height:1.5; }
  .btns { display:flex; gap:.6rem; }
  button.action { padding:.6rem 1.1rem; border:none; border-radius:10px; font-weight:700;
          background:var(--purple); color:#fff; cursor:pointer; }
  button.action.sec { background:var(--teal); }
  a { color:var(--purple); }
  #mode { position:fixed; top:10px; right:12px; font-size:.75rem; padding:.3em .7em;
          border-radius:99px; background:#fff; box-shadow:0 1px 4px rgba(0,0,0,.12); }
</style></head><body>
<div id="mode">…</div>
<h1>⭕❌ Gato × million</h1>
<div class="sub">cada jugada compra un pixel real en <a href="https://www.frontpage.sh/million" target="_blank">frontpage.sh/million</a></div>
<div id="board"></div>
<div id="status">cargando tablero…</div>
<div id="meta"></div>
<div class="btns">
  <button class="action" onclick="nuevo()">🆕 nuevo tablero</button>
  <button class="action" id="autobtn" onclick="toggleAuto()" style="background:var(--coral)">🤖 automático</button>
  <button class="action sec" onclick="window.open('https://www.frontpage.sh/million','_blank')">👀 ver canvas en vivo</button>
</div>
<script>
let st = null, busy = false, auto = false;
const B = document.getElementById('board');
for (let i = 0; i < 9; i++) {
  const b = document.createElement('button');
  b.className = 'cell'; b.onclick = () => move(i); B.appendChild(b);
}
function paint() {
  if (!st) return;
  document.getElementById('mode').textContent = st.live ? '🔴 LIVE — USDC real' : '🟡 dry-run';
  const w = st.winner;
  [...B.children].forEach((b, i) => {
    const v = st.board[i];
    b.textContent = v === ' ' ? '' : v;
    b.className = 'cell ' + (v === 'X' || v === 'O' ? v : '');
    b.disabled = busy || auto || v !== ' ' || !!w;
  });
  const ab = document.getElementById('autobtn');
  ab.textContent = auto ? '⏸ parar automático' : '🤖 automático';
  document.getElementById('status').textContent = busy ? '⏳ comprando pixel…'
    : w === 'X' ? (auto ? '🏆 Ganó X' : '🏆 ¡Ganaste!') : w === 'O' ? '🤖 Ganó O'
    : w === 'empate' ? '😼 ¡Gato! Empate'
    : auto ? '🤖 la IA está jugando sola…' : 'tu turno — juegas con X';
  const c = st.cells;
  document.getElementById('meta').innerHTML =
    `tablero en canvas (${c[0][0]},${c[0][1]}) → (${c[8][0]},${c[8][1]})` +
    ` · partida $${st.spent.toFixed(3)} · sesión $${st.total.toFixed(3)}`;
}
async function refresh() { st = await (await fetch('/state')).json(); paint(); }
async function move(i) {
  if (busy || !st || st.board[i] !== ' ' || st.winner) return;
  busy = true; st.board[i] = 'X'; paint();          // pinta optimista, el server confirma
  st = await (await fetch('/move', {method:'POST', headers:{'content-type':'application/json'},
       body: JSON.stringify({cell: i})})).json();
  busy = false; paint();
}
async function nuevo() {
  busy = true; paint();
  st = await (await fetch('/new', {method:'POST'})).json();
  busy = false; paint();
}
async function toggleAuto() {
  auto = !auto; paint();
  while (auto && st && !st.winner) {        // la IA juega sola, un pixel a la vez
    busy = true; paint();
    st = await (await fetch('/autostep', {method:'POST'})).json();
    busy = false; paint();
    await new Promise(r => setTimeout(r, 1500));
  }
  auto = false; paint();
}
refresh();
setInterval(() => { if (!busy) refresh(); }, 10000);  // el canvas es la fuente de verdad
</script></body></html>'''


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true')
    ap.add_argument('--email', default='javier@t-bit.io')
    ap.add_argument('--origin', default='494,465')
    ap.add_argument('--port', type=int, default=8787)
    a = ap.parse_args()
    S['live'] = a.live; S['email'] = a.email
    S['origin'] = tuple(int(v) for v in a.origin.split(','))
    print('buscando 9 pixeles vírgenes…')
    new_board()
    print(f"⭕❌ Gato {'🔴 LIVE' if a.live else 'dry-run'} → http://localhost:{a.port}")
    HTTPServer(('127.0.0.1', a.port), H).serve_forever()
