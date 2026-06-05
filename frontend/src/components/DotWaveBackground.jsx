import { useEffect, useRef } from "react";

/**
 * DotWaveBackground — 浅色主题点阵波动背景 + 丝滑鼠标涟漪交互
 *
 * 鼠标周围形成连续排斥场，点阵如丝绸般被推开。
 * 鼠标移动时额外抛射扩散涟漪环，如水投石子。
 */

const DOT_SPACING = 20;
const WAVES = [
  { amp: 12, freq: 0.0022, speed: 0.22, angle: 0.35 },
  { amp: 8,  freq: 0.0038, speed: 0.38, angle: -0.55 },
  { amp: 10, freq: 0.0028, speed: 0.28, angle: 1.05 },
  { amp: 6,  freq: 0.0052, speed: 0.48, angle: -0.18 },
  { amp: 5,  freq: 0.0065, speed: 0.58, angle: 0.72 },
];

// ── 连续排斥场参数 ──────────────────────────────────
const FIELD_SIGMA = 100;        // 排斥场高斯 σ (影响半径)
const FIELD_STRENGTH = 16;      // 最大推力 px
const FIELD_SMOOTH = 0.12;      // 鼠标平滑跟随系数 (每帧 lerp)

// ── 离散涟漪参数 ────────────────────────────────────
const RIPPLE_INIT_AMP = 18;
const RIPPLE_SPEED = 90;
const RIPPLE_SIGMA = 30;
const RIPPLE_DECAY = 0.968;
const RIPPLE_THROTTLE_MS = 50;
const RIPPLE_MIN_DIST = 16;
const RIPPLE_MIN_AMP = 0.3;

export default function DotWaveBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let animId;
    let running = true;
    let W = 0;
    let H = 0;

    // ── 鼠标 & 涟漪状态 ──────────────────────────────
    let mouseX = -1000;
    let mouseY = -1000;
    let smoothMouseX = -1000;
    let smoothMouseY = -1000;
    let mouseActive = false;
    let lastRippleTime = 0;
    let lastRippleX = -1000;
    let lastRippleY = -1000;
    const ripples = []; // { cx, cy, radius, amplitude }

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    window.addEventListener("resize", resize);

    // ── 鼠标事件 ─────────────────────────────────────
    const onMouseMove = (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;

      // 鼠标进入时，smoothed 直接跳到当前位置（避免从远处滑入）
      if (!mouseActive) {
        smoothMouseX = mouseX;
        smoothMouseY = mouseY;
      }
      mouseActive = true;

      const now = performance.now();
      const dx = mouseX - lastRippleX;
      const dy = mouseY - lastRippleY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (now - lastRippleTime >= RIPPLE_THROTTLE_MS && dist >= RIPPLE_MIN_DIST) {
        ripples.push({
          cx: mouseX,
          cy: mouseY,
          radius: 0,
          amplitude: RIPPLE_INIT_AMP,
        });
        lastRippleTime = now;
        lastRippleX = mouseX;
        lastRippleY = mouseY;
      }
    };

    const onMouseLeave = () => {
      mouseActive = false;
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("mouseleave", onMouseLeave);

    const maxWaveDisp = WAVES.reduce((s, w) => s + w.amp, 0);
    const rippleSigma2 = 2 * RIPPLE_SIGMA * RIPPLE_SIGMA;
    const fieldSigma2 = 2 * FIELD_SIGMA * FIELD_SIGMA;

    const draw = (time) => {
      ctx.clearRect(0, 0, W, H);

      // ── 蓝色渐变 ──────────────────────────────────
      const grad = ctx.createRadialGradient(
        W * 0.25, H * 0.15, 0,
        W * 0.55, H * 0.55, W * 1.3,
      );
      grad.addColorStop(0.0, "#e8ecf5");
      grad.addColorStop(0.3, "#dce2f0");
      grad.addColorStop(0.65, "#d0d8ea");
      grad.addColorStop(1.0, "#c8d0e4");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      const t = time * 0.001;
      const dt = Math.min((time - (draw._prevTime || time)) * 0.001, 0.1);
      draw._prevTime = time;

      // ── 平滑鼠标位置 ─────────────────────────────────
      smoothMouseX += (mouseX - smoothMouseX) * FIELD_SMOOTH;
      smoothMouseY += (mouseY - smoothMouseY) * FIELD_SMOOTH;

      // ── 更新涟漪 ─────────────────────────────────────
      for (let i = ripples.length - 1; i >= 0; i--) {
        const rp = ripples[i];
        rp.radius += RIPPLE_SPEED * dt;
        rp.amplitude *= RIPPLE_DECAY;
        if (rp.amplitude < RIPPLE_MIN_AMP) {
          ripples.splice(i, 1);
        }
      }

      // ── 横向扫描线 (极淡) ──────────────────────────────
      ctx.strokeStyle = "rgba(90, 120, 190, 0.05)";
      ctx.lineWidth = 1;
      const scanOffset = (t * 35) % 110;
      for (let sy = -110 + scanOffset; sy < H + 110; sy += 110) {
        ctx.beginPath();
        ctx.moveTo(0, sy);
        ctx.lineTo(W, sy);
        ctx.stroke();
      }

      // ── 点阵绘制 ──────────────────────────────────────
      for (let x = DOT_SPACING / 2; x < W + DOT_SPACING; x += DOT_SPACING) {
        for (let y = DOT_SPACING / 2; y < H + DOT_SPACING; y += DOT_SPACING) {
          // 正弦波位移
          let dx = 0, dy = 0;
          for (const w of WAVES) {
            const phase = t * w.speed;
            const proj = Math.cos(w.angle) * x + Math.sin(w.angle) * y;
            const val = Math.sin(proj * w.freq + phase);
            dx += Math.cos(w.angle) * val * w.amp;
            dy += Math.sin(w.angle) * val * w.amp;
          }

          let rippleBoost = 0;
          let mouseBoost = 0;

          // ── ① 连续排斥场：鼠标周围丝滑推开 ──────────
          if (mouseActive) {
            const mdx = x - smoothMouseX;
            const mdy = y - smoothMouseY;
            const mdist = Math.sqrt(mdx * mdx + mdy * mdy);
            if (mdist > 0.5) {
              const fieldFactor = Math.exp(-(mdist * mdist) / fieldSigma2);
              const push = FIELD_STRENGTH * fieldFactor;
              const nx = mdx / mdist;
              const ny = mdy / mdist;
              dx += nx * push;
              dy += ny * push;
              mouseBoost = fieldFactor;
            }
          }

          // ── ② 离散涟漪：移动时抛射波纹环 ─────────────
          let rippleDx = 0, rippleDy = 0;
          for (const rp of ripples) {
            const rdx = x - rp.cx;
            const rdy = y - rp.cy;
            const dist = Math.sqrt(rdx * rdx + rdy * rdy);
            if (dist < 0.5) continue;

            const ringArg = (dist - rp.radius);
            const ringFactor = Math.exp(-(ringArg * ringArg) / rippleSigma2);
            if (ringFactor < 0.001) continue;

            const nx = rdx / dist;
            const ny = rdy / dist;
            const push = rp.amplitude * ringFactor;
            rippleDx += nx * push;
            rippleDy += ny * push;
            if (ringFactor > rippleBoost) rippleBoost = ringFactor;
          }

          dx += rippleDx;
          dy += rippleDy;

          const px = x + dx;
          const py = y + dy;
          const disp = Math.sqrt(dx * dx + dy * dy);
          const intensity = Math.min(disp / maxWaveDisp, 1.0);

          // 综合亮度提升 (排斥场 + 涟漪)
          const boost = Math.min(mouseBoost * 0.5 + rippleBoost * 0.6, 0.7);
          const effectiveIntensity = Math.min(intensity + boost, 1.0);

          // ── 蓝色渐变圆点：中心深蓝 → 边缘浅蓝 ──────────
          const radius = 1.5 + effectiveIntensity * 2.8;
          const alpha = 0.18 + effectiveIntensity * 0.6;

          // 颜色随强度从饱满蓝渐变到鲜明蓝
          const cr = Math.round(30 + effectiveIntensity * 35);    // 30→65
          const cg = Math.round(65 + effectiveIntensity * 55);    // 65→120
          const cb = Math.round(185 + effectiveIntensity * 70);   // 185→255

          const gradDot = ctx.createRadialGradient(px, py, 0, px, py, radius);
          gradDot.addColorStop(0, `rgba(${cr},${cg},${cb},${alpha})`);
          gradDot.addColorStop(0.35, `rgba(${cr+25},${cg+25},${Math.min(cb+15,255)},${alpha*0.55})`);
          gradDot.addColorStop(1, `rgba(${cr+70},${cg+45},${Math.min(cb+5,255)},0)`);

          ctx.beginPath();
          ctx.arc(px, py, radius, 0, Math.PI * 2);
          ctx.fillStyle = gradDot;
          ctx.fill();
        }
      }

      // ── 纵向能量线 ──────────────────────────────────
      const energyPhase = t * 0.12;
      for (let i = 0; i < 3; i++) {
        const ex = (W * 0.12) + (W * 0.76) * ((i * 0.33 + energyPhase * 0.08) % 1);
        const gradLine = ctx.createLinearGradient(ex, 0, ex, H);
        gradLine.addColorStop(0, "rgba(80, 120, 210, 0)");
        gradLine.addColorStop(0.35, "rgba(80, 120, 210, 0.04)");
        gradLine.addColorStop(0.5, "rgba(80, 120, 210, 0.07)");
        gradLine.addColorStop(0.65, "rgba(80, 120, 210, 0.04)");
        gradLine.addColorStop(1, "rgba(80, 120, 210, 0)");
        ctx.fillStyle = gradLine;
        ctx.fillRect(ex - 1, 0, 2, H);
      }

      if (running) animId = requestAnimationFrame(draw);
    };

    animId = requestAnimationFrame(draw);

    return () => {
      running = false;
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseleave", onMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
      }}
    />
  );
}
