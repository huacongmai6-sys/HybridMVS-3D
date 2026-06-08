import { useCallback, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import * as THREE from "three";

/* ── Sphere point cloud geometry ────────────── */
function buildParticleGeo(count = 8000) {
  const geo = new THREE.BufferGeometry();
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);

  const radius = 2.5;
  const colorPrimary = new THREE.Color("#4F8CFF");
  const colorHighlight = new THREE.Color("#00E5FF");
  const colorWhite = new THREE.Color("#8AB8FF");

  for (let i = 0; i < count; i++) {
    /* spherical distribution with noise */
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = radius * (0.75 + Math.random() * 0.5); /* hollow-ish sphere */

    positions[i * 3] = Math.sin(phi) * Math.cos(theta) * r;
    positions[i * 3 + 1] = Math.sin(phi) * Math.sin(theta) * r;
    positions[i * 3 + 2] = Math.cos(phi) * r;

    /* color mix between primary, highlight, and white */
    const mix = Math.random();
    let color;
    if (mix < 0.5) {
      color = colorPrimary.clone().lerp(colorHighlight, mix * 2);
    } else if (mix < 0.85) {
      color = colorHighlight.clone().lerp(colorWhite, (mix - 0.5) / 0.35);
    } else {
      color = colorWhite.clone();
    }
    /* brightness variation */
    color.multiplyScalar(0.5 + Math.random() * 0.5);

    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }

  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return { geo, radius };
}

/* ── Inner scene ───────────────────────────── */
function ParticleScene() {
  const { geo } = useMemo(() => buildParticleGeo(8000), []);

  const groupRefCb = useCallback((group) => {
    if (!group) return;
    /* initial random rotation */
    group.rotation.x = Math.random() * Math.PI;
    group.rotation.y = Math.random() * Math.PI * 2;
  }, []);

  return (
    <group ref={groupRefCb}>
      {/* Main particle field */}
      <points>
        <bufferGeometry attach="geometry" {...geo} />
        <pointsMaterial
          attach="material"
          size={0.018}
          vertexColors
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          transparent
          opacity={0.85}
        />
      </points>

      {/* Outer halo — larger, more transparent */}
      <points>
        <bufferGeometry attach="geometry" {...geo} />
        <pointsMaterial
          attach="material"
          size={0.035}
          vertexColors
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          transparent
          opacity={0.15}
        />
      </points>
    </group>
  );
}

/* ═══════════════════════════════════════════════
   ParticleField — Full-viewport Three.js particle
   background. Fixed, behind all UI, no interaction.
   ═══════════════════════════════════════════════ */
export default function ParticleField() {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
      }}
    >
      <Canvas
        frameloop="always"
        camera={{ position: [0, 0, 5], fov: 50 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
        style={{ background: "transparent" }}
      >
        <ParticleScene />
        {/* Slow continuous rotation via render loop */}
        <Rotator />
      </Canvas>
    </div>
  );
}

/* ── Continuous slow rotation ───────────────── */
import { useFrame } from "@react-three/fiber";

function Rotator() {
  useFrame(({ scene }) => {
    const t = performance.now() * 0.0001;
    scene.rotation.y += 0.0003;
    scene.rotation.x = Math.sin(t * 0.3) * 0.05;
    scene.rotation.z = Math.cos(t * 0.25) * 0.03;
  });
  return null;
}
