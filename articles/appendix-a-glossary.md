# 附录 A：术语表

## 📖 使用说明

本表汇总全书使用的关键术语，按领域分组。**翻译约定**：概念性术语以中文为主、首次出现标注英文；API 名、类名与代码标识符保持英文原文。各篇正文与代码示例中的术语以本表为准。

---

## 一、引擎与架构

| 术语 | 解释 |
|------|------|
| Object | 对象，Godot 所有类型的根类，非 GC、需手动释放 |
| RefCounted | 引用计数对象，最后一个引用消失时自动释放 |
| Node | 节点，场景树的组成单元 |
| SceneTree | 场景树，管理节点树与主循环的对象 |
| Resource | 资源，可序列化、可共享的数据容器 |
| ClassDB | 类注册数据库，记录全部内置类与脚本类的属性/方法/信号 |
| ObjectID | 实例 ID，64 位整数，跨帧安全引用对象的方式 |
| Variant | 变体类型，可承载任意 Godot 类型的动态容器 |
| Callable | 可调用对象，方法引用与参数绑定的载体 |
| Signal | 信号，观察者模式实现（见第 6 篇） |
| Notification | 通知，`_notification()` 收到的引擎事件 |
| Autoload | 自动加载单例，全局可访问的常驻节点 |
| GDExtension | 原生扩展机制（C/C++ 等，4.x 取代 GDNative） |
| ObjectDB | 对象数据库，登记所有存活对象及其 ID |

---

## 二、渲染系统

| 术语 | 解释 |
|------|------|
| RenderingServer | 渲染服务器，全部渲染指令的低层出口 |
| Forward+ | 前向+ 渲染器（集群光照，桌面默认） |
| Mobile / Compatibility | 移动渲染器与兼容（Web/GLES3）渲染器 |
| PBR | 基于物理的渲染（Base/Metallic/Roughness 工作流） |
| SDFGI | 有符号距离场全局光照，实时 GI 方案 |
| VoxelGI | 体素化实时全局光照 |
| LightmapGI | 光照贴图烘焙全局光照 |
| Draw Call | 绘制调用，CPU 向 GPU 提交的一次绘制指令 |
| 宽相位 / 窄相位 | 物理两阶段筛选，见物理分组 |
| MSAA | 多重采样抗锯齿 |
| FXAA / SMAA / TAA | 屏幕空间与时间抗锯齿（`screen_space_aa`/`use_taa`） |
| SSAO | 屏幕空间环境光遮蔽 |
| SSIL | 屏幕空间间接光照 |
| SSR | 屏幕空间反射（Environment 属性为 `ssr_enabled`） |
| LOD | 细节层次，按距离切换模型精度（`visibility_range_*`） |
| 烘焙（Baking） | 离线预计算（光照贴图、遮挡网格） |
| Import | 导入，源资产到引擎资源的转换（`.import` 元数据） |

---

## 三、物理系统

| 术语 | 解释 |
|------|------|
| PhysicsServer2D/3D | 物理服务器，低层物理接口（全局单例） |
| RigidBody | 刚体，受力/冲量驱动的动态体 |
| CharacterBody | 角色体，`move_and_slide()` 驱动的运动学体 |
| AnimatableBody | 可动画体，由动画/代码驱动并推动其他物体 |
| StaticBody | 静态体，永不移动的碰撞体 |
| Area | 区域，只检测不产生物理响应 |
| CollisionShape | 碰撞形状节点，承载具体形状资源 |
| 宽相位（Broadphase） | 粗筛选阶段（AABB），决定哪些碰撞对需要精算 |
| 窄相位（Narrowphase） | 精确检测阶段（GJK/SAT/EPA） |
| GJK | Gilbert–Johnson–Keerthi，凸体距离/穿透算法 |
| SAT | 分离轴定理，凸体碰撞检测 |
| EPA | 扩展多面体算法，求穿透深度与接触点 |
| 求解器（Solver） | 约束求解阶段，分配冲量消解接触 |
| 休眠（Sleeping） | 刚体停止模拟，`sleeping` 属性控制 |
| 冻结（Freeze） | 刚体冻结，`freeze` + `freeze_mode` 取代 3.x 的 `mode` |
| CCD | 连续碰撞检测，防止高速穿透 |
| Jolt Physics | 第三方物理引擎，4.4 起作为内置模块随引擎分发 |
| PBD | 位置动力学，布料/软体的稳定模拟方法 |
| OccluderInstance3D | 遮挡体实例，遮挡剔除的载体 |

---

## 四、动画系统

| 术语 | 解释 |
|------|------|
| AnimationPlayer | 动画播放器，直接播放 Animation 资源 |
| AnimationTree | 动画树，挂载 AnimationNode 图的混合容器 |
| AnimationNodeStateMachine | 动画状态机节点 |
| AnimationNodeStateMachinePlayback | 状态机运行时控制器（`travel()`/`get_current_node()`） |
| AnimationNodeBlendSpace1D/2D | 1D/2D 混合空间，按参数插值 |
| AnimationNodeBlendTree | 混合树，把节点串成有向图 |
| 根运动（Root Motion） | 用动画驱动位移而非代码位移 |
| 骨骼（Bone） | Skeleton3D 中以索引访问的骨骼数据（无节点对象） |
| IK | 反向运动学（LookAt/SkeletonIK3D 等） |
| 重定向（Retargeting） | 把动画映射到另一骨架 |
| 变形目标 | Blend Shape / Morph Target，网格顶点插值 |
| 动画遮罩 | 控制混合作用到的骨骼子集 |

---

## 五、音频系统

| 术语 | 解释 |
|------|------|
| AudioStreamPlayer | 音频播放器（2D/3D 为对应子类） |
| AudioBus | 音频总线，`AudioServer` 的混音通道 |
| DSP | 数字信号处理，AudioEffect 系列效果器 |
| HRTF | 头部相关传输函数，3D 空间音频定位 |
| 多普勒（Doppler） | 相对运动导致的音调偏移 |

---

## 六、网络系统

| 术语 | 解释 |
|------|------|
| MultiplayerPeer | 多人对等连接基类（ENet/WebSocket/WebRTC 实现） |
| RPC | 远程过程调用，`@rpc` 注解声明 |
| authority | 权威端（默认服务器），4.x 取代 3.x 的 `set_network_master` |
| 客户端预测 | 本地先行执行输入，服务器校正 |
| 服务器校正 | 服务器状态回传后拉回客户端（区别于"回滚"） |
| 回滚（Rollback） | 回退到历史帧重新模拟 |
| ENet | 基于 UDP 的低层可靠/不可靠传输库 |
| Snapshot | 状态快照，权威服务器下发的状态包 |

---

## 七、文件与序列化

| 术语 | 解释 |
|------|------|
| FileAccess | 文件访问类（静态工厂 `open()` 族） |
| DirAccess | 目录访问类（迭代协议 `list_dir_begin` → `get_next`） |
| `res://` | 项目资源路径，导出后只读（PCK 包内） |
| `user://` | 用户数据路径，跨平台映射到系统数据目录 |
| PCK | Godot 打包文件格式，导出时聚合全部资源 |
| 序列化 | 对象 ↔ 文件的双向转换（.tscn/.tres/.res） |
| `@export` | 导出属性，出现在检查器并可序列化 |

---

## 八、编辑器与工具

| 术语 | 解释 |
|------|------|
| 检查器（Inspector） | 查看与编辑节点/资源属性的编辑器面板 |
| 停靠面板（Dock） | 编辑器侧边可停靠的功能面板 |
| EditorPlugin | 编辑器插件，扩展编辑器行为的入口 |
| EditorInterface | 编辑器接口单例（场景/选择/文件系统等入口） |
| 导入器（Importer） | `EditorImportPlugin`，把外部格式转为引擎资源 |
| `editor_plugins/enabled` | 项目设置键：已启用插件列表（plugin.cfg 路径） |

---

*本术语表对应全书版本基线：Godot 4.3（4.x 通用），2026-09 勘误。*
