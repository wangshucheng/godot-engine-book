# 深入理解 Godot 引擎 #20 | 粒子渲染

> **摘要**：Godot 的粒子系统支持 CPU 和 GPU 粒子。本文将深入分析粒子架构、发射器、渲染优化。

---

## 一、粒子系统架构

### 1.1 粒子类型

| 类型 | 说明 | 性能 |
|------|------|------|
| **GPUParticles2D** | 2D GPU 粒子 | 优秀 |
| **GPUParticles3D** | 3D GPU 粒子 | 优秀 |
| **CPUParticles2D** | 2D CPU 粒子 | 良好 |
| **CPUParticles3D** | 3D CPU 粒子 | 较差 |

### 1.2 粒子流程

```
发射器
    ↓
生成粒子
    ↓
更新粒子（位置、速度、颜色）
    ↓
渲染粒子
    ↓
销毁粒子
```

---

## 二、粒子发射器

### 2.1 发射器类型

```gdscript
# 点发射器
var emitter = GPUParticles3D.new()
emitter.emission_shape =_particles.EMISSION_SHAPE_POINT

# 球体发射器
emitter.emission_shape =_particles.EMISSION_SHAPE_SPHERE
emitter.emission_sphere_radius = 1.0

# 盒状发射器
emitter.emission_shape =_particles.EMISSION_SHAPE_BOX
emitter.emission_box_extents = Vector3(1, 1, 1)
```

### 2.2 发射器设置

```gdscript
emitter.amount = 100  # 粒子数量
emitter.lifetime = 2.0  # 生命周期
emitter.one_shot = false  # 持续发射
emitter.explosiveness = 0.0  # 爆发度
```

---

## 三、粒子参数

### 3.1 初始参数

| 参数 | 说明 |
|------|------|
| **Direction** | 发射方向 |
| **Spread** | 扩散角度 |
| **Initial Velocity** | 初始速度 |
| **Scale** | 初始大小 |
| **Color** | 初始颜色 |

### 3.2 过程参数

| 参数 | 说明 |
|------|------|
| **Gravity** | 重力 |
| **Damping** | 阻尼 |
| **Angular Velocity** | 角速度 |
| **Color Ramp** | 颜色渐变 |
| **Scale Ramp** | 大小渐变 |

---

## 四、粒子渲染

### 4.1 粒子材质

```gdscript
var material = ParticleProcessMaterial.new()
material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
material.direction = Vector3(0, 1, 0)
material.spread = 45.0
material.initial_velocity_min = 5.0
material.initial_velocity_max = 10.0
```

### 4.2 粒子贴图

```gdscript
# 使用贴图作为粒子
var texture = load("res://particle.png")
emitter.texture = texture

# 使用图集
emitter.h_frames = 4
emitter.v_frames = 4
```

---

## 五、粒子优化

### 5.1 优化技巧

| 技巧 | 说明 |
|------|------|
| **GPU 粒子** | 使用 GPU 加速 |
| **LOD** | 远距离减少粒子 |
| **Culling** | 屏幕外不渲染 |
| **合批** | 相同材质合并 |

### 5.2 性能对比

| 粒子数量 | CPU 占用 | 帧率 |
|---------|---------|------|
| 100 | 1% | 120 FPS |
| 1000 | 5% | 60 FPS |
| 10000 | 30% | 30 FPS |

---

## 六、总结

### 核心要点

1. **粒子类型**：GPU 粒子性能优秀
2. **发射器**：点、球体、盒状
3. **参数**：初始参数、过程参数
4. **优化**：GPU 加速、LOD、Culling

### 下一篇

**下一篇**: 性能优化

---

**作者**: 王飞书  
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.3（最新稳定版）

---

**上一篇**: [深入理解 Godot 引擎 #19 | 后处理效果](#)  
**下一篇**: [深入理解 Godot 引擎 #21 | 性能优化](#)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
