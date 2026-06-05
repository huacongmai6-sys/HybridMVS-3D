"""
Parallax Garden — Refined Poster for HybridMVS
Second pass: polish, tighten, elevate to museum quality.
Every element labored over with painstaking attention.
"""

import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Config ──────────────────────────────────────────────────
W, H = 2400, 3600
OUTPUT = "HybridMVS_Poster.png"
FONTS_DIR = r"C:\Users\xiaomai\.claude\skills\canvas-design\canvas-fonts"

# Refined thermal palette — cold measurement → warm emergence
C = {
    # Deep space — the measurement void
    "void":       (14, 16, 28),
    "abyss":      (16, 20, 36),
    # Slate — cartesian foundation
    "slate_dark": (20, 26, 46),
    "slate":      (24, 34, 58),
    "slate_med":  (32, 44, 72),
    # Silver — surveying instruments
    "silver_dim": (120, 132, 155),
    "silver":     (165, 178, 200),
    "silver_bri": (200, 210, 225),
    # Thermal midpoint
    "twilight":   (60, 55, 70),
    # Copper/amber — darkroom warmth
    "copper_dk":  (140, 90, 70),
    "copper":     (185, 125, 98),
    "copper_bri": (210, 150, 118),
    "amber":      (225, 168, 128),
    "ember":      (238, 192, 152),
    # Computation — neural spark
    "cyan_dk":    (20, 90, 120),
    "cyan":       (0, 195, 235),
    "cyan_bri":   (80, 220, 248),
    # Synaptic accents
    "chartreuse": (135, 185, 78),
    "mint":       (100, 180, 155),
    # Warm darks
    "warm_dark":  (40, 30, 26),
    "warm_dk2":   (50, 38, 32),
    # Neutrals
    "white":      (245, 242, 238),
    "off_white":  (228, 225, 220),
    "cream":      (240, 232, 222),
}

# ── Helpers ─────────────────────────────────────────────────
def load_font(name, size):
    path = f"{FONTS_DIR}/{name}"
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def lerp(a, b, t):
    return tuple(int(ai + (bi - ai) * t) for ai, bi in zip(a, b))

def blend(c1, c2, t):
    t = max(0, min(1, t))
    return tuple(max(0, min(255, int(c1[i] + (c2[i] - c1[i]) * t))) for i in range(3))

def draw_dot(draw, x, y, r, color, alpha=255):
    c = color + (alpha,) if len(color) == 3 else color
    draw.ellipse([x-r, y-r, x+r, y+r], fill=c)

def draw_glow_dot(draw, x, y, r, color, alpha):
    """Dot with soft glow halo."""
    if r > 2:
        halo_r = r * 2.5
        halo = Image.new('RGBA', (int(halo_r*2+2), int(halo_r*2+2)), (0,0,0,0))
        hdraw = ImageDraw.Draw(halo)
        for hr in range(int(halo_r), 0, -1):
            a = int(alpha * 0.15 * (hr / halo_r))
            hdraw.ellipse([halo_r-hr, halo_r-hr, halo_r+hr, halo_r+hr],
                         fill=color+(a,))
        layer.paste(halo, (int(x-halo_r), int(y-halo_r)), halo)
    c = color + (alpha,)
    draw.ellipse([x-r, y-r, x+r, y+r], fill=c)


# ── Layer Builders ──────────────────────────────────────────

def layer_background():
    """Deep void with subtle atmospheric gradient."""
    img = Image.new('RGBA', (W, H), C["void"] + (255,))
    draw = ImageDraw.Draw(img)

    # Vertical thermal shift — barely perceptible
    for y in range(H):
        t = y / H
        top = C["abyss"]
        bot = blend(C["abyss"], C["warm_dark"], 0.30)
        color = lerp(top, bot, t)
        draw.line([(0, y), (W, y)], fill=color + (255,))

    # Subtle horizontal warm glow near center (like a light source)
    cx, cy = W // 2, H * 0.45
    for y in range(H):
        for x_chunk in range(0, W, 4):
            dx = x_chunk - cx
            dy = y - cy
            dist = math.sqrt(dx**2 + (dy*1.3)**2)
            max_dist = max(W, H)
            t = max(0, 1 - dist / max_dist)
            glow = int(t * 8)
            if glow > 0:
                warm = blend(C["void"], C["warm_dk2"], t * 0.25)
                draw.line([(x_chunk, y), (x_chunk+3, y)], fill=warm+(glow,))

    return img


def layer_measurement_grid():
    """The cartesian skeleton — extremely subtle, like surveying marks on dark paper."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    rng = random.Random(42)

    # Major grid — barely visible
    spacing = 80
    for x in range(0, W, spacing):
        a = 14 + rng.randint(-3, 3)
        draw.line([(x, 0), (x, H)], fill=C["slate_med"]+(a,), width=1)

    for y in range(0, H, spacing):
        a = 14 + rng.randint(-3, 3)
        draw.line([(0, y), (W, y)], fill=C["slate"]+(a,), width=1)

    # Fine subdivision
    fine = 20
    for x in range(0, W, fine):
        if x % spacing != 0:
            draw.line([(x, 0), (x, H)], fill=C["slate"]+(7,), width=1)
    for y in range(0, H, fine):
        if y % spacing != 0:
            draw.line([(0, y), (W, y)], fill=C["slate"]+(7,), width=1)

    # Origin crosshair — bottom-left area
    ox, oy = 220, H - 320
    axis_alpha = 75
    # X-axis
    draw.line([(ox, oy), (ox + 200, oy)], fill=C["silver_dim"]+(axis_alpha,), width=2)
    # Y-axis (up)
    draw.line([(ox, oy), (ox, oy - 200)], fill=C["silver_dim"]+(axis_alpha,), width=2)
    # Arrowheads
    draw.line([(ox+200, oy), (ox+186, oy-7)], fill=C["silver_dim"]+(axis_alpha,), width=2)
    draw.line([(ox+200, oy), (ox+186, oy+7)], fill=C["silver_dim"]+(axis_alpha,), width=2)
    draw.line([(ox, oy-200), (ox-7, oy-186)], fill=C["silver_dim"]+(axis_alpha,), width=2)
    draw.line([(ox, oy-200), (ox+7, oy-186)], fill=C["silver_dim"]+(axis_alpha,), width=2)
    # Origin dot
    draw_dot(draw, ox, oy, 4, C["silver_dim"], axis_alpha + 30)

    return img


def layer_parallax_field():
    """The stereoscopic heart — offset dot matrices creating depth illusion.
    Two interleaved dot fields with varying disparity that suggests a 3D surface
    to those who look closely. The core metaphor: depth from parallax."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    rng = random.Random(99)
    cx, cy = W // 2, H * 0.44
    field_w, field_h = 1500, 1900
    left = cx - field_w // 2
    top = cy - field_h // 2

    # Dense parallax dot field
    dot_step = 38
    max_dist = math.sqrt((field_w/2)**2 + (field_h/2)**2)

    for row_y in range(int(top), int(top + field_h), dot_step):
        for col_x in range(int(left), int(left + field_w), dot_step):
            dx = col_x - cx
            dy = row_y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            # Parallax strongest at center, fading toward edges
            parallax = (1.0 - (dist / max_dist) * 0.65)

            shift = parallax * 20  # Max displacement in pixels

            # Channel 1: Cyan dots (the "neural" eye) — offset left
            x1 = col_x - shift * 0.5
            y1 = row_y - shift * 0.25
            r1 = 2.5 + parallax * 2.5
            a1 = 35 + int(parallax * 95)
            draw_dot(draw, x1, y1, r1, C["cyan"], a1)

            # Channel 2: Amber dots (the "geometric" eye) — offset right
            x2 = col_x + shift * 0.5
            y2 = row_y + shift * 0.25
            r2 = 2.0 + parallax * 2.0
            a2 = 30 + int(parallax * 80)
            draw_dot(draw, x2, y2, r2, C["amber"], a2)

            # Disparity connector — the vector between the two views
            if parallax > 0.35 and rng.random() < 0.25:
                la = int(a1 * 0.25)
                draw.line([(x1, y1), (x2, y2)], fill=C["silver_dim"]+(la,), width=1)

    # Larger reference dots — "feature correspondences" tracked across views
    rng2 = random.Random(42)
    for _ in range(180):
        x = cx + int(rng2.gauss(0, field_w * 0.22))
        y = cy + int(rng2.gauss(0, field_h * 0.22))
        x = max(120, min(W-120, x))
        y = max(120, min(H-120, y))

        r = rng2.uniform(4, 11)
        alpha = rng2.randint(55, 135)
        color = rng2.choice(["cyan", "cyan_bri", "amber", "copper", "copper_bri", "mint"])
        draw_dot(draw, x, y, r, C[color], alpha)

        # Ghost partner — the parallax companion
        sx = x + rng2.uniform(-18, 18)
        sy = y + rng2.uniform(-12, 12)
        draw_dot(draw, sx, sy, r * 0.35, C[color], alpha // 3)

        # Faint connector
        if rng2.random() < 0.3:
            draw.line([(x, y), (sx, sy)], fill=C["silver_dim"]+(alpha//4,), width=1)

    # Concentric parallax rings — depth contour lines
    for ring_r in np.arange(100, field_w//2, 150):
        ring_pts = []
        for angle in np.linspace(0, 2*math.pi, 120):
            rx = cx + math.cos(angle) * ring_r
            ry = cy + math.sin(angle) * ring_r * 1.25  # Slight vertical stretch
            ring_pts.append((rx, ry))

        ring_alpha = 18 + int(25 * (1 - ring_r / (field_w/2)))
        for i in range(len(ring_pts)):
            j = (i + 1) % len(ring_pts)
            draw.line([ring_pts[i], ring_pts[j]], fill=C["silver_dim"]+(ring_alpha,), width=1)

    return img


def layer_wireframe_forms():
    """Geometric volumes emerging from the cartesian plane —
    wireframe cubes, tetrahedra, geodesic fragments.
    Forms warm from cyan (flat/measured) to copper (volumetric/emerged)."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    rng = random.Random(77)

    def project_iso(x, y, z, ox, oy, scale=1.0):
        """Clean isometric projection."""
        angle = math.radians(30)
        px = ox + (x - y) * math.cos(angle) * scale
        py = oy + (x + y) * math.sin(angle) * scale - z * scale
        return px, py

    # ── Main voxel assembly — right-center, the primary emergence ──
    ox1, oy1 = W * 0.56, H * 0.40
    scale1 = 165

    for lz in range(6):
        z = lz * 0.55
        t_height = z / 3.0
        color = blend(C["cyan_dk"], C["copper"], t_height)
        alpha = 55 + int(t_height * 90)

        for bx in range(-1, 2):
            for by in range(-1, 2):
                if rng.random() < 0.3:
                    continue

                s = 1.0
                corners_3d = [
                    (bx*s,      by*s,      z),
                    (bx*s + s,  by*s,      z),
                    (bx*s + s,  by*s + s,  z),
                    (bx*s,      by*s + s,  z),
                    (bx*s,      by*s,      z + s),
                    (bx*s + s,  by*s,      z + s),
                    (bx*s + s,  by*s + s,  z + s),
                    (bx*s,      by*s + s,  z + s),
                ]
                corners = [project_iso(*c, ox1, oy1, scale1) for c in corners_3d]

                # Bottom face
                draw.polygon([corners[0], corners[1], corners[2], corners[3]],
                           outline=color+(alpha,), fill=color+(max(6, alpha//3),))
                # Top face
                draw.polygon([corners[4], corners[5], corners[6], corners[7]],
                           outline=color+(alpha,), fill=color+(max(6, alpha//3),))
                # Vertical edges
                for i in range(4):
                    draw.line([corners[i], corners[i+4]], fill=color+(alpha,), width=1)

    # ── Tetrahedron cluster — left, floating, computational ──
    ox2, oy2 = W * 0.28, H * 0.48
    scale2 = 110

    for i in range(5):
        angle = i * math.pi / 2.5 + 0.15
        rx = math.cos(angle) * 1.6
        ry = math.sin(angle) * 1.6
        rz = 0.4 + i * 0.4

        h_tet = 1.3
        pts_3d = [
            (rx,           ry,           rz),
            (rx + 0.75,    ry,           rz - 0.25),
            (rx,           ry + 0.75,    rz - 0.25),
            (rx + 0.35,    ry + 0.35,    rz + h_tet),
        ]
        pts = [project_iso(*p, ox2, oy2, scale2) for p in pts_3d]

        t = i / 4.0
        color = blend(C["cyan"], C["mint"], t)
        alpha = 45 + int(t * 80)
        lw = max(1, int(2.5 - t))

        edges = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
        for e1, e2 in edges:
            draw.line([pts[e1], pts[e2]], fill=color+(alpha,), width=lw)

        # Small node dots at vertices
        for pt in pts:
            draw_dot(draw, int(pt[0]), int(pt[1]), 2, color, alpha)

    # ── Geodesic arcing — right side, like a dome under construction ──
    ox3, oy3 = W * 0.74, H * 0.52
    scale3 = 105
    prev_ring_pts = None

    for ring in range(5):
        ring_z = ring * 0.45
        ring_r = 1.3 - ring * 0.12
        n_pts = 9 - ring

        ring_pts = []
        for j in range(n_pts):
            a = j * 2 * math.pi / n_pts + ring * 0.25
            ring_pts.append((math.cos(a) * ring_r, math.sin(a) * ring_r, ring_z))

        t_ring = ring / 4.0
        color = blend(C["copper_dk"], C["amber"], t_ring)
        alpha = 65 + int(t_ring * 100)
        lw = max(1, 3 - ring)

        proj = [project_iso(*p, ox3, oy3, scale3) for p in ring_pts]

        # Ring connections
        for j in range(n_pts):
            jn = (j + 1) % n_pts
            draw.line([proj[j], proj[jn]], fill=color+(alpha,), width=lw)

        # Vertical struts
        if prev_ring_pts is not None:
            prev_proj = [project_iso(*p, ox3, oy3, scale3) for p in prev_ring_pts]
            for j in range(min(n_pts, len(prev_proj))):
                draw.line([proj[j], prev_proj[j]], fill=color+(alpha//2,), width=1)

        prev_ring_pts = ring_pts

    # ── Measurement projection lines — grid-to-volume connections ──
    for _ in range(25):
        x1 = rng.uniform(120, W - 120)
        y1 = rng.uniform(H * 0.58, H - 250)
        x2 = x1 + rng.uniform(-100, 100)
        y2 = y1 - rng.uniform(120, 350)
        a = rng.randint(12, 40)
        color = blend(C["silver_dim"], C["cyan_dk"], rng.random() * 0.4)
        draw.line([(x1, y1), (x2, y2)], fill=color+(a,), width=1)

        # Dash marks
        dl = 6
        color_dash = color+(min(255, a+10),)
        draw.line([(x1-dl, y1), (x1+dl, y1)], fill=color_dash, width=1)
        draw.line([(x2-dl, y2), (x2+dl, y2)], fill=color_dash, width=1)

    return img


def layer_point_cloud():
    """Dimensional particles — dense reconstruction surface below,
    sparse rising information stream above.
    The MVS point cloud made visual poetry."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    rng = np.random.RandomState(42)

    # ── Dense surface — the reconstructed terrain in warm tones ──
    cx, cy = W * 0.48, H * 0.74
    n_surface = 3500

    xs = rng.normal(cx, 420, n_surface)
    ys = rng.normal(cy, 320, n_surface)

    for i in range(n_surface):
        x = xs[i]
        y = ys[i]
        if x < 60 or x > W-60 or y < H*0.48 or y > H-150:
            continue

        dist = math.sqrt((x - cx)**2 + (y - cy)**2)
        r = max(0.8, 3.5 - dist / 280)
        t = min(1.0, dist / 420)
        color = blend(C["amber"], blend(C["copper_dk"], C["cyan_dk"], t*0.5), t)
        alpha = max(18, int(175 - dist / 6))

        draw_dot(draw, int(x), int(y), r, color, alpha)

    # ── Rising particle stream — information ascending ──
    n_rise = 1000
    xs_r = rng.normal(cx, 520, n_rise)
    ys_r = rng.uniform(H * 0.08, H * 0.55, n_rise)

    for i in range(n_rise):
        x = xs_r[i]
        y = ys_r[i]
        if x < 80 or x > W-80:
            continue

        t_height = y / H
        r = rng.uniform(1.0, 3.8)
        color = blend(C["cyan"], C["chartreuse"], 1.0 - t_height)
        alpha = rng.randint(25, 105)

        draw_dot(draw, int(x), int(y), r, color, alpha)

    # ── Accent clusters — feature correspondences ──
    clusters = [
        (W*0.24, H*0.36, C["cyan"],      42, 28),
        (W*0.66, H*0.33, C["mint"],       35, 22),
        (W*0.44, H*0.47, C["amber"],      40, 26),
        (W*0.31, H*0.56, C["copper_bri"], 38, 24),
        (W*0.76, H*0.60, C["cyan_dk"],    35, 20),
        (W*0.58, H*0.64, C["copper"],     30, 25),
    ]

    for ax, ay, color, count, spread in clusters:
        for _ in range(count):
            x = int(ax + rng.normal(0, spread))
            y = int(ay + rng.normal(0, spread))
            r = rng.uniform(2, 6)
            alpha = rng.randint(75, 175)
            draw_dot(draw, x, y, r, color, alpha)

            # Dot's parallax ghost
            gx = int(x + rng.uniform(-8, 8))
            gy = int(y + rng.uniform(-6, 6))
            draw_dot(draw, gx, gy, r * 0.3, color, alpha // 4)

    return img


def layer_accent_elements():
    """Horizontal thermal dividers + vertical surveyor reference line."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Horizontal accents marking thermal transitions
    accents = [
        (0.30, C["cyan"],      155),
        (0.50, blend(C["cyan"], C["copper"], 0.35), 110),
        (0.66, C["copper_bri"], 80),
    ]

    for y_frac, color, alpha in accents:
        y = int(H * y_frac)
        # Core line
        draw.line([(W*0.07, y), (W*0.93, y)], fill=color+(alpha,), width=1)
        # Soft glow above/below
        for dy in range(1, 10):
            a = alpha // (dy * 2 + 1)
            draw.line([(W*0.09, y-dy), (W*0.91, y-dy)], fill=color+(a,), width=1)
            draw.line([(W*0.09, y+dy), (W*0.91, y+dy)], fill=color+(a,), width=1)

    # Vertical reference line — left margin
    vx = 130
    draw.line([(vx, H*0.12), (vx, H*0.88)], fill=C["silver_dim"]+(22,), width=1)
    for y in np.arange(H*0.15, H*0.89, 80):
        draw.line([(vx-9, int(y)), (vx+9, int(y))], fill=C["silver_dim"]+(30,), width=1)

    # Right margin subtle line
    vx2 = W - 130
    draw.line([(vx2, H*0.15), (vx2, H*0.85)], fill=C["silver_dim"]+(12,), width=1)

    return img


def layer_typography():
    """Minimal text as sculptural element — the wordmark, annotations, surveyor marks."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fonts
    title_bold = load_font("Outfit-Bold.ttf", 190)
    title_reg = load_font("Outfit-Regular.ttf", 190)
    sub_font = load_font("WorkSans-Regular.ttf", 42)
    sub_italic = load_font("WorkSans-Italic.ttf", 42)
    tag_font = load_font("CrimsonPro-Italic.ttf", 34)
    mono = load_font("JetBrainsMono-Regular.ttf", 22)
    mono_bold = load_font("JetBrainsMono-Bold.ttf", 22)
    small_mono = load_font("JetBrainsMono-Regular.ttf", 18)
    tiny_mono = load_font("JetBrainsMono-Regular.ttf", 15)
    top_font = load_font("InstrumentSans-Regular.ttf", 19)

    # ── Primary wordmark ──
    title = "HybridMVS"
    bbox = draw.textbbox((0, 0), title, font=title_bold)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) // 2
    ty = H * 0.51

    # Layered glows for sculptural depth
    glow_offsets = [
        (4, 4, C["cyan"], 50),
        (-3, -3, C["amber"], 35),
        (1, 1, C["cyan"], 30),
        (-1, -1, C["copper"], 25),
    ]
    for dx, dy, color, alpha in glow_offsets:
        draw.text((tx+dx, ty+dy), title, font=title_bold, fill=color+(alpha,))

    # Main text — slightly warm silver
    title_color = blend(C["white"], C["cream"], 0.3)
    draw.text((tx, ty), title, font=title_bold, fill=title_color+(248,))

    # ── Subtitle ──
    subtitle = "Hybrid 3D Reconstruction System"
    bbox_sub = draw.textbbox((0, 0), subtitle, font=sub_font)
    sw = bbox_sub[2] - bbox_sub[0]
    sx = (W - sw) // 2
    sy = ty + 220

    # Subtle backdrop line for subtitle
    line_y = sy + 28
    draw.line([(sx, line_y), (sx + sw, line_y)], fill=C["silver_dim"]+(35,), width=1)

    draw.text((sx, sy), subtitle, font=sub_font, fill=C["silver"]+(195,))

    # ── Tagline ──
    tagline = "— 从平面到立体 · From Pixels to Point Clouds —"
    bbox_tag = draw.textbbox((0, 0), tagline, font=tag_font)
    ttw = bbox_tag[2] - bbox_tag[0]
    ttx = (W - ttw) // 2
    tty = sy + 70
    draw.text((ttx, tty), tagline, font=tag_font, fill=C["copper"]+(155,))

    # ── Top reference field ──
    draw.text((W - 390, 92), "PARALLAX GARDEN", font=top_font, fill=C["cyan"]+(85,))
    draw.text((W - 430, 118), "Design Philosophy / Manifesto", font=top_font, fill=C["silver_dim"]+(45,))

    # Top scale bar
    for i in range(6):
        x = 320 + i * 350
        val = f"{i*5:02d}"
        draw.text((x, 75), val, font=tiny_mono, fill=C["silver_dim"]+(45,))
        draw.line([(x, 62), (x, 70)], fill=C["silver_dim"]+(35,), width=1)

    # ── Bottom info — surveyor-style ──
    bottom_y = H - 190
    left_x = 180
    right_x = W - 560

    # Left block
    left_lines = [
        ("SYSTEM:",    "COLMAP SfM + CasMVSNet"),
        ("RECONSTRUCTION:", "PatchMatch + Deep MVS"),
        ("PIPELINE:",  "SfM → Depth → Fusion"),
    ]
    for i, (label, value) in enumerate(left_lines):
        y_pos = bottom_y + i * 35
        draw.text((left_x, y_pos), label, font=mono_bold, fill=C["silver"]+(105,))
        draw.text((left_x + 170, y_pos), value, font=mono, fill=C["silver"]+(130,))

    # Right block
    right_lines = [
        ("REF:",   "DTU / BlendedMVS"),
        ("GPU:",   "NVIDIA RTX 4060 · 8GB"),
        ("BUILD:", "PyTorch 2.7 · CUDA 11.8"),
    ]
    for i, (label, value) in enumerate(right_lines):
        y_pos = bottom_y + i * 35
        draw.text((right_x, y_pos), label, font=mono_bold, fill=C["copper"]+(95,))
        draw.text((right_x + 65, y_pos), value, font=mono, fill=C["copper"]+(125,))

    # ── Coordinate annotations ──
    ox, oy = 220, H - 320
    draw.text((ox - 35, oy + 8), "(0,0)", font=small_mono, fill=C["silver_dim"]+(90,))
    draw.text((ox + 195, oy - 22), "x", font=small_mono, fill=C["silver_dim"]+(70,))
    draw.text((ox - 22, oy - 215), "y", font=small_mono, fill=C["silver_dim"]+(70,))

    # Vertical margin scale
    for i, val in enumerate(["8.0", "6.0", "4.0", "2.0", "0.0"]):
        yy = int(H * 0.19 + i * H * 0.12)
        draw.text((90, yy), val, font=tiny_mono, fill=C["silver_dim"]+(55,))

    # ── Key accent callout ──
    callout_font = load_font("InstrumentSerif-Italic.ttf", 26)
    draw.text((W*0.16, H*0.31), "depth from", font=callout_font, fill=C["cyan"]+(70,))
    draw.text((W*0.16, H*0.31 + 32), "parallax", font=callout_font, fill=C["cyan"]+(60,))

    return img


def layer_vignette():
    """Atmospheric edge darkening for depth and focus."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Edge soft darken
    margin = 80
    for i in range(margin):
        alpha = int(12 * (1 - i / margin))
        draw.rectangle([i, i, W-i, H-i], outline=C["void"]+(alpha,), width=1)

    # Corner gradients — atmospheric vignette
    corner = 350
    for i in range(corner):
        alpha = int(10 * (1 - i / corner))
        if alpha <= 0:
            continue
        c = C["void"] + (alpha,)
        # Four corners
        draw.line([(0, i), (corner-i, i)], fill=c, width=1)  # TL
        draw.line([(W-corner+i, i), (W, i)], fill=c, width=1)  # TR
        draw.line([(0, H-i), (corner-i, H-i)], fill=c, width=1)  # BL
        draw.line([(W-corner+i, H-i), (W, H-i)], fill=c, width=1)  # BR

    return img


# ── Assemble ────────────────────────────────────────────────
def create_poster_refined():
    print("Building layers with painstaking attention...")

    layers = [
        ("Background",       layer_background()),
        ("Grid",             layer_measurement_grid()),
        ("Parallax Field",   layer_parallax_field()),
        ("Wireframe Bloom",  layer_wireframe_forms()),
        ("Point Cloud",      layer_point_cloud()),
        ("Accents",          layer_accent_elements()),
        ("Typography",       layer_typography()),
        ("Vignette",         layer_vignette()),
    ]

    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for name, layer in layers:
        canvas = Image.alpha_composite(canvas, layer)
        print(f"  [OK] {name}")

    # Final composite to RGB
    final = Image.new('RGB', (W, H), C["void"])
    final.paste(canvas, mask=canvas.split()[3])

    # Subtle overall warmth adjustment
    enhancer = ImageEnhance.Color(final)
    final = enhancer.enhance(1.08)

    final.save(OUTPUT, 'PNG', dpi=(300, 300), optimize=True)
    print(f"\n>> Poster saved: {OUTPUT}")
    print(f"  Size: {W}×{H} px · 300 DPI · {(W/300):.1f}×{(H/300):.1f} inches")
    return final


if __name__ == "__main__":
    create_poster_refined()
