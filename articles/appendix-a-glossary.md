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
| MainLoop | 主循环，驱动 idle 帧与物理帧的调度者（`SceneTree` 是它的实现） |
| NodePath | 指向场景中节点的路径（`get_node()` 的参数、`%UniqueName` 语法） |
| StringName | 引擎内部驻留字符串，O(1) 比较；方法名/信号名/属性名均用它 |
| PackedScene | 打包场景资源，`instantiate()` 由其生成节点树 |
| Tween | 补间动画（`create_tween()`），替代手写 `_process` 插值 |
| Packed\*Array | 打包数组（`PackedByteArray`/`PackedInt32Array`/`PackedVector3Array`…），连续内存、值语义 |
| TypedArray / TypedDictionary | 类型化容器（`Array[int]` 等），元素类型受检查器约束 |
| Thread / WorkerThreadPool | 线程与线程池；`Mutex`/`Semaphore` 为并发原语 |

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
| MeshInstance3D | 网格实例节点，场景中渲染网格的载体 |
| MultiMesh | 一次绘制提交多个网格实例，替代传统合批的手段 |
| visibility_range | 可见性距离范围，配合 `lod_bias` 实现距离 LOD 与视锥剔除 |
| WorldEnvironment / Environment | 环境节点与环境资源，SSAO/SSR/SDFGI 等后处理开关的入口 |
| ShaderMaterial / Shader | 材质与着色器资源；`shader_parameter` 传参的载体 |

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
| 窄相位（Narrowphase） | 精确检测阶段。Godot 自带 3D 物理以**支撑映射 + 分离轴**为主；Jolt 后端另含 GJK/EPA 等算法 |
| GJK | Gilbert–Johnson–Keerthi，凸体距离/穿透算法（**Jolt 等第三方物理后端**所用；Godot 自带物理未采用） |
| SAT | 分离轴定理，凸体碰撞检测（Godot 自带 3D 物理的窄相位思路之一） |
| EPA | 扩展多面体算法，求穿透深度与接触点（**Jolt 后端**所用） |
| 求解器（Solver） | 约束求解阶段，分配冲量消解接触 |
| 休眠（Sleeping） | 刚体停止模拟，`sleeping` 属性控制 |
| 冻结（Freeze） | 刚体冻结，`freeze` + `freeze_mode` 取代 3.x 的 `mode` |
| CCD | 连续碰撞检测，防止高速穿透 |
| Jolt Physics | 第三方物理引擎，4.4 起作为内置模块随引擎分发；**4.6 起为新建 3D 项目的默认物理引擎**（4.4 时仍是实验性选项） |
| PBD | 位置动力学，布料/软体的稳定模拟方法 |
| OccluderInstance3D | 遮挡体实例，遮挡剔除的载体 |
| PhysicsDirectSpaceState3D | 物理空间的直接查询接口（`intersect_ray`/`cast_motion`），**只能在物理帧内使用** |
| Shape3D | 形状资源基类；`ConvexPolygonShape3D` 可用于动态体，`ConcavePolygonShape3D` 仅限静态体 |
| CollisionObject3D | 碰撞对象基类（`PhysicsBody3D`/`Area3D`/`StaticBody3D` 的共同祖先） |
| monitoring / monitorable | `Area3D` 的两个开关：是否检测他人（monitoring）、是否被他人检测（monitorable） |
| 动力学体 vs 运动学体 | `RigidBody3D` 受力驱动、`CharacterBody3D` 由 `move_and_slide()` 驱动 —— 两者行为模型不同 |

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
| 动画混合过滤 | Godot 4 **没有** `AnimationMask` 资源；分层混合靠 `AnimationNodeBlendTree` + `AnimationNodeAdd2`，轨道级开关用 `Animation.track_set_enabled()` |
| AnimationMixer | 动画混音器基类（4.x 引入）；`AnimationPlayer` 与 `AnimationTree` 均派生自它，负责"播放"，混合由 Tree 负责 |
| BoneAttachment3D | 骨骼挂点节点，跟随指定骨骼的全局变换 |
| Skin / Skeleton3D | 蒙皮资源与骨骼容器；Godot 4 的骨骼以索引访问，无独立骨骼节点 |

---

## 五、音频系统

| 术语 | 解释 |
|------|------|
| AudioStreamPlayer | 音频播放器（**非定位/通用**类型；2D/3D 定位分别是 `AudioStreamPlayer2D` / `AudioStreamPlayer3D`） |
| AudioBus | 音频总线，`AudioServer` 的混音通道 |
| DSP | 数字信号处理，AudioEffect 系列效果器 |
| HRTF | 头部相关传输函数，双耳卷积的**空间音频理论概念**——**Godot 4.x 引擎未实现**（`AudioServer` 无相关 API，也无 HRTF 效果器） |
| 多普勒（Doppler） | 相对运动导致的音调偏移（**Godot 4.x 引擎未实现**；`AudioStreamPlayer3D.doppler_tracking` 只决定是否跟随物理步长，不做频移） |
| AudioStream | 音频流资源基类；`AudioStreamWAV`（PCM8/16、IMA ADPCM、QOA）、`AudioStreamOggVorbis`、`AudioStreamMP3` |
| AudioBusLayout / AudioEffect | 总线布局资源与效果器链（Reverb、Compressor、EQ…） |
| attenuation_model | 3D 音源的衰减模型（线性/平方反比/对数/关闭），与 `unit_size`、`max_distance` 共同决定衰减 |

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
| MultiplayerAPI / SceneMultiplayer | 高层多人 API 抽象与场景多人封装；`@rpc` 的 authority 判定入口 |
| MultiplayerSpawner / MultiplayerSynchronizer | 引擎自带的场景生成与状态同步方案（`spawn_function` / `replication_config`） |
| ENetConnection | ENet 传输的连接侧对象，`MultiplayerPeer` 的具体实现之一 |

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
| ResourceLoader / ResourceSaver | 资源加载与保存入口（同步 / 线程化 / 缓存模式） |
| ResourceFormatLoader | 自定义资源格式扩展点（如自定义 `.myfmt` 的加载器） |
| `.import` 边车文件 | 导入产物旁记录源文件与导入参数的元数据文件 |

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
| EditorSettings | 编辑器设置单例（键值对 + 各自的默认值），与项目设置 `ProjectSettings` 分离 |
| 导出模板 / 调试导出模板 | 打包发行版的发布单元；自定义引擎模块必须为每个平台重编译导出模板 |
| godot-cpp / extension_api.json | GDExtension 的 C++ 绑定与引擎 API 清单，二者共同决定 ABI 兼容边界 |

---

*本术语表对应全书版本基线：Godot 4.3（4.x 通用），2026-10 勘误。*

---

**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

**上一篇**: [第 72 篇：自定义模块 vs GDExtension 选型与实战](/articles/72-modules-vs-gdextension.md)
**下一篇**: [附录 B：GDScript 快速参考](/articles/appendix-b-gdscript-reference.md)
