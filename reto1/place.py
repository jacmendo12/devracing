#!/usr/bin/env python3
"""Find the virgin rectangle (W x H) closest to the canvas center, using fresh grid data.
Usage: python3 place.py W H [margin]
Prints the top candidate origins (x0,y0) fully unowned, nearest to (500,500) first.
A `margin` (default 1) requires an extra virgin border around the piece so it doesn't touch other art.
"""
import json, sys, urllib.request

W = int(sys.argv[1]); H = int(sys.argv[2])
M = int(sys.argv[3]) if len(sys.argv) > 3 else 1

with urllib.request.urlopen('https://www.frontpage.sh/api/million/grid') as r:
    d = json.load(r)
owned = {(p['x'], p['y']) for p in d['pixels']}
print(f"grid fresh: {d['sold']} sold")

Wm, Hm = W + 2 * M, H + 2 * M
cands = []
for y0 in range(300, 700 - Hm, 2):
    for x0 in range(300, 700 - Wm, 2):
        if all((x, y) not in owned for x in range(x0, x0 + Wm) for y in range(y0, y0 + Hm)):
            cx, cy = x0 + Wm / 2, y0 + Hm / 2
            dist = ((cx - 500) ** 2 + (cy - 500) ** 2) ** 0.5
            cands.append((dist, x0 + M, y0 + M))
cands.sort()
for dist, x, y in cands[:8]:
    print(f"dist {dist:5.0f}  origin ({x},{y})  piece ({x},{y})-({x+W-1},{y+H-1})")
print("candidates:", len(cands))
