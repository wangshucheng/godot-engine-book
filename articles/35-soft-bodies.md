# 第 35 篇：软体与可变形体

> **摘要**：软体（Soft Body）与可变形体让物体"可以被压弯、被捏扁"。Godot 4 提供内置的 `SoftBody3D`（基于 MeshInstance3D 的布料/软布模拟）；本文分析其真实属性与固定点系统，给出旗帜、果冻方块的完整配置，并对比 `SoftBody3D`、自研 PBD（第 30 篇）与顶点着色器位移三条实现路线。

---

## 一、三条实现路线

| 路线 | 载体 | 适用 | 代价 |
|------|------|------|------|
| `SoftBody3D` | 内置节点 | 旗帜、披风、薄布料 | 每帧写回渲染网格，开销随顶点数增长 |
| 自研 PBD | 第 30 篇的质点弹簧系统 | 需要撕裂、自定义约束的布料 | CPU 密集，需自己做渲染同步 |
| 顶点着色器位移 | Shader | 纯视觉的"软"（草、果冻抖动） | 零物理，仅视觉 |

**先想清楚需求再选路线**：需要真实碰撞响应选前两者；只要视觉抖动，着色器最便宜。

---

## 二、SoftBody3D 详解

### 2.1 继承关系与数据流

```cpp
class SoftBody3D : public MeshInstance3D   // 4.3 源码，scene/3d/soft_body_3d.h
```

`SoftBody3D` **继承自 `MeshInstance3D`**：它本身就渲染一个网格，物理端模拟顶点位置，再通过渲染服务器把结果写回网格（内部辅助类 `SoftBodyRenderingServerHandler` 的 `set_vertex`/`set_normal`）。

### 2.2 真实属性清单（4.3）

| 属性 | 类型 | 作用 |
|------|------|------|
| `simulation_precision` | `int` | 模拟精度（子步/迭代数），越高越稳定越贵 |
| `total_mass` | `real_t` | 整个软体的总质量 |
| `linear_stiffness` | `real_t` | 线性刚度，越低越"软" |
| `pressure_coefficient` | `real_t` | 内压（封闭网格充气效果） |
| `damping_coefficient` | `real_t` | 阻尼，抑制持续晃动 |
| `drag_coefficient` | `real_t` | 空气阻力 |
| `parent_collision_ignore` | `NodePath` | 忽略的碰撞父节点（避免与宿主自撞） |
| `collision_layer` / `collision_mask` | `uint32_t` | 与其他物理体的层/掩码 |
| `disable_mode` | 枚举 | 隐藏时 `REMOVE`（停止模拟）或 `KEEP_ACTIVE` |

> ⚠️ **4.3 没有 `self_collision` 与 `collision_margin` 属性**——那是 Godot 3.x SoftBody 的属性，网上旧教程常照搬，在 4.x 会报"属性不存在"。软体自碰撞在 4.x 内置节点中不可用，需要自碰撞请走第 30 篇的自研 PBD。

### 2.3 隐藏时的行为

`disable_mode` 决定软体不可见时的处理：`DISABLE_MODE_REMOVE`（默认，从物理服务器移除模拟，省开销）或 `DISABLE_MODE_KEEP_ACTIVE`（保持模拟——适合"看不见但仍在飘动"的旗帜）。

---

## 三、固定点系统（pin）

布料要有"钉在杆上"的顶点。SoftBody3D 的固定点是**顶点索引级**的：

```gdscript
# 把顶点 0 钉在一个 Node3D 上（跟随该节点移动）
soft_body.pin_point(0, true, ^"Pole/Anchor")
print(soft_body.is_point_pinned(0))

# 取消固定
soft_body.pin_point_toggle(0)
```

| 方法 | 说明 |
|------|------|
| `pin_point(index, pin, attachment_path)` | 固定/解固定某个顶点 |
| `pin_point_toggle(index)` | 切换固定状态 |
| `is_point_pinned(index)` | 查询 |
| `get_point_transform(index)` | 取该模拟点的世界变换 |
| `set_pinned_points_indices()` | 批量设置 |

`spatial_attachment_path` 指向一个 `Node3D`：固定的顶点会跟随它移动——旗帜顶端随风摆动、两端钉死的窗帘，都用它实现。

---

## 四、实践

### 4.1 旗帜

```gdscript
# 旗帜：细长平面网格 + 顶边两个固定点 + 适度阻尼
func make_flag() -> SoftBody3D:
    var flag := SoftBody3D.new()
    flag.mesh = preload("res://flag_mesh.obj")   # 顶点数适中的平面网格
    flag.simulation_precision = 8                # 默认值偏低的场景可上调
    flag.total_mass = 0.5
    flag.linear_stiffness = 0.3                  # 布料要"软"
    flag.damping_coefficient = 0.05              # 太高会像纸板
    flag.drag_coefficient = 0.1                  # 空气阻力让摆动衰减
    flag.parent_collision_ignore = "../FlagPole" # 不与旗杆自撞
    add_child(flag)

    flag.pin_point(0, true, ^"FlagPole/Top")     # 顶边固定
    flag.pin_point(1, true, ^"FlagPole/Top")
    return flag
```

### 4.2 果冻方块（内压）

```gdscript
# 封闭网格 + 内压：压扁后回弹的"果冻"
func make_jelly() -> SoftBody3D:
    var jelly := SoftBody3D.new()
    jelly.mesh = preload("res://cube_mesh.obj")  # 封闭网格
    jelly.simulation_precision = 12
    jelly.total_mass = 2.0
    jelly.linear_stiffness = 0.7                 # 偏硬
    jelly.pressure_coefficient = 1.5             # 内压撑起体积
    jelly.damping_coefficient = 0.1
    add_child(jelly)
    return jelly
```

### 4.3 与角色交互

软体与 `RigidBody3D`/`CharacterBody3D` 的碰撞通过 `collision_layer`/`collision_mask` 正常工作；需要"踩上去"的布桥，把 `disable_mode` 设为 `KEEP_ACTIVE`，并确认角色的碰撞掩码覆盖软体的层。

---

## 五、性能与限制

- **顶点数是第一成本**：模拟开销与顶点数成正比，旗帜用几百顶点足够，不要拿高模直接软体化；
- **`simulation_precision` 是第二成本**：精度翻倍 ≈ 耗时翻倍，先调它再调网格；
- **渲染写回**：每帧把模拟位置写回网格（`set_vertex`/`set_normal`），顶点多时这是 CPU→GPU 的带宽瓶颈；
- **无自碰撞**：4.3 内置节点不支持（见 2.2），围巾自叠等需求用第 30 篇 PBD；
- **隐藏即省**：不可见的软体把 `disable_mode` 设为 `REMOVE`。

---

## 六、总结

- `SoftBody3D` 继承 `MeshInstance3D`，六个参数（precision/mass/stiffness/pressure/damping/drag）决定一切手感；
- **固定点系统**是布料玩法的核心：顶点索引级 pin + `Node3D` 锚点跟随；
- 4.3 的内置节点**没有** `self_collision`/`collision_margin`（旧教程照搬会报错），自碰撞需求走第 30 篇 PBD；
- 隐藏时用 `disable_mode` 控制是否继续模拟，是最容易拿到的性能节省。

---

## 🔗 延伸阅读

- **SoftBody3D**: <https://docs.godotengine.org/en/stable/classes/class_softbody3d.html>
- **源码位置**: `scene/3d/soft_body_3d.cpp`（模拟与渲染写回）
- **自研布料路线**: 见第 30 篇（质点弹簧与 PBD）

---

**Godot 版本**: 4.x（基线 4.3）

---

**上一篇**: [第 34 篇：Jolt Physics](/articles/34-jolt-physics.md)
**下一篇**: [第 36 篇：物理调试与问题排查](/articles/36-physics-debugging.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
