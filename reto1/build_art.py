#!/usr/bin/env python3
"""Genera pixels.json + preview.png del logo TBit en pixel art."""
from PIL import Image
import json

PAL = {
    'T': '#77bfbe',  # teal mascota
    'S': '#4c909d',  # teal sombra (borde inferior)
    'P': '#9755ff',  # morado (T y globo)
    'C': '#ff8270',  # coral (Bit)
    'K': '#161616',  # negro ojos/boca
}
# '.' = vacio (no se pinta, fondo del canvas)

rows = [
    #0.........1.........2.........3....
    #0123456789012345678901234567890123456
    "PPP..................................",  # 0  globo
    "PPP..................................",  # 1
    "PPP....T.............................",  # 2  apex mascota
    "..P...TTT............................",  # 3  tail globo
    "......TTT............................",  # 4
    ".....TTTTT.....PPPPPP.CCCC...CC..CC..",  # 5  T top / B top / i dot
    ".....TTTTT.....PPPPPP.CC.CC..CC..CC..",  # 6
    "....TTTTTTT......PP...CC.CC.....CCCC.",  # 7  t crossbar
    "....TKTTTKT......PP...CCCC...CC..CC..",  # 8  ojos
    "...TTKTTTKTT.....PP...CC.CC..CC..CC..",  # 9  ojos 2
    "...TTTTTTTTT.....PP...CC.CC..CC..CC..",  # 10
    "..TTTTKKKTTTT....PP...CC.CC..CC..CC..",  # 11 sonrisa
    "..TTTTTTTTTTT....PP...CCCC...CC...CCC",  # 12
    ".SSSSSSSSSSSSS.......................",  # 13 base/sombra
]

pixels = []
for dy, row in enumerate(rows):
    for dx, ch in enumerate(row):
        if ch in PAL:
            pixels.append({"dx": dx, "dy": dy, "rgb": PAL[ch]})

W = max(len(r) for r in rows)
H = len(rows)
print(f"bbox {W}x{H}, pintados: {len(pixels)}, costo base: ${len(pixels)*0.005:.3f}")

json.dump(pixels, open('pixels.json', 'w'))

# preview x20
S = 20
im = Image.new('RGB', (W * S, H * S), '#ececec')
px = im.load()
for p in pixels:
    r, g, b = (int(p['rgb'][i:i+2], 16) for i in (1, 3, 5))
    for yy in range(p['dy']*S, p['dy']*S+S):
        for xx in range(p['dx']*S, p['dx']*S+S):
            px[xx, yy] = (r, g, b)
im.save('preview.png')
print('preview.png listo')
