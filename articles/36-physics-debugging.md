# 第 36 篇：物理调试与问题排查

> **本章导读**：物理问题的典型特征是「看得见却查不出」：穿模、抖动、卡边、不触发。
> 本章先给工具总览（碰撞形状可视化、性能监视器、远程场景树、物理插值），再给六类高频问题的排查表，最后讲清**物理帧率与子步**这两个底层参数如何决定上面每一类问题的表现——多数「玄学 bug」的根因都在这两个数上。
> **前置知识**：第 23 篇《Godot 物理架构概述》、第 32 篇《物理性能优化》
> **难度**：进阶。

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

### 1.1 场景树的可视化开关（**是属性，不是方法**）

Godot 4.x 把调试可视化统一放在 `SceneTree` 上，并且**全部是属性**（不是 `set_xxx()` 方法——虽然 C++ 侧确实有 setter，但脚本里写属性更清晰）：

| 属性 | 类型 | 4.3 默认 | 作用 |
|---|---|---|---|
| `debug_collisions_hint` | `bool` | `false` | 显示所有碰撞形状 |
| `debug_navigation_hint` | `bool` | `false` | 显示导航网格与导航代理 |
| `debug_paths_hint` | `bool` | `false` | 显示 2D 导航路径 |
| `debug_collisions_color` | `Color` | — | 碰撞形状的线框颜色 |
| `debug_collision_contact_color` | `Color` | — | 接触点的颜色 |
| `debug_paths_color` | `Color` | — | 路径线的颜色 |
| `debug_paths_width` | `float` | `1.0` | 路径线宽 |

> ⚠️ 这三个 `debug_*_hint` **只在带 `DEBUG_ENABLED` 的构建里生效**（编辑器与 debug 导出模板有，release 导出模板没有）。4.3 的 `scene/main/scene_tree.h` 里，非 debug 构建下 setter 是空实现、getter 恒返回 `false`。
>
> ⚠️ 另一个 4.x 的变化：这三个开关**从 4.3 起已不再受"调试 > 可视化碰撞形状"菜单项之外的额外开关控制**，直接设属性即可。3.x 教程里 `Viewport.debug_draw` 之类的写法在 4.x 已不存在。

### 1.2 命令行开关

Godot 4.3 的 `main/main.cpp` 里注册了这些调试用命令行开关（可以直接用在导出后的可执行文件上）：

| 开关 | 等价于 |
|---|---|
| `--debug-collisions` | `set_debug_collisions_hint(true)` |
| `--debug-navigation` | `set_debug_navigation_hint(true)` + 打开 `NavigationServer3D` 的调试绘制 |
| `--debug-paths` | `set_debug_paths_hint(true)` |
| `--debug-avoidance` | 打开导航避障的调试绘制 |
| `--debug-canvas-item-redraw` | 强制重绘 CanvasItem（排查 2D 渲染缓存问题） |
| `--debug-server` | 启用调试服务器（远程调试） |
| `--debug-stringnames` | 把 `StringName` 显示为字符串（排查性能热点） |

```bash
# 例：在 CI 或 QA 机器上跑一遍带碰撞显示的构建
my_game.exe --debug-collisions --debug-navigation
```

这比在运行时改属性更适合"给不熟悉项目的测试同事一份能立刻看到碰撞的包"。

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

### 2.1 只看某一个对象的碰撞形状

全局开关会画出**所有**碰撞形状，场景复杂时反而看不清目标。Godot 4.x 提供了一个更精确的办法：给 `CollisionShape2D` / `CollisionShape3D` 设置 `debug_color`，或者干脆用 `ShapeCast` / `PhysicsDirectSpaceState` 在代码里做一次"我到底撞到了什么"的查询：

```gdscript
# 精确查询：这个角色脚下的地板到底是什么
func _physics_process(_delta: float) -> void:
    move_and_slide()
    var collision := get_last_slide_collision()
    if collision == null:
        return
    var collider := collision.get_collider()       # 节点（可能是 TileMap）
    var shape_idx := collision.get_collider_shape_index()
    print("踩到：", collider, " 的形状 #", shape_idx,
          " 法线：", collision.get_normal(),
          " 位置：", collision.get_position())
```

`KinematicCollision2D` 提供 `get_collider()`、`get_collider_rid()`、`get_collider_shape_index()`、`get_normal()`、`get_position()`、`get_travel()`、`get_remainder()`——**排查"撞到了什么"时优先用它们，而不是开全局可视化**。

### 2.2 第三方与扩展工具

| 工具 | 用途 |
|---|---|
| Godot 内置调试器 → 监视器面板 | 逐帧查看物理计数与耗时（本篇第四节） |
| Godot 内置调试器 → 远程场景树 | 运行时查看/修改节点属性（改一下碰撞层试试） |
| 编辑器"调试 → 显示碰撞形状" | 运行时全局可视化 |
| 第三方物理调试器（如各类 3D 物理可视化中间件） | 面向自研物理后端（见第 34 篇 `PhysicsServer3DExtension`） |
| 自绘 `_draw()` 调试层 | 画射线、形状查询结果、AI 路径——项目自己最常用的手段 |

> 建议在项目里内置一个"调试层"节点：用 `get_tree().debug_collisions_hint` 或自绘开关，并且**在 release 构建里默认关闭**。

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

### 3.1 八条常见错法逐条拆解

下面八条是 2D/3D 项目里出现频率最高的"代码没错但行为不对"，每条都给出**真实原因**与**验证方法**。

**① `CollisionShape2D.disabled` 忘了开回来**

`CollisionShape2D.disabled`（4.3，默认 `false`）会让该形状**完全不参与世界**。常见场景：调试时临时禁用了形状，改了别的参数忘了改回来。

```gdscript
# 验证：运行期直接读
print($Player/CollisionShape2D.disabled)   # true 就是它
```

> 类参考提醒：这个属性"should be changed with `Object.set_deferred`"——在物理回调里直接改它会报错，要用 `set_deferred("disabled", false)`。

**② `Area2D.monitoring` 与 `monitorable` 用反**

`monitoring` 管**输出**（我发信号），`monitorable` 管**输入**（我被信号）。想让"别人检测不到我"却去关 `monitoring`，结果自己的 `body_entered` 也不触发了。

```gdscript
# 验证：打印两个开关
print("monitoring=", monitoring, " monitorable=", monitorable)
```

**③ `TileMapLayer` 的碰撞层设错**

`TileMapLayer` 有自己的 `collision_enabled`（默认 `true`）与 `collision_visibility_mode`。整层关掉碰撞、或把层的 `collision_layer` 设成角色 `collision_mask` 没覆盖的值，都会导致"角色从地图上掉下去"。

```gdscript
# 验证：TileMapLayer 的瓦片碰撞用的是 TileSet 里定义的形状，
#       层号则来自节点的 collision_layer（CollisionObject2D 通用属性）
print($TileMapLayer.collision_enabled, " layer=", $TileMapLayer.collision_layer)
```

**④ 碰撞层 / 掩码的位运算写错**

最常见的两个错：

- **层号从 1 开始，位序号从 0 开始**：第 3 层是 `1 << 2`，不是 `1 << 3`；
- **只检查了单向**：A 能与 B 碰撞的充分必要条件是 `A.collision_mask & B.collision_layer != 0`。只查一个方向是"明明设了层却不碰"的根因。

```gdscript
# 验证：直接算一次
print((a.collision_mask & b.collision_layer) != 0)
```

**⑤ 形状与节点的父子关系错位**

`CollisionShape2D` / `CollisionShape3D` 必须挂在 `CollisionObject2D` / `CollisionObject3D` 下面。挂在普通 `Node2D` 下、或挂在**别的**物理体下面，形状就会作用在错误的物体上（或完全不生效）。

```gdscript
# 验证：沿父链找最近的 CollisionObject
var n := $Player/CollisionShape2D as Node
while n and not (n is CollisionObject2D):
    n = n.get_parent()
print("最近的物理体：", n)
```

**⑥ `CharacterBody2D` 的 `floor_snap_length` 与 `up_direction` 配错**

- `up_direction`（4.3 默认 `(0, -1)`）决定"哪边是上"。做重力翻转关卡时忘了改，`is_on_floor()` 永远为假；
- `floor_snap_length`（4.3 默认 `1.0` 像素）太小，下坡时角色会"跳起来"。

```gdscript
# 验证
print("up=", up_direction, " snap=", floor_snap_length)
print("on_floor=", is_on_floor(), " floor_normal=", get_floor_normal())
```

**⑦ `move_and_slide()` 之后忘记读 `get_last_slide_collision()`**

`move_and_slide()` 只写状态，**不返回碰撞详情**（它返回 `bool` 表示"是否发生了碰撞"）。要看撞到了谁、撞在哪，必须另外调 `get_last_slide_collision()` 或 `get_slide_collision(i)`。

```gdscript
move_and_slide()
if is_on_wall():
    var c := get_last_slide_collision()     # ← 必须另外取
    if c:
        print("撞到：", c.get_collider())
```

**⑧ 用 `Area2D` 当碰撞体**

`Area2D` **只检测、不产生物理响应**。想让角色被墙挡住，就必须用 `StaticBody2D` / `CharacterBody2D`；`Area2D` 只适合做"进入某区域"的触发器。

```gdscript
# 验证：看节点类型
print($Wall is CollisionObject2D, " ", $Wall is Area2D)
```

### 3.2 Jolt 与 Godot Physics 行为不同时的定位路径

同一场景在两个后端下表现不同，**不要靠猜**，按下面的顺序定位：

```
1. 确认到底用了哪个后端
   print(ProjectSettings.get_setting("physics/3d/physics_engine", "DEFAULT"))

2. 查 3.1 表（见第 34 篇 3.1 节）中与该现象对应的行
   —— 18 行里最常命中的是：
      第 3 行  休眠阈值不同      → "以前睡的现在不睡"
      第 7 行  关节软限位不支持   → 关节报警告、限位行为不同
      第 8 行  运动学体不报接触   → 接触事件不触发
      第 9 行  Area3D 与静态体   → 触发区不触发
      第 12 行 射线 face_index   → 命中判定取不到面
      第 13 行 SoftBody3D×Area3D → 软体不受风

3. 打开 Jolt 专属的开关复测
   physics/jolt_physics_3d/simulation/generate_all_kinematic_contacts = true
   physics/jolt_physics_3d/simulation/areas_detect_static_bodies = true   （4.4/4.5）
   physics/jolt_physics_3d/joints/world_node = 1                          （兼容旧行为）

4. 两个后端各跑一遍基线，用同一组固定输入对比输出
   （这一步与第 32 篇的基准测试流程是同一件事）
```

第 3 步很关键：**很多"行为不同"其实只是 Jolt 的一个默认优化**，打开对应开关就一致了——`generate_all_kinematic_contacts` 与 `areas_detect_static_bodies` 就是最典型的两个。

### 3.3 软体专项排查

软体的失败模式比刚体多，按现象分：

| 现象 | 可能原因 | 验证方法 |
|---|---|---|
| 软体整块飞走 / 炸开 | 顶点数太少导致约束退化；或网格有重复/退化顶点 | 检查网格三角面是否有效；提高 `simulation_precision` 看是否好转 |
| 软体穿模 | `linear_stiffness` 太高（太硬）而精度不够 | 降 `linear_stiffness`、升 `simulation_precision` |
| 软体抖动不止 | `damping_coefficient` 太低 | 从 `0.01` 起步逐步加 |
| 布料像纸板 | `linear_stiffness` 太高 或 `damping_coefficient` 太高 | 降 `linear_stiffness`，别升阻尼 |
| 内压没效果 | 网格**不封闭**，没有体积可作用 | 确认是封闭网格；`pressure_coefficient` 只对封闭网格有意义 |
| 布料穿过自己 | 4.x 无自碰撞 | 无解，只能走自研 PBD（第 30 篇） |
| 软体不受风 | Jolt 4.4–4.6 不支持软体与 `Area3D` 交互 | 检查引擎版本与后端（第 35 篇 2.5 节） |
| 软体不跟着锚点动 | `attachment_path` 指向的节点不在树里 / 不是 `Node3D` | 打印 `has_node(path)`；锚点要在场景树内 |
| 节点变换被无视 | 运行时 `SoftBody3D` 强制 `as_top_level` + 单位变换 | 改父节点位置，不要动软体节点自身（第 35 篇 2.4 节） |
| 软体看不见但仍在算 | `process_mode` 未禁用，`disable_mode` 不生效 | 打印 `process_mode` 与 `disable_mode` |

### 3.4 现象 → 可能原因 → 验证方法 速查表

这是本篇最实用的一张表。**从左往右查**，每一行都给出可立即执行的验证动作。

| 现象 | 可能原因 | 验证方法 |
|---|---|---|
| 完全不碰撞 | 层/掩码位运算错 | `print((a.collision_mask & b.collision_layer) != 0)` |
| 完全不碰撞 | 形状被 `disabled` | `print(shape.disabled)` |
| 完全不碰撞 | 形状挂在错误的父节点下 | 沿父链找最近的 `CollisionObject2D` |
| 完全不碰撞 | 用了 `Area2D` 当碰撞体 | `print(node is Area2D)` |
| 信号不触发 | `monitoring` 关了 | `print(monitoring)` |
| 信号不触发 | `contact_monitor` 没开（刚体） | `print(contact_monitor, " ", max_contacts_reported)` |
| 信号不触发 | `max_contacts_reported` 为 0 | 同上 |
| 信号不触发 | 对方是静态体而 Jolt 默认不检测 | 开 `generate_all_kinematic_contacts` / `areas_detect_static_bodies` |
| 高速穿透 | 单帧位移大于厚度且无 CCD | 开 `continuous_cd`；提高 `physics_ticks_per_second` |
| 高速穿透 | 物体初始位置已在墙内 | 打印初始 `global_position` |
| 抖动 | 渲染帧率 ≠ 物理帧率且未开插值 | 开 `physics/common/physics_interpolation` |
| 抖动 | 每帧施加了微小力/速度 | 在 `_physics_process` 里加日志 |
| 抖动 | 物理步被"补跑"（`max_physics_steps_per_frame`） | 打印 `Engine.max_physics_steps_per_frame` 与物理帧耗时 |
| 角色下坡"跳起来" | `floor_snap_length` 太小 | 调到 4–12 像素后对比 |
| 角色 `is_on_floor()` 恒假 | `up_direction` 配错 | `print(up_direction)` |
| 角色贴墙被拖走 | `platform_wall_layers` 误开 | `print(platform_wall_layers)` |
| 角色跳不起来 | 站在移动平台上被平台速度抵消 | 打印 `get_platform_velocity()` 与 `platform_on_leave` |
| 刚体不睡 | 每帧有微小扰动 | 打印 `sleeping` 与速度 |
| 刚体睡太早 | Jolt 与 Godot Physics 的休眠阈值口径不同 | 对照第 34 篇 3.1 节第 3 行 |
| 关节限位异常 | Jolt 不支持部分关节软限位属性 | 对照第 34 篇 3.1 节第 7 行 |
| 射线取不到面 | Jolt 下 `face_index` 恒为 `-1` | 开 `queries/enable_ray_cast_face_index` |
| 物理耗时高 | 碰撞对过多（掩码过宽） | 看 `PHYSICS_*_COLLISION_PAIRS` |
| 物理耗时高 | 求解器压力（关节链过长 / 迭代次数高） | 看 `velocity_steps` / `position_steps` |
| 物理耗时高 | 软体渲染写回 | 降顶点数；降 `simulation_precision` |
| 物理耗时高 | `_integrate_forces` 里做了重活 | 在回调里加计时 |
| 2D 掉帧但 3D 正常 | 2D 物理对数量异常 | 看 `PHYSICS_2D_COLLISION_PAIRS` 与 `PHYSICS_2D_ISLAND_COUNT` |
| 角色卡在斜坡边缘 | 用了矩形碰撞形状 | 换 `CapsuleShape2D` |
| 角色卡在斜坡边缘 | `floor_max_angle` 太小 | 调 `floor_max_angle`（默认 45°） |
| 软体炸开 | 网格退化 / 顶点数不足 / 精度不够 | 提高 `simulation_precision`；检查网格 |
| 软体不受风 | Jolt 4.4–4.6 不支持 | 查版本与后端 |
| 一切"改了没反应" | 改的是被 `set_deferred` 保护的属性 | 用 `set_deferred()` 改 `disabled` 等 |

---

## 四、性能诊断

### 4.1 2D / 3D 性能监视器对照

`Performance` 类里与物理相关的监视器共 6 个，2D 与 3D 各三个（4.3 `Performance.xml` 逐项核实）：

| 监视器常量 | 4.3 值 | 含义 | 2D 对应 | 3D 对应 |
|---|---|---|---|---|
| `PHYSICS_2D_ACTIVE_OBJECTS` | 17 | 2D 中**未休眠**的 `RigidBody2D` 数量 | ✅ | — |
| `PHYSICS_2D_COLLISION_PAIRS` | 18 | 2D 物理引擎当前的碰撞对数量 | ✅ | — |
| `PHYSICS_2D_ISLAND_COUNT` | 19 | 2D 物理引擎的"岛"数量（互相连通、可独立求解的碰撞簇） | ✅ | — |
| `PHYSICS_3D_ACTIVE_OBJECTS` | 20 | 3D 中未休眠的 `RigidBody3D` 与 `VehicleBody3D` 数量 | — | ✅ |
| `PHYSICS_3D_COLLISION_PAIRS` | 21 | 3D 物理引擎当前的碰撞对数量 | — | ✅ |
| `PHYSICS_3D_ISLAND_COUNT` | 22 | 3D 物理引擎的"岛"数量 | — | ✅ |

配套的通用监视器：`TIME_PHYSICS_PROCESS`（物理帧耗时，秒）、`TIME_PROCESS`（整帧耗时，秒）、`TIME_FPS`。

```gdscript
func _physics_debug_report() -> void:
    print("活跃刚体(3D)：", int(Performance.get_monitor(Performance.PHYSICS_3D_ACTIVE_OBJECTS)))
    print("碰撞对：", int(Performance.get_monitor(Performance.PHYSICS_3D_COLLISION_PAIRS)))
    print("岛数量：", int(Performance.get_monitor(Performance.PHYSICS_3D_ISLAND_COUNT)))
    print("物理帧耗时：", Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0, " ms")
```

2D 的等价写法（**很多项目只写了 3D，漏了 2D**）：

```gdscript
func _physics_debug_report_2d() -> void:
    print("活跃刚体(2D)：", int(Performance.get_monitor(Performance.PHYSICS_2D_ACTIVE_OBJECTS)))
    print("碰撞对(2D)：", int(Performance.get_monitor(Performance.PHYSICS_2D_COLLISION_PAIRS)))
    print("岛数量(2D)：", int(Performance.get_monitor(Performance.PHYSICS_2D_ISLAND_COUNT)))
```

> "岛"（island）是求解器的并行单元：**互不相连的一簇碰撞体**。岛数量爆炸 = 碰撞图碎成了很多小块 = 求解器并行度上不去、缓存局部性差。这是"碰撞对数量看起来不多但物理却很慢"的典型原因。

除了 `Performance`，还有一条更底层的通道：`PhysicsServer2D.get_process_info()` / `PhysicsServer3D.get_process_info()`，取值为 `INFO_ACTIVE_OBJECTS` / `INFO_COLLISION_PAIRS` / `INFO_ISLAND_COUNT`（4.3 类参考核实）。它读的是服务器内部的同一组计数器，适合写进自定义监视器：

```gdscript
# 把自定义监视器挂到编辑器的"监视器"面板
func _ready() -> void:
    Performance.add_custom_monitor("Physics/2D_Pairs",
        func() -> int:
            return PhysicsServer2D.get_process_info(PhysicsServer2D.INFO_COLLISION_PAIRS))
```

> ⚠️ `Performance` 类参考有两点提醒：① 某些内置监视器**只在 debug 构建里可用**，release 导出后恒为 `0`；② 部分监视器**不是实时更新**的，最多有 1 秒延迟。

### 4.2 诊断顺序

诊断顺序（与第 32 篇一致）：

1. **碰撞对数量异常大** → 掩码过宽、碎形状过多 → 收窄 `collision_mask`、合并形状；
2. **活跃刚体多** → 该睡的没睡 → 检查是否有代码每帧施加微小力/速度；
3. **岛数量异常多而碰撞对正常** → 碰撞图碎裂 → 检查是否有大量互不相干的静态体、是否有"岛被切断"的碰撞例外；
4. **物理帧耗时高但碰撞对正常** → 求解器压力（关节链过长、迭代次数高）或 `_integrate_forces` 里的重逻辑；
5. **物理帧耗时高但监视器都正常** → 看软体渲染写回、或物理线程被抢占（`physics/3d/run_on_separate_thread`）。

> ⚠️ 上面第 3、4、5 条是**排查方向**，不是阈值。任何"碰撞对超过 N 就该优化"的说法都必须绑定具体场景与硬件才有意义。

---

## 五、物理帧率与子步

```gdscript
# 两个底层参数（均可用代码调整）
Engine.physics_ticks_per_second = 60        # 物理 Hz（默认 60）
Engine.max_physics_steps_per_frame = 8      # 单帧最多补跑的物理步数（防"死亡螺旋"）
```

对应的项目设置键（4.4 `ProjectSettings.xml` 逐项核实）：

| 设置键 | 默认 | 等价的 `Engine` 属性 |
|---|---|---|
| `physics/common/physics_ticks_per_second` | `60` | `Engine.physics_ticks_per_second` |
| `physics/common/max_physics_steps_per_frame` | `8` | `Engine.max_physics_steps_per_frame` |
| `physics/common/physics_interpolation` | `false` | —（项目级开关，节点级用 `physics_interpolation_mode`） |
| `physics/common/physics_jitter_fix` | `0.5` | —（插值时向上一物理位置偏移的比例） |

- **提高物理频率**：降低穿透概率、提高接触稳定，但 CPU 按比例增加；
- **`max_physics_steps_per_frame`**：渲染帧过慢时最多补跑多少个物理步；超过就"慢动作"而不是死循环——调大它只会让卡顿时更卡；
- **子步**：引擎内部对快体做子步细分（配合 CCD），脚本层无需干预。

排查口诀：**先看监视器数值，再改参数；每改一项，回到同一测试场景对比**。

### 5.1 物理插值相关的抖动排查

| 现象 | 可能原因 | 验证方法 |
|---|---|---|
| 物体在屏幕上"抽帧" | 物理帧率低于渲染帧率，未开插值 | 开 `physics/common/physics_interpolation` |
| 插值后有"残影" | `physics_jitter_fix` 太小 | 从 `0.5` 往上调 |
| 某个节点抖动但别的正常 | 该节点 `physics_interpolation_mode` 被单独关掉 | 打印 `physics_interpolation_mode` |
| 开了插值但仍然抖 | 物理步本身不稳定（求解器在抖） | 看 `PHYSICS_*_ISLAND_COUNT` 与碰撞对数量 |

> 2D 物理插值是 **4.3** 引入的，3D 是 **4.4**（依据 Godot 4.4 官方发布页："With Godot 4.3, we introduced physics interpolation for your 2D projects. In this release, the long-awaited 3D counterpart has been merged as well!"）。

---

## 六、总结

- 可视化先行：`debug_collisions_hint` + 监视器的**六个**物理计数（2D 三个、3D 三个）；
- `debug_collisions_hint` / `debug_navigation_hint` / `debug_paths_hint` 是 **`SceneTree` 的属性**，且只在 debug 构建里生效；命令行等价物是 `--debug-collisions` / `--debug-navigation` / `--debug-paths`；
- 高频问题各有明确的源码级原因：八条常见错法见 3.1 节，速查表见 3.4 节；
- Jolt 与 Godot Physics 的行为差异要**按表逐项对照**，而不是靠猜（第 34 篇 3.1 节）；多数"差异"其实是 Jolt 的一个默认优化，打开对应开关即一致；
- 软体有独立的失败模式（穿插、抖动、穿模），排查表见 3.3 节；
- 物理帧率与插值是"抖动/穿透"的两个总开关；
- 任何调参都要在同一测试场景下做前后对比——这既是第 32 篇的方法，也是本篇的收尾。

---

## 🔗 延伸阅读

- **Performance**: <https://docs.godotengine.org/en/stable/classes/class_performance.html>
- **SceneTree**: <https://docs.godotengine.org/en/stable/classes/class_scenetree.html>
- **PhysicsServer2D / PhysicsServer3D**: <https://docs.godotengine.org/en/stable/classes/class_physicsserver2d.html>
- **物理教程总览**: <https://docs.godotengine.org/en/stable/tutorials/physics/index.html>
- **使用 Jolt Physics**: <https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html>
- **源码位置**: `servers/physics_2d/`、`servers/physics_3d/`、`scene/main/scene_tree.h`

---

## 📋 下一章预告

**第 37 篇：动画系统基础**

- `AnimationPlayer` 与 `AnimationMixer` 的关系
- `AnimationLibrary` 与动画资源
- 动画回调模式：`ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS` 与物理的配合
- 循环模式：`Animation.LOOP_NONE` / `LOOP_LINEAR` / `LOOP_PINGPONG`
- `AnimationTree` 的参数路径与条件

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 35 篇：软体与可变形体](/articles/35-soft-bodies.md)
**下一篇**: [第 37 篇：动画系统基础](/articles/37-animation-system-basics.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
