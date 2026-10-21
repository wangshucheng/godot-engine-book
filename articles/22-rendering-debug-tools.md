# 第 22 篇：渲染调试工具

> **本章导读**：渲染问题 notoriously 难查——「画面不对」可能是剔除、材质、排序、着色器、驱动，
> 也可能只是「你看的那个视口本来就不渲染这一层」。本章把 Godot 4.x 的调试能力分成三层讲：
> **开关层**（项目设置 / 命令行参数 / 运行时属性）、
> **可视化层**（`Viewport.DebugDraw` 的**全 27 项**清单，不只是线框和 Overdraw 四个）、
> **量化层**（`Performance` 监视器、视口渲染统计、`RenderingServer` 的帧时间接口）。
> 第四章再补上 GPU 帧分析工具链：C++ 层的 `RenderingServer::get_frame_profile()` 与 `FrameProfileArea`、
> 编辑器 Visual Profiler、以及 **RenderDoc** / apitrace / Nsight 三类第三方工具的定位与取舍。
> 读完你应该能对着「帧率掉了」这个现象，走完一条从「看数据 → 定位 pass → 抓帧 → 改代码」的完整排查路径。
> **前置知识**：第 11 篇《Godot 渲染架构概述》、第 21 篇《渲染性能优化》。
> **难度**：进阶。

---

## 一、调试能力的三层来源

### 1.1 三种开关的分工

| 层 | 载体 | 生效时机 | 适合调什么 |
|----|------|----------|------------|
| **项目设置** | Project Settings 里的键值对 | 启动时读取 | 渲染后端、遮挡剔除开关、缩放策略 |
| **命令行开关** | `godot --xxx` | 启动时读取 | 图形 API 验证层、调试绘制（碰撞体、导航） |
| **运行时属性 / API** | 节点属性、脚本调用 | 随时（部分需重启） | `Viewport.debug_draw`、统计采样 |

> 📌 **优先级**：命令行 > 项目设置。项目设置里改了没生效，先看看是不是被命令行覆盖了。
> 运行时能改的只有一部分——比如 `Viewport.debug_draw` 随时可改，
> 而图形 API 验证层是**进程级**开关，只能启动时开。

### 1.2 `SceneTree` 的调试提示开关

```gdscript
# 启用渲染 Debug
# 4.3 没有 debug/settings/visible_collision_shapes 这个项目设置，
# 也没有 ProjectSettings.set() 方法（只有 set_setting()）。
# 碰撞体 / 导航网格 / 路径曲线的显示开关在 SceneTree 上：
get_tree().debug_collisions_hint = true
get_tree().debug_navigation_hint = true
get_tree().debug_paths_hint = true

# 更推荐用命令行开关（Debug 构建可用，见 --help）：
#   --debug-collisions   显示碰撞体
#   --debug-navigation   显示导航多边形
#   --debug-paths        显示 Path2D / Path3D 曲线
#   --debug-avoidance    显示导航避障调试
# 注意：官方文档标注这几个属性 "is not designed to be changed at run-time"。

# 渲染统计
var stats = Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)
print("渲染对象数：", stats)
```

| 选项 | 说明 |
|------|------|
| **Collision Shapes** | 显示碰撞体（`--debug-collisions` / `SceneTree.debug_collisions_hint`） |
| **Navigation** | 显示导航网格（`--debug-navigation` / `SceneTree.debug_navigation_hint`） |
| **Paths** | 显示 Path2D / Path3D 曲线（`--debug-paths` / `SceneTree.debug_paths_hint`） |
| **Avoidance** | 显示导航避障调试（`--debug-avoidance`） |

> ⚠️ 这四个属性官方标注为「不设计成运行时修改」——
> 改了不一定立刻反映到画面上（有时要等下一帧重建调试网格）。**排查时优先用命令行开关**。

### 1.3 命令行开关速查

```bash
# 图形 API 验证层（检查 API 使用错误、资源泄漏）
godot --gpu-validation

# 检测到 API 错误时直接中止（仅调试构建）
godot --gpu-abort

# 输出 GPU 帧耗时
godot --gpu-profile

# 场景调试绘制
godot --debug-collisions
godot --debug-navigation
godot --debug-paths
godot --debug-avoidance
```

> 💡 验证层与 `--gpu-abort` 是**排查「随机崩溃」「黑屏」「画面错乱」**的第一手段：
> 它们能在几秒内指出「你把一个已经被销毁的资源又用了一次」这类问题。

### 1.4 编辑器里的调试面板速查

| 面板 | 位置 | 回答什么问题 |
|------|------|--------------|
| **Debugger** | 底部 Debugger 标签页 | 报错、断点、调用栈 |
| **Profiler** | 底部 Profiler 标签页 | 逐帧时间（脚本 / 物理 / 渲染分组） |
| **Visual Profiler** | 底部 Visual Profiler 标签页 | 逐节点 / 逐 pass 的 GPU 与 CPU 耗时 |
| **Remote** | 底部 Remote 标签页 | 运行时检查/改动远端场景树 |
| **Game** | 底部 Game 标签页 | 启动游戏、连设备 |
| **监视器（Monitors）** | 底部 Monitor 标签页 | 帧率、内存、对象数等实时曲线 |
| **渲染查看器（Render Viewport）** | 3D 视口右上角下拉 | 切到某个摄像机 / 调试视口 |

> 📌 **Visual Profiler 与 Profiler 的分工**：
> Profiler 是「脚本层」的（谁在 `_process` 里花的時間），Visual Profiler 是「渲染层」的（哪个 pass 花的 GPU 时间）。
> 两者的时间是**不同口径**，不要相加。

> 📌 **渲染查看器**在排查多相机问题（画面渲染的是错误的相机、UI 相机盖住了主相机）时非常有用：
> 它能让你在编辑器里直接看某个相机的画面，不需要运行游戏。

---

## 二、`Viewport.DebugDraw`：全 27 项清单

### 2.0 项目设置里与调试相关的几项

| 设置键 | 作用 | 备注 |
|--------|------|------|
| `rendering/renderer/rendering_method` | 渲染后端（`forward_plus` / `mobile` / `gl_compatibility`） | **排查「粒子不显示」先看这个** |
| `rendering/renderer/rendering_method.mobile` | 移动端单独指定的后端 | |
| `rendering/occlusion_culling/use_occlusion_culling` | 全局遮挡剔除开关（默认 false） | 见第 21 篇 |
| `rendering/anti_aliasing/quality/msaa_3d` | 3D MSAA 档位 | 影响填充率 |
| `rendering/scaling_3d/mode` | 3D 缩放策略（双线性 / FSR / FSR2） | 影响 GPU 开销 |
| `rendering/driver/depth_prepass/enable` | 深度预通道 | 改它会改变透明排序结果 |
| `debug/shapes/collision/*` | 碰撞形状绘制的细分等选项 | 4.3 的一组 `debug/shapes/collision/` 设置 |

> ⚠️ 项目设置的键名**在版本之间会变**（4.x 内部重构过多次）。
> 上表是 4.3 的写法；**实际改设置请直接在编辑器的 Project Settings 面板里搜索**，
> 面板显示的是当前版本真实的键。不要凭记忆写键名。

### 2.1 怎么用

```gdscript
# 线框模式
get_viewport().debug_draw = Viewport.DEBUG_DRAW_WIREFRAME

# 无光照模式
get_viewport().debug_draw = Viewport.DEBUG_DRAW_UNSHADED

# 光照模式
get_viewport().debug_draw = Viewport.DEBUG_DRAW_LIGHTING
```

底层等价于 `RenderingServer.viewport_set_debug_draw()`；
`Viewport.debug_draw` 是**按视口**设置的，所以分屏 / 多视口可以各看各的。

> 📌 **调试绘制本身有开销**：很多可视化项要把额外的缓冲 blit 到屏幕上。
> 排查完记得关掉，否则「加了调试开关就掉帧」会变成一个假问题。

### 2.2 27 项完整清单

`Viewport.DebugDraw` 在 4.3 一共有 **27** 个取值，下面按用途分组：

#### （1）基础显示（3 项）

| 常量 | 作用 | 备注 |
|------|------|------|
| `DEBUG_DRAW_DISABLED` | 关闭调试绘制 | 默认值 |
| `DEBUG_DRAW_UNSHADED` | 无光照（纯 albedo） | 看贴图、UV、法线贴图是否正确 |
| `DEBUG_DRAW_LIGHTING` | 只看光照结果 | albedo 被替换成白色，只保留光照贡献 |

#### （2）几何与缓冲（4 项）

| 常量 | 作用 | 备注 |
|------|------|------|
| `DEBUG_DRAW_WIREFRAME` | 线框显示 | 看几何是否有破面、缺面 |
| `DEBUG_DRAW_NORMAL_BUFFER` | 法线缓冲 | 法线朝向是否正确、切线空间是否翻转 |
| `DEBUG_DRAW_OVERDRAW` | 过度绘制 | 亮的地方 = 重复画的次数多 |
| `DEBUG_DRAW_INTERNAL_BUFFER` | 后处理前的内部缓冲 | 定位「是场景渲染错了还是后处理搞坏了」 |

#### （3）阴影（2 项）

| 常量 | 作用 | 备注 |
|------|------|------|
| `DEBUG_DRAW_SHADOW_ATLAS` | 阴影图集 | Omni / Spot 灯的立方体阴影贴图布局 |
| `DEBUG_DRAW_DIRECTIONAL_SHADOW_ATLAS` | 平行光阴影图集 | 看级联（cascade）占用与浪费 |

#### （4）全局光照（7 项）

| 常量 | 作用 | 备注 |
|------|------|------|
| `DEBUG_DRAW_VOXEL_GI_ALBEDO` | VoxelGI 的反照率数据 | VoxelGI 烘焙结果是否正确 |
| `DEBUG_DRAW_VOXEL_GI_LIGHTING` | VoxelGI 的光照数据 | |
| `DEBUG_DRAW_VOXEL_GI_EMISSION` | VoxelGI 的自发光数据 | |
| `DEBUG_DRAW_GI_BUFFER` | GI 缓冲 | 屏幕空间 GI 的中间结果 |
| `DEBUG_DRAW_SDFGI` | SDFGI 级联 | SDFGI 的级联分布与收敛情况 |
| `DEBUG_DRAW_SDFGI_PROBES` | SDFGI 探针 | 探针位置的分布与命中情况 |
| `DEBUG_DRAW_SCENE_LUMINANCE` | 场景亮度缓冲 | SDFGI / 环境光计算的基础数据 |

#### （5）屏幕空间效果（2 项）

| 常量 | 作用 | 备注 |
|------|------|------|
| `DEBUG_DRAW_SSAO` | SSAO 缓冲 | 环境光遮蔽强度是否合理 |
| `DEBUG_DRAW_SSIL` | SSIL 缓冲 | 屏幕空间间接光 |

#### （6）聚簇（Forward+ 专属，4 项）

| 常量 | 作用 | 备注 |
|------|------|------|
| `DEBUG_DRAW_CLUSTER_OMNI_LIGHTS` | 聚簇 Omni 光源分布 | 看光源有没有挤进同一簇 |
| `DEBUG_DRAW_CLUSTER_SPOT_LIGHTS` | 聚簇聚光灯分布 | |
| `DEBUG_DRAW_CLUSTER_DECALS` | 聚簇贴花分布 | |
| `DEBUG_DRAW_CLUSTER_REFLECTION_PROBES` | 聚簇反射探针分布 | 反射探针覆盖是否够 |

> 📌 这四项是 **Forward+ 的聚簇（cluster）分配可视化**：
> 每一簇（cluster）能容纳的光源数量有限，簇分得太细 → 簇太多 → 光源被截断；
> 分得太粗 → 簇内所有物体都吃满那簇的光源数。
> 调 `rendering/clustering` 相关的项目设置时，这四个视图是最直接的反馈。

#### （7）其它（5 项）

| 常量 | 作用 | 备注 |
|------|------|------|
| `DEBUG_DRAW_PSSM_SPLITS` | 平行光级联分界线 | 看级联分割位置与过渡是否合理 |
| `DEBUG_DRAW_DECAL_ATLAS` | 贴花图集 | 贴花分配是否正确 |
| `DEBUG_DRAW_OCCLUDERS` | 遮挡剔除缓冲 | 遮挡体烘焙出来的遮挡图（需开遮挡剔除） |
| `DEBUG_DRAW_MOTION_VECTORS` | 运动矢量 | TAA / 运动模糊的输入是否正确 |
| `DEBUG_DRAW_DISABLE_LOD` | 全部按最高精度绘制 | **不是「显示 LOD」**，而是「禁用 LOD」 |

> `Viewport.DebugDraw` 里**没有** `DEBUG_DRAW_LOD` 这个常量；与 LOD 相关的只有 `DEBUG_DRAW_DISABLE_LOD`（强制用最高精度绘制）。

> ⚠️ 缓冲类可视化（SSAO / SSIL / SDFGI / GI / 聚簇 / 运动矢量等）**基本只在 Forward+ 下有内容**；
> Mobile 只有一部分；Compatibility 下多数是空的。别把「看不到内容」误判成「功能没生效」。

### 2.3 常用组合技

| 症状 | 组合 | 说明 |
|------|------|------|
| 画面比预期暗 | `DEBUG_DRAW_LIGHTING` + `DEBUG_DRAW_UNSHADED` 对比 | 差值就是光照贡献 |
| 阴影不对 | `DEBUG_DRAW_DIRECTIONAL_SHADOW_ATLAS` + `DEBUG_DRAW_PSSM_SPLITS` | 先看级联，再看图集 |
| 画面糊 / 有色块 | `DEBUG_DRAW_INTERNAL_BUFFER` | 判断是场景渲染问题还是后处理问题 |
| 物体莫名消失 | `DEBUG_DRAW_WIREFRAME` + `DEBUG_DRAW_OCCLUDERS` | 视锥剔除 vs 遮挡剔除 |
| 帧率掉但看不出 | `DEBUG_DRAW_OVERDRAW` | 亮处就是过度绘制热点 |

### 2.4 原始清单（保留）

| 类型 | 常量 | 说明 |
|------|------|------|
| **Wireframe** | `DEBUG_DRAW_WIREFRAME` | 线框显示 |
| **Unshaded** | `DEBUG_DRAW_UNSHADED` | 无光照 |
| **Lighting** | `DEBUG_DRAW_LIGHTING` | 只显示光照信息 |
| **Overdraw** | `DEBUG_DRAW_OVERDRAW` | 过度绘制（半透明叠加，看哪里在重复画） |
| **Normal Buffer** | `DEBUG_DRAW_NORMAL_BUFFER` | 法线缓冲 |
| **SSAO / SSIL** | `DEBUG_DRAW_SSAO` / `DEBUG_DRAW_SSIL` | 屏幕空间遮蔽 / 间接光缓冲 |
| **PSSM Splits** | `DEBUG_DRAW_PSSM_SPLITS` | 平行光级联分界线 |
| **SDFGI** | `DEBUG_DRAW_SDFGI` / `DEBUG_DRAW_SDFGI_PROBES` | SDFGI 级联与探针 |
| **Disable LOD** | `DEBUG_DRAW_DISABLE_LOD` | 全部按最高精度绘制，检查 LOD 差异 |
| **Occluders** | `DEBUG_DRAW_OCCLUDERS` | 遮挡剔除缓冲 |
| **Motion Vectors** | `DEBUG_DRAW_MOTION_VECTORS` | 运动矢量 |
| **Internal Buffer** | `DEBUG_DRAW_INTERNAL_BUFFER` | 后处理前的内部缓冲 |

### 2.5 调试绘制的代价与用法

| 情况 | 代价 |
|------|------|
| 线框 / 无光照 | 很低（只是换一种着色输出） |
| 缓冲类可视化（SSAO / SDFGI / 聚簇 / 运动矢量） | 中等（要把内部缓冲 blit 到屏幕） |
| `DEBUG_DRAW_OVERDRAW` | 中等（需要额外的叠加 pass） |
| 反复切换 debug_draw | 会触发视口重建，切换瞬间会掉帧 |

**用法建议**：

1. **一次只开一项**，切换之间留几帧稳定期；
2. **截图优先于实时观察**：调试绘制是「运行时状态」，截图才能拿去和别人讨论；
3. **关掉再测性能**：带调试绘制的帧时间没有参考价值；
4. **记录开关名**：截图上写清楚「这是 `DEBUG_DRAW_NORMAL_BUFFER`」，否则三天后没人认得。

```gdscript
# 一个「按 F 键轮换调试视图」的小工具
extends Node3D

const debug_views := [
	Viewport.DEBUG_DRAW_DISABLED,
	Viewport.DEBUG_DRAW_UNSHADED,
	Viewport.DEBUG_DRAW_WIREFRAME,
	Viewport.DEBUG_DRAW_OVERDRAW,
	Viewport.DEBUG_DRAW_NORMAL_BUFFER,
	Viewport.DEBUG_DRAW_LIGHTING,
]

var _index := 0

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		_index = (_index + 1) % debug_views.size()
		get_viewport().debug_draw = debug_views[_index]
		print("debug_draw = ", debug_views[_index])
```

> 📌 `Viewport.debug_draw` 的枚举值是**整数**，这个数组里存的是常量本身，
> 打印出来是一串数字——对照 2.2 的清单表可以查到它对应哪一项。



## 三、渲染统计与帧时间

### 3.1 `Performance` 监视器

```gdscript
# 获取性能数据
var fps = Performance.get_monitor(Performance.TIME_FPS)
var draw_calls = Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
var objects = Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)

print("FPS: ", fps)
print("Draw Calls: ", draw_calls)
print("Objects: ", objects)
```

> 常量名是 `Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME`（带 `_IN_FRAME` 后缀），不是 `RENDER_TOTAL_DRAW_CALLS`。4.3 的 `Performance.Monitor` 枚举里与渲染相关的三个是 `RENDER_TOTAL_OBJECTS_IN_FRAME` / `RENDER_TOTAL_PRIMITIVES_IN_FRAME` / `RENDER_TOTAL_DRAW_CALLS_IN_FRAME`。
>
> 也可以按渲染通道细分统计：`Viewport.get_render_info(Viewport.RENDER_INFO_TYPE_SHADOW, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)`。

4.3 里与渲染 / 时间相关的监视器常量：

| 常量 | 含义 | 用途 |
|------|------|------|
| `Performance.TIME_FPS` | 当前帧率 | 最基本的健康指标 |
| `Performance.TIME_PROCESS` | 主线程一帧的耗时（秒） | 看脚本逻辑占了多少 |
| `Performance.TIME_PHYSICS_PROCESS` | 物理一帧的耗时（秒） | 物理是不是瓶颈 |
| `Performance.TIME_NAVIGATION_PROCESS` | 导航一帧的耗时（秒） | 导航网格查询开销 |
| `Performance.RENDER_TOTAL_OBJECTS_IN_FRAME` | 本帧渲染对象数 | 场景规模 |
| `Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME` | 本帧提交的图元数 | 几何量 |
| `Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME` | 本帧绘制调用数 | 提交量 |
| `Performance.RENDER_VIDEO_MEM_USED` | 显存占用 | 贴图 / 网格预算 |
| `Performance.RENDER_TEXTURE_MEM_USED` | 纹理显存 | |
| `Performance.RENDER_BUFFER_MEM_USED` | 渲染缓冲显存 | 后处理与中间缓冲的代价 |
| `Performance.OBJECT_NODE_COUNT` | 场景节点数 | 逻辑规模 |

> 💡 **`TIME_PROCESS` 与 `TIME_FPS` 的关系**：`TIME_PROCESS` 只统计**主线程**的工作，
> 不含渲染线程与 GPU 的等待时间。所以「`TIME_PROCESS` 很小但帧率上不去」
> 几乎必然意味着瓶颈在渲染线程或 GPU——这是最省事的一次分流判断。

### 3.2 视口级渲染统计

```gdscript
# 按渲染通道拆分
var visible := get_viewport().get_render_info(
	Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)
var shadow := get_viewport().get_render_info(
	Viewport.RENDER_INFO_TYPE_SHADOW, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)
var canvas := get_viewport().get_render_info(
	Viewport.RENDER_INFO_TYPE_CANVAS, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)

# 图元数
var primitives := get_viewport().get_render_info(
	Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_PRIMITIVES_IN_FRAME)
```

| 通道常量 | 含义 |
|----------|------|
| `Viewport.RENDER_INFO_TYPE_VISIBLE` | 可见通道（主场景） |
| `Viewport.RENDER_INFO_TYPE_SHADOW` | 阴影通道 |
| `Viewport.RENDER_INFO_TYPE_CANVAS` | 2D Canvas 通道 |

> 📌 **阴影通道常常比可见通道还大**：每个投影的物体都要在阴影 pass 里再画一遍。
> 看到 shadow > visible 时，第一反应应该是「关掉小物件的投影」。

### 3.3 渲染服务器侧的接口

| 接口 | 作用 |
|------|------|
| `RenderingServer.get_frame_setup_time_cpu()` | 取回**上一帧**的 CPU 端帧准备时间（秒） |
| `RenderingServer.force_sync()` | 强制等待渲染线程把命令队列跑完（测时间点用） |
| `RenderingServer.force_draw()` | 强制提交一帧 |
| `RenderingServer.get_video_adapter_name()` | GPU 型号（写性能报告必备） |
| `RenderingServer.get_video_adapter_vendor()` | GPU 厂商 |
| `RenderingServer.get_video_adapter_api_version()` | 图形 API 版本 |
| `RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)` | 全局绘制调用数 |

```gdscript
# 抓一帧的 CPU 端准备时间
var setup := RenderingServer.get_frame_setup_time_cpu()
print("上一帧 CPU 准备时间：%.2f ms" % (setup * 1000.0))
```

> ⚠️ `get_frame_setup_time_cpu()` 读的是**上一帧**的值（引擎在帧末才更新），
> 所以它适合做连续采样统计，不适合做「这一帧花了多少」的精确断言。

### 3.4 视口的渲染时间测量

```gdscript
# 打开视口的渲染时间测量（4.3 签名：viewport、enable、measure_cpu_time、measure_gpu_time）
var vp_rid := get_viewport().get_viewport_rid()
RenderingServer.viewport_set_measure_render_time(vp_rid, true, true, true)

# 下一帧之后读数
var cpu_ms := RenderingServer.viewport_get_measured_render_time_cpu() * 1000.0
var gpu_ms := RenderingServer.viewport_get_measured_render_time_gpu() * 1000.0
```

| 接口 | 含义 |
|------|------|
| `RenderingServer.viewport_set_measure_render_time()` | 开关测量（可分别开关 CPU / GPU） |
| `RenderingServer.viewport_get_measured_render_time_cpu()` | CPU 侧渲染时间（秒） |
| `RenderingServer.viewport_get_measured_render_time_gpu()` | GPU 侧渲染时间（秒） |

> ⚠️ 开启测量会引入同步等待，**它本身会拖慢帧率**。
> 正确用法是「开启 → 采样若干帧 → 关闭 → 记录数据」，而不是长期挂着做性能对比。
> 另外这个接口是**视口级**的：只有主视口的读数才对应你看到的画面。

### 3.5 性能指标目标表

> ⚠️ 下表目标值为**示意数据**（未附测试环境），请按自己的项目预算调整。

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。实际开销取决于场景规模与目标硬件，请在目标平台实测。

| 指标 | 说明 | 目标 |
|------|------|------|
| **FPS** | 帧率 | 60 |
| **Draw Calls** | 绘制调用 | <500 |
| **Objects** | 渲染对象 | <2000 |
| **Video Mem** | 显存占用 | <2GB |

### 3.6 一个渲染诊断面板

把上面的统计接口拼成一个屏幕上的小面板，排查时一眼就能看到：

```gdscript
# 渲染诊断面板：挂在 CanvasLayer 下
extends CanvasLayer

var _label: Label
var _accum := 0.0
var _frames := 0
var _worst := 0.0

func _ready() -> void:
	_label = Label.new()
	_label.position = Vector2(12, 12)
	_label.add_theme_font_size_override("font_size", 14)
	add_child(_label)

func _process(delta: float) -> void:
	_accum += delta
	_frames += 1
	if delta > _worst:
		_worst = delta
	if _accum < 0.5:
		return
	var avg := _accum / _frames
	var text := "FPS %.1f（平均帧时间 %.2f ms，最差 %.2f ms）\n" % [
		1.0 / avg, avg * 1000.0, _worst * 1000.0]
	text += "渲染对象 %d / 图元 %d / 绘制调用 %d\n" % [
		int(Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))]
	text += "可见 %d / 阴影 %d / Canvas %d\n" % [
		_get_draws(Viewport.RENDER_INFO_TYPE_VISIBLE),
		_get_draws(Viewport.RENDER_INFO_TYPE_SHADOW),
		_get_draws(Viewport.RENDER_INFO_TYPE_CANVAS)]
	text += "CPU 帧准备 %.2f ms / 显存 %d MB" % [
		RenderingServer.get_frame_setup_time_cpu() * 1000.0,
		int(Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576)]
	_label.text = text
	_accum = 0.0
	_frames = 0
	_worst = 0.0

func _get_draws(type: int) -> int:
	return int(get_viewport().get_render_info(
		type, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME))
```

> 💡 面板里的「平均 / 最差」两个数字比单纯的 FPS 有用得多：
> **平均值稳定但最差值很大**，说明有偶发卡顿（GC、资源加载、shader 编译）；
> **平均值本身就大**，说明是持续性的性能问题。
> 这两种病因的排查方向完全不同。

> ⚠️ `get_render_info()` 读的是**上一帧**的统计，切换通道时数字会滞后一帧，属正常现象。

### 3.7 `--gpu-profile` 的输出

```bash
godot --gpu-profile
```

| 项 | 说明 |
|----|------|
| 输出位置 | 标准输出（调试构建） |
| 内容 | 逐帧的 GPU 耗时与部分管线信息 |
| 与 `viewport_get_measured_render_time_gpu()` 的区别 | 前者是**进程级、逐帧打印**；后者是**视口级、可脚本读取** |
| 开销 | 中等；比验证层便宜，但也不适合当常规性能测试 |

> 📌 `--gpu-profile` 与 `--gpu-validation` 可以同时开，但**不要在性能测试时开任何一个**。
> 它们的数字只用来做「相对比较」（同一场景开 / 关的差别），不能当成绝对性能数据。

---

## 四、GPU 帧分析工具链

### 4.1 C++ 层：`get_frame_profile()` 与 `FrameProfileArea`

这是本章最重要的一条**事实纠正**：

> ⚠️ **`get_frame_profile()` 在 Godot 4.3 里没有导出为 GDScript 方法**。
> `doc/classes/RenderingServer.xml` 里搜不到 `get_frame_profile`、`FrameProfileArea`、`set_frame_profiling_enabled` 中的任何一个——
> 它只在 C++ 层存在（`servers/rendering_server.h`），**编辑器 Visual Profiler 是它的主要消费者**。
> 想在脚本里拿 GPU 侧数据，4.3 的公开入口是 `get_rendering_info()` / `viewport_get_render_info()` 这类统计接口。

C++ 层的结构（`servers/rendering_server.h`）：

| 符号 | 形态 | 说明 |
|------|------|------|
| `RenderingServer::get_frame_profile()` | 虚函数 | 返回本帧的 profile 列表 |
| `RenderingServer::FrameProfileArea` | 结构体 | 字段只有三个：`String name; double gpu_msec; double cpu_msec;` |
| `FrameProfileArea` 的取值 | 枚举 | Viewport / Pass / Draw Call / Object / Process 等分区 |

> 📌 也就是说：**每一项 profile 记录的是「一个名字 + 它的 GPU 毫秒 + 它的 CPU 毫秒」**。
> 编辑器 Visual Profiler 画出来的时间条，就是这些 `name` 与 `gpu_msec` / `cpu_msec`。
> 名字的来源是引擎里的 `RENDER_TIMESTAMP()` 宏（在 `renderer_scene_render_rd.cpp` 等文件里打点）。

### 4.2 编辑器 Visual Profiler

| 项 | 说明 |
|----|------|
| 位置 | 编辑器底部 **Debugger → Visual Profiler** 面板 |
| 数据来源 | C++ 层 `RenderingServer::get_frame_profile()` |
| 显示内容 | 逐节点帧时间、渲染管线各阶段（pass）耗时 |
| 适用 | 定位「哪一帧的哪一步慢」 |

用法要点：

1. **先跑起来**：在编辑器里运行项目（`F5`），Visual Profiler 才有数据；
2. **看两条线**：CPU 时间与 GPU 时间。CPU 高 = 引擎在准备；GPU 高 = 显卡在算；
3. **对照 pass 名**：时间条上的名字就是源码里 `RENDER_TIMESTAMP()` 的名字，
   找到同名的时间戳就等于知道去源码的哪一行看（见第 14 篇《场景渲染流程》）；
4. **别在编辑器里下结论**：编辑器本身有额外开销，最终数据要在导出构建里复核。

> ⚠️ Visual Profiler 显示的粒度是 **pass 级**，不是 draw call 级。
> 想看「一帧里到底发出了哪些 draw call、每个的状态是什么」，需要第三方工具（见 4.4）。

### 4.3 `RENDER_TIMESTAMP` 与 pass 名

引擎在渲染管线的关键节点打时间戳，名字会同时出现在：

- 编辑器 Visual Profiler 的时间条上；
- 调试构建的日志输出里（配合 `--gpu-profile` / `--gpu-abort`）。

| 时间戳名字 | 对应阶段 |
|------------|----------|
| `Render Setup` | 帧准备（可见性、剔除、命令录制） |
| `Shadow Setup` | 阴影 pass 的准备 |
| `Render Viewport` | 视口整体 |
| `Pre Opaque` / `Opaque` | 不透明前 / 不透明 |
| `Transparent` | 透明 |
| `Post Sky` / `Post Opaque` / `Post Transparent` | 后处理回调的前后 |
| `Tonemap` | 色调映射 |
| `Bokeh` | 景深 |

> 📌 上表是「按阶段名理解时间条的思路」，**不是逐字对照的官方清单**——
> 实际名字以你所用版本的 `RENDER_TIMESTAMP()` 打点为准（在 `servers/rendering/renderer_rd/` 下搜 `RENDER_TIMESTAMP` 即可）。

### 4.4 **RenderDoc**：抓帧与逐 pass 读数

| 项 | 说明 |
|----|------|
| 定位 | 「这一帧到底画了什么」「这个 draw call 的管线状态对不对」 |
| 能力 | 抓一帧、列出所有 draw call、看每个的顶点/索引数、管线状态、绑定资源、着色器源码与反汇编 |
| 对 Godot 的支持 | 支持 Vulkan；对 Forward+ 场景可直接使用（需要 debug 构建或开启捕获层） |
| 不擅长 | 长时间性能分析（抓帧本身有开销）、CPU 侧逻辑 |

典型工作流：

1. 用 debug 构建（或带调试符号的 release 构建）启动游戏；
2. 在 RenderDoc 里选择目标进程，触发抓帧；
3. 在 Event Browser 里逐个事件看：**Drawcall 数量、顶点缓冲、索引数、管线状态、绑定贴图**；
4. 重点看两类异常：**本该被剔除的物体出现了**、**本该出现的物体没出现**；
5. 选中某个 draw call 看它用的着色器（可以直接读反汇编的指令）。

> 💡 RenderDoc 的独特价值是**逐 draw call 的管线状态对比**：
> 第 21 篇说过「共享材质能减少状态切换」，
> 用 RenderDoc 就能直接看到「切换前后的管线状态到底差在哪」。

### 4.5 **apitrace**：追 API 调用

| 项 | 说明 |
|----|------|
| 定位 | 「Vulkan API 调用层面发生了什么」——不是画面问题，是**驱动 / 同步 / 资源生命周期**问题 |
| 能力 | 把每一帧的 Vulkan（也支持 D3D11/GL）调用记录成 trace，可以在 UI 里单步回放 |
| 典型用途 | 资源泄漏、内存分配尖刺、命令缓冲区提交异常、驱动层 bug 复现 |
| 对 Godot 的支持 | 通过 Vulkan 的 `VK_EXT_tooling_info` / 捕获层工作 |

> 📌 **apitrace 记录的是「调用」不是「画面」**。
> 如果你怀疑的是「画面内容不对」，用 RenderDoc；
> 如果怀疑的是「某帧特别慢但不知道卡在哪」，
> apitrace 的 trace 能看到这一帧发了多少次 `vkQueueSubmit`、分配了多少内存。

### 4.6 **Nsight**：系统级与着色器级

| 工具 | 定位 | 适合回答的问题 |
|------|------|----------------|
| **Nsight Systems** | 系统级时间线（CPU 线程 + GPU + CUDA/D3D/Vulkan API） | 「这一帧的时间花在哪」——CPU 侧哪段代码、哪次 API 调用 |
| **Nsight Graphics** | 逐 pass 逐着色器分析（像素着色器占用率、寄存器数、指令数） | 「这个 shader 为什么这么慢」「哪里是瓶颈着色器」 |

> 📌 两者的关系：Systems 给你**时间线**（宏观定位），Graphics 给你**单个 pass 的细节**（微观优化）。
> 典型配合是：先用 Systems 找到最慢的 pass，再用 Graphics 分析那个 pass 的着色器。
> 注意它们是 **NVIDIA 工具**，在 AMD / Intel 显卡上不可用——那就要回到 RenderDoc。

### 4.7 工具选型矩阵

| 你想知道 | 首选 | 备选 |
|----------|------|------|
| 哪一帧、哪一步最慢 | 编辑器 Visual Profiler | Nsight Systems |
| 这帧画了什么、状态对不对 | **RenderDoc** | 无 |
| 资源泄漏、驱动层异常 | **apitrace** | 引擎自带的 `--gpu-validation` |
| 某个着色器为什么慢 | Nsight Graphics | RenderDoc 看反汇编 |
| 帧率、绘制调用、显存 | `Performance` 监视器 | Visual Profiler |
| 画面某块区域颜色不对 | `Viewport.DebugDraw` 全 27 项 | RenderDoc |

### 4.8 第三方工具的定位与取舍

| 工具 | 成本 | 风险 | 什么时候用 |
|------|------|------|----------|
| **RenderDoc** | 抓帧有明显开销；需要 debug 构建 | 会和引擎自己的验证层抢占 | 怀疑「画错了」时 |
| **apitrace** | trace 文件巨大；回放慢 | 需要驱动支持 | 怀疑「API 用错了 / 泄漏了」时 |
| **Nsight Systems** | 需要 NVIDIA 卡 + 驱动 | 商用授权条款 | 需要全系统时间线时 |
| **Nsight Graphics** | 开销最大 | 同上 | 已经定位到具体 shader 时 |

> 💡 **一条实用建议**：先用引擎自带的量（`Performance` + Visual Profiler + `DebugDraw`）缩小范围，
> **再**上第三方工具。直接上 RenderDoc 抓一帧然后在几千个事件里翻，
> 是最容易浪费时间的做法。

### 4.9 Visual Profiler 读图指南

打开面板后，按这个顺序读：

| 步骤 | 看什么 | 结论 |
|------|--------|------|
| 1 | 顶部总帧时间条 | 先确认「慢」是稳定慢还是尖刺 |
| 2 | 总条里的 CPU / GPU 比例 | GPU 占比高 → 往 pass 里找；CPU 占比高 → 看主线程与提交 |
| 3 | 展开各个 pass 的时间条 | 找出最长的那一条 |
| 4 | 对照 pass 名去源码找 `RENDER_TIMESTAMP()` | 知道问题在哪个函数附近 |
| 5 | 切换不同视角 / 场景复测 | 确认是「特定场景慢」还是「普遍慢」 |

**读图时最常见的三个误判**：

1. **把「Shadow Setup」很长当成阴影 pass 慢**——它常常只是「准备阴影贴图布局」的 CPU 时间；
2. **忽略 `Render Setup`**——它包含了剔除与命令录制，场景组织差时它会异常地长；
3. **在编辑器里比绝对值**——编辑器有额外开销，只能比**相对比例**。

> 📌 Visual Profiler 的时间条是**累积值**（这一帧所有同名打点加起来），
> 所以「一个名字出现很多次」是正常的，不要当成重复渲染。

### 4.10 RenderDoc 实操七步

以「某个物体没有画出来」为例：

| 步 | 操作 | 目的 |
|----|------|------|
| 1 | 用**调试构建**（或带符号的 release 构建）启动 | 抓帧需要可调试的着色器与符号 |
| 2 | 在 RenderDoc 的 Target 面板里选中 Godot 进程 | 建立连接 |
| 3 | 触发抓帧（Capture Frame） | 拿到一帧的全部 GPU 事件 |
| 4 | 在 Event Browser 里筛 `Drawcall` | 只看绘制事件 |
| 5 | 逐个看 **顶点 / 索引数** | 索引数为 0 或异常的条目 = 可疑 |
| 6 | 看 **Pipeline State** 与绑定资源 | 混合模式、深度状态、贴图是否如预期 |
| 7 | 选中可疑 draw call，看**着色器源码 / 反汇编** | 确认是不是被 `discard`、被 alpha 裁掉 |

**三类常见发现**：

| 发现 | 说明的问题 |
|------|------------|
| 该物体**根本没有 drawcall** | 被剔除了（视锥 / 距离 / 遮挡）或被 `visible = false` |
| 有 drawcall 但**索引数为 0** | 网格数据有问题（导入出错、LOD 切到了空层） |
| 有 drawcall 且**被 discard 掉** | 着色器里 alpha 判定、clip 距离或自定义逻辑把它丢了 |

> 💡 第 5 步的「索引数为 0」是 Godot 里最常见的一类问题：
> 网格导入时勾了某些选项（比如没有生成 LOD、或者倒面/无 UV 被剔除），
> 结果某个 LOD 层级是空的。用 `DEBUG_DRAW_WIREFRAME` 能先在画面上确认这一点。

### 4.11 第三方工具的接入成本

| 准备 | RenderDoc | apitrace | Nsight |
|------|-----------|----------|--------|
| 需要 debug 构建 | 是 | 否（但建议） | 否 |
| 需要显卡驱动支持 | 否（用捕获层） | 是（要 trace 支持） | 是（NVIDIA 驱动） |
| 会对性能产生影响 | 抓帧时明显 | 记录时明显 | 采集时明显 |
| 结果可复现 | 是（trace 可存档） | 是 | 部分 |
| 学习成本 | 中 | 高 | 中 |

> 📌 **建议的引入顺序**：先用引擎自带的量 → 需要逐 draw call 时上 RenderDoc →
> 怀疑驱动 / 资源问题时上 apitrace → 需要着色器级分析时上 Nsight。
> 一次上一个全套，既慢又容易得出互相矛盾的结论。



### 4.12 在目标设备上调试（PC 工具链用不了的时候）

RenderDoc / Nsight 基本是桌面工具。移动端要换手段：

| 平台 | 手段 | 说明 |
|------|------|------|
| Android | 编辑器 **Remote** 面板连真机运行 | 脚本、监视器、Visual Profiler 在真机上都能用 |
| Android | `adb logcat` 看引擎与验证层输出 | 崩溃与验证层报错的日志都在这里 |
| Android | Android GPU Inspector（AGI） | Google 官方的 GPU 跟踪工具，抓帧 + 逐 pass 分析 |
| iOS | Xcode Instruments | Metal System Trace / GPU Frame Capture |
| 任意平台 | 编辑器连真机 + 设备端 `Performance` 采样 | 最通用的做法：数据在真机采，脚本在编辑器写 |

> 📌 **真机调试的关键纪律**：在编辑器里连真机跑，和在 PC 上跑，**渲染后端可能不同**
> （移动端常常落到 Compatibility）。很多「PC 上好好的、手机上不对」的问题，
> 根因就是后端不同，而不是代码不同。
> 第 20 篇 1.4 讲的「GPU 粒子在 Compatibility 下不可用」就是典型例子。

> 💡 移动端上最实用的组合是：**编辑器 Remote 跑真机 + 脚本内采样 `Performance` 监视器 + 把数据写进文件**，
> 这样既拿到了真机数据，又不用在手机上装任何分析工具。

---

## 五、性能问题的排查流程

### 5.1 决策树

```
现象：帧率低
    │
    ├─ Q1：TIME_PROCESS（主线程）占多少？
    │     ├─ 很大 → 脚本 / 物理 / 导航逻辑
    │     │        → 查 TIME_PHYSICS_PROCESS、TIME_NAVIGATION_PROCESS
    │     └─ 很小 ──────────────────────────────────────┐
    │                                                    │
    ├─ Q2：绘制调用 / 渲染对象数是否异常？                 │
    │     ├─ 是 → 场景组织问题（第 21 篇）                │
    │     │        → MultiMesh / 可见性范围 / 阴影剔除     │
    │     └─ 否 ↓                                       │
    │                                                    │
    ├─ Q3：GPU 时间高还是 CPU 渲染时间高？                │
    │     ├─ GPU 高 → 填充率 / 几何 / shader              │
    │     │        → DebugDraw：OVERDRAW / WIREFRAME      │
    │     │        → RenderDoc 看具体 draw call           │
    │     └─ CPU 渲染时间长 → 剔除 / 状态切换             │
    │              → Visual Profiler 看 pass 分布         │
    └────────────────────────────────────────────────────┘
```

### 5.2 分层排查法

| 层 | 工具 | 产出 |
|----|------|------|
| **帧级** | `Performance` 监视器、编辑器 Profiler | 「瓶颈在 CPU 还是 GPU」 |
| **pass 级** | 编辑器 Visual Profiler | 「瓶颈在阴影 / 不透明 / 透明 / 后处理」 |
| **draw call 级** | RenderDoc | 「这个物体为什么被画了、状态对不对」 |
| **shader 级** | Nsight Graphics / RenderDoc 反汇编 | 「这段 shader 指令是不是太重」 |
| **API 级** | apitrace / 验证层 | 「有没有用错 API / 资源泄漏」 |

> 📌 **从粗到细**是排查的基本纪律：先花 30 秒用 `Performance` 分流，
> 再花 5 分钟看 Visual Profiler 定位到 pass，
> 最后才上 RenderDoc 抓帧。反过来做，效率差十倍。

### 5.3 记录与复现

每次排查都留一份「最小复现记录」：

```text
【现象】室内场景，帧率 45（目标 60）
【环境】Godot 4.3.stable，Forward+，RTX 3060，1920×1080，VSync 关闭
【测量】TIME_PROCESS 4.2 ms；RenderingServer.get_frame_setup_time_cpu() 0.9 ms；
        可见通道绘制调用 312，阴影通道绘制调用 1180
【定位】阴影通道绘制调用是可见通道的 3.8 倍 → 大量小物件在投影
【验证】把远处的小物件 cast_shadow 设为 OFF 后，阴影绘制调用降到 84，帧率回到 59
【结论】问题在阴影 pass，不在主视图
```

> ⚠️ 记录里的每个数字都要带测试条件（模板见第 21 篇 5.2 节），
> 否则下一个人无法判断这条结论在别的机器上还成不成立。

### 5.4 三个走查案例

#### 案例 A：物体在远处「凭空消失」

| 步骤 | 操作 | 观察 |
|------|------|------|
| 1 | `Viewport.debug_draw = Viewport.DEBUG_DRAW_WIREFRAME` | 物体整个不见了（不是变黑） |
| 2 | 检查 `GeometryInstance3D.visibility_range_end` / `_begin` | 距离剔除把它剔掉了 |
| 3 | 改 `visibility_range_fade_mode` 为 `VISIBILITY_RANGE_FADE_SELF` 并给足 margin | 变成淡出而不是硬切 |
| 4 | 若仍异常 → 开 `DEBUG_DRAW_OCCLUDERS` | 遮挡剔除把它剔掉了（需开遮挡剔除开关） |
| 5 | 若仍异常 → 用 RenderDoc 看有没有它的 drawcall | 没有 drawcall = 剔除；有但索引数 0 = 网格问题 |

#### 案例 B：画面比预期暗

| 步骤 | 操作 | 观察 |
|------|------|------|
| 1 | `DEBUG_DRAW_UNSHADED` | albedo 正确 → 问题在光照 |
| 2 | `DEBUG_DRAW_LIGHTING` | 只剩光照贡献，暗得离谱 |
| 3 | 检查光源的 `light_energy` / `light_color` | 能量或颜色不对 |
| 4 | 检查 `Environment` 的 `ambient_light_source` | 环境光没开 |
| 5 | `DEBUG_DRAW_SHADOW_ATLAS` | 阴影把物体全遮住了 |

#### 案例 C：粒子完全不显示

| 步骤 | 操作 | 观察 |
|------|------|------|
| 1 | 看项目设置 `rendering/renderer/rendering_method` | 是 `gl_compatibility` 吗？→ GPU 粒子不可用（见第 20 篇 1.4） |
| 2 | `DEBUG_DRAW_OVERDRAW` | 没有 overdraw → 粒子根本没画 |
| 3 | 检查 `GPUParticles3D.emitting` 与 `amount` | `amount` 为 0 或 `emitting` 为 false |
| 4 | 检查 `draw_pass_1` 与 `draw_passes` | 通道为空或 `draw_passes = 0` |
| 5 | 检查过程材质的 `color` 与 alpha | 全透明也是「看不见」 |

> 📌 三个案例的共同点：**先用最便宜的手段排除「根本没画」**，
> 再考虑「画错了」。跳过这一步直接上 RenderDoc，多半是在抓一个不存在的 bug。

---

## 六、Vulkan 调试层

### 6.1 启用 Vulkan 调试

4.3 **没有** `rendering/vulkan/debug_layers` / `rendering/vulkan/sync_mode` 这类项目设置——`rendering/vulkan/*` 下的设置项在 4.3 命中数为 0。图形 API 验证层走**命令行开关**：

```bash
# 启用图形 API 验证层（检查 API 使用错误、资源泄漏等）
godot --gpu-validation

# 调试构建还可以让引擎在检测到 API 错误时直接中止
godot --gpu-abort

# 同时输出 GPU 帧耗时
godot --gpu-profile
```

> 验证层是**进程级**开关，无法在运行时通过 `ProjectSettings` 打开；它会明显拖慢渲染，只应在排查问题时使用。

### 6.2 调试输出

```
Vulkan Validation Layer:
- 检查 API 使用错误
- 检查资源泄漏
- 检查性能问题
```

> 💡 验证层的输出会指出**具体是哪个资源、哪次调用**出的问题。
> 典型报错形如「对象已被销毁但仍在使用」「同步屏障缺失」——
> 这类问题在画面上可能只是「偶尔黑一帧」，靠肉眼看几乎不可能定位。

### 6.3 验证层常见报错速查

| 报错类型 | 含义 | 常见原因 |
|----------|------|----------|
| 使用已销毁的对象 | 资源生命周期用错了 | 在渲染线程还在用某个已释放的 RID |
| 缺少同步屏障 | CPU 改了数据但 GPU 还没读完就换了 | 动态更新网格 / 纹理时没走 `RenderingServer` 的同步接口 |
| 描述符已分配 | 重复创建同一种描述符 | 频繁创建管线 / 描述符池耗尽 |
| 内存分配失败 | 显存不足 | 贴图太大、缓冲太多、后处理分辨率过高 |
| 命令缓冲区未结束 | 一帧内录制量过大 | 单帧绘制调用过多（回到第 21 篇的合批） |

> 📌 **验证层报错的定位价值极高**：它把「画面偶发不对」变成了「某一行 API 用错了」。
> 但**不要在验证层开着的情况下测性能**——验证层会插入大量检查，
> 帧时间可能膨胀好几倍。

### 6.4 什么时候该开验证层

| 症状 | 建议 |
|------|------|
| 偶发黑屏 / 花屏 | 立刻开 |
| 偶发崩溃（尤其是退出时崩溃） | 开（多半是资源释放顺序问题） |
| 画面在某些角度花掉 | 开（可能是越界读写） |
| 性能问题 | **不要开**（开销太大，改用 Visual Profiler） |
| 内存持续增长 | 开（验证层会报泄漏） |

---

## 七、第二卷总结

### 7.1 已完成内容

✅ 11: Godot 渲染架构概述  
✅ 12: Vulkan 渲染后端  
✅ 13: Godot vs Unity 渲染对比  
✅ 14: 场景渲染流程  
✅ 15: 光照系统  
✅ 16: 材质系统  
✅ 17: GDShader 语言  
✅ 18: 2D 渲染  
✅ 19: 后处理效果  
✅ 20: 粒子渲染  
✅ 21: 性能优化  
✅ 22: 渲染调试工具  

### 7.2 核心知识点

| 主题 | 核心概念 |
|------|---------|
| **架构** | RenderingServer、RenderingDevice、Vulkan |
| **光照** | 光源类型、阴影、SDFGI |
| **材质** | StandardMaterial3D、PBR |
| **Shader** | GDShader、Spatial、CanvasItem |
| **2D** | CanvasItem、MultiMesh（无自动合批） |
| **后处理** | Bloom、DOF、SSAO、Compositor |
| **粒子** | GPU 粒子、发射器 |
| **优化** | DrawCall、LOD、遮挡剔除 |
| **调试** | Profiler、可视化器、验证层 |

### 7.3 一页纸排查手册

```text
┌─ 渲染问题排查 ───────────────────────────────────────────┐
│ 0. 先确认「画的是哪个视口、哪个相机」                    │
│ 1. Performance 监视器 → CPU 忙还是 GPU 忙                │
│ 2. TIME_PROCESS 小 → 瓶颈在渲染线程 / GPU               │
│ 3. 绘制调用、渲染对象数异常 → 场景组织问题（第 21 篇）   │
│ 4. Visual Profiler → 定位到具体 pass                    │
│ 5. DebugDraw 27 项 → 确认「画错了」还是「没画」         │
│ 6. RenderDoc → 逐 draw call 查管线状态                  │
│ 7. apitrace / 验证层 → 怀疑 API 用错时                  │
└──────────────────────────────────────────────────────────┘
```

> 📌 这张表建议**打印出来贴在显示器边上**。
> 排查渲染问题的时间，八成花在「跳过了第 0 步和第 1 步」上。

---

## 核心要点

1. **调试开关有三层**：项目设置、命令行参数、运行时属性；命令行优先级最高，验证层只能启动时开。
2. **`Viewport.DebugDraw` 有 27 项**：从 `DEBUG_DRAW_UNSHADED` 到 `DEBUG_DRAW_CLUSTER_REFLECTION_PROBES`，覆盖几何、阴影、GI、聚簇、运动矢量等；缓冲类可视化基本只在 Forward+ 下有内容。
3. **`DEBUG_DRAW_DISABLE_LOD` 不是「显示 LOD」**，而是「禁用 LOD、全部按最高精度绘制」。
4. **统计三个口径**：`Performance` 监视器（全局）、`Viewport.get_render_info()`（按视口按通道）、`RenderingServer.get_frame_setup_time_cpu()`（CPU 帧准备时间）。
5. **`RenderingServer::get_frame_profile()` 在 4.3 没有导出到脚本**：它只存在于 C++ 层（`servers/rendering_server.h`），`FrameProfileArea` 结构体只有 `name` / `gpu_msec` / `cpu_msec` 三个字段，编辑器的 **Visual Profiler** 是它的主要消费者。
6. **工具分工**：RenderDoc 看「画了什么 / 状态对不对」，apitrace 看「API 调用与资源生命周期」，Nsight Systems 看时间线、Nsight Graphics 看着色器；三者都贵，先用引擎自带的量缩小范围。
7. **排查纪律**：从帧级 → pass 级 → draw call 级 → shader 级 → API 级，**从粗到细**，别一上来就抓帧。
8. **任何结论都要带测试条件**（引擎版本 / 后端 / GPU / 分辨率 / 场景规模 / 采样方式），否则下一轮无法复现。

---

## 🔗 延伸阅读

- **官方文档**: [命令行教程（命令行参数）](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)、[使用 Viewport](https://docs.godotengine.org/en/stable/tutorials/rendering/viewports.html)、[调试与可视化](https://docs.godotengine.org/en/stable/tutorials/editor/debugging.html)
- **类参考**: [Viewport](https://docs.godotengine.org/en/stable/classes/class_viewport.html)、[Performance](https://docs.godotengine.org/en/stable/classes/class_performance.html)、[SceneTree](https://docs.godotengine.org/en/stable/classes/class_scenetree.html)、[RenderingServer](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html)
- **源码位置**: `servers/rendering_server.h`（`get_frame_profile()` / `FrameProfileArea`）、`servers/rendering/renderer_viewport.cpp`、`main/main.cpp`（命令行开关的注册处）
- **第三方工具**: [RenderDoc](https://renderdoc.org/)、[apitrace](https://github.com/apitrace/apitrace)、[NVIDIA Nsight](https://developer.nvidia.com/nsight)

---

## 📋 下一章预告

**第 23 篇：Godot 物理架构概述**

- 物理服务器的职责与线程模型
- PhysicsServer2D / PhysicsServer3D
- 刚体、碰撞体与空间
- Godot 4 的 Jolt / Godot Physics 2D / Godot Physics 3D 三个后端

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 21 篇：渲染性能优化](/articles/21-performance-optimization.md)
**下一篇**: [第 23 篇：Godot 物理架构概述](/articles/23-godot-physics-architecture.md)

---

**第二卷 完**

*如果你觉得文章有帮助，欢迎转发给更多开发者！*
