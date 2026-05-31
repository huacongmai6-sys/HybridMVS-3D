# HybridMVS - 基于COLMAP与深度学习MVS的混合式三维重建系统

## 环境
- Conda env: `hybridMVS` (Python 3.10, PyTorch 2.7.1+cu118)
- GPU: RTX 4060 Laptop 8GB
- COLMAP: `C:/Users/45310/colmap/bin/colmap.exe` (v4.1.0 CUDA)

## 启动
```bash
# 终端1: 后端
conda activate hybridMVS
cd d:/HybridMVS/backend
python app.py

# 终端2: 前端
cd d:/HybridMVS/frontend
npm run dev
# 浏览器: http://localhost:5173
```

## 项目结构
```
hybridmvs/
├── colmap_wrapper/   # COLMAP SfM + 稠密重建引擎
├── mvs_network/      # MVSNet/CasMVSNet 深度学习MVS
│   ├── modules.py    # FeatureNet, CostRegNet, homo_warp
│   ├── cas_mvsnet.py # 三阶段级联MVS(当前用单阶段stage0+cost_reg_2)
│   └── inference.py  # 推理管道
├── fusion/           # 深度图融合 + 格式转换
└── pipeline.py       # 主入口, use_colmap_dense=True用PatchMatch/False用MVS
backend/              # Flask API + 异步线程
frontend/             # React + Three.js 3D查看器
checkpoints/          # 预训练权重(DTU/BlendedMVS)
```

## 关键问题
- **use_colmap_dense=True** (backend/tasks.py): COLMAP PatchMatch稠密重建, 结果可靠, 稀疏和稠密一致
- **use_colmap_dense=False**: MVS模式, 已修bug(homo_warp源相机外参未取逆, 重叠率62%→88%), 但稠密点云质量仍不理想
- 合成测试场景: `d:/HybridMVS/test_mvs_scene/` (10 views, 1600x1200, 高纹理球体)
- 合成测试结果: `d:/HybridMVS/test_mvs_full/output/` (66万点, 88%重叠, 置信度1.0)
- 真实照片MVS效果差, 疑似深度估计偏差大

## 代码关键细节
- `modules.py:homo_warp()` - 参考和源相机都需W2C, 通过torch.inverse转换
- `pipeline.py` - K_list用于融合(像素坐标), MVS推理也用同一套K
- `cas_mvsnet.py` - 当前只用stage0(8ch) + cost_reg_2(8ch), 48深度平面
- Pretrained weights通过convert_checkpoint.py从Lightning ckpt转换

## 测试
```bash
conda activate hybridMVS
python test_all.py          # 14项全量测试
python test_imports.py      # 模块导入验证
python test_mvs_scene.py    # 生成合成纹理球体测试数据
```
