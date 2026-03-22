# 深入理解 Godot 引擎 #15 | 光照系统

> **摘要**：Godot 的光照系统支持实时光照、烘焙光照、全局光照。本文将深入分析光照类型、阴影、SDFGI。

---

## 一、光照类型

### 1.1 光源类型

| 类型 | 说明 | 使用场景 |
|------|------|---------|
| **DirectionalLight** | 平行光 | 太阳光 |
| **OmniLight** | 点光源 | 灯泡、火把 |
| **SpotLight** | 聚光灯 | 手电筒、舞台灯 |
| **WorldEnvironment** | 环境光 | 天空光 |

### 1.2 光照属性

```gdscript
# 光源属性
var light = DirectionalLight3D.new()
light.light_color = Color(1, 0.9, 0.8)  # 暖色阳光
light.light_energy = 1.5  # 光照强度
light.shadow_enabled = true  # 启用阴影
light.shadow_max_distance = 100  # 阴影最大距离
```

---

## 二、阴影系统

### 2.1 阴影类型

| 类型 | 说明 | 性能 |
|------|------|------|
| **硬阴影** | 清晰边缘 | 低 |
| **软阴影** | 模糊边缘 | 中 |
| **PCF 阴影** | 百分比渐近 | 中 |
| **VSM 阴影** | 方差阴影 | 高 |

### 2.2 阴影优化

```gdscript
# 阴影设置
var light = DirectionalLight3D.new()
light.shadow_enabled = true
light.shadow_max_distance = 50  # 减少阴影距离
light.shadow_orthogonal_size = 20  # 正交大小
light.shadow_bias = 0.01  # 阴影偏移
```

---

## 三、全局光照（GI）

### 3.1 SDFGI（实时 GI）

Godot 4.x 的 SDFGI 是实时全局光照技术：

| 特性 | 说明 |
|------|------|
| **实时** | 动态更新 |
| **体素化** | 空间分割 |
| **反射** | 间接光照 |
| **性能** | 中等 |

### 3.2 SDFGI 设置

```gdscript
# 启用 SDFGI
var sdfgi = WorldEnvironment.new()
sdfgi.environment.glow_enabled = true
sdfgi.environment.sdfgi_enabled = true
sdfgi.environment.sdfgi_y_scale = 1.0
```

---

## 四、光照烘焙

### 4.1 烘焙光照贴图

```gdscript
# 烘焙设置
var gi = LightmapGI.new()
gi.bake_mode = LightmapGI.BAKE_MODE_STATIC
gi.quality = LightmapGI.QUALITY_HIGH
gi.light_data = "res://lightmap.gi"

# 开始烘焙
gi.bake(get_tree().root)
```

### 4.2 烘焙 vs 实时

| 维度 | 烘焙 | 实时 |
|------|------|------|
| **性能** | 高 | 中 |
| **质量** | 高 | 中 |
| **动态** | ❌ | ✅ |
| **内存** | 高 | 低 |

---

## 五、总结

### 核心要点

1. **光照类型**：Directional、Omni、Spot
2. **阴影系统**：硬阴影、软阴影、PCF、VSM
3. **全局光照**：SDFGI（实时）、烘焙
4. **性能优化**：根据平台选择

### 下一篇

**下一篇**: 材质系统

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #14 | 场景渲染流程](#)  
**下一篇**: [深入理解 Godot 引擎 #16 | 材质系统](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
