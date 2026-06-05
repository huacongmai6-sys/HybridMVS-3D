"""
HybridMVS Poster v3 — Landscape, High Contrast, Statue of Liberty Point Cloud
Colors: Tiffany Blue #80d1c8 × Cheese #f8f5d6
Tech aesthetic, bold typography, minimal negative space.
"""

import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Config ──────────────────────────────────────────────────
W, H = 3840, 2160  # 16:9 landscape
OUTPUT = "HybridMVS_Poster.png"
FONTS_DIR = r"C:\Users\xiaomai\.claude\skills\canvas-design\canvas-fonts"

# Color palette
TIFFANY    = (0x80, 0xD1, 0xC8)
TIFFANY_B  = (0x50, 0xC0, 0xB5)  # brighter variant
TIFFANY_D  = (0x40, 0xA0, 0x98)  # darker variant
CHEESE     = (0xF8, 0xF5, 0xD6)
CHEESE_B   = (0xFF, 0xFC, 0xE8)
DARK       = (0x0A, 0x0C, 0x12)
DARK_WARM  = (0x12, 0x10, 0x0D)
DARK_SLATE = (0x14, 0x18, 0x22)
WHITE_SOFT = (0xF0, 0xF0, 0xEE)
CORAL      = (0xE8, 0x6A, 0x50)  # warm accent for triadic contrast
SLATE      = (0x60, 0x6A, 0x78)

C = {
    "tiffany":   TIFFANY,
    "tiffany_b": TIFFANY_B,
    "tiffany_d": TIFFANY_D,
    "cheese":    CHEESE,
    "cheese_b":  CHEESE_B,
    "dark":      DARK,
    "dark_warm": DARK_WARM,
    "dark_slate":DARK_SLATE,
    "white":     WHITE_SOFT,
    "coral":     CORAL,
    "slate":     SLATE,
}

# ── Helpers ─────────────────────────────────────────────────
def load_font(name, size):
    try:
        return ImageFont.truetype(f"{FONTS_DIR}/{name}", size)
    except:
        return ImageFont.load_default()

def blend(c1, c2, t):
    t = max(0, min(1, t))
    return tuple(max(0, min(255, int(c1[i]+(c2[i]-c1[i])*t))) for i in range(3))

def draw_dot(draw, x, y, r, color, alpha=255):
    c = color + (alpha,) if len(color) == 3 else color
    draw.ellipse([x-r, y-r, x+r, y+r], fill=c)

def draw_glow_dot(layer, x, y, r, color, alpha):
    """Dot with soft glow."""
    if r > 1.5:
        hr = r * 3
        for step in range(int(hr), 0, -1):
            a = int(alpha * 0.08 * (step/hr))
            ImageDraw.Draw(layer).ellipse(
                [x-step, y-step, x+step, y+step], fill=color+(a,))
    draw_dot(ImageDraw.Draw(layer), x, y, r, color, alpha)


# ── Statue of Liberty point cloud generator ─────────────────
def generate_statue_points():
    """Statue of Liberty — robed figure, raised torch arm, crown spikes, tablet.
    High-density point cloud (~9000 points).
    Returns list of (x, y, z, type) in normalized coordinates."""
    pts = []
    rng = np.random.RandomState(2026)

    # ── Body/robe — tall tapered column with drapery ──
    n_body = 3500
    for _ in range(n_body):
        y = rng.uniform(-0.9, 0.35)  # from feet to shoulders
        t = (y + 0.9) / 1.25  # 0 at feet, 1 at shoulders
        # Robe gets slightly wider toward the bottom
        robe_r = 0.22 + (1-t) * 0.12

        # Drape folds: sinusoidal modulation
        angle = rng.uniform(0, 2 * math.pi)
        fold = 1 + math.sin(angle * 7) * 0.04 + math.sin(angle * 3) * 0.06
        r = robe_r * fold

        nx = math.cos(angle) * r + rng.normal(0, 0.008)
        ny = y + rng.normal(0, 0.008)
        nz = math.sin(angle) * r + rng.normal(0, 0.008)
        pts.append((nx, ny, nz, 'robe'))

    # ── Torso/chest — upper body, narrower ──
    for _ in range(800):
        y = rng.uniform(0.2, 0.5)
        t = (y - 0.2) / 0.3
        chest_r = 0.18 + t * 0.03
        angle = rng.uniform(0, 2 * math.pi)
        nx = math.cos(angle) * chest_r + rng.normal(0, 0.006)
        ny = y + rng.normal(0, 0.006)
        nz = math.sin(angle) * chest_r + rng.normal(0, 0.006)
        pts.append((nx, ny, nz, 'chest'))

    # ── Head — ellipsoid ──
    head_cy = 0.62
    for _ in range(900):
        theta = rng.uniform(0, 2 * math.pi)
        phi = rng.uniform(0, math.pi)
        hrx, hry, hrz = 0.10, 0.13, 0.10
        hx = math.sin(phi) * math.cos(theta) * hrx + rng.normal(0, 0.004)
        hy = head_cy + math.cos(phi) * hry + rng.normal(0, 0.004)
        hz = math.sin(phi) * math.sin(theta) * hrz + rng.normal(0, 0.004)
        pts.append((hx, hy, hz, 'head'))

    # Facial features — slightly higher density center
    for _ in range(120):
        fx = rng.normal(0, 0.04)
        fy = rng.normal(head_cy, 0.04)
        fz = rng.normal(0.09, 0.03)
        pts.append((fx, fy, fz, 'face'))

    # ── Crown — 7 spikes radiating from head ──
    n_spikes = 7
    for spike_i in range(n_spikes):
        angle = spike_i * 2 * math.pi / n_spikes + rng.uniform(-0.05, 0.05)
        spike_base_x = math.cos(angle) * 0.1
        spike_base_z = math.sin(angle) * 0.1
        spike_base_y = head_cy + 0.12

        n_pts_per_spike = 100
        for _ in range(n_pts_per_spike):
            t = rng.uniform(0, 1)
            sx = spike_base_x * (1 - t*0.3) + rng.normal(0, 0.01)
            sy = spike_base_y + t * 0.15 + rng.normal(0, 0.008)
            sz = spike_base_z * (1 - t*0.3) + rng.normal(0, 0.01)
            pts.append((sx, sy, sz, 'crown'))

    # ── Right arm — raised, holding torch ──
    # Upper arm extends from shoulder upward-right
    shoulder_y = 0.42
    shoulder_x = 0.16
    shoulder_z = 0.04

    for _ in range(600):
        t = rng.uniform(0, 1)
        # Arm curves up and slightly forward
        ax = shoulder_x + t * 0.08 + rng.normal(0, 0.03)
        ay = shoulder_y + t * 0.40 + rng.normal(0, 0.02)
        az = shoulder_z + t * 0.06 + rng.normal(0, 0.03)
        pts.append((ax, ay, az, 'arm'))

    # Forearm + hand
    for _ in range(300):
        t = rng.uniform(0, 1)
        fx = shoulder_x + 0.08 + t * 0.04 + rng.normal(0, 0.02)
        fy = shoulder_y + 0.40 + t * 0.25 + rng.normal(0, 0.02)
        fz = shoulder_z + 0.06 + t * 0.02 + rng.normal(0, 0.02)
        pts.append((fx, fy, fz, 'hand'))

    # ── Torch — small cylinder + flame at top ──
    torch_x = shoulder_x + 0.11
    torch_y_base = shoulder_y + 0.65
    torch_z = shoulder_z + 0.08

    # Torch handle
    for _ in range(200):
        ty = rng.uniform(torch_y_base - 0.05, torch_y_base + 0.08)
        tr = 0.03 + rng.normal(0, 0.005)
        angle = rng.uniform(0, 2*math.pi)
        tx = torch_x + math.cos(angle) * tr
        tz = torch_z + math.sin(angle) * tr
        pts.append((tx, ty, tz, 'torch'))

    # Flame — flickering upward cluster
    flame_y = torch_y_base + 0.08
    for _ in range(300):
        fy = flame_y + rng.uniform(0, 0.12)
        # Flame narrows at top
        fr = 0.04 * (1 - (fy - flame_y) / 0.13)
        fx = torch_x + rng.normal(0, 0.025)
        fz = torch_z + rng.normal(0, 0.025)
        pts.append((fx, fy, fz, 'flame'))

    # ── Left arm — bent, holding tablet ──
    lshoulder_x = -0.16
    lshoulder_z = 0.04
    # Upper arm
    for _ in range(350):
        t = rng.uniform(0, 1)
        ax = lshoulder_x - t * 0.05 + rng.normal(0, 0.025)
        ay = shoulder_y + t * 0.05 + rng.normal(0, 0.02)
        az = lshoulder_z + t * 0.02 + rng.normal(0, 0.02)
        pts.append((ax, ay, az, 'larm'))

    # Forearm + hand holding tablet
    for _ in range(250):
        t = rng.uniform(0, 1)
        ax = lshoulder_x - 0.05 - t * 0.02 + rng.normal(0, 0.02)
        ay = shoulder_y + 0.05 + t * 0.15 + rng.normal(0, 0.02)
        az = lshoulder_z + 0.02 + t * 0.05 + rng.normal(0, 0.02)
        pts.append((ax, ay, az, 'lhand'))

    # ── Tablet — rectangular slab ──
    tablet_x = lshoulder_x - 0.07
    tablet_cy = shoulder_y + 0.18
    tablet_z = lshoulder_z + 0.07
    for _ in range(350):
        tx = tablet_x + rng.uniform(-0.02, 0.02)
        ty = tablet_cy + rng.uniform(-0.1, 0.1)
        tz = tablet_z + rng.uniform(-0.03, 0.03)
        pts.append((tx, ty, tz, 'tablet'))

    # ── Pedestal/base — rectangular block ──
    for _ in range(600):
        px = rng.uniform(-0.18, 0.18)
        py = rng.uniform(-1.05, -0.9)
        pz = rng.uniform(-0.15, 0.15)
        pts.append((px, py, pz, 'pedestal'))

    # Pedestal upper ledge
    for _ in range(200):
        px = rng.uniform(-0.20, 0.20)
        py = rng.uniform(-0.92, -0.88)
        pz = rng.uniform(-0.17, 0.17)
        pts.append((px, py, pz, 'pedestal'))

    return pts


def project_point(x, y, z, ox, oy, tilt_x=0.30, rot_y=0.78, scale=1.0):
    """Project 3D point to 2D. rot_y=0.78 ≈ 45° viewing angle."""
    # Rotate around X axis (tilt forward)
    cos_x, sin_x = math.cos(tilt_x), math.sin(tilt_x)
    y2 = y * cos_x - z * sin_x
    z2 = y * sin_x + z * cos_x

    # Rotate around Y axis (~45° side view for best dragon profile)
    cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
    x2 = x * cos_y + z2 * sin_y
    z3 = -x * sin_y + z2 * cos_y

    # Project
    px = ox + (x2 - z3 * 0.3) * scale
    py = oy + (y2 - z3 * 0.2) * scale
    return px, py, z3  # return z for depth sorting


# ── Layers ──────────────────────────────────────────────────

def layer_background():
    """Dark tech background with subtle radial gradient."""
    img = Image.new('RGBA', (W, H), DARK + (255,))
    draw = ImageDraw.Draw(img)

    cx, cy = W * 0.55, H * 0.45
    for y in range(0, H, 4):
        for x_chunk in range(0, W, 8):
            dx = x_chunk - cx
            dy = y - cy
            dist = math.sqrt(dx**2 + dy**2)
            t = max(0, 1 - dist / max(W, H))
            glow = int(t * 18)
            if glow > 0:
                warm = blend(DARK, DARK_WARM, t * 0.3)
                draw.line([(x_chunk, y), (x_chunk+7, y)], fill=warm+(glow,))

    return img


def layer_grid():
    """Subtle tech grid — very fine, like a digital surface."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(42)

    step = 60
    for x in range(0, W, step):
        a = 10 + rng.randint(-2, 2)
        draw.line([(x, 0), (x, H)], fill=SLATE+(a,), width=1)
    for y in range(0, H, step):
        a = 10 + rng.randint(-2, 2)
        draw.line([(0, y), (W, y)], fill=SLATE+(a,), width=1)

    # Fine sub-grid
    fine = 15
    for x in range(0, W, fine):
        if x % step != 0:
            draw.line([(x, 0), (x, H)], fill=SLATE+(5,), width=1)
    for y in range(0, H, fine):
        if y % step != 0:
            draw.line([(0, y), (W, y)], fill=SLATE+(5,), width=1)

    return img


def layer_statue_point_cloud():
    """The hero visual — Statue of Liberty rendered as a dense ~9000 point cloud.
    Viewed at ~45° angle for the iconic silhouette."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    statue_pts = generate_statue_points()
    print(f"  Statue points: {len(statue_pts)}")

    # Center position — right side of canvas
    statue_ox = W * 0.52
    statue_oy = H * 0.56
    statue_scale = 1100

    # Project all points with depth
    projected = []
    for x, y, z, ptype in statue_pts:
        px, py, pz = project_point(x, y, z, statue_ox, statue_oy,
                                   tilt_x=0.26, rot_y=0.78, scale=statue_scale)
        projected.append((px, py, pz, ptype))

    # Sort by depth (far to near)
    projected.sort(key=lambda p: p[2])

    # Color mapping by part
    type_colors = {
        'robe':     TIFFANY,
        'chest':    TIFFANY_B,
        'head':     CHEESE,
        'face':     CHEESE_B,
        'crown':    TIFFANY_B,
        'arm':      TIFFANY,
        'hand':     CHEESE,
        'torch':    TIFFANY_B,
        'flame':    CORAL,
        'larm':     TIFFANY_D,
        'lhand':    TIFFANY,
        'tablet':   CHEESE,
        'pedestal': TIFFANY_D,
    }

    # Draw points with depth-based brightness
    for px, py, pz, ptype in projected:
        if px < -80 or px > W+80 or py < -80 or py > H+80:
            continue

        depth_norm = (pz + 1.5) / 3.0
        base_color = type_colors.get(ptype, TIFFANY)

        if depth_norm < 0.4:
            color = blend(base_color, CHEESE_B, 0.12 + depth_norm * 0.55)
        else:
            color = blend(base_color, TIFFANY_D, (depth_norm - 0.4) * 0.7)

        dot_r = 1.1 + (1 - depth_norm) * 3.0
        alpha = 155 + int((1 - depth_norm) * 90)

        draw_dot(draw, int(px), int(py), dot_r, color, min(255, alpha))

    # ── Floating particles — torch glow effect ──
    rng2 = np.random.RandomState(42)
    flame_cx = statue_ox + statue_scale * 0.12
    flame_cy = statue_oy - statue_scale * 0.48

    for _ in range(500):
        sx = flame_cx + rng2.normal(0, statue_scale * 0.15)
        sy = flame_cy + rng2.uniform(-statue_scale * 0.12, -statue_scale * 0.35)
        if sx < 50 or sx > W-50 or sy < 40 or sy > H-50:
            continue
        r = rng2.uniform(1.0, 4.5)
        color = random.choice([CORAL, CHEESE, TIFFANY_B])
        alpha = rng2.randint(25, 110)
        draw_dot(draw, int(sx), int(sy), r, color, alpha)

    # Ambient floating dots
    for _ in range(400):
        ax = statue_ox + rng2.normal(0, statue_scale * 0.55)
        ay = statue_oy + rng2.normal(0, statue_scale * 0.5)
        if ax < 50 or ax > W-50 or ay < 40 or ay > H-50:
            continue
        r = rng2.uniform(0.8, 3.0)
        color = random.choice([TIFFANY, TIFFANY_D, CHEESE])
        alpha = rng2.randint(15, 55)
        draw_dot(draw, int(ax), int(ay), r, color, alpha)

    # Bottom reflection
    for _ in range(250):
        gx = statue_ox + rng2.normal(0, statue_scale * 0.6)
        gy = statue_oy + statue_scale * 0.42 + rng2.uniform(0, statue_scale * 0.2)
        if gx < 60 or gx > W-60 or gy > H-60:
            continue
        r = rng2.uniform(0.8, 2.5)
        dist = abs(gx - statue_ox) / (statue_scale * 0.6)
        alpha = rng2.randint(8, max(9, int(50 - dist * 35)))
        draw_dot(draw, int(gx), int(gy), r, TIFFANY_D, alpha)

    return img


def layer_accent_geometry():
    """Geometric accent elements — rings, lines, wireframe fragments
    that create a tech/scientific visualization feel."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Left side: concentric technical rings (like radar/sonar)
    ring_cx, ring_cy = W * 0.12, H * 0.78
    for i, r in enumerate([40, 80, 130, 190, 260]):
        alpha = 80 - i * 12
        draw.ellipse([ring_cx-r, ring_cy-r, ring_cx+r, ring_cy+r],
                    outline=TIFFANY+(alpha,), width=max(1, 3-i//2))

    # Crosshair at ring center
    draw.line([(ring_cx-15, ring_cy), (ring_cx+15, ring_cy)], fill=TIFFANY+(100,), width=2)
    draw.line([(ring_cx, ring_cy-15), (ring_cx, ring_cy+15)], fill=TIFFANY+(100,), width=2)
    draw_dot(draw, ring_cx, ring_cy, 4, TIFFANY_B, 200)

    # Right side: horizontal measurement bars
    bar_x, bar_y = W * 0.85, H * 0.25
    bar_w = 280
    for i in range(5):
        y = bar_y + i * 45
        prog = 0.3 + i * 0.15
        draw.line([(bar_x, y), (bar_x + bar_w, y)], fill=SLATE+(40,), width=1)
        # Filled portion
        draw.line([(bar_x, y), (bar_x + int(bar_w * prog), y)],
                 fill=TIFFANY+(80 + i*15,), width=4)
        # End dot
        draw_dot(draw, bar_x + int(bar_w * prog), y, 5, TIFFANY_B, 160 + i*15)

    # Bottom tech line — full width accent
    draw.line([(80, H-45), (W-80, H-45)], fill=TIFFANY+(60,), width=1)
    draw.line([(80, H-43), (W-80, H-43)], fill=CHEESE+(25,), width=1)

    # Top thin accent
    draw.line([(80, 55), (W-80, 55)], fill=TIFFANY+(40,), width=1)

    # Left vertical measurement markings
    for i in range(8):
        y = 100 + i * (H-200) // 7
        draw.line([(65, y), (80, y)], fill=TIFFANY+(50,), width=1)

    # Right vertical measurement markings
    for i in range(8):
        y = 100 + i * (H-200) // 7
        draw.line([(W-80, y), (W-65, y)], fill=TIFFANY+(50,), width=1)

    # Diagonal tech lines — bottom left area
    for i in range(4):
        sx = 150 + i * 35
        sy = H - 120 - i * 60
        ex = sx + 200
        ey = sy + 80
        draw.line([(sx, sy), (ex, ey)], fill=CORAL+(20 + i*10,), width=1)

    return img


def layer_typography():
    """Bold, prominent typography — high contrast, large scale."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fonts
    title_font = load_font("Outfit-Bold.ttf", 260)
    title_font2 = load_font("Outfit-Regular.ttf", 260)
    sub_font = load_font("WorkSans-Bold.ttf", 72)
    sub_font_reg = load_font("WorkSans-Regular.ttf", 48)
    mono = load_font("JetBrainsMono-Bold.ttf", 28)
    mono_reg = load_font("JetBrainsMono-Regular.ttf", 24)
    mono_sm = load_font("JetBrainsMono-Regular.ttf", 20)
    tag_font = load_font("CrimsonPro-Italic.ttf", 38)
    accent_font = load_font("InstrumentSans-Bold.ttf", 28)

    # ── Main Title: "HybridMVS" — LARGE, spanning left side ──
    title = "HybridMVS"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Position: left side, vertically centered-ish
    tx = 80
    ty = H * 0.22

    # Multiple offset layers for a bold "printed" look with depth
    # Shadow layer — dark offset
    for dx, dy in [(6, 6), (4, 4), (2, 2)]:
        draw.text((tx+dx, ty+dy), title, font=title_font, fill=DARK+(180,))

    # Tiffany Blue glow offset
    draw.text((tx+3, ty+1), title, font=title_font, fill=TIFFANY+(100,))
    draw.text((tx-1, ty+3), title, font=title_font, fill=CHEESE+(60,))

    # Main fill — TIFFANY BLUE, bold and bright
    draw.text((tx, ty), title, font=title_font, fill=TIFFANY_B+(252,))

    # ── Subtitle line 1 — below title ──
    sub1 = "HYBRID 3D RECONSTRUCTION"
    bbox1 = draw.textbbox((0, 0), sub1, font=sub_font)
    sw1 = bbox1[2] - bbox1[0]
    sx1 = tx + 15
    sy1 = ty + th + 10

    # Cheese color subtitle for high contrast
    draw.text((sx1+2, sy1+2), sub1, font=sub_font, fill=DARK+(100,))
    draw.text((sx1, sy1), sub1, font=sub_font, fill=CHEESE+(240,))

    # ── Subtitle line 2 ──
    sub2 = "COLMAP SfM  ×  Deep MVS"
    bbox2 = draw.textbbox((0, 0), sub2, font=sub_font_reg)
    sx2 = tx + 20
    sy2 = sy1 + 80
    draw.text((sx2+1, sy2+1), sub2, font=sub_font_reg, fill=DARK+(80,))
    draw.text((sx2, sy2), sub2, font=sub_font_reg, fill=TIFFANY+(200,))

    # ── Tagline ──
    tagline = "从平面到立体  ·  From Pixels to Point Clouds"
    bbox_t = draw.textbbox((0, 0), tagline, font=tag_font)
    tx_t = tx + 25
    ty_t = sy2 + 70
    draw.text((tx_t, ty_t), tagline, font=tag_font, fill=CORAL+(180,))

    # ── Descriptor pills / badges ──
    badge_font = load_font("InstrumentSans-Bold.ttf", 26)
    badges = ["SfM", "MVS", "Deep Learning", "Point Cloud"]
    badge_x = tx + 30
    badge_y = ty_t + 65
    for i, badge in enumerate(badges):
        bx = badge_x + i * 220
        # Pill background
        bbox_b = draw.textbbox((0, 0), badge, font=badge_font)
        bw = bbox_b[2] - bbox_b[0] + 32
        bh = bbox_b[3] - bbox_b[1] + 18
        draw.rounded_rectangle(
            [bx-16, badge_y-9, bx+bw-16, badge_y+bh-9],
            radius=20,
            outline=TIFFANY+(120,),
            width=2,
            fill=TIFFANY+(12,)
        )
        draw.text((bx, badge_y), badge, font=badge_font, fill=TIFFANY+(220,))

    # ── Bottom info bar — spec sheet style ──
    info_y = H - 130
    left_x = 80
    right_x = W - 680

    # Left specs
    specs_left = [
        ("SYSTEM", "COLMAP 4.1 + CasMVSNet"),
        ("RESOLUTION", "PatchMatch + Deep MVS Fusion"),
        ("OUTPUT", "Dense Point Cloud + Mesh"),
    ]
    for i, (label, value) in enumerate(specs_left):
        y = info_y + i * 38
        draw.text((left_x, y), label, font=mono, fill=TIFFANY+(190,))
        draw.text((left_x + 210, y), value, font=mono_reg, fill=CHEESE+(180,))

    # Right specs
    specs_right = [
        ("GPU", "NVIDIA RTX 4060 · 8 GB"),
        ("ENGINE", "PyTorch 2.7 · CUDA 11.8"),
        ("TRAINING", "DTU + BlendedMVS"),
    ]
    for i, (label, value) in enumerate(specs_right):
        y = info_y + i * 38
        draw.text((right_x, y), label, font=mono, fill=CORAL+(180,))
        draw.text((right_x + 180, y), value, font=mono_reg, fill=CHEESE+(170,))

    # Bottom copyright / version line
    version_text = "v3.0  ·  STATUE OF LIBERTY  ·  Hybrid Reconstruction Pipeline"
    bbox_v = draw.textbbox((0, 0), version_text, font=mono_sm)
    vw = bbox_v[2] - bbox_v[0]
    draw.text(((W-vw)//2, H-48), version_text, font=mono_sm, fill=SLATE+(140,))

    # ── Top right: large numbered accent ──
    num_font = load_font("Outfit-Bold.ttf", 120)
    draw.text((W-350, 50), "03", font=num_font, fill=TIFFANY+(35,))

    return img


def layer_vignette():
    """Subtle edge darkening for depth."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 50
    for i in range(margin):
        a = int(15 * (1 - i/margin))
        draw.rectangle([i, i, W-i, H-i], outline=DARK+(a,), width=1)

    corner = 250
    for i in range(corner):
        a = int(12 * (1 - i/corner))
        if a <= 0: continue
        c = DARK+(a,)
        draw.line([(0,i),(corner-i,i)], fill=c, width=1)
        draw.line([(W-corner+i,i),(W,i)], fill=c, width=1)
        draw.line([(0,H-i),(corner-i,H-i)], fill=c, width=1)
        draw.line([(W-corner+i,H-i),(W,H-i)], fill=c, width=1)

    return img


# ── Assemble ────────────────────────────────────────────────
def create_poster_v2():
    layers = [
        ("Background",        layer_background()),
        ("Grid",              layer_grid()),
        ("Statue Point Cloud",  layer_statue_point_cloud()),
        ("Accent Geometry",   layer_accent_geometry()),
        ("Typography",        layer_typography()),
        ("Vignette",          layer_vignette()),
    ]

    canvas = Image.new('RGBA', (W, H), (0,0,0,0))
    for name, layer in layers:
        canvas = Image.alpha_composite(canvas, layer)
        print(f"  [OK] {name}")

    final = Image.new('RGB', (W, H), DARK)
    final.paste(canvas, mask=canvas.split()[3])
    final.save(OUTPUT, 'PNG', dpi=(300, 300))
    print(f"\n>> Saved: {OUTPUT}  ({W}x{H}, 300 DPI)")
    return final

if __name__ == "__main__":
    create_poster_v2()
