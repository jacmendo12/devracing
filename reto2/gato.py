#!/usr/bin/env python3
"""
⭕❌ GATO en el canvas de frontpage.sh/million
==============================================
Cada movimiento COMPRA un pixel real (USDC en Tempo vía MPP/mppx).
El estado del juego se lee SIEMPRE del canvas (API), nunca de memoria local.

Economía del diseño:
  - En el gato una casilla jugada nunca se reescribe → máx 9 compras/partida.
  - Tablero nuevo por partida: se auto-coloca en 9 pixeles VÍRGENES ($0.005 c/u)
    → una partida completa cuesta como máximo $0.045.
  - Vacío = pixel sin comprar (el fondo del canvas es el tercer color, gratis).

Uso:
  python3 gato.py             # dry-run: lee el canvas real, simula las compras
  python3 gato.py --live      # compras reales (pide confirmación al inicio)
  python3 gato.py --live --email tu@correo.com --origin 494,465 --spacing 3
"""
import argparse, json, random, subprocess, sys, time, urllib.error, urllib.request

BASE = 'https://www.frontpage.sh'
X_RGB, O_RGB = '#ff8270', '#9755ff'          # X humano (coral), O bot (morado TBit)
CX, CO, DIM, BOLD, END = '\033[38;5;209m', '\033[38;5;135m', '\033[2m', '\033[1m', '\033[0m'
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]


def api(path, body=None, tries=4):
    """GET/POST con retry+backoff (el API rate-limitea con 429)."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(BASE + path,
                data=json.dumps(body).encode() if body else None,
                headers={'content-type': 'application/json'} if body else {})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < tries - 1:
                wait = 2 * (attempt + 1)
                print(f'{DIM}   (rate limit {e.code}, reintento en {wait}s…){END}')
                time.sleep(wait)
            else:
                raise


def find_virgin_board(origin, spacing):
    """Desplaza el origen hasta que las 9 casillas sean pixeles vírgenes."""
    grid = api('/api/million/grid')
    owned = {(p['x'], p['y']) for p in grid['pixels']}
    x0, y0 = origin
    for dy in range(0, 200, spacing * 3 + 2):
        for dx in range(0, 200, spacing * 3 + 2):
            cells = [(x0 + dx + c % 3 * spacing, y0 + dy + c // 3 * spacing) for c in range(9)]
            if all(c not in owned for c in cells):
                return cells
    sys.exit('No encontré 9 pixeles vírgenes cerca del origen; prueba otro --origin')


def read_board(cells, overlay):
    """Lee las 9 casillas del CANVAS (fuente de verdad). overlay = jugadas dry-run."""
    board = []
    for i, (x, y) in enumerate(cells):
        if i in overlay:
            board.append(overlay[i]); continue
        p = api(f'/api/million/pixel?x={x}&y={y}')
        if not p.get('owned'):
            board.append(' ')
        else:
            board.append({X_RGB: 'X', O_RGB: 'O'}.get(p.get('rgb'), '?'))  # '?' = pixel robado por un tercero
    return board


def buy_pixel(x, y, rgb, email, live):
    if not live:  # dry-run: precio directo del pixel, sin gastar quotes (rate limit)
        p = api(f'/api/million/pixel?x={x}&y={y}')
        usd = p['nextPriceUsd']
        print(f'{DIM}   [dry-run] compraría ({x},{y}) {rgb} por ${usd}{END}')
        return float(usd)
    q = api('/api/million/quote', {'pixels': [{'x': x, 'y': y, 'rgb': rgb}]})
    usd = q['totalUsd']
    out = subprocess.run(['npx', 'mppx', f'{BASE}/api/million/buy', '-J',
                          json.dumps({'quoteId': q['quoteId'], 'email': email}),
                          '--network', 'mainnet'], capture_output=True, text=True)
    res = json.loads(out.stdout.strip().splitlines()[-1])
    if not res.get('ok'):
        sys.exit(f'Compra falló: {out.stdout} {out.stderr}')
    print(f'{DIM}   ✓ pixel ({x},{y}) comprado — ${usd} · buyId {res["buyId"]}{END}')
    return float(usd)


def render(board, cells, spent):
    c = lambda v: f'{CX}{BOLD}X{END}' if v == 'X' else (f'{CO}{BOLD}O{END}' if v == 'O' else (f'{DIM}?{END}' if v == '?' else f'{DIM}·{END}'))
    print(f'\n   tablero en canvas ({cells[0][0]},{cells[0][1]})…({cells[8][0]},{cells[8][1]}) · gastado ${spent:.3f}')
    for r in range(3):
        print('     ' + ' │ '.join(c(board[r * 3 + i]) for i in range(3)) +
              f'{DIM}      {r*3+1} {r*3+2} {r*3+3}{END}')
        if r < 2: print(f'    ────┼───┼────')


def winner(b):
    for a, m, z in LINES:
        if b[a] != ' ' and b[a] != '?' and b[a] == b[m] == b[z]:
            return b[a]
    return 'empate' if all(v != ' ' for v in b) else None


def bot_move(b):
    """Minimax imbatible para O."""
    def score(b, turn):
        w = winner(b)
        if w == 'O': return 1
        if w == 'X': return -1
        if w == 'empate': return 0
        vals = [(score(b[:i] + [turn] + b[i+1:], 'X' if turn == 'O' else 'O'), i)
                for i in range(9) if b[i] == ' ']
        return (max if turn == 'O' else min)(vals)[0]
    moves = [(score(b[:i] + ['O'] + b[i+1:], 'X'), i) for i in range(9) if b[i] == ' ']
    best = max(moves)[0]
    return random.choice([i for s, i in moves if s == best])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true', help='compras reales (default: dry-run)')
    ap.add_argument('--email', default='javier@t-bit.io')
    ap.add_argument('--origin', default='494,465', help='esquina preferida x,y (default: bajo el logo TBit)')
    ap.add_argument('--spacing', type=int, default=3, help='separación entre casillas en px')
    a = ap.parse_args()

    print(f'{BOLD}⭕❌ GATO — frontpage.sh/million{END}')
    print(f'   modo: {"🔴 LIVE (USDC real)" if a.live else "dry-run (lee canvas real, simula compras)"}')
    origin = tuple(int(v) for v in a.origin.split(','))
    cells = find_virgin_board(origin, a.spacing)
    print(f'   tablero virgen encontrado · partida completa ≤ $0.045')
    if a.live and input('   ¿Confirmas compras reales? (si/no) ').strip().lower() not in ('si', 'sí', 's', 'y', 'yes'):
        sys.exit('   cancelado')

    overlay, spent = {}, 0.0
    while True:
        board = read_board(cells, overlay)          # ← estado desde el canvas
        render(board, cells, spent)
        w = winner(board)
        if w:
            print(f'\n   🏁 {"¡Empate! (gato)" if w == "empate" else f"¡Gana {w}!"}\n')
            break
        try:
            mv = int(input(f'\n   tu jugada {CX}X{END} (1-9): ')) - 1
        except (ValueError, EOFError):
            print('   número 1-9'); continue
        if not (0 <= mv <= 8) or board[mv] != ' ':
            print('   casilla inválida u ocupada'); continue
        spent += buy_pixel(*cells[mv], X_RGB, a.email, a.live)
        if not a.live: overlay[mv] = 'X'
        board = read_board(cells, overlay)
        if winner(board): continue
        bm = bot_move(board)
        print(f'   bot {CO}O{END} juega la casilla {bm + 1}')
        spent += buy_pixel(*cells[bm], O_RGB, a.email, a.live)
        if not a.live: overlay[bm] = 'O'


if __name__ == '__main__':
    main()
