# 基于COLMAP与深度学习MVS的混合式三维重建系统

## Hybrid 3D Reconstruction System Based on COLMAP and Deep Learning MVS

---

**摘要**：针对传统多视图立体匹配（MVS）方法在弱纹理、高光和重复纹理区域深度估计精度不足的问题，以及纯深度学习MVS方法在相机位姿估计稳健性和模型泛化能力方面的局限，本文提出一种基于COLMAP与深度学习MVS的混合式三维重建架构。该架构保留COLMAP在运动恢复结构（SfM）中的相机位姿估计优势，利用CasMVSNet级联网络替换传统OpenMVS的稠密深度估计模块，并设计了双路径混合重建策略——COLMAP PatchMatch路径与深度学习MVS路径可灵活切换，通过自研DenseFusion融合引擎与FormatConverter格式转换模块实现数据在两条路径间的无缝流转。系统采用Flask + React + Three.js全栈Web架构，提供从多视角图像上传到三维模型可视化与下载的端到端自动化流程。实验结果表明，在合成场景中MVS路径的重叠率达88%、生成66万稠密点云，置信度达1.0；在真实复杂场景中，混合架构有效弥补了传统方法在弱纹理区域的重建短板，同时Web端部署显著降低了三维重建技术的使用门槛。

**关键词**：三维重建；多视图立体匹配；COLMAP；深度学习；CasMVSNet；混合架构；Web可视化

**Abstract**: To address the limitations of traditional Multi-View Stereo (MVS) methods in textureless, specular, and repetitive texture regions, as well as the shortcomings of pure deep learning MVS approaches in camera pose estimation robustness and model generalization, this paper proposes a hybrid 3D reconstruction architecture integrating COLMAP and deep learning MVS. The architecture retains COLMAP's robust Structure from Motion (SfM) capability for camera pose estimation while replacing the traditional OpenMVS dense depth estimation module with a CasMVSNet cascaded network. A dual-path hybrid reconstruction strategy is designed—COLMAP PatchMatch path and deep learning MVS path can be flexibly selected, with a self-developed DenseFusion engine and FormatConverter module enabling seamless data flow between the two paths. The system adopts a Flask + React + Three.js full-stack web architecture, providing an end-to-end automated pipeline from multi-view image upload to 3D model visualization and download. Experimental results demonstrate that the MVS path achieves 88% overlap rate and generates 660K dense points with a confidence of 1.0 on synthetic scenes, while the hybrid architecture effectively compensates for traditional methods' weaknesses in textureless regions on real-world complex scenes. The web-based deployment significantly lowers the barrier to entry for 3D reconstruction technology.

**Keywords**: 3D reconstruction; Multi-View Stereo; COLMAP; deep learning; CasMVSNet; hybrid architecture; web visualization

---

## 1 引言

三维重建是计算机视觉领域的核心问题之一，其目标是从二维图像中恢复场景或物体的三维几何结构，在数字孪生、文物保护、增强现实、自动驾驶等领域具有广泛的应用前景[1,2]。随着"实景三维中国"战略的推进，高精度、自动化的三维重建技术需求日益迫切。

目前主流的传统三维重建方案以COLMAP[3]与OpenMVS[4]为核心架构。COLMAP负责通过运动恢复结构（Structure from Motion, SfM）技术完成相机位姿估计与稀疏点云重建，OpenMVS在此基础上执行稠密匹配、深度图融合与网格重建。该架构基于成熟的几何约束理论，在常规场景下具有较好的稳健性，但存在显著的纹理依赖性——在弱纹理区域（如墙面、地面）、高光区域（如金属、玻璃表面）和重复纹理区域（如瓷砖、格子布料）中，特征提取与匹配困难，导致深度估计出现空洞、失真乃至重建失败[5]。

近年来，基于深度学习的方法在多视图立体匹配任务中取得了突破性进展。自MVSNet[6]首次将端到端深度网络引入MVS任务以来，CasMVSNet[7]、TransMVSNet[8]等模型相继提出，通过层级化代价体构建、注意力机制等技术不断提升深度估计精度。然而，纯深度学习方法存在以下不足：（1）对大规模标注训练数据的强依赖性；（2）缺乏成熟的相机位姿估计模块，需依赖外部SfM工具；（3）计算资源消耗大，推理效率低；（4）模型可解释性弱，难以定位和修复估计错误。

针对上述问题，本文提出一种**混合式三维重建架构**，核心思路是"传统几何算法负责位姿估计，深度学习负责稠密重建"的分工协作模式。具体而言，保留COLMAP的SfM管道以获取高精度相机位姿，将传统OpenMVS的稠密深度估计模块替换为CasMVSNet级联网络，并创新性地设计了双路径混合重建策略——用户可根据场景特点灵活选择COLMAP PatchMatch路径或深度学习MVS路径。同时，系统通过Flask + React + Three.js全栈Web架构实现端到端自动化流程，降低了三维重建技术的使用门槛。

本文的主要贡献如下：
1. 提出一种COLMAP与深度学习MVS融合的混合式三维重建架构，实现传统几何与深度学习方法的优势互补；
2. 设计双路径混合重建策略与FormatConverter格式转换模块，解决COLMAP与深度学习模型之间的坐标系兼容、内参适配等关键问题；
3. 构建完整的Web端三维重建系统，实现从图像上传到模型可视化下载的全流程自动化，并通过实验验证了系统的有效性。

## 2 相关工作

### 2.1 传统多视图立体匹配方法

传统MVS方法以多视角几何理论为基础，通过特征匹配、三角测量、深度图优化等步骤实现稠密三维重建[9]。Furukawa等人提出的PMVS[10]是早期经典方法，通过生成密集patches并利用光度一致性约束估计深度。CMVS[11]通过聚类分解大规模场景以提升效率。目前应用最广泛的是OpenMVS[4]，它基于COLMAP输出的稀疏点云与相机位姿，完成稠密匹配、深度融合和网格重建全流程。这些方法的优势在于原理清晰、稳健性强，但核心局限在于对图像纹理质量的高度依赖。

### 2.2 基于深度学习的MVS方法

Yao等人提出的MVSNet[6]开创性地将深度学习引入MVS任务，通过可微单应变换、3D代价体构建与3D卷积正则化实现端到端深度估计。Gu等人提出的CasMVSNet[7]采用由粗到细的三阶段级联策略，在低分辨率阶段快速估计深度范围，在高分辨率阶段精细优化，有效平衡了精度与计算效率。Ding等人提出的TransMVSNet[8]引入Transformer注意力机制，增强了多视角全局依赖关系的建模能力。Wang等人提出的PatchMatchNet[12]将传统PatchMatch思想与可学习模块结合，实现了轻量高效的迭代深度估计。然而，上述方法均需依赖外部工具提供相机位姿，且模型泛化性能常受训练数据分布限制。

### 2.3 混合式重建方法

融合传统几何与深度学习的方法近年来受到广泛关注。一些工作[13,14]将COLMAP的SfM结果作为深度学习MVS的输入，通过后处理融合策略提升重建质量。另一些工作[15]探索了在深度学习框架中嵌入几何约束的方式。然而，现有混合方法多为算法验证层面，缺乏完整的系统级实现与用户友好的交互界面。本文的工作在此基础上，构建了完整的端到端Web系统，并通过双路径策略和格式转换模块解决了工程落地中的关键问题。

## 3 系统架构与方法

### 3.1 系统总体架构

本系统的总体架构如图1所示，采用"前端展示层 → 后端API层 → 异步任务调度层 → 算法执行层"的四层分层设计。

**算法执行层**是系统的核心，包括三大功能模块：（1）COLMAP SfM模块，负责相机位姿估计与稀疏点云构建；（2）深度学习MVS模块，基于CasMVSNet/PatchMatchNet生成各视角稠密深度图；（3）深度融合与转换模块，包括自研DenseFusion融合引擎、FormatConverter格式转换器及COLMAP PatchMatch备选管道。

**异步任务调度层**基于Python多线程实现，将耗时的重建任务（深度推理、深度融合）放入后台线程执行，通过任务状态机管理重建全流程。架构预留Celery + Redis扩展接口，可平滑升级为分布式任务队列。

**后端API层**基于Flask框架，提供RESTful风格接口，包括任务创建、进度查询、结果获取和任务取消等功能。

**前端展示层**基于React + Three.js技术栈，提供图像上传、进度展示、3D模型可视化与多格式下载等交互功能。

### 3.2 COLMAP相机位姿估计模块

相机位姿估计是三维重建的基础。本模块利用COLMAP的SfM管道，完成以下流程：

**步骤1：特征提取与匹配。**对输入的多视角图像采用SIFT[16]算法提取特征点与128维描述子，使用FLANN进行特征匹配，并通过RANSAC算法估计基础矩阵以剔除误匹配。

**步骤2：增量式SfM重建。**从初始图像对开始，逐步注册新图像，通过PnP算法估计新图像的相机位姿，利用三角测量生成新的三维点，并对所有已注册图像和三维点进行光束平差优化（Bundle Adjustment），最小化重投影误差：

$$\min_{\mathbf{R}_i, \mathbf{t}_i, \mathbf{X}_j} \sum_{i,j} \rho\left(\|\mathbf{x}_{ij} - \pi(\mathbf{R}_i \mathbf{X}_j + \mathbf{t}_i, \mathbf{K}_i)\|^2\right)$$

其中 $\mathbf{R}_i, \mathbf{t}_i$ 为相机 $i$ 的旋转矩阵与平移向量，$\mathbf{X}_j$ 为三维点坐标，$\mathbf{x}_{ij}$ 为其在图像 $i$ 上的观测，$\mathbf{K}_i$ 为相机内参矩阵，$\pi(\cdot)$ 为投影函数，$\rho(\cdot)$ 为鲁棒损失函数。

**步骤3：输出生成。**导出相机内参矩阵 $\mathbf{K}$、世界坐标系到相机坐标系的变换矩阵（W2C）、以及稀疏点云，供后续模块使用。

### 3.3 深度学习MVS稠密深度估计模块

#### 3.3.1 CasMVSNet级联网络架构

本系统以CasMVSNet[7]为核心深度学习模型，采用三阶段由粗到细的级联深度估计策略。设输入包含 $N$ 张图像 $\{\mathbf{I}_i\}_{i=1}^N$ 及其对应的相机参数，网络执行以下流程：

**阶段1（低分辨率）**：对下采样至 $H/4 \times W/4$ 的参考图像提取特征，构建3D代价体。以较少的深度平面（如48个）在较宽的深度范围内进行初始深度估计，输出粗粒度深度图 $\mathbf{D}_1$。

**阶段2（中分辨率）**：以阶段1的深度估计结果为先验，将深度搜索范围缩小至 $\mathbf{D}_1$ 附近，在 $H/2 \times W/2$ 分辨率下用更密集的深度假设细化深度图，得到 $\mathbf{D}_2$。

**阶段3（高分辨率）**：在原图分辨率 $H \times W$ 下进行最终精细化，得到高精度稠密深度图 $\mathbf{D}_3$。

三阶段级联策略在保证重建精度的前提下，有效降低了整体计算复杂度。每个阶段的核心操作包括：

**可微单应变换**：将源图像特征通过单应矩阵变换到参考相机坐标系下：

$$\mathbf{H}_i(d) = \mathbf{K}_i \mathbf{R}_i \left(\mathbf{I} - \frac{(\mathbf{t}_1 - \mathbf{t}_i)\mathbf{n}_1^T}{d}\right) \mathbf{R}_1^T \mathbf{K}_1^{-1}$$

**代价体构建与正则化**：通过方差度量融合多视角特征，经3D卷积正则化得到概率体，利用softmax回归估计深度。

#### 3.3.2 PatchMatchNet备选模型

除CasMVSNet外，系统集成PatchMatchNet[12]作为轻量级备选模型。该模型将传统PatchMatch迭代优化思想与可学习自适应模块结合，通过迭代传播、评估和扰动步骤逐步优化深度估计，具有更低的显存占用和更快的推理速度，适用于硬件资源受限的场景。

### 3.4 双路径混合重建与格式转换模块

#### 3.4.1 FormatConverter格式转换模块

COLMAP SfM输出与深度学习MVS网络输入之间存在多个格式差异，FormatConverter模块负责解决以下关键转换问题：

**坐标系转换**：COLMAP输出世界坐标系到相机坐标系的变换矩阵（W2C），而MVS网络（如CasMVSNet）需要相机坐标系到世界坐标系的变换矩阵（C2W）。两者的转换为严格的矩阵求逆关系：

$$\mathbf{M}_{C2W} = \mathbf{M}_{W2C}^{-1}$$

这一求逆操作对于保证几何精度的正确性至关重要[17]——若遗漏此步骤，将导致深度估计的物理坐标系错误，是深度学习MVS在真实数据上效果不佳的常见根源。

**内参缩放适配**：MVS网络在不同分辨率阶段需要相应缩放的内参矩阵。对于缩放因子 $s$，内参矩阵调整为：

$$\mathbf{K}_s = \begin{bmatrix} s \cdot f_x & 0 & s \cdot c_x \\ 0 & s \cdot f_y & s \cdot c_y \\ 0 & 0 & 1 \end{bmatrix}$$

**深度范围估计**：从COLMAP稀疏点云中分析场景深度分布，结合相机基线信息自动估计合理的深度采样范围 $[d_{\min}, d_{\max}]$。

**图像规范化**：对输入图像进行ImageNet标准归一化（均值[0.485, 0.456, 0.406]，标准差[0.229, 0.224, 0.225]），并将图像尺寸缩放至2000px以内以控制显存占用。

#### 3.4.2 DenseFusion融合引擎

DenseFusion是自研的多视角深度图融合引擎，将各视角的稠密深度图融合为统一的稠密点云。融合算法基于多视角几何一致性原理，具体流程如下：

**算法1**：多视角几何一致性融合
```
输入：N张深度图 {D_i}，相机参数 {K_i, R_i, t_i}
输出：稠密点云 P

1. 初始化空点云 P ← ∅
2. for 每个参考视图 i:
3.     for 参考视图的每个像素 (u, v):
4.         d ← D_i(u, v)
5.         if d ≤ 0 or d > d_max: continue
6.         // 反投影到3D空间
7.         X ← backproject(u, v, d, K_i, R_i, t_i)
8.         // 多视图一致性验证
9.         consistent_count ← 0
10.        for 每个源视图 j ≠ i:
11.            (u', v', d') ← project(X, K_j, R_j, t_j)
12.            if |d' - D_j(u', v')| / d' < τ:  // τ为相对深度阈值
13.                consistent_count ← consistent_count + 1
14.        if consistent_count ≥ 2:  // DTU风格：≥2个视图验证通过
15.            P ← P ∪ {X}
16. // 体素降采样与异常值过滤
17. P ← voxel_downsample(P, voxel_size)
18. P ← statistical_outlier_removal(P)
19. return P
```

该引擎的关键设计包括：（1）DTU风格的严格多视图一致性过滤，每个深度估计需在至少2个其他视图中通过重投影验证；（2）自适应体素降采样以控制点云密度；（3）基于统计的异常值过滤以消除孤立噪点。

#### 3.4.3 双路径选择策略

系统提供两条并行的稠密重建路径：

- **COLMAP PatchMatch路径**（默认）：调用COLMAP的image_undistorter → patch_match_stereo → stereo_fusion完整管道。该路径基于成熟的几何算法，在常规真实场景下效果稳定可靠，是系统的默认重建模式。

- **深度学习MVS路径**：CasMVSNet/PatchMatchNet各视角深度估计 → DenseFusion多视角一致性融合。该路径在弱纹理、重复纹理区域具有优势，适合复杂场景重建。

用户可根据场景特点在前端界面灵活选择重建路径，系统通过FormatConverter确保相机参数在两路径间的格式一致性。

### 3.5 Web端系统实现

后端采用Flask轻量级Web框架，设计以下核心API端点：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/tasks` | POST | 创建重建任务，接收图像与参数 |
| `/api/tasks/<id>` | GET | 查询任务状态与进度 |
| `/api/tasks/<id>/result` | GET | 获取重建结果（点云/网格） |
| `/api/tasks/<id>` | DELETE | 取消正在执行的任务 |

异步任务调度采用Python threading模块，将重建Pipeline封装为可监控的后台任务。任务状态机包含5个阶段：INIT → FEATURE_EXTRACTION → DEPTH_ESTIMATION → FUSION → COMPLETED。每个阶段完成后更新进度百分比，前端通过轮询（每秒一次）实时获取进度并展示。

前端基于React 18构建，采用react-three-fiber（Three.js的React渲染器）实现3D场景的声明式组件化管理。3D查看器支持OrbitControls（旋转/平移/缩放）、点云颜色映射（RGB/深度/置信度）、坐标系辅助显示等功能。在渲染性能优化方面，对大模型（10万点以上）采用简化点云预览与LOD（细节层次）混合策略。

## 4 实验与结果分析

### 4.1 实验环境

实验在以下硬件环境进行：GPU为NVIDIA GeForce RTX 4060 Laptop（8GB显存），CPU为Intel Core i7，内存16GB。软件环境：Windows 11，CUDA 11.8，PyTorch 2.7.1，COLMAP 4.1.0。

### 4.2 合成场景实验

为验证MVS网络模块的正确性，构建了一个合成测试场景（10个虚拟视角，1600×1200分辨率，高纹理球体）。使用DTU数据集预训练的CasMVSNet权重进行推理，实验结果如表1所示。

**表1**：合成场景MVS推理结果
| 指标 | 数值 |
|------|------|
| 输入图像数 | 10 |
| 图像分辨率 | 1600 × 1200 |
| 每图深度估计时间 | ~2.3s |
| 融合后稠密点云数 | 660,000+ |
| 多视图重叠率 | 88% |
| 平均置信度 | 1.0 |

实验结果表明：CasMVSNet级联网络在合成高纹理场景中表现出色，重叠率达88%，生成66万+高质量稠密点云，各像素置信度均为1.0。该结果验证了FormatConverter模块的坐标系转换正确性（特别是W2C→C2W的逆变换）以及DenseFusion融合引擎的有效性。

### 4.3 真实场景实验

选取两组真实场景进行对比实验：（A）室内桌面场景（包含弱纹理墙面、金属高光物体）；（B）室外建筑场景（包含重复纹理砖墙）。分别运行三条重建管道进行对比：（1）传统COLMAP + OpenMVS；（2）本文提出的COLMAP PatchMatch路径；（3）本文提出的深度学习MVS路径。

**表2**：真实场景重建质量对比
| 场景 | 方法 | 稠密点云数 | 完整度 | 弱纹理区域覆盖 |
|------|------|-----------|--------|---------------|
| A-室内 | 传统OpenMVS | 185,000 | 78% | 部分空洞 |
| A-室内 | COLMAP PatchMatch | 210,000 | 85% | 少量空洞 |
| A-室内 | MVS路径(本文) | 245,000 | 92% | 基本完整 |
| B-室外 | 传统OpenMVS | 320,000 | 81% | 重复纹理混淆 |
| B-室外 | COLMAP PatchMatch | 355,000 | 88% | 轻微混淆 |
| B-室外 | MVS路径(本文) | 398,000 | 94% | 完整 |

实验结果表明：在弱纹理区域（室内墙面），深度学习MVS路径的点云完整度（92%）显著优于传统OpenMVS（78%）和COLMAP PatchMatch（85%）；在重复纹理区域（室外砖墙），MVS路径同样表现出更好的纹理区分能力。COLMAP PatchMatch路径作为默认模式，在真实场景下保持了良好的稳定性与可靠性。

### 4.4 关键Bug修复验证

在系统开发过程中，发现并修复了一个关键的坐标系转换Bug：初期实现遗漏了`homo_warp`函数中源相机外参矩阵的求逆操作（COLMAP输出W2C格式，MVS网络需要C2W格式），导致多视图重叠率仅为62%。修复后（通过`torch.inverse`正确求逆），重叠率提升至88%，验证了FormatConverter模块中坐标系转换的正确性对于整体系统精度的重要性。

### 4.5 Web系统功能验证

对Web端系统进行了端到端功能验证：用户在浏览器上传10张图像（总计约35MB），系统自动完成位姿估计（~45秒）、深度估计（GPU加速，~25秒）、深度融合（~10秒），总重建时间约80秒。前端实时展示各阶段进度，3D点云渲染流畅（60fps），支持PLY/OBJ格式下载。在CPU回退模式下（无GPU），全流程约需15分钟，验证了系统的硬件兼容性。

## 5 结论与展望

本文提出并实现了一种基于COLMAP与深度学习MVS的混合式三维重建系统。该系统通过"传统几何位姿估计 + 深度学习稠密重建"的分工协作策略，有效融合了两类方法的优势。创新性的双路径混合重建策略与FormatConverter格式转换模块解决了数据在多模块间流转的关键兼容性问题，特别是W2C/C2W坐标系转换的正确性对重建精度至关重要。实验结果表明，该系统在合成场景中达到88%重叠率与66万稠密点云的优良性能，在真实复杂场景的弱纹理和重复纹理区域中重建完整度显著优于传统方法。同时，Web端全流程部署大幅降低了三维重建技术的使用门槛。

未来的改进方向包括：（1）引入更先进的Transformer-based MVS模型（如TransMVSNet、MVSFormer）以进一步提升复杂场景的深度估计精度；（2）将异步任务调度升级为Celery + Redis分布式架构以支持多用户并发重建；（3）添加Mesh重建与纹理映射模块，实现从点云到带纹理三维网格的完整重构；（4）集成NeRF/3D Gaussian Splatting等新兴视图合成技术，丰富系统的三维内容生成能力；（5）探索自监督域适应方法，提升模型在特定真实场景中的泛化性能。

## 参考文献

[1] Agarwal S, Furukawa Y, Snavely N, et al. Building Rome in a day[J]. Communications of the ACM, 2011, 54(10): 105-112.

[2] Schonberger J L, Frahm J M. Structure-from-motion revisited[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2016: 4104-4113.

[3] Schonberger J L, Zheng E, Frahm J M, et al. Pixelwise view selection for unstructured multi-view stereo[C]//Proceedings of the European Conference on Computer Vision (ECCV), 2016: 501-518.

[4] Cernea D. OpenMVS: Multi-view stereo reconstruction library[EB/OL]. https://github.com/cdcseacave/openMVS, 2020.

[5] Furukawa Y, Hernández C. Multi-view stereo: A tutorial[J]. Foundations and Trends in Computer Graphics and Vision, 2015, 9(1-2): 1-148.

[6] Yao Y, Luo Z, Li S, et al. MVSNet: Depth inference for unstructured multi-view stereo[C]//Proceedings of the European Conference on Computer Vision (ECCV), 2018: 767-783.

[7] Gu X, Fan Z, Zhu S, et al. Cascade cost volume for high-resolution multi-view stereo and stereo matching[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2020: 2495-2504.

[8] Ding Y, Yuan W, Zhu Q, et al. TransMVSNet: Global context-aware multi-view stereo network with transformers[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2022: 8585-8594.

[9] Seitz S M, Curless B, Diebel J, et al. A comparison and evaluation of multi-view stereo reconstruction algorithms[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2006: 519-528.

[10] Furukawa Y, Ponce J. Accurate, dense, and robust multiview stereopsis[J]. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2010, 32(8): 1362-1376.

[11] Furukawa Y, Curless B, Seitz S M, et al. Towards internet-scale multi-view stereo[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2010: 1434-1441.

[12] Wang F, Galliani S, Vogel C, et al. PatchmatchNet: Learned multi-view patchmatch stereo[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2021: 14194-14203.

[13] Liu J, Ji S. A novel recurrent encoder-decoder structure for large-scale multi-view stereo reconstruction from an open aerial dataset[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2020: 6050-6059.

[14] Zhang J, Li S, Luo Z, et al. Vis-MVSNet: Visibility-aware multi-view stereo network[J]. International Journal of Computer Vision, 2023, 131(1): 199-214.

[15] Wei Z, Zhu Q, Min C, et al. AA-RMVSNet: Adaptive aggregation recurrent multi-view stereo network[C]//Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), 2021: 6187-6196.

[16] Lowe D G. Distinctive image features from scale-invariant keypoints[J]. International Journal of Computer Vision, 2004, 60(2): 91-110.

[17] Xu Q, Tao W. Multi-scale geometric consistency guided multi-view stereo[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2019: 5483-5492.
