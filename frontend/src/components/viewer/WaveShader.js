import * as THREE from "three";

/**
 * WaveShader — Custom GLSL shaders for the wave-reveal point cloud effect.
 *
 * Effect: Points are hidden by default and revealed by:
 *   1. Breathing concentric rings expanding from top-center (primary)
 *   2. Mouse cursor spotlight (supplemental)
 *
 * Exports:
 *   WAVE_VERTEX   — vertex shader source
 *   WAVE_FRAGMENT — fragment shader source
 *   createWaveMaterial(pointSize, extent) — builds a ShaderMaterial with uniforms
 *   WAVE_DEFAULTS — default uniform values
 */

// ── Vertex Shader ───────────────────────────────────────────────────────────
// Standard point rendering with perspective size attenuation.
// Passes clip-space position and vertex color to fragment stage.
export const WAVE_VERTEX = /* glsl */ `
  uniform float uSize;
  uniform float uScale;

  varying vec4 vClipPosition;
  varying vec3 vColor;

  void main() {
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    vClipPosition = gl_Position;
    vColor = color;

    // Point size with perspective attenuation (matching THREE.PointsMaterial)
    gl_PointSize = uSize;
    #ifdef USE_SIZEATTENUATION
      gl_PointSize *= uScale / -mvPosition.z;
    #endif
  }
`;

// ── Fragment Shader ─────────────────────────────────────────────────────────
// Per-fragment visibility check: wave front reveal + mouse spotlight.
// Uses discard to hide fragments outside the revealed region.
export const WAVE_FRAGMENT = /* glsl */ `
  uniform vec2  uMouse;          // mouse NDC (-1..1), sentinel {-99,-99} when off-screen
  uniform vec2  uWaveCenter;     // wave origin in NDC (top-middle)
  uniform float uTime;           // elapsed seconds
  uniform float uBreathFreq;     // breathing oscillation Hz
  uniform float uBreathAmp;      // breathing depth (0..0.5)
  uniform float uWaveSpeed;      // ring expansion speed in NDC/s
  uniform float uRingCount;      // number of concentric ring systems (int, cast in shader)
  uniform float uRingSpacing;    // spacing between rings in NDC
  uniform float uRingWidth;      // ring edge softness
  uniform float uMouseRadius;    // mouse reveal radius in NDC
  uniform float uMouseSoftness;  // mouse edge fade
  uniform vec2  uResolution;     // viewport dimensions

  varying vec4 vClipPosition;
  varying vec3 vColor;

  void main() {
    // ── Circular point sprite with soft edge ──────────────────────────────
    float dPt = length(gl_PointCoord - 0.5) * 2.0;   // 0 at center, 1 at edge
    if (dPt > 1.0) discard;
    float pointAlpha = 1.0 - smoothstep(0.0, 1.0, dPt);

    // ── Point center in NDC space ─────────────────────────────────────────
    vec3 ndc3 = vClipPosition.xyz / vClipPosition.w;
    vec2 ndc = ndc3.xy;

    // Correct aspect ratio so distances feel circular on screen
    float aspect = uResolution.x / uResolution.y;

    // ── ① Wave reveal: breathing rings from top-center ────────────────────
    // Breathing envelope — organic inhale/exhale rhythm
    // Use a composite sine for a more natural breathing curve:
    // fast shallow ripple + slow deep swell
    float breathSlow = sin(uTime * uBreathFreq * 0.7) * 0.5 + 0.5;          // 0..1 slow
    float breathFast = sin(uTime * uBreathFreq * 1.8 + 1.2) * 0.5 + 0.5;    // 0..1 faster, phase-shifted
    float breath = mix(breathSlow, breathFast, 0.35);                        // blended breath
    breath = 1.0 - uBreathAmp + uBreathAmp * breath;                         // scale to [1-amp, 1]

    // Distance from wave center (aspect-corrected)
    vec2 delta = (ndc - uWaveCenter) * vec2(aspect, 1.0);
    float distToCenter = length(delta);

    // Leading wavefront — sweeps outward, revealing points behind it
    float waveFront = uTime * uWaveSpeed * breath;
    float frontReveal = 1.0 - smoothstep(waveFront - uRingWidth, waveFront, distToCenter);

    // Concentric ripples on the revealed surface
    float ringSum = 0.0;
    int rings = int(uRingCount);
    float ahead = distToCenter - waveFront;
    for (int i = 0; i < 6; i++) {   // capped loop (uRingCount clamped to ≤6)
      if (i >= rings) break;
      float offset = float(i) * uRingSpacing;
      // Each ring system has a slightly different phase speed for organic feel
      float phase = (distToCenter - offset) * 8.0 - uTime * uWaveSpeed * 3.0 * (1.0 + float(i) * 0.25);
      float ring = sin(phase);
      ring = ring * 0.5 + 0.5;                              // normalize 0..1
      ring *= smoothstep(offset + uRingWidth, offset, distToCenter);  // fade near ring origin
      // Fade rings ahead of the wave front (only visible on revealed surface)
      ring *= 1.0 - smoothstep(0.0, uRingWidth * 4.0, ahead);
      ringSum += ring;
    }
    ringSum = clamp(ringSum, 0.0, 1.0);

    // Combine front reveal with ripple texture
    float waveReveal = max(frontReveal * 0.65, ringSum * 0.45 * breath);

    // ── ② Mouse reveal: soft spotlight around cursor ──────────────────────
    float mouseReveal = 0.0;
    if (uMouse.x > -50.0) {  // sentinel check: mouse is on-screen
      vec2 mDelta = (ndc - uMouse) * vec2(aspect, 1.0);
      float distToMouse = length(mDelta);
      mouseReveal = 1.0 - smoothstep(0.0, uMouseRadius + uMouseSoftness, distToMouse);
      // Gaussian falloff for a softer feel at the edges
      float mouseGauss = exp(-distToMouse * distToMouse / (uMouseRadius * uMouseRadius * 0.5));
      mouseReveal = mix(mouseReveal, mouseGauss, 0.4);
    }

    // ── ③ Combine ─────────────────────────────────────────────────────────
    float reveal = max(waveReveal, mouseReveal * 0.75);

    // Discard unrevealed fragments (small threshold for antialiasing)
    if (reveal < 0.015) discard;

    // Emit with reveal-dimmed color — points fade in as wave reaches them
    vec3 outColor = vColor * reveal;

    gl_FragColor = vec4(outColor, 1.0);
  }
`;

// ── Default Uniforms ────────────────────────────────────────────────────────
export const WAVE_DEFAULTS = {
  uMouse: new THREE.Vector2(-99, -99),
  uWaveCenter: new THREE.Vector2(0.0, 0.65),
  uTime: 0,
  uBreathFreq: 0.55,
  uBreathAmp: 0.35,
  uWaveSpeed: 0.12,
  uRingCount: 3,
  uRingSpacing: 0.35,
  uRingWidth: 0.06,
  uMouseRadius: 0.28,
  uMouseSoftness: 0.15,
  uResolution: new THREE.Vector2(1, 1),
  uSize: 0.01,
  uScale: 1.0,
};

// ── Helper: create a configured ShaderMaterial ──────────────────────────────
/**
 * Creates a ShaderMaterial for the wave-reveal point cloud effect.
 *
 * @param {number} pointSize  - base point size (e.g. extent * 0.004)
 * @param {number} extent     - point cloud extent (for viewport scale calc)
 * @returns {THREE.ShaderMaterial}
 */
export function createWaveMaterial(pointSize, extent) {
  const uniforms = {
    uSize: { value: pointSize },
    uScale: { value: 300.0 },       // will be updated per-frame from viewport
    uMouse: { value: WAVE_DEFAULTS.uMouse.clone() },
    uWaveCenter: { value: WAVE_DEFAULTS.uWaveCenter.clone() },
    uTime: { value: 0 },
    uBreathFreq: { value: WAVE_DEFAULTS.uBreathFreq },
    uBreathAmp: { value: WAVE_DEFAULTS.uBreathAmp },
    uWaveSpeed: { value: WAVE_DEFAULTS.uWaveSpeed },
    uRingCount: { value: WAVE_DEFAULTS.uRingCount },
    uRingSpacing: { value: WAVE_DEFAULTS.uRingSpacing },
    uRingWidth: { value: WAVE_DEFAULTS.uRingWidth },
    uMouseRadius: { value: WAVE_DEFAULTS.uMouseRadius },
    uMouseSoftness: { value: WAVE_DEFAULTS.uMouseSoftness },
    uResolution: { value: WAVE_DEFAULTS.uResolution.clone() },
  };

  return new THREE.ShaderMaterial({
    uniforms,
    vertexShader: WAVE_VERTEX,
    fragmentShader: WAVE_FRAGMENT,
    transparent: false,
    depthWrite: true,
    depthTest: true,
    blending: THREE.NormalBlending,
    defines: {
      USE_SIZEATTENUATION: "",
    },
  });
}
