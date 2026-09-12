# 第 36 篇：物理调试与问题排查

> **摘要**：物理问题往往"看得见却查不出"：穿模、抖动、卡边、不触发。本文梳理 Godot 的调试设施（碰撞形状可视化、性能监视器）、给出六类高频问题的排查表，并讲清物理帧率与子步两个底层参数对上述问题的影响。

---

## 一、调试工具总览

| 工具 | 入口 | 用途 |
|------|------|------|
| 碰撞形状可视化 | 编辑器菜单 调试 → 显示碰撞形状；代码等价 `get_tree().debug_collisions_hint = true` | 让所有碰撞形状运行时可见 |
| 性能监视器 | 调试器底部 → 监视器 | 活跃刚体数、碰撞对数、岛数量、物理帧耗时 |
| 物理插值开关 | 项目设置 `physics/common/physics_interpolation`（4.3 起支持 2D） | 排查"渲染抖动但物理正常" |
| 远程场景树 | 调试器 → 远程 | 运行时检查节点碰撞层/掩码配置 |

**先开可视化，再谈优化**：绝大多数"为什么撞不上/为什么穿过去"问题，肉眼看一眼形状就能定位——形状太小、位置不对、层掩码没对上。

---

## 二、代码化可视化

```gdscript
# 等价于编辑器菜单勾选（仅运行项目时生效）
func _ready() -> void:
    get_tree().debug_collisions_hint = true
```

需要更精细的自绘时（例如画自定义检测区域），在 `_draw()` 中叠加：

```gdscript
func _draw() -> void:
    if Engine.is_editor_hint():
        return
    draw_circle(detect_origin, detect_radius, Color(1, 0.3, 0.3, 0.25))
```

---

## 三、高频问题排查表

| 现象 | 常见原因 | 对策 |
|------|----------|------|
| 高速物体穿墙 | 单帧位移大于碰撞体厚度；无 CCD | 开启 `continuous_cd`；提高 `Engine.physics_ticks_per_second`；或加厚静态体 |
| 渲染抖动但物理正常 | 物理帧率 ≠ 渲染帧率且未开插值 | 开启 `physics/common/physics_interpolation` |
| 卡在斜坡/台阶边缘 | 角色用矩形形状；`floor_snap_length` 过小 | 换 `CapsuleShape2D`；加大 snap；调 `floor_max_angle` |
| `body_entered` 不触发 | 刚体未开接触报告；层/掩码没对上；面积监测关了 | 2D：`contact_monitor` + `max_contacts_reported`；核对 `collision_layer`/`collision_mask` 与 `monitoring` |
| 刚体不动 | 已休眠；被冻结 | 检查 `sleeping`/`can_sleep`/`freeze`；确认未在每帧施加微小扰动 |
| 角色被旋转 | 用了 `RigidBody2D` 做角色 | 改 `CharacterBody2D`，或 `lock_rotation = true` + 角阻尼 |

---

## 四、性能诊断

```gdscript
func _physics_debug_report() -> void:
    print("活跃刚体(3D)：", int(Performance.get_monitor(Performance.PHYSICS_3D_ACTIVE_OBJECTS)))
    print("碰撞对：", int(Performance.get_monitor(Performance.PHYSICS_3D_COLLISION_PAIRS)))
    print("岛数量：", int(Performance.get_monitor(Performance.PHYSICS_3D_ISLAND_COUNT)))
    print("物理帧耗时：", Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0, " ms")
```

诊断顺序（与第 32 篇一致）：

1. **碰撞对数量异常大** → 掩码过宽、碎形状过多 → 收窄 `collision_mask`、合并形状；
2. **活跃刚体多** → 该睡的没睡 → 检查是否有代码每帧施加微小力/速度；
3. **物理帧耗时高但碰撞对正常** → 求解器压力（关节链过长）或 `_integrate_forces` 里的重逻辑。

---

## 五、物理帧率与子步

```gdscript
# 两个底层参数（均可用代码调整）
Engine.physics_ticks_per_second = 60        # 物理 Hz（默认 60）
Engine.max_physics_steps_per_frame = 8      # 单帧最多补跑的物理步数（防"死亡螺旋"）
```

- **提高物理频率**：降低穿透概率、提高接触稳定，但 CPU 按比例增加；
- **`max_physics_steps_per_frame`**：渲染帧过慢时最多补跑多少个物理步；超过就"慢动作"而不是死循环——调大它只会让卡顿时更卡；
- **子步**：引擎内部对快体做子步细分（配合 CCD），脚本层无需干预。

排查口诀：**先看监视器数值，再改参数；每改一项，回到同一测试场景对比**。

---

## 六、总结

- 可视化先行：`debug_collisions_hint` + 监视器的三个物理计数；
- 六类高频问题各有明确的源码级原因，排查表见第三节；
- 物理帧率与插值是"抖动/穿透"的两个总开关；
- 任何调参都要在同一测试场景下做前后对比——这既是第 32 篇的方法，也是本篇的收尾。

---

## 🔗 延伸阅读

- **Performance**: <https://docs.godotengine.org/en/stable/classes/class_performance.html>
- **物理教程总览**: <https://docs.godotengine.org/en/stable/tutorials/physics/index.html>
- **源码位置**: `servers/physics_2d/`, `servers/physics_3d/`

---

**Godot 版本**: 4.x（基线 4.3）

---

**上一篇**: [第 35 篇：软体与可变形体](/articles/35-soft-bodies.md)
**下一篇**: [第 37 篇：动画系统基础](/articles/37-animation-system-basics.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
