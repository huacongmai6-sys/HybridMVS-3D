"""
Side-by-side comparison: 4 point cloud options for HybridMVS poster
1. Classical Bust — head + shoulders
2. Stanford Dragon — serpentine body, spines, legs
3. Gothic Cathedral — towers, rose window, spires
4. Klein Bottle — parametric non-orientable surface

2x2 grid, each rendered in Tiffany Blue + Cheese point cloud style.
"""

import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Config ──────────────────────────────────────────────────
PANEL_W, PANEL_H = 1800, 1800   # each panel
GAP = 40
CANVAS_W = PANEL_W * 2 + GAP * 3
CANVAS_H = PANEL_H * 2 + GAP * 3

OUTPUT = "d:/项目实践/罗版本/HybridMVS/poster/4_options_comparison.png"
FONTS_DIR = r"C:\Users\xiaomai\.claude\skills\canvas-design\canvas-fonts"

TIFFANY   = (0x80, 0xD1, 0xC8)
TIFFANY_B = (0x50, 0xC0, 0xB5)
TIFFANY_D = (0x40, 0xA0, 0x98)
CHEESE    = (0xF8, 0xF5, 0xD6)
CHEESE_B  = (0xFF, 0xFC, 0xE8)
DARK      = (0x08, 0x0A, 0x10)
DARK_BG   = (0x0C, 0x0E, 0x16)
CORAL     = (0xE8, 0x6A, 0x50)
SLATE     = (0x55, 0x5E, 0x6E)

# ── Helpers ─────────────────────────────────────────────────
def blend(c1, c2, t):
    t = max(0, min(1, t))
    return tuple(max(0, min(255, int(c1[i]+(c2[i]-c1[i])*t))) for i in range(3))

def load_font(name, size):
    try: return ImageFont.truetype(f"{FONTS_DIR}/{name}", size)
    except: return ImageFont.load_default()

# ── 1. CLASSICAL BUST ───────────────────────────────────────
def gen_bust():
    """Head + neck + shoulders of a classical marble bust."""
    pts = []
    rng = np.random.RandomState(1)

    # Head: ellipsoid, slightly taller than wide
    head_cx, head_cy, head_cz = 0, 0.35, 0
    head_rx, head_ry, head_rz = 0.38, 0.48, 0.35

    n_head = 2200
    for _ in range(n_head):
        # Sample on ellipsoid surface via spherical coords
        theta = rng.uniform(0, 2*math.pi)
        phi = rng.uniform(0, math.pi)
        # More density on face (front: z > 0)
        if rng.random() < 0.3 and math.cos(phi) > 0:
            # bias toward facial features
            theta = rng.normal(0, 0.6)  # cluster around center
            phi = rng.normal(math.pi/2, 0.4)

        sx = math.sin(phi) * math.cos(theta)
        sy = math.cos(phi)
        sz = math.sin(phi) * math.sin(theta)

        x = head_cx + sx * head_rx + rng.normal(0, 0.008)
        y = head_cy + sy * head_ry + rng.normal(0, 0.008)
        z = head_cz + sz * head_rz + rng.normal(0, 0.008)
        pts.append((x, y, z, 'head'))

    # Facial features — higher density clusters
    # Eyes
    for _ in range(120):
        side = 1 if rng.random() < 0.5 else -1
        x = side * 0.12 + rng.normal(0, 0.03)
        y = 0.42 + rng.normal(0, 0.025)
        z = 0.28 + rng.normal(0, 0.02)
        pts.append((x, y, z, 'eye'))
    # Nose
    for _ in range(80):
        x = rng.normal(0, 0.025)
        y = rng.normal(0.35, 0.03)
        z = rng.normal(0.33, 0.02)
        pts.append((x, y, z, 'nose'))
    # Mouth
    for _ in range(60):
        x = rng.normal(0, 0.06)
        y = rng.normal(0.28, 0.015)
        z = rng.normal(0.32, 0.015)
        pts.append((x, y, z, 'mouth'))

    # Neck: cylinder
    neck_cy = -0.05
    for _ in range(400):
        angle = rng.uniform(0, 2*math.pi)
        r = 0.15 + rng.normal(0, 0.01)
        x = math.cos(angle) * r
        z = math.sin(angle) * r
        y = neck_cy + rng.uniform(-0.3, -0.05)
        pts.append((x, y, z, 'neck'))

    # Shoulders: broad curved surface
    for _ in range(900):
        angle = rng.uniform(-math.pi*0.7, math.pi*0.7)
        y = rng.uniform(-0.65, -0.15)
        shoulder_r = 0.6 - (y + 0.65) * 0.05  # wider at bottom
        dist = shoulder_r + rng.normal(0, 0.02)
        x = math.cos(angle) * dist
        z = math.sin(angle) * dist * 0.5 + 0.1
        # Drape/robe fold noise
        x += rng.normal(0, 0.015)
        z += rng.normal(0, 0.015)
        pts.append((x, y, z, 'shoulder'))

    # Chest drapery
    for _ in range(500):
        angle = rng.uniform(-math.pi*0.6, math.pi*0.6)
        y = rng.uniform(-1.0, -0.5)
        r = 0.7 + rng.normal(0, 0.03)
        x = math.cos(angle) * r * (0.5 + 0.5 * abs(y+1.0)/0.5)
        z = math.sin(angle) * r * 0.4 + 0.15
        pts.append((x, y, z, 'chest'))

    return pts


# ── 2. STANFORD DRAGON ─────────────────────────────────────
def gen_dragon():
    """Serpentine dragon body with spines, legs, horns."""
    pts = []
    rng = np.random.RandomState(2)

    # Main body: sinusoidal curve in 3D
    n_body = 3000
    for i in range(n_body):
        t = rng.uniform(0, 1)
        # Parametric body curve — spiral/serpentine
        x = math.sin(t * 3.5) * 0.55 * (1 - t*0.3)
        y = t * 1.0 - 0.3  # from bottom to top
        z = math.cos(t * 2.8) * 0.25 + t * 0.1

        # Body thickness decreases toward tail
        body_r = 0.12 * (1 - t*0.7)
        # Add surface noise
        angle = rng.uniform(0, 2*math.pi)
        nx = x + math.cos(angle) * body_r * rng.uniform(0.4, 1.0)
        ny = y + rng.normal(0, body_r*0.5)
        nz = z + math.sin(angle) * body_r * rng.uniform(0.4, 1.0)
        pts.append((nx, ny, nz, 'body'))

    # Spines along the back — more at head, fewer at tail
    n_spines = 500
    for _ in range(n_spines):
        t = rng.uniform(0, 0.75)  # spines mostly on front 3/4
        bx = math.sin(t * 3.5) * 0.55 * (1 - t*0.3)
        by = t * 1.0 - 0.3
        bz = math.cos(t * 2.8) * 0.25 + t * 0.1
        spine_h = 0.06 * (1 - t*0.8)
        sx = bx + rng.normal(0, 0.015)
        sy = by + rng.uniform(0, spine_h)
        sz = bz + rng.normal(0, 0.015)
        pts.append((sx, sy, sz, 'spine'))

    # Head
    head_x = math.sin(0) * 0.55
    head_y = -0.3
    head_z = math.cos(0) * 0.25
    for _ in range(400):
        hx = head_x + rng.normal(0, 0.08)
        hy = head_y + rng.normal(0, 0.06)
        hz = head_z + rng.normal(0, 0.07)
        # Elongate the head slightly forward
        hx += 0.04
        pts.append((hx, hy, hz, 'head'))

    # Horns
    for _ in range(150):
        side = 1 if rng.random() < 0.5 else -1
        t = rng.uniform(0, 1)
        hx = head_x + side * 0.03 + side * t * 0.15
        hy = head_y + 0.04 + t * 0.12
        hz = head_z + t * 0.05
        pts.append((hx, hy, hz, 'horn'))

    # Legs (4)
    leg_positions = [(0.25, 0.0), (0.25, 0.15), (0.55, -0.05), (0.55, 0.1)]
    for leg_t, leg_z_offset in leg_positions:
        bx = math.sin(leg_t * 3.5) * 0.55 * (1 - leg_t*0.3)
        by = leg_t * 1.0 - 0.3
        bz = math.cos(leg_t * 2.8) * 0.25 + leg_t * 0.1
        for _ in range(200):
            lx = bx + rng.normal(0, 0.03)
            ly = by - rng.uniform(0, 0.2)
            lz = bz + leg_z_offset + rng.normal(0, 0.03)
            pts.append((lx, ly, lz, 'leg'))

    return pts


# ── 3. GOTHIC CATHEDRAL ────────────────────────────────────
def gen_cathedral():
    """Gothic cathedral facade — twin towers, rose window, pointed arches."""
    pts = []
    rng = np.random.RandomState(3)

    # Twin towers
    for tower_cx in [-0.35, 0.35]:
        # Tower body
        for _ in range(600):
            x = tower_cx + rng.normal(0, 0.1)
            y = rng.uniform(0.0, 0.8)
            z = rng.uniform(-0.05, 0.05)
            pts.append((x, y, z, 'tower'))

        # Tower spire (pyramid)
        for _ in range(400):
            t = rng.uniform(0, 1)
            y = 0.8 + t * 0.4
            r = 0.1 * (1 - t) + rng.normal(0, 0.01)
            angle = rng.uniform(0, 2*math.pi)
            x = tower_cx + math.cos(angle) * r
            z = math.sin(angle) * r
            pts.append((x, y, z, 'spire'))

        # Spire tip
        pts.append((tower_cx, 1.22, 0, 'spire_tip'))

    # Central facade wall
    for _ in range(800):
        x = rng.uniform(-0.25, 0.25)
        y = rng.uniform(0.0, 0.7)
        z = rng.uniform(-0.02, 0.02)
        pts.append((x, y, z, 'wall'))

    # Rose window (circular stained glass)
    rose_cx, rose_cy = 0, 0.55
    for _ in range(500):
        angle = rng.uniform(0, 2*math.pi)
        r = rng.uniform(0, 0.14)
        # Radial spokes
        if rng.random() < 0.4:
            spoke_angle = rng.randint(0, 11) * math.pi / 6
            angle = spoke_angle + rng.normal(0, 0.04)
            r = rng.uniform(0.02, 0.14)
        x = rose_cx + math.cos(angle) * r
        y = rose_cy + math.sin(angle) * r
        z = 0.03 + rng.normal(0, 0.005)
        pts.append((x, y, z, 'rose'))

    # Pointed arch entrance (central)
    for _ in range(400):
        t = rng.uniform(0, 1)
        arch_h = 0.35
        arch_w = 0.12
        if t < 0.5:  # vertical sides
            y = t * 2 * 0.2
            x = rng.uniform(-arch_w, arch_w)
        else:  # pointed arch top
            arch_t = (t - 0.5) * 2
            y = 0.2 + arch_t * arch_h
            x_half = arch_w * (1 - arch_t)
            x = rng.uniform(-x_half, x_half)
        z = 0.04 + rng.normal(0, 0.005)
        pts.append((x, y, z, 'arch'))

    # Flying buttresses — left and right
    for side in [-1, 1]:
        for _ in range(250):
            t = rng.uniform(0, 1)
            bx = side * (0.3 + t * 0.2)
            by = 0.15 + t * 0.5
            bz = 0.04 + rng.normal(0, 0.015)
            pts.append((bx, by, bz, 'buttress'))

    # Ground plane
    for _ in range(300):
        x = rng.uniform(-0.6, 0.6)
        y = rng.uniform(-0.05, 0.02)
        z = rng.uniform(-0.3, 0.3)
        pts.append((x, y, z, 'ground'))

    return pts


# ── 4. KLEIN BOTTLE ────────────────────────────────────────
def gen_klein_bottle():
    """Klein bottle parametric surface — the elegant non-orientable shape."""
    pts = []
    rng = np.random.RandomState(4)

    n_pts = 4000
    # Standard Klein bottle parameterization
    for _ in range(n_pts):
        u = rng.uniform(0, 2*math.pi)
        v = rng.uniform(0, 2*math.pi)

        r = 0.35
        a = 0.55

        # Klein bottle parametric equations
        cu, su = math.cos(u), math.sin(u)
        cv, sv = math.cos(v), math.sin(v)

        # Standard immersion formula
        denom = 1 + 0.5 * sv * cu  # self-intersection term for twist
        if abs(denom) < 0.01:
            denom = 0.01

        x = (a + r * cv * cu - r * sv * su * 0.5) / denom
        y = (r * cv * su + r * sv * cu * 0.5) / denom
        z = r * sv * 0.8

        # Add surface noise
        x += rng.normal(0, 0.01)
        y += rng.normal(0, 0.01)
        z += rng.normal(0, 0.01)

        pts.append((x, y, z, 'klein'))

    return pts


# ── Project & Render ────────────────────────────────────────
def project_ortho(x, y, z, cx, cy, scale, tilt_x=0.3, rot_y=0.3):
    """Orthographic-ish projection with tilt."""
    cos_tx, sin_tx = math.cos(tilt_x), math.sin(tilt_x)
    y2 = y * cos_tx - z * sin_tx
    z2 = y * sin_tx + z * cos_tx

    cos_ry, sin_ry = math.cos(rot_y), math.sin(rot_y)
    x2 = x * cos_ry + z2 * sin_ry
    z3 = -x * sin_ry + z2 * cos_ry

    px = cx + x2 * scale
    py = cy - y2 * scale  # flip Y for screen
    return px, py, z3


def render_point_cloud(pts, cx, cy, scale, tilt_x=0.3, rot_y=0.3):
    """Render a point cloud onto a PIL Image."""
    img = Image.new('RGBA', (PANEL_W, PANEL_H), DARK_BG + (255,))
    draw = ImageDraw.Draw(img)

    # Project all points
    proj = []
    for x, y, z, ptype in pts:
        px, py, pz = project_ortho(x, y, z, cx, cy, scale, tilt_x, rot_y)
        if 10 < px < PANEL_W-10 and 10 < py < PANEL_H-10:
            proj.append((px, py, pz, ptype))

    # Depth sort far → near
    proj.sort(key=lambda p: p[2], reverse=True)

    # Color mapping by type
    type_colors = {
        'head': TIFFANY, 'eye': CHEESE, 'nose': CHEESE, 'mouth': CHEESE,
        'neck': TIFFANY_D, 'shoulder': TIFFANY, 'chest': TIFFANY_D,
        'body': TIFFANY, 'spine': TIFFANY_B, 'head_d': TIFFANY_B,
        'horn': CHEESE, 'leg': TIFFANY_D,
        'tower': TIFFANY, 'spire': TIFFANY_B, 'spire_tip': CHEESE,
        'wall': TIFFANY_D, 'rose': CHEESE, 'arch': TIFFANY_B,
        'buttress': TIFFANY_D, 'ground': SLATE,
        'klein': TIFFANY,
    }

    for px, py, pz, ptype in proj:
        depth_norm = (pz + 1.5) / 3.0
        base_color = type_colors.get(ptype, TIFFANY)
        color = blend(base_color, CHEESE if depth_norm < 0.5 else TIFFANY_D,
                      abs(depth_norm - 0.5) * 0.6)
        r = 1.5 + (1 - depth_norm) * 2.5
        alpha = 160 + int((1 - depth_norm) * 70)
        draw.ellipse([px-r, py-r, px+r, py+r], fill=color+(min(255, alpha),))

    # Ground reflection — faint mirror below
    for px, py, pz, ptype in proj[:len(proj)//6]:
        if ptype in ('ground',): continue
        refl_y = py + (cy - py) * 1.85  # reflect across bottom
        if refl_y > PANEL_H - 30 or refl_y < PANEL_H * 0.6: continue
        r = 0.8
        alpha = 15
        draw.ellipse([px-r, refl_y-r, px+r, refl_y+r], fill=TIFFANY+(alpha,))

    return img


def add_labels(img, index, name, subtitle):
    """Add label to a panel."""
    draw = ImageDraw.Draw(img)

    # Panel border
    border_alpha = 60
    draw.rectangle([4, 4, PANEL_W-4, PANEL_H-4], outline=TIFFANY+(border_alpha,), width=2)

    # Number badge — top left
    badge_font = load_font("Outfit-Bold.ttf", 36)
    name_font = load_font("InstrumentSans-Bold.ttf", 32)
    sub_font = load_font("WorkSans-Regular.ttf", 22)

    # Number circle
    bx, by = 40, 40
    draw.ellipse([bx-18, by-18, bx+18, by+18], fill=TIFFANY+(200,))
    draw.text((bx-8, by-16), f"{index}", font=badge_font, fill=DARK+(255,))

    # Title
    draw.text((bx + 35, by - 16), name, font=name_font, fill=CHEESE+(230,))
    # Subtitle
    draw.text((bx + 35, by + 18), subtitle, font=sub_font, fill=SLATE+(160,))

    return img


# ── Main ────────────────────────────────────────────────────
def main():
    print("Generating point clouds...")

    datasets = [
        (1, gen_bust(),       "Classical Bust",       "Marble sculpture · 3D scan aesthetic"),
        (2, gen_dragon(),     "Stanford Dragon",      "Serpentine · CV benchmark classic"),
        (3, gen_cathedral(),  "Gothic Cathedral",     "Twin towers · Rose window · Buttresses"),
        (4, gen_klein_bottle(), "Klein Bottle",       "Non-orientable · Parametric surface"),
    ]

    panels = []
    for idx, pts, name, sub in datasets:
        print(f"  Rendering {idx}: {name} ({len(pts)} points)...")
        panel = render_point_cloud(pts, PANEL_W//2, PANEL_H*0.52, PANEL_W*0.55,
                                   tilt_x=0.25, rot_y=0.35)
        panel = add_labels(panel, idx, name, sub)
        panels.append(panel)

    # Assemble 2x2 grid
    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), DARK+(255,))
    draw_canvas = ImageDraw.Draw(canvas)

    # Thin grid lines for separation
    for i in range(1, 3):
        y = GAP + PANEL_H + (i-1)*(PANEL_H+GAP) + GAP//2
        draw_canvas.line([(0, y), (CANVAS_W, y)], fill=SLATE+(30,), width=1)

    for i in range(1, 3):
        x = GAP + PANEL_W + (i-1)*(PANEL_W+GAP) + GAP//2
        draw_canvas.line([(x, 0), (x, CANVAS_H)], fill=SLATE+(30,), width=1)

    positions = [(GAP, GAP), (GAP*2+PANEL_W, GAP),
                 (GAP, GAP*2+PANEL_H), (GAP*2+PANEL_W, GAP*2+PANEL_H)]

    for (px, py), panel in zip(positions, panels):
        canvas.paste(panel, (px, py))

    # Top title bar
    title_font = load_font("Outfit-Bold.ttf", 48)
    top_font = load_font("WorkSans-Regular.ttf", 26)

    title = "POINT CLOUD OPTIONS — HybridMVS Poster"
    bbox_t = draw_canvas.textbbox((0,0), title, font=title_font)
    tw = bbox_t[2] - bbox_t[0]
    draw_canvas.text(((CANVAS_W-tw)//2, 28), title, font=title_font, fill=CHEESE+(230,))

    # Color legend
    legend_font = load_font("JetBrainsMono-Regular.ttf", 20)
    legend_items = [
        ("■ Tiffany Blue", TIFFANY),
        ("■ Cheese/Cream", CHEESE),
        ("■ Dark Slate", TIFFANY_D),
    ]
    lx = CANVAS_W - 500
    for i, (text, color) in enumerate(legend_items):
        draw_canvas.text((lx + i*175, 32), text, font=legend_font, fill=color+(200,))

    # Bottom instruction
    inst_font = load_font("JetBrainsMono-Regular.ttf", 22)
    inst = "Which shape resonates?  ←  Choose your hero  →  Each ~3000–4000 points"
    bbox_i = draw_canvas.textbbox((0,0), inst, font=inst_font)
    iw = bbox_i[2] - bbox_i[0]
    draw_canvas.text(((CANVAS_W-iw)//2, CANVAS_H-60), inst, font=inst_font, fill=SLATE+(150,))

    # Save
    final = Image.new('RGB', (CANVAS_W, CANVAS_H), DARK)
    final.paste(canvas, mask=canvas.split()[3])
    final.save(OUTPUT, 'PNG', dpi=(150, 150))  # lower DPI for reasonable file size
    print(f"\n>> Saved: {OUTPUT}")
    print(f"   Size: {CANVAS_W}x{CANVAS_H} px")

if __name__ == "__main__":
    main()
