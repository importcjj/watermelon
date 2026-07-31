#!/usr/bin/env python3
"""生成 PWA 图标：原创西瓜切面，纯 stdlib 手写 PNG，解析式抗锯齿。"""
import math
import os
import struct
import zlib

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")

CREAM = (0xFB, 0xF6, 0xE7)
RIND = (0x2F, 0x7D, 0x4F)
RIND_HI = (0x57, 0xA6, 0x6E)
PALE = (0xED, 0xF3, 0xDC)
FLESH = (0xE0, 0x43, 0x2E)
FLESH_HI = (0xEE, 0x6B, 0x55)
SEED = (0x23, 0x30, 0x1F)


def write_png(path, w, h, buf):
    raw = b"".join(b"\x00" + bytes(buf[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def blend(buf, i, color, a):
    if a <= 0:
        return
    if a >= 1:
        buf[i] = color[0]; buf[i + 1] = color[1]; buf[i + 2] = color[2]; buf[i + 3] = 255
        return
    for k in range(3):
        buf[i + k] = int(buf[i + k] + (color[k] - buf[i + k]) * a + 0.5)
    buf[i + 3] = int(buf[i + 3] + (255 - buf[i + 3]) * a + 0.5)


def disc(buf, S, cx, cy, r, color, y0=None, y1=None):
    """带 1px 解析式抗锯齿的实心圆。"""
    y0 = max(0, int(cy - r - 2)) if y0 is None else y0
    y1 = min(S, int(cy + r + 3)) if y1 is None else y1
    x0 = max(0, int(cx - r - 2))
    x1 = min(S, int(cx + r + 3))
    for y in range(y0, y1):
        dy = y + 0.5 - cy
        row = y * S * 4
        for x in range(x0, x1):
            dx = x + 0.5 - cx
            d = math.hypot(dx, dy)
            a = r - d + 0.5
            if a <= 0:
                continue
            blend(buf, row + x * 4, color, min(1.0, a))


def ellipse(buf, S, cx, cy, A, B, ang, color):
    ca, sa = math.cos(-ang), math.sin(-ang)
    rad = max(A, B) + 2
    for y in range(max(0, int(cy - rad)), min(S, int(cy + rad + 1))):
        dy = y + 0.5 - cy
        row = y * S * 4
        for x in range(max(0, int(cx - rad)), min(S, int(cx + rad + 1))):
            dx = x + 0.5 - cx
            u = dx * ca - dy * sa
            v = dx * sa + dy * ca
            nd = math.hypot(u / A, v / B)
            a = (1.0 - nd) * min(A, B) + 0.5
            if a <= 0:
                continue
            blend(buf, row + x * 4, color, min(1.0, a))


def make(S, melon_ratio, bg):
    """melon_ratio: 西瓜半径占边长的比例（maskable 需留安全区）"""
    buf = bytearray(S * S * 4)
    if bg:
        for i in range(0, len(buf), 4):
            buf[i] = bg[0]; buf[i + 1] = bg[1]; buf[i + 2] = bg[2]; buf[i + 3] = 255

    cx = cy = S / 2
    R = S * melon_ratio

    # 落影
    disc(buf, S, cx, cy + R * 0.06, R * 1.005, (0x1A, 0x28, 0x1E))
    for i in range(3, len(buf), 4):
        pass
    # 瓜皮 → 白瓤 → 果肉
    disc(buf, S, cx, cy, R, RIND)
    disc(buf, S, cx - R * 0.07, cy - R * 0.09, R * 0.985, RIND_HI)
    disc(buf, S, cx, cy, R * 0.90, PALE)
    disc(buf, S, cx, cy, R * 0.835, FLESH)
    disc(buf, S, cx - R * 0.16, cy - R * 0.18, R * 0.60, FLESH_HI)
    disc(buf, S, cx, cy, R * 0.60, FLESH)

    # 高光（在瓜子之下，避免压出脏斑）
    for y in range(S):
        dy = y + 0.5 - (cy - R * 0.52)
        row = y * S * 4
        for x in range(S):
            dx = x + 0.5 - (cx - R * 0.38)
            nd = math.hypot(dx / (R * 0.30), dy / (R * 0.13))
            a = (1.0 - nd) * (R * 0.13) + 0.5
            if a <= 0:
                continue
            blend(buf, row + x * 4, (255, 255, 255), min(1.0, a) * 0.30)

    # 瓜子：外圈 7 颗 + 内圈 3 颗，长轴朝向圆心
    for k in range(7):
        t = -math.pi / 2 + k * (2 * math.pi / 7) + 0.28
        ellipse(buf, S, cx + math.cos(t) * R * 0.52, cy + math.sin(t) * R * 0.52,
                R * 0.115, R * 0.068, t, SEED)
    for k in range(3):
        t = -math.pi / 2 + k * (2 * math.pi / 3) - 0.5
        ellipse(buf, S, cx + math.cos(t) * R * 0.24, cy + math.sin(t) * R * 0.24,
                R * 0.10, R * 0.06, t, SEED)
    return buf


os.makedirs(OUT, exist_ok=True)
jobs = [
    ("icon-192.png", 192, 0.43, CREAM),
    ("icon-512.png", 512, 0.43, CREAM),
    ("icon-maskable-512.png", 512, 0.34, CREAM),   # 安全区：内容限中心 80%
    ("apple-touch-icon.png", 180, 0.43, CREAM),
    ("favicon-32.png", 32, 0.45, CREAM),
]
for name, size, ratio, bg in jobs:
    n = write_png(os.path.join(OUT, name), size, size, make(size, ratio, bg))
    print(f"{name:26s} {size}x{size}  {n/1024:.1f} KB")
