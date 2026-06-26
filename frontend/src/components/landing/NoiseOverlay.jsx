/**
 * NoiseOverlay — 微噪点纹理叠加层
 *
 * 使用 CSS repeating-conic-gradient 模拟胶片噪点质感，
 * 零外部资源依赖，零 JS 开销。
 * 参考 a.md 设计稿的 noise 覆盖层效果。
 */
export default function NoiseOverlay() {
  return <div className="noise-overlay" aria-hidden="true" />;
}
