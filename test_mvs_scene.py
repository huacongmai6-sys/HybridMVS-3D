"""
Generate a 3D textured scene and test MVS pipeline.
Scene: textured ground plane + several colored spheres at different depths.
"""

import os, sys, numpy as np, cv2

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
output_dir = os.path.join(PROJECT_ROOT, "test_mvs_scene")
os.makedirs(output_dir, exist_ok=True)

w, h = 1600, 1200
f = w  # focal length in pixels
K = np.array([[f, 0, w/2], [0, f, h/2], [0, 0, 1]], dtype=np.float64)

# Generate a textured ground plane texture (1024x1024)
tex_size = 1024
tex = np.zeros((tex_size, tex_size, 3), dtype=np.uint8)
xs, ys = np.meshgrid(np.arange(tex_size), np.arange(tex_size))
# Rich procedural texture with many SIFT-friendly features
tex[:,:,0] = (np.sin(xs/30) * np.cos(ys/40) * 127 + 128).astype(np.uint8)
tex[:,:,1] = (np.cos(xs/25) * np.sin(ys/35) * 127 + 128).astype(np.uint8)
tex[:,:,2] = (np.sin((xs+ys)/50) * 127 + 128).astype(np.uint8)
# Add high-frequency details (SIFT needs corners/blobs)
for _ in range(2000):
    tx = np.random.randint(0, tex_size)
    ty = np.random.randint(0, tex_size)
    cv2.circle(tex, (tx, ty), np.random.randint(2, 6),
               np.random.randint(0, 255, 3).tolist(), -1)

print("Scene: textured ground + 6 colored spheres")

# Scene definition:
# Ground plane at y = 500 (in world coords), extends from x=-800 to 800, z=0 to 1600
# Spheres at various positions
ground_y = 500

# Spheres: (cx, cy, cz, radius, color_bgr)
spheres = [
    (-300, 200, 400, 120, (50, 100, 220)),   # blue
    (300, 150, 350, 100, (50, 200, 50)),     # green
    (0, 300, 600, 150, (220, 50, 50)),       # red
    (-200, 280, 800, 80, (200, 200, 50)),    # yellow
    (250, 250, 700, 90, (200, 50, 200)),     # purple
    (-400, 220, 500, 110, (50, 200, 200)),   # cyan
]

def ray_plane_intersect(origin, direction, plane_y):
    """Intersect ray with horizontal plane at y=plane_y"""
    t = (plane_y - origin[1]) / (direction[1] + 1e-8)
    return t

def ray_sphere_intersect(origin, direction, center, radius):
    """Return (t_near, t_far) or None for ray-sphere intersection"""
    oc = origin - center
    a = np.dot(direction, direction)
    b = 2 * np.dot(oc, direction)
    c_val = np.dot(oc, oc) - radius**2
    disc = b**2 - 4*a*c_val
    if disc < 0:
        return None
    sqrt_disc = np.sqrt(disc)
    t1 = (-b - sqrt_disc) / (2*a)
    t2 = (-b + sqrt_disc) / (2*a)
    if t1 > 0:
        return min(t1, t2)
    elif t2 > 0:
        return t2
    return None

print(f"Rendering {10} views...")

for view_idx in range(10):
    angle = np.deg2rad(-35 + 70 * view_idx / 9)
    cam_dist = 1200  # camera distance from center
    cam_x = np.sin(angle) * cam_dist
    cam_y = 350  # above ground
    cam_z = np.cos(angle) * cam_dist + 600

    cam_pos = np.array([cam_x, cam_y, cam_z])
    look_at = np.array([0, 200, 600])
    z_axis = look_at - cam_pos
    z_axis /= np.linalg.norm(z_axis)
    x_axis = np.cross(np.array([0, 1, 0]), z_axis)
    x_axis /= np.linalg.norm(x_axis)
    y_axis = np.cross(z_axis, x_axis)

    c2w = np.eye(4)
    c2w[:3, 0] = x_axis
    c2w[:3, 1] = y_axis
    c2w[:3, 2] = z_axis
    c2w[:3, 3] = cam_pos

    # Ray tracing
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # For anti-aliasing, supersample
    ss = 1  # set to 2 for AA but slow
    sh, sw = h * ss, w * ss

    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    x_cam = (xs - K[0, 2]) / K[0, 0]
    y_cam = (ys - K[1, 2]) / K[1, 1]
    z_cam = np.ones_like(x_cam)

    rays_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)
    # Normalize ray directions in camera space, then transform to world
    norms = np.linalg.norm(rays_cam, axis=-1, keepdims=True)
    rays_cam_n = rays_cam / norms
    rays_world = (c2w[:3, :3] @ rays_cam_n[..., None]).squeeze(-1)

    # Find closest hit for each pixel
    best_t = np.full((h, w), np.inf)
    best_color = np.zeros((h, w, 3), dtype=np.float32)
    best_type = np.full((h, w), -1, dtype=int)  # -1=none, 0=ground, 1=sphere

    # Check ground plane
    t_ground = ray_plane_intersect(cam_pos, rays_world, ground_y)
    hit_ground = t_ground > 0
    pts_ground = cam_pos + rays_world * t_ground[..., None]
    # Sample texture
    tex_u = (pts_ground[..., 0] % tex_size).clip(0, tex_size-1).astype(int)
    tex_v = (pts_ground[..., 2] % tex_size).clip(0, tex_size-1).astype(int)
    ground_color = tex[tex_v[hit_ground], tex_u[hit_ground]].astype(np.float32) / 255.0
    # Lighting
    diffuse = np.clip(np.abs(rays_world[hit_ground, 1]), 0.3, 1.0)
    ground_color *= diffuse[..., None]

    mask = hit_ground & (t_ground < best_t)
    best_t = np.where(mask, t_ground, best_t)
    best_type = np.where(mask, 0, best_type)
    for c in range(3):
        bc = best_color[..., c]
        bc_flat = bc.ravel()
        gc_flat = (ground_color[..., c] * 255).ravel()
        m_flat = mask.ravel()
        bc_flat[m_flat] = gc_flat[m_flat]
        best_color[..., c] = bc

    # Check spheres
    for si, (sx, sy, sz, sr, s_color) in enumerate(spheres):
        sphere_center = np.array([sx, sy, sz])

        # Vectorized sphere intersection (per-pixel)
        oc = cam_pos - sphere_center
        a = np.sum(rays_world**2, axis=-1)
        b = 2 * (rays_world[..., 0]*oc[0] + rays_world[..., 1]*oc[1] + rays_world[..., 2]*oc[2])
        c_val = oc[0]**2 + oc[1]**2 + oc[2]**2 - sr**2
        disc = b**2 - 4*a*c_val

        hit = disc > 0
        sqrt_disc = np.sqrt(np.maximum(disc, 0))
        t1 = (-b - sqrt_disc) / (2*a + 1e-8)
        t2 = (-b + sqrt_disc) / (2*a + 1e-8)
        t_sphere = np.where(t1 > 0, np.minimum(t1, np.where(t2 > 0, t2, np.inf)),
                            np.where(t2 > 0, t2, np.inf))

        valid_hit = hit & (t_sphere > 0) & (t_sphere < best_t)
        best_t = np.where(valid_hit, t_sphere, best_t)
        best_type = np.where(valid_hit, si + 1, best_type)

    # Apply colors from spheres
    for si, (sx, sy, sz, sr, s_color) in enumerate(spheres):
        mask = best_type == si + 1
        if mask.any():
            # Compute normal for lighting
            pts = cam_pos + rays_world[mask] * best_t[mask, None]
            normals = pts - np.array([sx, sy, sz])
            normals /= np.linalg.norm(normals, axis=-1, keepdims=True) + 1e-8
            light_dir = np.array([0.5, 0.7, 0.5])
            light_dir /= np.linalg.norm(light_dir)
            diffuse = np.clip(np.sum(normals * light_dir, axis=-1), 0.15, 1.0)
            color = np.array(s_color[::-1], dtype=np.float32) / 255.0 * diffuse[..., None]
            for c in range(3):
                cc = best_color[..., c]
                cc[mask] = color[..., c] * 255
                best_color[..., c] = cc

    # Sky for background
    sky_mask = best_type == -1
    best_color[sky_mask] = [0.3, 0.4, 0.6]  # blue-gray sky

    img = np.clip(best_color, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0.8)  # slight blur for realism

    cv2.imwrite(os.path.join(output_dir, f"view_{view_idx:02d}.png"), img)
    print(f"  View {view_idx}: angle={np.rad2deg(angle):.0f}° pos=({cam_x:.0f},{cam_y:.0f},{cam_z:.0f})")

print(f"\nDone! {10} views saved to {output_dir}/")
print(f"Intrinsics: f={f:.0f}px, ({w/2:.0f}, {h/2:.0f})")

# Also save intrinsics for reference
np.savez(os.path.join(output_dir, "cameras.npz"),
         K=K, views=10, width=w, height=h)

print(f"\nUpload {output_dir}/*.png to http://localhost:5173 and run reconstruction")
print(f"Or use CLI: python -c \"from hybridmvs.pipeline import HybridReconstructionPipeline; ...\"")
