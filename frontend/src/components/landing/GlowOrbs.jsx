/**
 * GlowOrbs — 氛围光斑背景层
 *
 * 3 个缓慢浮动的彩色模糊光斑，纯 CSS 动画驱动，零 JS 开销。
 * 参考 a.md 设计稿的光斑氛围效果。
 */
export default function GlowOrbs() {
  return (
    <div className="glow-orbs" aria-hidden="true">
      <div className="glow-orb glow-orb--1" />
      <div className="glow-orb glow-orb--2" />
      <div className="glow-orb glow-orb--3" />
    </div>
  );
}
