# 深入理解 Godot 引擎 #18 | 2D 渲染

> **摘要**：Godot 有原生 2D 渲染引擎。本文将深入分析 2D 渲染架构、CanvasItem、2D 合批。

---

## 一、2D 渲染架构

### 1.1 原生 2D

Godot 使用原生 2D 渲染，而非 3D 模拟：

| 特性 | Godot | Unity |
|------|-------|-------|
| **2D 坐标** | 像素坐标 | 3D 投影 |
| **渲染器** | CanvasItem | 3D 管线 |
| **合批** | 自动 | 需配置 |
| **性能** | 优秀 | 良好 |

### 1.2 CanvasItem

```gdscript
# CanvasItem 是所有 2D 节点的基类
# Node2D
#   ├── Sprite2D
#   ├── Polygon2D
#   └── TileMap
# Control
#   ├── Label
#   ├── Button
#   └── Panel
```

---

## 二、2D 合批

### 2.1 合批原理

```
多个 Sprite2D
    ↓
相同纹理/材质
    ↓
合并为一个 DrawCall
    ↓
GPU 渲染
```

### 2.2 合批优化

| 技巧 | 效果 |
|------|------|
| **相同纹理** | 自动合批 |
| **相同材质** | 自动合批 |
| **TileMap** | 自动合批 |
| **NinePatch** | 特殊处理 |

---

## 三、2D 光照

### 3.1 2D 光照系统

```gdscript
# 2D 光源
var light = PointLight2D.new()
light.color = Color.YELLOW
light.energy = 2.0
light.shadow_enabled = true

# 2D 阴影
var shadow = LightOccluder2D.new()
shadow.occluder = occluder_resource
```

### 3.2 2D 法线贴图

```gdscript
# 2D 法线贴图材质
var material = CanvasItemMaterial.new()
material.normal_map = load("res://normal.png")
material.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
```

---

## 四、2D 优化

### 4.1 优化技巧

| 技巧 | 说明 |
|------|------|
| **纹理图集** | 合并纹理 |
| **TileMap** | 自动合批 |
| **可见性** | 关闭屏幕外渲染 |
| **LOD** | 远距离简化 |

### 4.2 性能对比

| 优化前 | 优化后 | 提升 |
|--------|--------|------|
| 100 DrawCall | 20 DrawCall | 80% |
| 60 FPS | 120 FPS | 100% |

---

## 五、总结

### 核心要点

1. **原生 2D**：像素坐标，CanvasItem
2. **2D 合批**：自动合并相同纹理
3. **2D 光照**：PointLight2D、LightOccluder2D
4. **优化**：纹理图集、TileMap

### 下一篇

**下一篇**: 后处理效果

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #17 | GDShader 语言](#)  
**下一篇**: [深入理解 Godot 引擎 #19 | 后处理效果](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
