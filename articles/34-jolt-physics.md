# 第 34 篇：Jolt Physics

> **摘要**：Jolt 是由 Jorrit Rouwe 开发、在《Horizon Forbidden West》中验证过的高性能物理引擎。Godot 4.4 起将其作为内置模块随引擎分发（4.1–4.3 通过 godot-jolt 扩展使用）。本文讲解启用方式、与 Godot Physics 的取舍、运行时探测与调优清单。

---

## 一、Jolt 是什么

| 事实 | 说明 |
|------|------|
| 来源 | Jorrit Rouwe 的开源 C++ 物理引擎，曾在《地平线：西之绝境》中承载全场景物理 |
| 4.1–4.3 | 以 GDExtension 形式提供（godot-jolt 项目），需手动安装 |
| 4.4 起 | 官方将其合并为**内置引擎模块**，随编辑器/导出模板分发 |
| 4.4 状态 | 官方文档标注为实验性：功能尚未与 Godot Physics 完全对齐 |
| 定位 | 3D 物理；**2D 物理不受影响**，仍由 Godot Physics 2D 驱动 |

> 版本提示：本书示例基线为 4.3，涉及 Jolt 的行为以 4.4+ 为准；4.1–4.3 需安装扩展。

---

## 二、启用与切换

### 2.1 项目设置（4.4+）

路径：**项目设置 → 物理 → 3D → 物理引擎（Physics Engine）→ Jolt Physics**。

对应的项目设置键为 `physics/3d/physics_engine`，可选值包括默认的 `GodotPhysics3D` 与 `Jolt Physics`：

```gdscript
# 用代码确认当前引擎（与第 23 篇 2.3 节一致）
func get_physics_engine_name() -> String:
    return str(ProjectSettings.get_setting("physics/3d/physics_engine", "DEFAULT"))
```

切换是**项目级**的：整个 3D 物理世界从启动起就运行在 Jolt 上，无需逐对象指定。

### 2.2 4.1–4.3 的安装

1. 从 Asset Library 或 godot-jolt 的 GitHub Release 获取与引擎版本匹配的扩展包；
2. 解压到 `res://addons/godot-jolt/`；
3. 启用扩展并重启编辑器，随后同样在项目设置中切换物理引擎。

### 2.3 代码无需改动

Jolt 是**即插即用（drop-in）替换**：`RigidBody3D`、`CharacterBody3D`、`Area3D`、`PhysicsDirectSpaceState3D` 等节点与查询 API 完全不变。第 23–33 篇的所有示例在两种引擎下语义一致——差异只在表现（稳定性、性能、边缘行为的细节）。

---

## 三、与 Godot Physics 的取舍

| 维度 | Godot Physics | Jolt Physics |
|------|---------------|--------------|
| 线程模型 | 单线程为主 | 多线程任务系统，大规模场景收益明显 |
| 稳定性 | 复杂堆叠场景易抖动 | 工业级求解器，堆叠与约束更稳 |
| 功能对齐 | 完整 | 4.4 时实验性，部分行为有差异 |
| 2D | 唯一实现 | 不涉及（2D 始终用 Godot Physics 2D） |
| 体积 | 内置 | 内置（4.4+），导出模板已包含 |

选型建议（与第 23 篇 9.3 节一致）：

- 小型/中型项目、2D 项目：默认 Godot Physics 足够；
- 大量刚体、复杂关节链、堆叠玩法：切换 Jolt 实测；
- **任何切换都必须在目标平台上重跑性能与行为测试**——两个引擎的接触表现、休眠阈值并不逐一等价。

---

## 四、运行时探测与容错

```gdscript
func is_jolt_active() -> bool:
    return str(ProjectSettings.get_setting("physics/3d/physics_engine", "DEFAULT")) == "Jolt Physics"
```

用途：

- 依赖 Jolt 专属调优时给出提示（例如堆叠玩法的关卡加载时打印引擎名，便于 QA 复现）；
- 工具插件在两种引擎下选择不同的诊断阈值。

注意：**物理 API 不做引擎分支**。凡是需要按引擎写不同代码的需求，先怀疑用法错误——两个引擎公开给脚本的接口是同一套。

---

## 五、调优清单

Jolt 的调优项集中在项目设置的 `Physics → Jolt Physics` 分节（4.4+ 内置模块），常用的三组：

| 分节 | 常用项 | 说明 |
|------|--------|------|
| Simulation | Worker Count | 物理工作线程数，通常设为物理核数 |
| Simulation | Use Enhanced Internal Edge Removal | 减少内部边缘"挂边"抖动 |
| Contacts | Max Contact Points | 单对碰撞体最多报告的接触点数 |

调优顺序建议：先保证帧内物理耗时（`Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)`）稳定，再逐项微调，每改一项都做前后对比——与第 32 篇的基准测试流程相同。

---

## 六、迁移检查清单

从 Godot Physics 迁移到 Jolt 时，逐项确认：

- [ ] **场景逐个过**：接触表现（弹跳、摩擦、堆叠高度）与之前是否一致；
- [ ] **约束关节**：马达速度、限制角度在两个引擎下的求解结果差异；
- [ ] **休眠行为**：阈值不同可能导致"以前睡的现在不睡"（或相反），观察 `sleeping` 状态；
- [ ] **CCD**：高速投射物两边的穿透表现差异；
- [ ] **`_integrate_forces`**：直接改写物理状态的代码（第 24/33 篇模式）要在 Jolt 下复测；
- [ ] **导出模板**：确认使用的导出模板包含 Jolt 模块（4.4+ 官方模板已包含）。

---

## 七、总结

- Jolt 是 4.4 起**内置**的 3D 物理替代实现，多线程、大规模场景更稳，4.4 时仍属实验性；
- 启用只需一个项目设置（`physics/3d/physics_engine`），节点与查询 API 完全不变；
- 2D 物理与 Jolt 无关；
- 迁移的核心工作是**行为复测**，不是代码改写。

---

## 🔗 延伸阅读

- **使用 Jolt Physics（官方文档）**: <https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html>
- **godot-jolt 项目**: <https://github.com/godot-jolt/godot-jolt>
- **Jolt 官方**: <https://github.com/jrouwe/JoltPhysics>
- **源码位置**: `modules/jolt_physics/`

---

**Godot 版本**: 4.x（基线 4.3，Jolt 内容以 4.4+ 为准）

---

**上一篇**: [第 33 篇：2D 物理系统](/articles/33-2d-physics.md)
**下一篇**: [第 35 篇：软体与可变形体](/articles/35-soft-bodies.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
