#!/usr/bin/env python3
"""
⚔️ DUELO Tic-Tac-Toe TBIT vs Javi — frontpage.sh/million
=========================================================
Tablero fijo del duelo (spec: github.com/clovisrodriguez/tbit-frontpage-race/DUELO.md)
  celda (fila, col) → x = 41 + 2·col, y = 53 + 2·fila
  vacío #d9d9d9 · X TBIT #7b2ff2 · O nosotros (Javi) #f97066
El estado se lee SIEMPRE del canvas. Una jugada = una compra real.

Uso:
  python3 duelo.py state              # pinta el tablero actual
  python3 duelo.py advise             # jugada óptima para O (minimax), no compra
  python3 duelo.py move <fila> <col>  # compra NUESTRA O en esa celda (1 sola jugada)
  python3 duelo.py move <fila> <col> --dry   # simula sin comprar
"""
import argparse, json, subprocess, sys, time, urllib.error, urllib.request

BASE = 'https://www.frontpage.sh'
EMPTY_RGB, X_RGB, O_RGB = '#d9d9d9', '#7b2ff2', '#f97066'   # X = TBIT, O = nosotros
IDXS = ','.join(str((53 + 2 * r) * 1000 + (41 + 2 * c)) for r in range(3) for c in range(3))
CX, CO, DIM, BOLD, END = '\033[38;5;135m', '\033[38;5;209m', '\033[2m', '\033[1m', '\033[0m'
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

cell_xy = lambda i: (41 + 2 * (i % 3), 53 + 2 * (i // 3))


def api(path, body=None, tries=7):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(BASE + path,
                data=json.dumps(body).encode() if body else None,
                headers={'content-type': 'application/json'} if body else {})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < tries - 1:
                wait = 5 * (attempt + 1)
                print(f'{DIM}   (HTTP {e.code}, reintento en {wait}s…){END}')
                time.sleep(wait)
            else:
                raise


def read_board():
    """Estado desde el canvas (fuente de verdad). Devuelve (board, precios)."""
    data = api(f'/api/million/pixel?idxs={IDXS}')
    by_idx = {p['idx']: p for p in data['pixels']}
    board, prices = [], []
    for i in range(9):
        x, y = cell_xy(i)
        p = by_idx[y * 1000 + x]
        rgb = (p.get('rgb') or '').lower()
        board.append({X_RGB: 'X', O_RGB: 'O', EMPTY_RGB: ' '}.get(rgb, '?'))
        prices.append(float(p['nextPriceUsd']))
    return board, prices


def render(board, prices):
    c = lambda v: f'{CX}{BOLD}X{END}' if v == 'X' else (f'{CO}{BOLD}O{END}' if v == 'O' else (f'{DIM}?{END}' if v == '?' else f'{DIM}·{END}'))
    print(f'\n   duelo en canvas (41,53)…(45,57)   {DIM}fila,col{END}')
    for r in range(3):
        cost = ' '.join(f'${prices[r*3+i]:.2f}' for i in range(3))
        print('     ' + ' │ '.join(c(board[r * 3 + i]) for i in range(3)) + f'{DIM}      {cost}{END}')
        if r < 2: print('    ────┼───┼────')
    w = winner(board)
    if w: print(f'\n   🏁 {"¡Empate!" if w == "empate" else f"¡Gana {w}!"}')


def winner(b):
    for a, m, z in LINES:
        if b[a] in ('X', 'O') and b[a] == b[m] == b[z]:
            return b[a]
    return 'empate' if all(v != ' ' for v in b) else None


def best_move(b):
    """Minimax imbatible para O; entre empates de score prefiere la celda más barata."""
    def score(b, turn):
        w = winner(b)
        if w == 'O': return 1
        if w == 'X': return -1
        if w == 'empate': return 0
        vals = [score(b[:i] + [turn] + b[i+1:], 'X' if turn == 'O' else 'O')
                for i in range(9) if b[i] == ' ']
        return (max if turn == 'O' else min)(vals)
    _, prices = BOARD_CACHE
    moves = [(score(b[:i] + ['O'] + b[i+1:], 'X'), -prices[i], i) for i in range(9) if b[i] == ' ']
    s, _, i = max(moves)
    return i, s


def buy(i, dry):
    x, y = cell_xy(i)
    q = api('/api/million/quote', {'pixels': [{'x': x, 'y': y, 'rgb': O_RGB}]})
    usd = q['totalUsd']
    if dry:
        print(f'{DIM}   [dry-run] compraría ({x},{y}) {O_RGB} por ${usd}{END}')
        return
    out = subprocess.run(['npx', 'mppx', f'{BASE}/api/million/buy', '-J',
                          json.dumps({'quoteId': q['quoteId'], 'email': 'javier@t-bit.io'}),
                          '--network', 'mainnet'], capture_output=True, text=True)
    res = json.loads(out.stdout.strip().splitlines()[-1])
    if not res.get('ok'):
        sys.exit(f'Compra falló: {out.stdout} {out.stderr}')
    print(f'   ✓ O jugada en ({x},{y}) — ${usd} · buyId {res["buyId"]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['state', 'advise', 'move'])
    ap.add_argument('fila', nargs='?', type=int)
    ap.add_argument('col', nargs='?', type=int)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    global BOARD_CACHE
    board, prices = read_board()
    BOARD_CACHE = (board, prices)
    render(board, prices)

    if a.cmd == 'advise':
        if winner(board): return
        i, s = best_move(board)
        verdict = {1: 'ganamos', 0: 'empate asegurado', -1: 'vamos perdiendo'}[s]
        print(f'\n   💡 jugada óptima O: fila {i // 3}, col {i % 3}  ({verdict}) — ${prices[i]:.2f}')
    elif a.cmd == 'move':
        if a.fila is None or a.col is None:
            sys.exit('uso: duelo.py move <fila 0-2> <col 0-2>')
        i = a.fila * 3 + a.col
        if not (0 <= a.fila <= 2 and 0 <= a.col <= 2):
            sys.exit('fila y col deben ser 0-2')
        if board[i] != ' ':
            sys.exit(f'celda ({a.fila},{a.col}) ocupada con "{board[i]}" — no se pisa (duplica precio)')
        buy(i, a.dry)
        if not a.dry:
            board, prices = read_board()
            BOARD_CACHE = (board, prices)
            render(board, prices)


if __name__ == '__main__':
    main()
