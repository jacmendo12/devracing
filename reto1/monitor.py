#!/usr/bin/env python3
"""Monitor del canvas frontpage.sh/million.
Cada 30s: baja el grid, reporta vendidos + delta, densidad del centro,
actividad reciente y si los rects candidatos siguen 100% virgenes.
Log: monitor.log (una linea por tick) + ultimo grid en grid-latest.json
"""
import json, time, urllib.request, sys, datetime

BASE = 'https://www.frontpage.sh'
OUT = '/private/tmp/claude-501/-Users-javier-Documents-reto/6ce54c39-09f5-4623-819d-f12ac133aa84/scratchpad'
# rects candidatos (x0,y0,x1,y1) — se actualizan editando candidates.json
prev_sold = None

def fetch(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        return json.load(r)

while True:
    try:
        d = fetch('/api/million/grid')
        act = fetch('/api/million/activity')
        owned = {(p['x'], p['y']) for p in d['pixels']}
        sold = d['sold']
        delta = '' if prev_sold is None else f" (+{sold - prev_sold})"
        prev_sold = sold
        center = sum(1 for (x, y) in owned if 380 <= x <= 620 and 380 <= y <= 620)
        try:
            cands = json.load(open(OUT + '/candidates.json'))
        except Exception:
            cands = []
        status = []
        for c in cands:
            x0, y0, x1, y1 = c
            taken = sum(1 for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) if (x, y) in owned)
            status.append(f"rect({x0},{y0})-({x1},{y1}): {'VIRGEN' if taken == 0 else f'{taken} TOMADOS!'}")
        recent = act.get('activity') or act.get('buys') or []
        rec = recent[0] if isinstance(recent, list) and recent else {}
        line = (f"{datetime.datetime.now().strftime('%H:%M:%S')} sold={sold}{delta} "
                f"centro380-620={center} | {' | '.join(status) or 'sin candidatos'} "
                f"| ult.compra={json.dumps(rec, default=str)[:140]}")
        with open(OUT + '/monitor.log', 'a') as f:
            f.write(line + '\n')
        json.dump(d, open(OUT + '/grid-latest.json', 'w'))
        print(line, flush=True)
    except Exception as e:
        print(f"ERROR {e}", flush=True)
    time.sleep(30)
