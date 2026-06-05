"""
Parallax Garden — Poster for HybridMVS
A visual philosophy of dimensional emergence.
Generative art exploring the threshold where 2D becomes 3D.
"""

import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ── Config ──────────────────────────────────────────────────
W, H = 2400, 3600  # 2:3 poster ratio
OUTPUT = "HybridMVS_Poster.png"
FONTS_DIR = r"C:\Users\xiaomai\.claude\skills\canvas-design\canvas-fonts"

# Color palette — thermal gradient: cold measurement → warm emergence
C = {
    "void":      (18, 18, 36),       # Deep space indigo
    "slate":     (22, 30, 52),       # Dark slate blue
    "midnight":  (28, 40, 68),       # Midnight measurement
    "silver":    (165, 175, 195),    # Surveying instrument silver
    "frost":     (210, 218, 232),    # Cold highlight
    "copper":    (195, 130, 105),    # Warm emergence copper
    "amber":     (220, 160, 120),    # Darkroom safelight
    "ember":     (235, 185, 145),    # Glowing ember
    "cyan":      (0, 200, 240),      # Neural spark
    "cyan_dim":  (30, 120, 155),     # Subdued cyan
    "chartreuse":(140, 185, 80),     # Synaptic green
    "warm_dark": (45, 35, 30),       # Warm dark for depth
    "white":     (242, 240, 238),    # Soft white
    "off_white": (225, 222, 218),    # Aged paper white
}

# ── Helpers ─────────────────────────────────────────────────
def load_font(name, size):
    """Load a font from canvas-fonts directory."""
    path = f"{FONTS_DIR}/{name}"
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def lerp(a, b, t):
    return tuple(int(ai + (bi - ai) * t) for ai, bi in zip(a, b))

def blend_colors(c1, c2, t):
    """Blend two RGB tuples."""
    return tuple(max(0, min(255, int(c1[i] + (c2[i] - c1[i]) * t))) for i in range(3))

def circle_mask(size, feather=0):
    """Create a circular gradient mask."""
    arr = np.zeros((size, size), dtype=np.float32)
    cx = cy = size / 2
    for y in range(size):
        for x in range(size):
            d = math.sqrt((x - cx)**2 + (y - cy)**2)
            r = size / 2
            if feather > 0 and d > r - feather:
                arr[y, x] = max(0, (r - d) / feather)
            else:
                arr[y, x] = 1.0 if d < r else 0.0
    return arr

def draw_dot(draw, x, y, r, color, alpha=255):
    """Draw a soft dot."""
    c = color + (alpha,) if len(color) == 3 else color
    draw.ellipse([x - r, y - r, x + r, y + r], fill=c)

def draw_crosshair(draw, x, y, size, color, alpha=180):
    """Draw a surveyor's crosshair marker."""
    c = color + (alpha,) if len(color) == 3 else color
    lw = max(1, size // 10)
    # Circle
    draw.ellipse([x-size, y-size, x+size, y+size], outline=c, width=lw)
    # Cross
    draw.line([(x-size//2, y), (x+size//2, y)], fill=c, width=lw)
    draw.line([(x, y-size//2), (x, y+size//2)], fill=c, width=lw)

# ── Main Canvas Creation ────────────────────────────────────
def create_poster():
    # Create base canvas with deep indigo
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))

    # Layer 0: Deep void background
    bg = Image.new('RGBA', (W, H), C["void"] + (255,))
    img = Image.alpha_composite(img, bg)

    # Layer 1: Atmospheric depth gradient (bottom warm, top cool)
    grad = Image.new('RGBA', (W, H))
    gdraw = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / H
        # Cool slate at top, warming toward bottom
        top_color = C["slate"]
        bot_color = blend_colors(C["slate"], C["warm_dark"], 0.4)
        color = lerp(top_color, bot_color, t)
        gdraw.line([(0, y), (W, y)], fill=color + (255,))
    img = Image.alpha_composite(img, grad)

    # Layer 2: Measurement grid — the cartesian foundation
    grid_layer = create_measurement_grid()
    img = Image.alpha_composite(img, grid_layer)

    # Layer 3: Parallax offset zone — the stereoscopic heart
    parallax_layer = create_parallax_zone()
    img = Image.alpha_composite(img, parallax_layer)

    # Layer 4: Geometric wireframe bloom — forms emerging from grid
    wireframe_layer = create_wireframe_bloom()
    img = Image.alpha_composite(img, wireframe_layer)

    # Layer 5: Point cloud scatter — dimensional particles
    points_layer = create_point_cloud()
    img = Image.alpha_composite(img, points_layer)

    # Layer 6: Gradient accent bars — thermal transition zones
    accent_layer = create_accent_bars()
    img = Image.alpha_composite(img, accent_layer)

    # Layer 7: Typography — the wordmark and annotations
    type_layer = create_typography()
    img = Image.alpha_composite(img, type_layer)

    # Layer 8: Vignette frame — darken edges for depth
    vignette = create_vignette()
    img = Image.alpha_composite(img, vignette)

    # Convert to RGB and save
    final = Image.new('RGB', (W, H), (0, 0, 0))
    final.paste(img, mask=img.split()[3])
    final.save(OUTPUT, 'PNG', dpi=(300, 300))
    print(f"Poster saved: {OUTPUT}")
    return final


# ── Layer Functions ─────────────────────────────────────────

def create_measurement_grid():
    """Subtle cartesian grid — the surveying skeleton."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Major grid lines — very subtle
    grid_spacing = 80
    line_alpha = 18

    for x in range(0, W, grid_spacing):
        # Vary alpha slightly for a hand-drawn feel
        a = line_alpha + random.randint(-4, 4)
        draw.line([(x, 0), (x, H)], fill=C["silver"] + (a,), width=1)

    for y in range(0, H, grid_spacing):
        a = line_alpha + random.randint(-4, 4)
        draw.line([(0, y), (W, y)], fill=C["silver"] + (a,), width=1)

    # Secondary finer grid
    fine_spacing = 20
    for x in range(0, W, fine_spacing):
        if x % grid_spacing == 0:
            continue
        draw.line([(x, 0), (x, H)], fill=C["silver"] + (8,), width=1)

    for y in range(0, H, fine_spacing):
        if y % grid_spacing == 0:
            continue
        draw.line([(0, y), (W, y)], fill=C["silver"] + (8,), width=1)

    # Coordinate origin marker — bottom-left area
    ox, oy = 200, H - 300
    draw.line([(ox, oy), (ox + 160, oy)], fill=C["silver"] + (80,), width=2)
    draw.line([(ox, oy), (ox, oy - 160)], fill=C["silver"] + (80,), width=2)
    # Arrow heads
    draw.line([(ox+160, oy), (ox+148, oy-6)], fill=C["silver"]+(80,), width=2)
    draw.line([(ox+160, oy), (ox+148, oy+6)], fill=C["silver"]+(80,), width=2)
    draw.line([(ox, oy-160), (ox-6, oy-148)], fill=C["silver"]+(80,), width=2)
    draw.line([(ox, oy-160), (ox+6, oy-148)], fill=C["silver"]+(80,), width=2)

    return layer


def create_parallax_zone():
    """Central offset pattern — the stereoscopic heart of the poster.
    Two arrays of dots/circles, slightly offset, suggesting depth through parallax."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    random.seed(42)  # Reproducible

    # Large central parallax field
    cx, cy = W // 2, H // 2 - 100
    field_w, field_h = 1400, 1800

    # Generate two offset dot matrices
    dot_spacing = 45
    offset_dx, offset_dy = 12, 8  # Stereoscopic shift

    # Vary the offset across the field to create depth gradient illusion
    for row_y in range(cy - field_h//2, cy + field_h//2, dot_spacing):
        for col_x in range(cx - field_w//2, cx + field_w//2, dot_spacing):
            # Distance from center affects parallax shift (closer = more shift)
            dx = col_x - cx
            dy = row_y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            max_dist = math.sqrt((field_w/2)**2 + (field_h/2)**2)
            parallax_factor = 1.0 - (dist / max_dist) * 0.7

            shift = parallax_factor * dot_spacing * 0.35

            # First "eye" — slightly offset left/up
            x1 = col_x - shift * 0.5
            y1 = row_y - shift * 0.3
            dot_r = 3 + parallax_factor * 3
            alpha = 40 + int(parallax_factor * 80)
            draw_dot(draw, x1, y1, dot_r, C["cyan"], alpha)

            # Second "eye" — offset right/down
            x2 = col_x + shift * 0.5
            y2 = row_y + shift * 0.3
            draw_dot(draw, x2, y2, dot_r * 0.8, C["amber"], alpha)

            # Small connecting line between pairs — the "disparity vector"
            if parallax_factor > 0.4 and random.random() < 0.3:
                line_alpha = int(alpha * 0.3)
                draw.line([(x1, y1), (x2, y2)], fill=C["silver"] + (line_alpha,), width=1)

    # Larger accent dots — "feature points" tracked across views
    np.random.seed(123)
    for _ in range(200):
        x = cx + int(np.random.normal(0, field_w * 0.25))
        y = cy + int(np.random.normal(0, field_h * 0.25))
        x = max(100, min(W-100, x))
        y = max(100, min(H-100, y))
        r = np.random.uniform(4, 10)
        alpha = np.random.randint(60, 140)
        color_choice = np.random.choice(["cyan", "amber", "copper", "chartreuse"])
        draw_dot(draw, x, y, r, C[color_choice], alpha)

        # Tiny companion dot slightly offset
        sx = x + np.random.uniform(-15, 15)
        sy = y + np.random.uniform(-10, 10)
        draw_dot(draw, sx, sy, r * 0.4, C[color_choice], alpha // 2)

    return layer


def create_wireframe_bloom():
    """Geometric wireframe forms emerging from the grid —
    cubes, tetrahedra, and geodesic fragments growing upward."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Multiple 3D wireframe forms at different scales
    # Each form emerges from bottom (flat/grid) to top (volumetric)

    def project_iso(x, y, z, ox, oy, scale=1.0):
        """Isometric projection."""
        px = ox + (x - y) * math.cos(math.radians(30)) * scale
        py = oy + (x + y) * math.sin(math.radians(30)) * scale - z * scale
        return px, py

    # ── Form 1: Large central wireframe cube/block ──
    ox1, oy1 = W * 0.55, H * 0.42
    scale1 = 180

    # Draw multiple stacked wireframe boxes (like a voxel grid)
    np.random.seed(77)
    for layer_z in range(5):
        z = layer_z * 0.6
        for bx in range(-1, 2):
            for by in range(-1, 2):
                # Skip some to create interesting negative space
                if random.random() < 0.25:
                    continue

                # 8 corners of a box
                s = 1.0
                corners_3d = [
                    (bx*s, by*s, z),
                    (bx*s + s, by*s, z),
                    (bx*s + s, by*s + s, z),
                    (bx*s, by*s + s, z),
                    (bx*s, by*s, z + s),
                    (bx*s + s, by*s, z + s),
                    (bx*s + s, by*s + s, z + s),
                    (bx*s, by*s + s, z + s),
                ]

                corners = [project_iso(x, y, z, ox1, oy1, scale1) for x, y, z in corners_3d]

                # Color temperature shifts with height
                t = z / 3.0
                color = blend_colors(C["cyan_dim"], C["copper"], t)
                alpha = 60 + int(t * 80)

                # Bottom face
                draw.polygon([corners[0], corners[1], corners[2], corners[3]],
                           outline=color + (alpha,), fill=color + (max(8, alpha//3),))
                # Top face
                draw.polygon([corners[4], corners[5], corners[6], corners[7]],
                           outline=color + (alpha,), fill=color + (max(8, alpha//3),))
                # Side edges
                for i in range(4):
                    draw.line([corners[i], corners[i+4]], fill=color + (alpha,), width=1)

    # ── Form 2: Floating tetrahedron cluster — left side ──
    ox2, oy2 = W * 0.3, H * 0.5
    scale2 = 120

    for i in range(6):
        angle = i * math.pi / 3 + 0.2
        rx = math.cos(angle) * 1.8
        ry = math.sin(angle) * 1.8
        rz = 0.5 + i * 0.35

        # Tetrahedron: 4 points
        h = 1.2
        pts_3d = [
            (rx, ry, rz),
            (rx + 0.8, ry, rz - 0.3),
            (rx, ry + 0.8, rz - 0.3),
            (rx + 0.4, ry + 0.4, rz + h),
        ]
        pts = [project_iso(x, y, z, ox2, oy2, scale2) for x, y, z in pts_3d]

        t = i / 5.0
        color = blend_colors(C["cyan"], C["chartreuse"], t)
        alpha = 50 + int(t * 70)

        # Draw all edges
        edges = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
        for e1, e2 in edges:
            draw.line([pts[e1], pts[e2]], fill=color + (alpha,), width=max(1, int(2 - t)))

    # ── Form 3: Geodesic dome fragment — right side ──
    ox3, oy3 = W * 0.72, H * 0.55
    scale3 = 100

    for ring in range(4):
        ring_z = ring * 0.5
        ring_r = 1.2 - ring * 0.15
        n_points = 8 - ring

        ring_pts = []
        for j in range(n_points):
            angle = j * 2 * math.pi / n_points + ring * 0.3
            rx = math.cos(angle) * ring_r
            ry = math.sin(angle) * ring_r
            ring_pts.append((rx, ry, ring_z))

        # Connect ring points
        t_ring = ring / 3.0
        color = blend_colors(C["copper"], C["amber"], t_ring)
        alpha = 70 + int(t_ring * 90)

        for j in range(n_points):
            j_next = (j + 1) % n_points
            p1 = project_iso(*ring_pts[j], ox3, oy3, scale3)
            p2 = project_iso(*ring_pts[j_next], ox3, oy3, scale3)
            draw.line([p1, p2], fill=color + (alpha,), width=max(1, 3 - ring))

        # Connect to previous ring
        if ring > 0:
            for j in range(min(n_points, len(prev_ring_pts))):
                p1 = project_iso(*ring_pts[j], ox3, oy3, scale3)
                p2 = project_iso(*prev_ring_pts[j], ox3, oy3, scale3)
                draw.line([p1, p2], fill=color + (alpha // 2,), width=1)

        prev_ring_pts = ring_pts

    # ── Form 4: Scattered measurement lines connecting grid to volumes ──
    for _ in range(30):
        x1 = random.uniform(100, W - 100)
        y1 = random.uniform(H * 0.6, H - 200)
        x2 = x1 + random.uniform(-80, 80)
        y2 = y1 - random.uniform(100, 300)
        alpha = random.randint(15, 45)
        draw.line([(x1, y1), (x2, y2)], fill=C["silver"] + (alpha,), width=1)

        # Small dash marks at endpoints
        dash_len = 6
        draw.line([(x1-dash_len, y1), (x1+dash_len, y1)], fill=C["silver"]+(alpha,), width=1)
        draw.line([(x2-dash_len, y2), (x2+dash_len, y2)], fill=C["silver"]+(alpha,), width=1)

    return layer


def create_point_cloud():
    """Scattered point cloud — the densest near the bottom,
    becoming sparser and more organized toward the top.
    References the 3D point cloud output of MVS reconstruction."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Bottom region: dense "reconstructed surface" with warm tones
    np.random.seed(42)

    # Dense cluster in lower-center — the "reconstructed terrain"
    cx, cy = W * 0.5, H * 0.72
    for _ in range(3000):
        # Gaussian cluster
        x = cx + np.random.normal(0, 380)
        y = cy + np.random.normal(0, 280)
        x = max(50, min(W - 50, x))
        y = max(H * 0.5, min(H - 200, y))

        # Size varies with distance from center
        dist = math.sqrt((x - cx)**2 + (y - cy)**2)
        r = max(1, 3 - dist / 300)

        # Color shifts from copper (center) to cyan (edges)
        t = min(1.0, dist / 400)
        color = blend_colors(C["amber"], C["cyan_dim"], t)
        alpha = max(20, int(160 - dist / 5))

        draw_dot(draw, x, y, r, color, alpha)

    # Rising particle stream — sparse dots rising upward like information
    for _ in range(800):
        x = cx + np.random.normal(0, 500)
        y = np.random.uniform(H * 0.1, H * 0.55)
        x = max(60, min(W - 60, x))
        r = np.random.uniform(1, 3.5)

        # Height determines color
        t = y / H
        color = blend_colors(C["cyan"], C["chartreuse"], 1.0 - t)
        alpha = np.random.randint(30, 100)

        draw_dot(draw, x, y, r, color, alpha)

    # Accent clusters — dense nodes like feature points
    accent_positions = [
        (W * 0.25, H * 0.38, C["cyan"], 50),
        (W * 0.68, H * 0.35, C["chartreuse"], 40),
        (W * 0.45, H * 0.48, C["amber"], 45),
        (W * 0.32, H * 0.58, C["copper"], 50),
        (W * 0.78, H * 0.62, C["cyan_dim"], 40),
    ]

    for ax, ay, color, count in accent_positions:
        for _ in range(count):
            x = ax + np.random.normal(0, 25)
            y = ay + np.random.normal(0, 25)
            r = np.random.uniform(2, 6)
            draw_dot(draw, x, y, r, color, np.random.randint(80, 180))

    return layer


def create_accent_bars():
    """Horizontal gradient bars that mark thermal transitions."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    bars = [
        (0.32, C["cyan"], 180),     # Upper accent
        (0.52, blend_colors(C["cyan"], C["copper"], 0.4), 120),  # Mid transition
        (0.68, C["copper"], 90),    # Lower warm
    ]

    for y_frac, color, alpha in bars:
        y = int(H * y_frac)
        # Thin bright line
        draw.line([(W*0.08, y), (W*0.92, y)], fill=color + (alpha,), width=1)

        # Subtle glow above
        for dy in range(1, 8):
            a = alpha // (dy * 2)
            draw.line([(W*0.1, y-dy), (W*0.9, y-dy)], fill=color + (a,), width=1)

        # Subtle glow below
        for dy in range(1, 8):
            a = alpha // (dy * 2)
            draw.line([(W*0.1, y+dy), (W*0.9, y+dy)], fill=color + (a,), width=1)

    # Vertical accent line — left margin surveyor mark
    vx = 120
    draw.line([(vx, H*0.12), (vx, H*0.88)], fill=C["silver"] + (25,), width=1)
    # Tick marks
    for y in np.arange(H*0.15, H*0.9, 80):
        draw.line([(vx-8, int(y)), (vx+8, int(y))], fill=C["silver"]+(35,), width=1)

    return layer


def create_typography():
    """The wordmark and annotations — minimal text as visual element."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # ── Primary wordmark: "HybridMVS" ──
    # Large, sculptural, integrated into the visual architecture
    title_font = load_font("Outfit-Bold.ttf", 180)
    title_font_2 = load_font("Outfit-Regular.ttf", 180)

    title = "HybridMVS"
    # Measure text to center
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) // 2
    ty = H * 0.52  # Positioned near the thermal transition

    # Draw title with subtle shadow/glow for depth
    # Cyan glow offset
    draw.text((tx+3, ty+3), title, font=title_font, fill=C["cyan"] + (60,))
    # Copper glow offset
    draw.text((tx-2, ty-2), title, font=title_font, fill=C["amber"] + (40,))
    # Main text — bright silver, slightly warm
    title_color = blend_colors(C["white"], C["amber"], 0.08)
    draw.text((tx, ty), title, font=title_font, fill=title_color + (245,))

    # ── Subtitle line ──
    sub_font = load_font("WorkSans-Regular.ttf", 42)
    sub_font_italic = load_font("WorkSans-Italic.ttf", 42)

    subtitle = "Hybrid 3D Reconstruction System"
    bbox_sub = draw.textbbox((0, 0), subtitle, font=sub_font)
    sw = bbox_sub[2] - bbox_sub[0]
    sx = (W - sw) // 2
    sy = ty + 210

    draw.text((sx, sy), subtitle, font=sub_font, fill=C["silver"] + (200,))

    # ── Tagline: "从平面到立体" (From Flat to Solid) ──
    tag_font = load_font("CrimsonPro-Italic.ttf", 36)
    tagline = "— 从平面到立体 · From Pixels to Point Clouds —"
    bbox_tag = draw.textbbox((0, 0), tagline, font=tag_font)
    tw_tag = bbox_tag[2] - bbox_tag[0]
    ttx = (W - tw_tag) // 2
    tty = sy + 65
    draw.text((ttx, tty), tagline, font=tag_font, fill=C["copper"] + (160,))

    # ── Bottom info block — surveyor-style annotations ──
    mono_font = load_font("JetBrainsMono-Regular.ttf", 22)
    mono_bold = load_font("JetBrainsMono-Bold.ttf", 22)

    # Left annotation
    left_x = 160
    bottom_y = H - 180

    draw.text((left_x, bottom_y), "SYSTEM:     COLMAP + CasMVSNet",
              font=mono_font, fill=C["silver"] + (140,))
    draw.text((left_x, bottom_y + 32), "RESOLUTION: PatchMatch + Deep MVS",
              font=mono_font, fill=C["silver"] + (120,))
    draw.text((left_x, bottom_y + 64), "PIPELINE:   SfM → Depth → Fusion",
              font=mono_font, fill=C["silver"] + (120,))

    # Right annotation — coordinate-style
    right_x = W - 520
    draw.text((right_x, bottom_y), "REF: DTU/BlendedMVS",
              font=mono_font, fill=C["copper"] + (120,))
    draw.text((right_x, bottom_y + 32), "GPU: NVIDIA RTX 4060",
              font=mono_font, fill=C["copper"] + (120,))
    draw.text((right_x, bottom_y + 64), "ENGINE: PyTorch 2.7 + CUDA 11.8",
              font=mono_font, fill=C["copper"] + (120,))

    # ── Small surveyor marks ──
    # Coordinate labels near the origin axis
    small_mono = load_font("JetBrainsMono-Regular.ttf", 18)
    ox, oy = 200, H - 300
    draw.text((ox - 30, oy + 8), "0,0", font=small_mono, fill=C["silver"] + (100,))
    draw.text((ox + 155, oy - 20), "x", font=small_mono, fill=C["silver"] + (80,))
    draw.text((ox - 20, oy - 175), "y", font=small_mono, fill=C["silver"] + (80,))

    # Reference numbers along the vertical margin
    margin_font = load_font("JetBrainsMono-Regular.ttf", 16)
    for i, val in enumerate(["8.0", "6.0", "4.0", "2.0", "0.0"]):
        yy = int(H * 0.2 + i * H * 0.12)
        draw.text((85, yy), val, font=margin_font, fill=C["silver"] + (60,))

    # Top reference marker
    top_font = load_font("InstrumentSans-Regular.ttf", 20)
    draw.text((W - 380, 80), "PARALLAX GARDEN", font=top_font, fill=C["cyan"] + (90,))
    draw.text((W - 420, 108), "Design Philosophy / Manifesto", font=top_font, fill=C["silver"] + (50,))

    # Grid ref numbers — top scale bar
    for i in range(6):
        x = 300 + i * 350
        val = f"{i*5:02d}"
        draw.text((x, 70), val, font=margin_font, fill=C["silver"] + (50,))
        draw.line([(x, 58), (x, 65)], fill=C["silver"] + (40,), width=1)

    return layer


def create_vignette():
    """Darken edges to create depth and focus."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Draw concentric dark borders
    margin = 60
    for i in range(margin):
        alpha = int(15 * (1 - i / margin))
        draw.rectangle(
            [i, i, W - i, H - i],
            outline=C["void"] + (alpha,),
            width=1
        )

    # Corner darkening
    corner_size = 300
    for i in range(corner_size):
        alpha = int(8 * (1 - i / corner_size))
        # Top-left
        draw.line([(0, i), (corner_size - i, i)], fill=C["void"]+(alpha,), width=1)
        # Top-right
        draw.line([(W - corner_size + i, i), (W, i)], fill=C["void"]+(alpha,), width=1)
        # Bottom-left
        draw.line([(0, H - i), (corner_size - i, H - i)], fill=C["void"]+(alpha,), width=1)
        # Bottom-right
        draw.line([(W - corner_size + i, H - i), (W, H - i)], fill=C["void"]+(alpha,), width=1)

    return layer


# ── Run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    create_poster()
