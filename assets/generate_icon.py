#!/usr/bin/env python3
"""Render the AURORA app icon on the external build runner."""
import sys
from PIL import Image, ImageDraw, ImageFilter

SIZE = 128
S = 4
n = SIZE * S
im = Image.new("RGB", (n, n), (7, 9, 16))
px = im.load()
for y in range(n):
    for x in range(n):
        glow = max(0.0, 1.0 - (((x-n*.78)/(n*.85))**2 + ((y-n*.18)/(n*.85))**2)**0.5)
        px[x, y] = (int(9+19*glow), int(11+11*glow), int(19+31*glow))
mask = Image.new("L", (n,n), 0)
ImageDraw.Draw(mask).rounded_rectangle((2,2,n-3,n-3), radius=27*S, fill=255)
im.putalpha(mask)
d = ImageDraw.Draw(im)
# Orbit halo and vinyl record.
d.ellipse((20*S,20*S,108*S,108*S), outline=(89,70,115,255), width=3*S)
d.ellipse((27*S,27*S,101*S,101*S), fill=(17,21,35,255), outline=(255,112,76,255), width=3*S)
for radius in (31, 25, 19):
    d.ellipse(((64-radius)*S,(64-radius)*S,(64+radius)*S,(64+radius)*S),
              outline=(79,67,100,255), width=2*S)
d.ellipse((52*S,52*S,76*S,76*S), fill=(255,112,76,255))
d.ellipse((60*S,60*S,68*S,68*S), fill=(9,11,19,255))
# Three violet/coral sound bars crossing the lower edge of the disc.
for i, h in enumerate((13, 25, 18, 31, 14)):
    x = (43 + i*11)*S
    d.rounded_rectangle((x, (106-h)*S, x+5*S, 106*S), radius=2*S,
                        fill=(185,139,255,255) if i%2 else (255,132,95,255))
im = im.resize((SIZE,SIZE), Image.Resampling.LANCZOS)
im.save(sys.argv[1], "PNG", optimize=True)
