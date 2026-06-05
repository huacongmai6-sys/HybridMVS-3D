import { useEffect, useRef } from "react";

/**
 * DotWaveBackground — 随机飘浮点阵背景 + 鼠标扰动
 *
 * 每个点独立随机漂移，向随机目标缓慢移动，叠加微幅正弦扰动。
 * 鼠标周围形成排斥场，推开附近的点并使其变亮变大。
 * 参考粒子浮游风格，不使用外部动画库。
 */

const NUM_DOTS = 600;
const MOUSE_RADIUS = 100;          // 鼠标影响半径 px
const MOUSE_STRENGTH = 35;         // 最大推力
const MOUSE_SMOOTH = 0.08;         // 鼠标平滑跟随系数 (每帧 lerp)
const MAX_SPEED = 0.8;             // 最大漂移速度 px/帧 @60fps
const WANDER_FORCE = 0.03;         // 随机游走力度

// 5 色调色板（参考原版粒子动画）
const PALETTE = [
  [178, 148, 157],  // #B2949D 紫灰 mauve
  [255, 245, 120],  // #FFF578 暖黄
  [255, 95, 141],   // #FF5F8D 粉红
  [55, 169, 204],   // #37A9CC 浅青
  [24, 142, 178],   // #188EB2 深青
];

export default function DotWaveBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let animId;
    let running = true;
    let W = 0;
    let H = 0;

    // ── 鼠标状态 ──────────────────────────────────────
    let mouseX = -1000;
    let mouseY = -1000;
    let smoothMouseX = -1000;
    let smoothMouseY = -1000;
    let mouseActive = false;

    // ── 点数组 ──────────────────────────────────────
    let dots = [];

    const rand = (min, max) => min + Math.random() * (max - min);

    /** 初始化所有点：随机位置 + 随机速度 + 个体参数 */
    const initDots = () => {
      dots = [];
      for (let i = 0; i < NUM_DOTS; i++) {
        const angle = rand(0, Math.PI * 2);
        const spd = rand(0.1, MAX_SPEED);
        dots.push({
          x: rand(0, W),
          y: rand(0, H),
          vx: Math.cos(angle) * spd,     // 随机初始速度方向
          vy: Math.sin(angle) * spd,
          radius: rand(6, 12),
          baseAlpha: rand(0.2, 0.55),
          colorIndex: Math.floor(Math.random() * PALETTE.length),
        });
      }
    };

    // ── Resize ───────────────────────────────────────
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      initDots();
    };

    resize();
    window.addEventListener("resize", resize);

    // ── 鼠标事件 ─────────────────────────────────────
    const onMouseMove = (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      if (!mouseActive) {
        smoothMouseX = mouseX;
        smoothMouseY = mouseY;
      }
      mouseActive = true;
    };

    const onMouseLeave = () => {
      mouseActive = false;
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("mouseleave", onMouseLeave);

    const mouseRadius2 = MOUSE_RADIUS * MOUSE_RADIUS;
    const FPS_NORM = 60; // 归一化到 60fps 的速度基准

    // ── 主绘制循环 ──────────────────────────────────
    const draw = (time) => {
      ctx.clearRect(0, 0, W, H);

      // ── 蓝色渐变背景 ────────────────────────────────
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

      // ── 平滑鼠标 ────────────────────────────────────
      smoothMouseX += (mouseX - smoothMouseX) * MOUSE_SMOOTH;
      smoothMouseY += (mouseY - smoothMouseY) * MOUSE_SMOOTH;

      // ── 横向扫描线 ──────────────────────────────────
      ctx.strokeStyle = "rgba(90, 120, 190, 0.04)";
      ctx.lineWidth = 1;
      const scanOffset = (t * 35) % 110;
      for (let sy = -110 + scanOffset; sy < H + 110; sy += 110) {
        ctx.beginPath();
        ctx.moveTo(0, sy);
        ctx.lineTo(W, sy);
        ctx.stroke();
      }

      // ── 更新点位置（纯随机游走）────────────────────
      const dtNorm = dt * FPS_NORM;

      for (const dot of dots) {
        // ① 随机扰动加速度（布朗运动）
        const ax = rand(-WANDER_FORCE, WANDER_FORCE) * dtNorm;
        const ay = rand(-WANDER_FORCE, WANDER_FORCE) * dtNorm;
        dot.vx += ax;
        dot.vy += ay;

        // ② 限速
        const spd = Math.sqrt(dot.vx * dot.vx + dot.vy * dot.vy);
        if (spd > MAX_SPEED) {
          dot.vx = (dot.vx / spd) * MAX_SPEED;
          dot.vy = (dot.vy / spd) * MAX_SPEED;
        }

        // ③ 更新位置
        dot.x += dot.vx * dtNorm;
        dot.y += dot.vy * dtNorm;

        // ④ 边界软反弹
        if (dot.x < 0) { dot.x = 0; dot.vx *= -1; }
        if (dot.x > W) { dot.x = W; dot.vx *= -1; }
        if (dot.y < 0) { dot.y = 0; dot.vy *= -1; }
        if (dot.y > H) { dot.y = H; dot.vy *= -1; }
      }

      // ── 鼠标排斥场（第二遍遍历，确保所有点位置已更新）──
      if (mouseActive) {
        for (const dot of dots) {
          const mdx = dot.x - smoothMouseX;
          const mdy = dot.y - smoothMouseY;
          const mdist2 = mdx * mdx + mdy * mdy;

          if (mdist2 < mouseRadius2 && mdist2 > 0.01) {
            const mdist = Math.sqrt(mdist2);
            // 二次衰减：距离越近推力越大
            const factor = 1 - mdist / MOUSE_RADIUS;
            const push = MOUSE_STRENGTH * factor * factor * dtNorm;

            dot.x += (mdx / mdist) * push;
            dot.y += (mdy / mdist) * push;
          }
        }
      }

      // ── 绘制所有点 ──────────────────────────────────
      for (const dot of dots) {
        let alpha = dot.baseAlpha;
        let radius = dot.radius;
        let brightness = 0;

        // 鼠标附近的点更亮更大
        if (mouseActive) {
          const mdx = dot.x - smoothMouseX;
          const mdy = dot.y - smoothMouseY;
          const mdist2 = mdx * mdx + mdy * mdy;

          if (mdist2 < mouseRadius2) {
            const mdist = Math.sqrt(mdist2);
            const factor = 1 - mdist / MOUSE_RADIUS;
            brightness = factor;
            alpha = Math.min(dot.baseAlpha + factor * 0.5, 0.82);
            radius = dot.radius * (1 + factor * 0.7);
          }
        }

        // 颜色：从 5 色调色板取色，带透明度
        const [pr, pg, pb] = PALETTE[dot.colorIndex];
        // 鼠标附近略微提亮
        const cr = Math.round(Math.min(pr + brightness * 30, 255));
        const cg = Math.round(Math.min(pg + brightness * 30, 255));
        const cb = Math.round(Math.min(pb + brightness * 30, 255));

        ctx.beginPath();
        ctx.arc(dot.x, dot.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${alpha})`;
        ctx.fill();
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
