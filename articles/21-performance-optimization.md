# 第 21 篇：渲染性能优化

> **摘要**：渲染性能优化是游戏开发的关键。本文将深入分析 DrawCall 优化、LOD、遮挡剔除、GPU 优化。

---

## 一、DrawCall 优化

### 1.1 DrawCall 原理

```
每个 DrawCall
    ↓
CPU 准备数据
    ↓
GPU 执行渲染
    ↓
瓶颈：CPU 准备时间
```

### 1.2 合批优化

| 方法 | 说明 | 效果 |
|------|------|------|
| **自动合批** | 相同材质自动合并 | 50-80% |
| **手动合批** | 手动合并网格 | 60-90% |
| **GPU Instancing** | GPU 实例化 | 80-95% |
| **纹理图集** | 合并纹理 | 40-70% |

---

## 二、LOD（Level of Detail）

### 2.1 LOD 原理

```
近距离 → 高模（多边形多）
    ↓
中距离 → 中模（多边形中）
    ↓
远距离 → 低模（多边形少）
```

### 2.2 LOD 设置

```gdscript
var lod = LOD3D.new()
lod.add_level(high_poly_mesh, 0.0)    # 0-10 米
lod.add_level(medium_poly_mesh, 10.0) # 10-30 米
lod.add_level(low_poly_mesh, 30.0)    # 30+ 米
```

### 2.3 LOD 效果

> ⚠️ 下表为示意数据（未附测试环境），实际收益取决于材质数量、
> Draw Call 与过度绘制占比，请在目标平台实测。

| 距离 | 多边形数 | 预期收益 |
|------|---------|---------|
| 0-10m | 10000 | - |
| 10-30m | 5000 | 显著下降 |
| 30+m | 1000 | 接近消除几何开销 |

---

## 三、遮挡剔除

### 3.1 剔除类型

| 类型 | 说明 |
|------|------|
| **Frustum Culling** | 视锥体剔除 |
| **Occlusion Culling** | 遮挡剔除 |
| **Distance Culling** | 距离剔除 |

### 3.2 遮挡剔除设置

```gdscript
# 遮挡剔除的正确做法（Godot 4 没有 OcclusionCulling 类，也没有全局开关）：
# 1) 在场景中放置 OccluderInstance3D，把大块墙体/地板标记为遮挡体
# 2) 编辑器自动烘焙遮挡网格，运行时相机自动使用
var occluder := OccluderInstance3D.new()
occluder.name = "RoomOccluders"
add_child(occluder)
```

---

## 四、GPU 优化

### 4.1 GPU 优化技巧

| 技巧 | 说明 |
|------|------|
| **减少纹理大小** | 使用压缩纹理 |
| **减少着色器复杂度** | 简化计算 |
| **使用 Instancing** | GPU 实例化 |
| **减少 Overdraw** | 排序优化 |

### 4.2 纹理压缩

| 格式 | 平台 | 压缩比 |
|------|------|--------|
| **BPTC** | PC | 4:1 |
| **ETC2** | Android | 4:1 |
| **PVRTC** | iOS | 4:1 |
| **S3TC** | 通用 | 4:1 |

---

## 五、性能分析

### 5.1 分析工具

| 工具 | 说明 |
|------|------|
| **Profiler** | Godot 内置性能分析器 |
| **Monitor** | 实时性能监控 |
| **Vulkan Layer** | Vulkan 调试层 |

### 5.2 性能指标

| 指标 | 目标 |
|------|------|
| **帧率** | 60 FPS |
| **DrawCall** | <500 |
| **GPU 占用** | <80% |
| **显存占用** | <2GB |

---

## 六、总结

### 核心要点

1. **DrawCall 优化**：合批、Instancing
2. **LOD**：多层次细节
3. **遮挡剔除**：减少渲染对象
4. **GPU 优化**：纹理压缩、着色器简化

### 下一篇

**下一篇**: [第 22 篇：渲染调试工具](/articles/22-rendering-debug-tools.md)

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.3，2026-09 最新稳定版为 4.7）

---

**上一篇**: [第 20 篇：粒子渲染](/articles/20-particle-rendering.md)
**下一篇**: [第 22 篇：渲染调试工具](/articles/22-rendering-debug-tools.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
