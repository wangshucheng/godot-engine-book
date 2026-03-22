# 深入理解 Godot 引擎 #16 | 材质系统

> **摘要**：Godot 的材质系统基于 StandardMaterial3D 和 ShaderMaterial。本文将深入分析材质类型、PBR 流程、材质实例化。

---

## 一、材质类型

### 1.1 StandardMaterial3D

StandardMaterial3D 是 Godot 的标准材质：

| 属性 | 说明 |
|------|------|
| **Albedo** | 基础颜色/纹理 |
| **Metallic** | 金属度 |
| **Roughness** | 粗糙度 |
| **Normal** | 法线贴图 |
| **Emission** | 自发光 |
| **AO** | 环境光遮蔽 |

### 1.2 ShaderMaterial

ShaderMaterial 允许自定义 Shader：

```gdscript
var material = ShaderMaterial.new()
material.shader = load("res://shaders/custom.gdshader")
material.set_shader_parameter("albedo", Color.RED)
material.set_shader_parameter("roughness", 0.5)
```

---

## 二、PBR 流程

### 2.1 PBR 原理

PBR（基于物理的渲染）模拟真实材质：

```
光线 → 表面
    ↓
反射（镜面）
    ↓
折射（漫反射）
    ↓
吸收/散射
```

### 2.2 PBR 参数

| 参数 | 范围 | 说明 |
|------|------|------|
| **Albedo** | 0-1 | 基础颜色 |
| **Metallic** | 0-1 | 0=非金属，1=金属 |
| **Roughness** | 0-1 | 0=光滑，1=粗糙 |
| **Normal** | - | 法线方向 |

---

## 三、材质实例化

### 3.1 实例化优势

| 优势 | 说明 |
|------|------|
| **性能** | 共享底层数据 |
| **内存** | 减少内存占用 |
| **灵活性** | 独立修改参数 |

### 3.2 实例化示例

```gdscript
# 创建基础材质
var base_material = StandardMaterial3D.new()
base_material.albedo_color = Color.RED

# 创建实例
var instance1 = base_material.duplicate()
var instance2 = base_material.duplicate()

# 独立修改
instance1.albedo_color = Color.BLUE
instance2.roughness = 0.8
```

---

## 四、材质优化

### 4.1 优化技巧

| 技巧 | 说明 |
|------|------|
| **共享材质** | 减少材质数量 |
| **材质 LOD** | 远距离简化材质 |
| **纹理压缩** | 减少显存占用 |
| **合批** | 相同材质合并 |

### 4.2 性能对比

| 材质数量 | DrawCall | 帧率 |
|---------|---------|------|
| 100 | 100 | 60 FPS |
| 50 | 50 | 90 FPS |
| 10 | 10 | 120 FPS |

---

## 五、总结

### 核心要点

1. **材质类型**：StandardMaterial3D、ShaderMaterial
2. **PBR 流程**：Albedo、Metallic、Roughness
3. **实例化**：共享数据，独立参数
4. **优化**：共享材质、纹理压缩

### 下一篇

**下一篇**: GDShader 语言

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #15 | 光照系统](#)  
**下一篇**: [深入理解 Godot 引擎 #17 | GDShader 语言](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
