# 第 13 篇：Godot vs Unity 渲染对比

> **本章导读**：两个引擎的渲染**机制**差异，远比 API 差异更值得先搞清楚——它决定了你从 Unity 迁移过来时哪些思路要整个换掉。
> 本章给出三套渲染机制（Forward+ / Mobile / Compatibility）的逐项差异矩阵、GI 方案全景（LightmapGI / VoxelGI / LightmapProbe / ReflectionProbe / SDFGI / SSIL ↔ Unity 的 Lightmapping / Enlighten / Progressive Lightmapper / Light Probe Group / Adaptive Probe Volumes）、阴影与后处理全景、透明排序与剔除对照，最后收在**迁移清单、风险排序、执行顺序与坑位速查表**上。
> **前置知识**：第 11 篇《Godot 渲染架构概述》、第 12 篇《Vulkan 渲染后端深度解析》。
> **难度**：进阶。

> **摘要**：本文从渲染架构、GI 方案、阴影、后处理、剔除、透明排序六个维度系统对比 Godot 与 Unity 的渲染机制，给出迁移到 Godot 时最容易踩的坑与可执行的切换顺序。

## 一、渲染架构对比

### 1.1 Godot 渲染架构

```
场景节点
    ↓
RenderingServer（抽象层）
    ↓
RenderingDevice（Vulkan/OpenGL）
    ↓
GPU
```

### 1.2 Unity 渲染架构

```
GameObject
    ↓
ScriptableRenderPipeline（SRP）
    ↓
CommandBuffer
    ↓
GPU
```

### 1.3 架构对比表

| 维度 | Godot | Unity |
|------|-------|-------|
| **抽象层** | RenderingServer | SRP |
| **后端** | Vulkan/OpenGL | DX11/12/Metal/Vulkan |
| **2D 渲染** | 原生 2D | 3D 模拟 2D |
| **批处理** | 无通用合批器，靠 MultiMesh / 共享材质 | SRP Batcher / GPU Instancing |

---

> 💡 **结论（1.3 架构对比）**：Godot 把渲染拆成「场景端（主线程）+ `RenderingServer` 常驻服务 + 可选渲染线程」；Unity 把渲染拆成「`ScriptableRenderPipeline` + `CommandBuffer`」。**机制差异**在于 Godot 的 `RenderingServer` 是一个**常驻服务**，Unity 的 SRP 是一段**每帧被调用的脚本**。**可执行建议**：从 Unity 迁到 Godot 时，最需要改掉的是「在渲染回调里改场景」的习惯 —— Godot 的渲染线程拿不到场景树，渲染期只能通过 `RenderingServer` 的接口改状态。

### 1.4 线程模型与帧管线

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 渲染入口 | `RenderingServer`（常驻服务，RID 驱动） | `ScriptableRenderPipeline`（每帧被调用） |
| 渲染线程 | 可选。`rendering/driver/threads/thread_model` = `RENDER_SEPARATE_THREAD` 时开独立渲染线程（`OS::RenderThreadMode`） | 渲染在主线程；另有 "Graphics Jobs" 机制分担部分 GPU 提交工作（**以官方文档为准**） |
| 帧内顺序 | 剔除 → 排序 → 渲染数据 → 提交（主线程 `RendererSceneCull` → 渲染线程 `render_scene()`） | `ScriptableRenderContext` → Pass 队列 → `CommandBuffer` → 提交 |
| 自定义插入点 | `Compositor` + `CompositorEffect`，5 个回调点（不透明前 / 不透明后 / 天空后 / 透明前 / 透明后） | `ScriptableRenderPass` / `RendererFeature`（注入点） |
| 帧耗时口径 | `Performance.TIME_PROCESS` 只算主循环，**不含**渲染线程与 GPU | Profiler 把 Main Thread / 渲染线程 / GPU 分列（**以官方文档为准**） |
| 帧分析入口 | 编辑器 Visual Profiler（数据来自 C++ 层 `RenderingServer::get_frame_profile()`，4.3 未导出为脚本方法） | Window ▸ Analysis ▸ Frame Debugger 与 Profiler |

> 💡 **结论**：两边都是「CPU 提交 + GPU 执行」，但 Godot 多了一层**可独立成线程的渲染服务**。**机制差异**：Godot 的渲染线程与主线程之间用 `CommandQueueMT` 传递 RID 级别的请求；Unity 的 SRP 则是同线程内的 C# 调用。**可执行建议**：在 Godot 里写「渲染线程安全」的代码时，一律用 `RenderingServer.call_on_render_thread()` 包一层，不要直接在主线程上摸 `RenderingDevice`。

### 1.5 渲染后端与图形 API

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 桌面图形 API | Vulkan（主）、Direct3D 12（Windows，`drivers/d3d12/`） | Direct3D 11 / 12、Metal、Vulkan、OpenGL Core |
| macOS | 走 Vulkan 通路；Metal 转译方式**以官方文档为准** | ✅ Metal（Player 支持 iOS / tvOS / macOS） |
| 移动图形 API | Vulkan、OpenGL ES 3 | Vulkan（Android 新建项目默认）、OpenGL ES 3、Metal（iOS） |
| Web | **只有 WebGL 2**（OpenGL ES 3.0），对应 Compatibility 渲染器 | WebGL2（默认）与 **WebGPU**（可选，浏览器 / 设备支持有限） |
| 图形抽象层 | `RenderingDevice` + `RenderingDeviceDriver` | SRP 之下的图形 API 抽象（内部实现） |
| 切换渲染器 / 管线 | `rendering/renderer/rendering_method`（**启动时读取**，改完要重启） | `GraphicsSettings.defaultScriptableRenderPipelineType` / `QualitySettings.renderPipeline` |
| 平台专属后端 | 无（同一套代码跨平台） | 需自行维护平台构建配置与主机授权 |

> 💡 **结论**：**Godot 4.3 没有 WebGPU 后端**，Web 只能走 WebGL 2 / Compatibility；Unity 在 Web 上则可选 WebGPU。**机制差异**：Godot 的 Web 平台被 Compatibility 渲染器（OpenGL ES 3.0）锁定，而 Unity 的 WebGPU 仍属实验性、浏览器支持有限。**可执行建议**：项目要上 Web，先确认自己**不需要** compute shader、间接绘制这类 WebGPU 独有能力 —— Godot 4.3 给不了。

### 1.6 资源生命周期与所有权模型

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 渲染资源句柄 | **RID** —— `RenderingServer` 托管的整数句柄，脚本看不到内部结构 | 原生资源对象（`Texture2D` / `Material` / `Mesh`） |
| 谁创建 | 场景节点在 `_enter_tree` 时自动创建；手动创建走 `RenderingServer` 的 `*_create()` 系列方法 | 导入器在构建期生成，运行时由资源系统加载 |
| 谁释放 | 节点销毁时释放其持有的 RID；手动创建的必须显式 `RenderingServer.free_rid()` | 资源管理器按引用计数回收，场景卸载时批量卸载 |
| 引用语义 | RID **不共享所有权**，谁创建谁负责释放 | 资源对象是共享引用计数语义 |
| 跨线程使用 | RID 可跨线程"使用"，但创建/释放必须走主线程 | 资源对象的读写受 Unity 主线程规则约束 |

> 💡 **结论**：Godot 的渲染资源走的是"**显式句柄 + 显式释放**"，Unity 走的是"**共享对象 + 引用计数**"。**机制差异**：在 Godot 里用 `RenderingServer` 手动建资源，忘记 `free_rid()` 就是泄漏；在 Unity 里这一般不会发生。**可执行建议**：从 Unity 迁过来后，只要写了 `RenderingServer` 的 `*_create()` 系列方法，就一定要在同一个文件里写出对应的 `free_rid()`，否则会在长时间运行后看到显存持续上涨。

### 1.7 渲染扩展点对照

| 扩展点 | Godot 4.3 | Unity（以官方文档为准） |
|--------|-----------|------------------------|
| 自定义后处理 | `Compositor` + `CompositorEffect`，5 个注入点（不透明前 / 不透明后 / 天空后 / 透明前 / 透明后） | `ScriptableRenderPass` / `RendererFeature` |
| 自定义计算 | `RenderingDevice` + `shader_type compute` | Compute Shader（独立资产类型） |
| 自定义整套管线 | ❌ 基本不可行 —— 三种渲染器都是引擎内建实现 | ✅ 自定义 SRP（整个渲染流程可重写） |
| 着色器回调 | `.gdshader` 的 `vertex()` / `fragment()` / `light()` | ShaderLab 的 `SubShader` / `Pass` 内的 `vert` / `frag` |
| 引擎光照接入 | 写 `ALBEDO` / `ROUGHNESS` 等内置变量，引擎负责打光 | 需显式引用 Lighting 库，或使用 Shader Graph 的 Lit Target |
| 渲染期回调 | `RenderingServer.call_on_render_thread()` | `ScriptableRenderContext` |
| 渲染线程安全 | 有专门的线程模型（见第 11 篇 §8） | 渲染线程由引擎管理，扩展点在线程内回调 |

> 💡 **结论**：Unity 的扩展点是"**往管线里插东西**"，Godot 的扩展点是"**在既定管线的固定位置挂回调**"。**机制差异**：Unity 可以整个替换渲染流程，Godot 不能。**可执行建议**：如果你的项目重度依赖自定义延迟渲染或自研后处理链，迁到 Godot 前要先确认这部分的替代方案（Godot 侧只能用 `CompositorEffect` 做"插在既有流程里"的定制）。

---

### 1.8 场景树与渲染节点的对应关系

| 概念 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 场景根 | `Node3D`（`Node` → `Node3D` 继承链） | `GameObject` + `Transform` |
| 几何实例 | `MeshInstance3D`（`mesh` / `material_override` / `material_overlay` / `cast_shadow`） | `MeshFilter` + `MeshRenderer` |
| 灯光 | `DirectionalLight3D` / `OmniLight3D` / `SpotLight3D` | `Light` 组件 |
| 相机 | `Camera3D`（`fov` / `near` / `far` / `cull_mask` / `attributes`） | `Camera` 组件 |
| 环境 | `WorldEnvironment` + `Environment` + `Sky` | 场景光照设置（以官方文档为准） |
| 反射探针 | `ReflectionProbe` | `Reflection Probe` 组件 |
| 贴花 | `Decal` | Decal Projector（以官方文档为准） |
| 体积雾区域 | `FogVolume` | 体积雾设置（以官方文档为准） |
| 批处理 | 无（见 3.7 与第 21 篇） | MaterialPropertyBlock / SRP Batcher |

> 💡 **结论**：两边的**节点 ↔ 组件**映射几乎是 1:1，迁移时几乎不需要重新设计场景组织。**机制差异**：Godot 把"环境"做成了**场景里的一个节点**（`WorldEnvironment`），Unity 把光照设置做成了**资产**（Lighting Settings）。**可执行建议**：Godot 侧的 `WorldEnvironment` 是全局唯一的那一个；需要"局部换环境"时，只能按相机指定 `Environment` 或切换 `WorldEnvironment` 的资源 —— 这点在规划场景结构时就要想清楚。

### 1.9 相机与视口

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 相机节点 | `Camera3D` | `Camera` 组件 |
| 视口 | `Viewport`（根视口 + 子视口） | Camera 的 Render Texture / Display |
| 视锥剔除掩码 | `Camera3D.cull_mask` | `Camera.cullingMask` |
| 投影 | `Camera3D.projection`（透视 / 正交） | 相机投影模式（以官方文档为准） |
| 景深与自动曝光 | `Camera3D.attributes` → `CameraAttributesPractical` | Volume 覆盖（以官方文档为准） |
| 相机专属后处理 | `Camera3D.compositor`（挂 `Compositor` 资源） | 相机上的 Volume（以官方文档为准） |
| 相机专属环境 | `Camera3D.environment` | 以官方文档为准 |
| 渲染目标 | `Viewport` + `SubViewport` | Render Texture |
| 抗锯齿 | `Viewport.msaa_3d` / `screen_space_aa` / `use_taa` | 以官方文档为准 |
| 动态分辨率 | `Viewport.scaling_3d_mode` / `scaling_3d_scale` | Render Scale / Dynamic Resolution |

> 💡 **结论**：Godot 把"相机属性"和"渲染目标"**拆成了两个节点**（`Camera3D` 与 `Viewport`），Unity 把它们合在 Camera 组件与 Render Texture 上。**机制差异**：Godot 里一个 `SubViewport` 可以放多台相机并各自指定 `Camera3D`，这是做小地图、监控画面、离屏合成的标准做法。**可执行建议**：从 Unity 迁过来时，把所有"摄像机 + Render Texture"的组合，改写成"一个 `SubViewport` + 一台 `Camera3D`"，顺手就拿到了引擎内建的离屏渲染能力。

---

### 1.10 渲染 API 的暴露面

| 层次 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 日常材质与贴图 | `StandardMaterial3D` / `BaseMaterial3D` | Material / Shader Graph |
| 场景级渲染节点 | `MeshInstance3D` / `Decal` / `ReflectionProbe` | 组件（MeshRenderer / Decal / Reflection Probe） |
| 低层渲染服务 | `RenderingServer`（RID 级调用） | Graphics 类 / CommandBuffer（以官方文档为准） |
| 图形 API 抽象 | `RenderingDevice` | 引擎内建（以官方文档为准） |
| 自定义 2D 绘制 | 覆写 `_draw()`（`CanvasItem`） | OnGUI / UI Toolkit（以官方文档为准） |
| 渲染期回调 | `RenderingServer.call_on_render_thread()` | `ScriptableRenderContext` |
| 资源所有权 | 调用方负责 `free_rid()` | 引用计数自动回收 |

> 💡 **结论**：Godot 把渲染 API 分成了**四层**（节点 → `RenderingServer` → `RenderingDevice` → 驱动），Unity 则把大部分能力收在组件与 Graphics API 里。**机制差异**：Godot 的 `RenderingServer` 是**常驻服务**，任何线程都能调用，代价是所有调用都是"投递命令"；Unity 的渲染 API 调用通常要求在主线程。**可执行建议**：写 Godot 侧的自定义渲染代码时，先问自己"这是节点级、服务器级还是 RD 级" —— 选错层级的典型症状是"明明不需要 GPU 能力却写了一段 compute"。

---

### 1.11 本卷术语对照表

| Godot 4.3 术语 | Unity 对应术语 | 说明 |
|----------------|----------------|------|
| 渲染服务器 | Scriptable Render Pipeline | Godot 是常驻服务，Unity 是每帧被调用的脚本 |
| 渲染器 / 渲染方法 | Render Path / Pipeline Asset | Godot 按平台能力切，Unity 按画质档位切 |
| 场景剔除 | Culling | 概念一致，实现不同 |
| 视锥剔除 | Frustum Culling | 概念一致 |
| 遮挡剔除 | Occlusion Culling | Godot 4.3 基于 Embree |
| 簇 | Cluster | Godot 侧只在 Forward+ 存在 |
| 簇构建器 | — | Unity 侧无直接对应物 |
| 逐对象光照 | Forward（per-object） | Godot 的 Mobile / Compatibility 走这条 |
| 阴影图集 | Shadow Atlas / Per-light shadow map | Godot 把所有阴影图塞进一张图集 |
| 可见性范围 | LOD / Distance Culling | 概念相近，组织方式不同 |
| 环境资源 | Lighting Settings + Volume | Godot 合并在一个 `Environment` 里 |
| 光照贴图 | Lightmap | 流程相近，资产格式不同 |
| 体素 GI | — | 由 Enlighten / 探针体积覆盖 |
| 符号距离场 GI | Realtime GI (Enlighten) | 机制完全不同 |
| 屏幕空间间接光 | — | Unity 侧无独立等价物 |
| 反射探针 | Reflection Probe | 基本对应 |
| 合成器 / 合成器效果 | Scriptable Render Pass / Renderer Feature | 注入点数量与语义不同 |
| 渲染设备 | —（SRP 内部） | Godot 把它暴露成了脚本 API |
| 存储缓冲 | ComputeBuffer / GraphicsBuffer | 概念一致，绑定方式不同 |
| 绘制调用 | Draw Call / SetPass | Unity 额外区分 SRP Batcher 的 state 变更 |
| 渲染线程 | Render Thread | Godot 用 `OS::RenderThreadMode` 控制是否真的开线程 |

> 💡 **结论**：这张表读下来会发现一个规律 —— **两边"同名不同义"的地方集中在管线组织层，"同义不同名"的地方集中在特性层**。**机制差异**：迁移时最容易出错的不是特性名对不上，而是"渲染器 / 管线"这个词在两边指的不是一个东西。**可执行建议**：读 Unity 文档时，把 "Render Pipeline" 一律理解成"**一套资产**"；读 Godot 文档时，把 "渲染器" 一律理解成"**一个平台档位**"。

## 二、渲染管线对比

### 2.1 Godot 渲染管线

| 管线 | 说明 | 平台 |
|------|------|------|
| **Forward+** | 完整特性 | PC |
| **Mobile** | 移动优化 | 移动 |
| **Compatibility** | 兼容性最好 | 旧设备/Web |

### 2.2 Unity 渲染管线

| 管线 | 说明 | 平台 |
|------|------|------|
| **URP** | 通用管线 | 全平台 |
| **HDRP** | 高清管线 | PC/主机 |
| **Built-in** | 传统管线（已废弃） | 全平台 |

---

> 💡 **结论（2.1 / 2.2 管线对比）**：Godot 的「三种渲染器」是**三套并列实现**，Unity 的「URP / HDRP / Built-in」是**三个产品化的管线资产**。**机制差异**：Godot 换渲染器只换一个项目设置，材质与场景不用动；Unity 换管线要换渲染管线资产并连带处理材质 shader。**可执行建议**：如果你在 Unity 里同时维护 URP 与 HDRP 两套资产，迁到 Godot 后这部分维护成本会**直接消失** —— 这是 Godot 相对 Unity 最实在的一处优势。

### 2.3 Shader 编写方式

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 着色语言 | 自研 `.gdshader`（`shader_type spatial / canvas_item / particles / compute`） | ShaderLab（HLSL / LSL）+ Shader Graph 节点编辑器 |
| 与材质的关系 | `.gdshader` 配 `ShaderMaterial`；`StandardMaterial3D` 是引擎内建实现 | ShaderLab 本身就是 Material 的序列化格式；Shader Graph 生成 ShaderLab |
| 顶点 / 片元入口 | `vertex()` / `fragment()`（可只写其中一个） | `vert` / `frag`（写在 `SubShader` 的 `Pass` 里） |
| 接入引擎光照 | 写 `light()`，通过 `ALBEDO` / `ROUGHNESS` 等内置变量参与引擎光照 | 需显式引用 Lighting 库函数，或使用 Shader Graph 的 Lit Target |
| 变体策略 | 按 `render_mode` 与条件编译 shader 变体 | 按 keyword / multi-compile 生成变体；SRP Batcher 要求**尽量少的变体** |
| 跨引擎迁移 | 不兼容 | 不兼容 |

> 💡 **结论**：`.gdshader` 与 ShaderLab **语法与生态都不通用**，迁移必须重写。**机制差异**：Godot 的内置光照是「把 `ALBEDO` 等变量写进全局结构体，引擎负责打光」；Unity 需要在 ShaderLab 里自己引用光照库，或用 Shader Graph。**可执行建议**：迁移时按「目标引擎重写」处理，不要试图做语法级转换；Godot 侧可用 Shader Graph 风格的第三方工具降低美术的学习成本。

### 2.4 材质与渲染管线资产

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 通用材质 | `StandardMaterial3D`（PBR 参数化） | `Material`（引用某个 Shader / Shader Graph） |
| 材质与管线的绑定 | 材质**不绑定**渲染管线，同一份材质在三种渲染器下都能用 | `Material` **必须**引用 URP 或 HDRP 的 Shader，换管线要批量换 Shader |
| 覆盖 / 叠加 | `material_override` / `material_overlay` | Renderer 的 Material / Material Override 槽位 |
| 后处理资产 | `Environment`（后处理开关）+ `Compositor`（自定义 pass） | `Volume`（后处理）+ `RendererFeature`（自定义 pass） |
| 材质数量的代价 | 共享同一材质资源即可复用 uniform set | SRP Batcher 关心的是「同一 shader 变体」，材质多不致命，**变体多才致命** |

> 💡 **结论**：**Unity 的材质资产与渲染管线强绑定，Godot 的不绑定**。**机制差异**：Unity 的 `Material` 里存的是 shader 引用，换 URP ↔ HDRP 要重做资产；Godot 的 `StandardMaterial3D` 只是引擎内建的 PBR 描述，由渲染器自己去解释。**可执行建议**：从 Unity 迁移时，先把「材质 → 管线」的隐式依赖拆掉（统一 shader 家族），否则后期换管线的成本远高于重写材质。

### 2.5 渲染路径与特性支持总矩阵

| 能力 | Godot Forward+ | Godot Mobile | Godot Compatibility | Unity URP | Unity HDRP | Unity Built-in |
|------|----------------|---------------|---------------------|-----------|-----------|----------------|
| 光照剔除方式 | 簇分配 | 逐对象 | 逐对象 | 可选前向加簇 | 前向加簇 | 传统前向 |
| 计算着色器 | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| 自定义后处理 | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| GPU 粒子 | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| 烘焙 GI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 实时 GI | SDFGI | ❌ | ❌ | Enlighten / 探针体积 | Enlighten | Enlighten |
| 屏幕空间反射 | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| 屏幕空间间接光 | ✅ | ❌ | ❌ | 部分支持 | 部分支持 | ❌ |
| 体积雾 | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| 阴影贴图 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 阴影贴图格式 | PCF / PCSS（`light_size`） | PCF / PCSS（`light_size`） | PCF | 以官方文档为准 | 以官方文档为准 | 以官方文档为准 |
| 定向光级联 | 4.3 最多 4 级 | 4.3 最多 4 级 | 4.3 最多 4 级 | 1 ~ 4 级 | 1 ~ 4 级 | 以官方文档为准 |
| 运行时合批器 | ❌ | ❌ | ❌ | ✅ SRP Batcher | ✅ SRP Batcher | ❌ |
| 目标平台 | 桌面 / 主机 | 移动 / 中端桌面 | Web / 老旧设备 | 全平台 | 桌面 / 主机 | 全平台 |

> 💡 **结论**：Godot 的三个渲染器在"能力集合"上的关系，近似于 Unity 的 URP / HDRP / Built-in 三分，但**切分维度不同** —— Godot 按**平台能力**切，Unity 按**画质档位**切。**机制差异**：Unity 换管线是换资产（材质要重做），Godot 换渲染器是换一个项目设置（材质不动）。**可执行建议**：如果你的项目只在桌面与移动之间选，Godot 侧切渲染器几乎零成本；如果要同时覆盖 Web，Godot 侧要接受"回到 Compatibility 后端 + 砍掉一批特效"。

### 2.6 Shader 变体与批处理策略

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 变体来源 | `render_mode` + 条件编译 | keyword / multi-compile |
| 变体爆炸的代价 | 着色器编译变慢、启动变慢 | 同上；且**变体多会让 SRP Batcher 失效** |
| 批优化主思路 | 共享材质 + `MultiMesh` + 排序键（`sort_key1` / `sort_key2`） | SRP Batcher（减少 state 变更）/ GPU Instancing（减少 draw call） |
| 单个材质参数更新 | `ShaderMaterial.set_shader_parameter()` | Material 的 Setter 系列 |
| 材质数量多的代价 | 共享同一材质资源即可复用 uniform set | 材质多不致命，**变体多才致命** |
| 常量缓冲 | 引擎内建 UBO 布局由 `BaseMaterial3D` 决定 | 以官方文档为准 |

> 💡 **结论**：两边在"变体爆炸"这件事上的教训完全一致 —— **变体比材质更致命**。**机制差异**：Unity 的 SRP Batcher 会因为变体分叉而整块失效，Godot 没有 SRP Batcher 这种"整块失效"的概念，代价体现为编译时间与运行期的 uniform set 重复。**可执行建议**：迁移时先统计 Unity 项目的 shader keyword 数量，逐个对应到 Godot 的 `render_mode`；如果发现某个材质靠大量 keyword 组合出不同效果，在 Godot 侧通常应该拆成多个材质或多个 `ShaderMaterial` 实例。

---

### 2.7 天空、大气与雾

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 天空资源 | `Sky` + `ProceduralSkyMaterial` / `PanoramaSkyMaterial` | Skybox 材质（以官方文档为准） |
| 程序化天空参数 | `ProceduralSkyMaterial`（太阳角度、能量、天空覆盖等） | 以官方文档为准 |
| 全景天空 | `PanoramaSkyMaterial` | 以官方文档为准 |
| 环境光来源 | `Environment.ambient_light_source` | 以官方文档为准 |
| 环境反射来源 | `Environment.reflected_light_source` | 以官方文档为准 |
| 背景模式 | `Environment.background_mode` | 以官方文档为准 |
| 深度雾 | `Environment.fog_enabled` / `fog_mode` / `fog_density` / `fog_light_color` | 以官方文档为准 |
| 体积雾 | `Environment.volumetric_fog_enabled` / `volumetric_fog_density` / `volumetric_fog_length`（Forward+ 专属） | URP / HDRP 的 Volume 雾 |
| 局部雾区 | `FogVolume` 节点 | 以官方文档为准 |
| 雾对平行光的影响 | `Environment.fog_sun_scatter` | 以官方文档为准 |

> 💡 **结论**：Godot 把**天空、环境光、雾**全部收进一个 `Environment` 资源，Unity 则分散在 Skybox、Lighting Settings 与 Volume 三处。**机制差异**：Godot 侧改一个 `Environment` 资源就能整体换掉"天空 + 环境光 + 雾 + 后处理"，这在 Unity 里通常要同时动三套资产。**可执行建议**：迁移时把 Unity 的 Lighting Settings、Volume Profile、Skybox Material 三份资产**合并映射到一个 `Environment` 资源**（加上一个 `Sky` 资源），这会让后续调参成本明显下降。

---

### 2.8 切换渲染器 / 管线的运行时行为

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 切换时机 | **启动时**读 `rendering/renderer/rendering_method` | 构建 / 平台设置里选管线资产 |
| 平台覆盖项 | `rendering/renderer/rendering_method.mobile` / `rendering/renderer/rendering_method.web` | 平台构建配置 |
| 运行时切换 | ❌ 不支持（改设置也要重启进程） | ❌ 不支持（需重启） |
| 对材质的影响 | 无 —— 材质不绑定渲染器 | 需要换 shader 家族 |
| 对场景的影响 | 无 | 无 |
| 对后处理的影响 | RD 专属开关会被**静默忽略** | 换管线资产后效果按新管线重算 |

> 💡 **结论**：Godot 的"换渲染器"是一个**项目设置**（可按平台覆盖），Unity 的"换管线"是**换资产**（要连带处理材质与后处理）。**机制差异**：Godot 侧最容易踩的坑是**静默失效** —— `Environment` 上的 `sdfgi_enabled` / `ssr_enabled` / `ssil_enabled` / `volumetric_fog_enabled` 在 Compatibility 下不报错、也不生效。**可执行建议**：项目里如果依赖这些效果，在启动时按 `rendering/renderer/rendering_method` 做一次检查并给出提示（代码见第 11 篇 §9.7）。

---

## 三、特性对比

### 3.1 光照系统

| 特性 | Godot | Unity |
|------|-------|-------|
| **实时光照** | ✅ | ✅ |
| **烘焙光照** | ✅ | ✅ |
| **烘焙 GI** | LightmapGI / VoxelGI | Enlighten / Bakery |
| **动态 GI** | SDFGI（Forward+ 专属） | Enlighten 动态模式 |
| **光照探针** | LightmapProbe / ReflectionProbe | LightProbe / ReflectionProbe |

> Godot 4.3 注册了五个 GI 相关类：`VoxelGI` / `VoxelGIData`（动态烘焙 GI）、`LightmapGI` / `LightmapGIData`（光照贴图烘焙）、`LightmapProbe`（探针），加上 `Environment.sdfgi_enabled` 控制的 SDFGI（实时符号距离场 GI，仅 Forward+ 支持）。它们不是同一个东西，不能笼统地统称"SDFGI"。

### 3.2 阴影

| 特性 | Godot | Unity |
|------|-------|-------|
| **实时阴影** | ✅ | ✅ |
| **级联阴影** | ✅（PSSM 平行级联） | ✅ |
| **软阴影** | ✅（PCF / PCSS） | ✅ |
| **接触阴影** | ❌ 4.7.2 无此特性 | ✅ |

### 3.3 后处理

| 特性 | Godot | Unity |
|------|-------|-------|
| **Bloom** | ✅ | ✅ |
| **DOF** | ✅ | ✅ |
| **SSAO** | ✅ | ✅ |
| **色调映射** | ✅ | ✅ |

---

> 💡 **结论（3.1 – 3.3 特性对比）**：两边的「实时光照 / 烘焙光照 / 后处理开关」清单高度重合，差别主要在**实现粒度**而不是**功能有无**。**机制差异**：Godot 把 GI 拆成贴图 / 体素 / 探针 / SDFGI 四类独立资源；Unity 把烘焙、实时、探针打包成不同的产品概念。**可执行建议**：评估迁移成本时，不要按「特性有没有」列清单，要按「**这个特性在我的场景里由哪个资源承担**」逐项对照。

### 3.4 GI 与烘焙工作流

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 烘焙 GI | `LightmapGI` + `LightmapGIData`（编辑器内烘焙光照贴图） | Lightmapping / Baked GI。后端可选：Unity Compute Light Baker（**仅 URP / HDRP 可用**）、Progressive GPU Lightmapper（依赖 OpenCL）、Progressive CPU Lightmapper（**已废弃**） |
| 动态 GI | `SDFGI`（符号距离场，Forward+ 专属，实时） | Enlighten Realtime Global Illumination（中间件方案） |
| 探针 | `LightmapProbe`（**手工**放置的球形探针） | Light Probe Group；**Adaptive Probe Volumes（APV）**：按场景几何密度**自动**放置、**逐像素**采样、支持流式加载 |
| 体素烘焙 | `VoxelGI` / `VoxelGIData`（运行时烘焙的体素 GI） | 无直接对应（由 Enlighten / APV 覆盖） |
| 反射探针 | `ReflectionProbe` | Reflection Probe |
| 烘焙入口 | 编辑器内的 LightmapGI / VoxelGI 面板 | Lighting Settings Asset + Lightmap Editor |

> 💡 **结论**：Godot 的 GI 家族是「**贴图 / 体素 / 探针 / SDFGI 四件套**」，Unity 是「**烘焙 / Enlighten / 探针组 / APV**」。**机制差异**：Unity 的 APV 会**自动**按几何密度布点并逐像素采样，Godot 的 `LightmapProbe` 需要手工摆放。**可执行建议**：Unity 侧重度依赖 APV 的项目迁到 Godot 时，必须重新设计探针分布 —— Godot 4.3 没有「自动按密度摆探针」的等价物。

### 3.5 阴影实现

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 平行光阴影 | **PSSM**（平行分割级联）：`DirectionalLight3D.ShadowMode` = `ORTHOGONAL` / `PARALLEL_2_SPLITS` / `PARALLEL_4_SPLITS` | Cascaded Shadow Maps（CSM），级联数 1 ~ 4 |
| 解决的问题 | 同样是「近处阴影像素化」（透视走样），靠**分割视锥 + 多张 shadow map** 解决 | 同样解决 perspective aliasing |
| 作用范围 | **只对平行光有效** | **只对平行光有效**（shadow cascades only work with directional lights） |
| 阴影贴图管理 | Shadow Atlas：多张阴影图打进一张图集 | 按灯 / 按级联分开管理 |
| 软阴影 | PCF 多重采样 + `light_size` / `light_angular_distance` 控制的 PCSS | 软阴影方案**以官方文档为准** |
| 方差阴影（VSM） | ❌ 4.7.2 无 | 以官方文档为准 |
| 接触阴影 | ❌ 4.7.2 无此特性 | ✅ |

> 💡 **结论**：两边的平行光阴影思路几乎一样（**级联分割 + 多张贴图**），只是 Godot 叫 PSSM、Unity 叫 CSM。**机制差异**：Godot 把所有阴影图塞进一张 **Shadow Atlas**，Unity 按灯分张。**可执行建议**：Godot 里要注意 Shadow Atlas 的容量 —— 灯多或阴影图太大时可能装不下，具体表现与排查方式以引擎日志为准；Unity 迁过来时如果场景灯很多，先核对 atlas 尺寸。

### 3.6 后处理栈与自定义管线

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 内建后处理开关 | `Environment` 上的 `glow_enabled` / `ssao_enabled` / `ssil_enabled` / `ssr_enabled` / `sdfgi_enabled` / `volumetric_fog_enabled` / `fog_enabled` / `adjustment_enabled` / `tonemap_mode` | `Volume` 组件 + 后处理 Profile（效果栈由 Volume 驱动） |
| 景深 | `CameraAttributesPractical` 的 dof 参数 | URP 的 Depth of Field Volume override |
| 自定义 pass | `Compositor` + `CompositorEffect`（`compositor_effects` 数组），5 个回调点 | `ScriptableRenderPass` / `RendererFeature`（如 Full Screen Pass Renderer Feature，注入点为 Before Rendering Transparents / Before Rendering Post Processing / After Rendering Post Processing） |
| 色彩管线 | HDR → 色调映射（`Environment.tonemap_mode`）→ 输出 | HDR → Volume 后处理 → 输出；色调映射在管线资产里配置 |

> 💡 **结论**：Godot 的后处理是「**一个 `Environment` 资源上的开关集合**」，Unity 的后处理是「**Volume 组件驱动的效果栈**」。**机制差异**：Unity 的 Volume 可以按相机 / 按区域叠加不同的效果覆盖；Godot 的 `Environment` 通常是全局的，或按 `Camera` 指定。**可执行建议**：需要「走进一个房间就换一套后处理」的玩法，Godot 侧要靠 `WorldEnvironment` + 相机切换，或用 `CompositorEffect` 自己实现 —— 不要假设效果可以自由叠加。

### 3.7 批量绘制手段

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 运行时合批器 | ❌ **没有**通用合批器（Godot 3.x 的 batcher 已移除） | ✅ **SRP Batcher**（URP / HDRP / 自定义 SRP 支持；Built-in 不支持） |
| 实例化 | `MultiMesh` / `MultiMeshInstance3D`（同网格 N 实例 → 1 次实例化绘制） | ✅ **GPU Instancing**（同 mesh + 同 material → 单次绘制；URP / HDRP 下官方推荐优先用 SRP Batcher） |
| 静态合批 | 手动用 `SurfaceTool` / `ArrayMesh` 在离线阶段合并 | ✅ Static Batching（构建期或运行时） |
| 状态切换优化 | 排序按材质键（`sort_key1` / `sort_key2`），让相邻表面复用同一 uniform set | SRP Batcher 把 `bind` + `draw` 合并成一个 SRP batch，减少 render state 变更 |
| 大规模实例 | `MultiMesh` + `visibility_range` + LOD | BatchRendererGroup（更底层的大规模实例化方案） |

> 💡 **结论**：**Unity 有两种「合批」思路，Godot 4 一种都没有**，Godot 只提供「你自己合」（MultiMesh / 离线合面）。**机制差异**：Unity 的 SRP Batcher 优化的是 **CPU 端的 render state 变更**（不是 draw call 数量），GPU Instancing 优化的是 **draw call 数量**；Godot 的 MultiMesh 对应后者，前者没有对应物。**可执行建议**：从 Unity 迁过来时，凡是靠 SRP Batcher 撑住的场景都要重做 draw call 预算 —— 用「MultiMesh + 共享材质 + `visibility_range`」三件套替代。

### 3.8 机制差异矩阵

本节是本卷补写清单 #3 的落点：把三种渲染器的**机制**逐项摊开，再逐项映射到 Unity 的对应物。

#### 3.8.1 Godot 三渲染器的机制差异

| 机制 | Forward+ | Mobile | Compatibility |
|------|----------|--------|---------------|
| 图形 API | Vulkan / D3D12 / Metal | Vulkan / D3D12 / Metal | OpenGL 3.3 / GLES 3.0 / WebGL 2 |
| 图形抽象层 | `RenderingDevice` | `RenderingDevice` | 直连 OpenGL，**无 RD** |
| 光照剔除 | **簇分配**（3D 网格） | **逐对象** | **逐对象** |
| 单物体光源上限 | 无硬上限（按簇取） | 8（`MAX_RDL_CULL`） | 8（`rendering/limits/opengl/max_lights_per_object`） |
| 深度预通道 | ✅ | ❌ | ❌ |
| 阴影贴图管理 | Shadow Atlas | Shadow Atlas | Shadow Atlas |
| 定向光级联 | `SHADOW_PARALLEL_2_SPLITS` / `SHADOW_PARALLEL_4_SPLITS` | 同左 | 同左 |
| 软阴影 | PCF + `light_size` 控制的 PCSS | 同左 | 同左 |
| 环境光遮蔽 | `Environment.ssao_enabled` | ❌ | ✅ 4.7.2 提供（4.3 时没有） |
| 屏幕空间间接光 | `Environment.ssil_enabled` | ❌ | ❌ |
| 屏幕空间反射 | `Environment.ssr_enabled` | ❌ | ❌ |
| 符号距离场 GI | `Environment.sdfgi_enabled` | ❌ | ❌ |
| 体积雾 | `Environment.volumetric_fog_enabled` | ❌ | ❌ |
| 泛光 | `Environment.glow_enabled` | ✅ | ✅ |
| 色调映射 | `Environment.tonemap_mode` / `tonemap_exposure` | 同左 | 同左 |
| 深度雾 / 高度雾 | `Environment.fog_enabled` | ✅ | ✅ |
| 烘焙光照贴图 | `LightmapGI` | ✅ | ✅ |
| 体素 GI | `VoxelGI` | ✅ | ✅ |
| 探针 | `LightmapProbe` / `ReflectionProbe` | ✅ | ✅ |
| Compute shader | ✅ | ✅ | ❌ |
| 存储缓冲 / UBO 自定义 | ✅ | ✅ | ❌ |
| 自定义后处理注入 | `CompositorEffect`（5 个注入点） | 同左 | ❌ |
| GPU 粒子 | ✅ | ✅ | ❌（回退 CPU 粒子） |
| 遮挡剔除 | ✅（基于 Embree） | ✅ | ✅ |

> ⚠️ 表中"支持"指 **4.7.2 引擎自身提供了该特性的实现**；个别特性（尤其是屏幕空间效果）的 Compatibility 支持状态在不同 4.x 小版本间有变化，上线前请以目标版本源码与目标平台实测为准。

#### 3.8.2 机制 → Unity 对应物

| Godot 机制 | Godot 侧入口 | Unity 对应物 | 差异要点 |
|------------|--------------|--------------|----------|
| 簇分配光照 | `renderer_rd/forward_clustered/` + `cluster_builder_rd.h` | URP / HDRP 的 Forward+ 模式 | 思路一致（空间分桶），但 Unity 的分桶参数在管线资产里，Godot 侧是引擎内建 |
| 逐对象光照 | `renderer_rd/forward_mobile/` | Unity Built-in 的前向着色 | Godot 的 Mobile 仍有 8 盏的硬上限 |
| 深度预通道 | `Render Depth Pre-Pass` 时间戳（见第 14 篇） | 深度 / 不透明预通道 | Godot 的 Mobile 与 Compatibility 均无 |
| Shadow Atlas | `directional_shadow_atlas_set_size()` 等 | 按灯 / 按级联分张 | Godot 把所有阴影图塞进图集，容量有限 |
| SSAO | `Environment.ssao_enabled` 等 | URP / HDRP 的 SSAO 效果 | Godot 挂在 `Environment` 上，不在管线上 |
| SSIL | `Environment.ssil_enabled` 等 | 无独立等价物 | Unity 侧最接近的是 Progressive Lightmapper 的屏幕空间部分 |
| SSR | `Environment.ssr_enabled` 等 | URP / HDRP 的 Screen Space Reflections | Godot 的 SSR 不可用时没有回退 |
| SDFGI | `Environment.sdfgi_enabled` 等 | Enlighten（动态 GI） | 机制完全不同：SDFGI 用符号距离场，Enlighten 是中间件方案 |
| 体积雾 | `Environment.volumetric_fog_enabled` 等 | URP / HDRP 的 Volume 雾 | Godot 的体积雾是 Forward+ 专属 |
| 泛光 | `Environment.glow_enabled` 等 | URP / HDRP 的 Bloom | Godot 额外提供 HDR 阈值与强度分离（`glow_hdr_threshold` / `glow_intensity`） |
| 色调映射 | `Environment.tonemap_mode` | 管线资产里的 Tone Mapping | Godot 挂在 `Environment` 上 |
| 后处理注入 | `Compositor` + `CompositorEffect` | `ScriptableRenderPass` / `RendererFeature` | Godot 固定 5 个注入点，Unity 可自定义插入位置 |
| 烘焙 GI | `LightmapGI` + `LightmapGIData` | Lightmapping（Lightmap 资产） | 流程相近，编辑器面板不同 |
| 体素 GI | `VoxelGI` + `VoxelGIData` | 无直接对应 | 由 Enlighten / 探针体积覆盖 |
| 探针 | `LightmapProbe` | Light Probe Group / Adaptive Probe Volumes | Godot 的探针需手工布置（或用 `LightmapGI.generate_probes_subdiv` 自动生成） |
| 反射探针 | `ReflectionProbe` | Reflection Probe | 基本对应 |
| GPU 粒子 | `GPUParticles3D` / `GPUParticles2D` | Particle System | Godot 的 GPU 粒子依赖 compute，Compatibility 下不可用 |
| 实例化 | `MultiMesh` / `MultiMeshInstance3D` | GPU Instancing / DrawMeshInstanced | 目标相同（减少 draw call） |
| 遮挡剔除 | `rendering/occlusion_culling/use_occlusion_culling` | Umbra（官方方案） | 都是"用遮挡体减少绘制" |

> 💡 **结论**：**机制层面能一一对应的其实不多**。真正对得上的是"空间分桶光照""阴影""探针""实例化""后处理注入"这几项；差异最大的三块是 **GI（SDFGI vs Enlighten）**、**屏幕空间效果**、**批处理（无合批器 vs SRP Batcher）**。**可执行建议**：评估迁移成本时，把这三块单独列出来做原型验证，其余部分按"两边都有、细节不同"处理。

### 3.9 GI 方案全景

这是本卷补写清单 #6 的落点。Godot 4.3 的 GI 不是一个开关，而是**五个类 + 一个环境开关**的组合：

| Godot 4.3 | 类型 | 什么时候烘焙 / 更新 | 运行时开销 | 适用场景 |
|-----------|------|---------------------|-----------|----------|
| `LightmapGI` / `LightmapGIData` | 静态光照贴图 | 编辑器内烘焙 | 采样开销极低 | 静态建筑、关卡级间接光 |
| `VoxelGI` / `VoxelGIData` | 体素化 GI | 编辑器内烘焙（可运行时更新） | 中等 | 动态物体参与间接光 |
| `LightmapProbe` | 球形探针 | 手工放置或由 `LightmapGI.generate_probes_subdiv` 自动生成 | 极低 | 补充烘焙覆盖不到的位置 |
| `ReflectionProbe` | 反射探针 | 运行时按 `update_mode` 更新 | 中等 | 动态反射、环境镜面 |
| `Environment.sdfgi_enabled` | 符号距离场实时 GI | 运行时渐进更新（`sdfgi_cascades` / `sdfgi_min_cell_size` 控制成本） | **最高** | Forward+ 下的实时间接光 |
| `Environment.ssil_enabled` | 屏幕空间间接光 | 每帧屏幕空间计算 | 高 | 补近景间接光的细节 |

> ⚠️ **它们不是同一个东西，不能笼统地统称"SDFGI"**。4.3 注册了 `VoxelGI` / `VoxelGIData`、`LightmapGI` / `LightmapGIData`、`LightmapProbe` 五个 GI 相关类，加上 `Environment.sdfgi_enabled` 控制的实时 SDFGI。

**逐项对照 Unity**：

| Godot 4.3 | Unity（以官方文档为准） | 机制差异 |
|-----------|------------------------|----------|
| `LightmapGI` + `LightmapGIData` | Lightmapping（Lightmap 资产）+ Lighting Settings 资产 | 流程相近；Unity 的烘焙后端可选 Unity Compute Light Baker（仅 URP / HDRP）、Progressive GPU Lightmapper、Progressive CPU Lightmapper（**已废弃**） |
| `VoxelGI` + `VoxelGIData` | 无直接对应（由 Enlighten / 探针体积覆盖） | Godot 的体素 GI 是"把场景烘成体素"，Enlighten 是"动态全局光照中间件" |
| `LightmapProbe`（手工放置） | Light Probe Group（手工放置） | 基本对应 |
| `LightmapGI.generate_probes_subdiv` 自动生成探针 | Adaptive Probe Volumes（**自动**按几何密度布点、**逐像素**采样、支持流式加载） | Godot 的自动探针是烘焙时的静态网格，**没有逐像素采样与流式加载** |
| `Environment.sdfgi_enabled`（SDFGI） | Enlighten Realtime Global Illumination | 机制完全不同，且 Unity 的 Enlighten 是**中间件**（需要授权与单独安装） |
| `Environment.ssil_enabled` | 无独立等价物 | Unity 侧最接近的是 Progressive Lightmapper 的屏幕空间部分 |
| `ReflectionProbe` | Reflection Probe | 基本对应；Godot 侧有 `update_mode`（`UPDATE_ONCE` / `UPDATE_ALWAYS`）与 `box_projection` |
| `Environment.ssr_enabled` | URP / HDRP 的 Screen Space Reflections | Unity 侧可作为效果叠加，Godot 侧是 `Environment` 上的开关 |
| `Light3D.light_bake_mode`（`BAKE_DISABLED` / `BAKE_STATIC` / `BAKE_DYNAMIC`） | Lighting Settings 里的混合光照设置 | Godot 把"是否参与烘焙"放在灯上，Unity 放在场景设置上 |

> 💡 **结论**：Godot 的 GI 家族是「**贴图 / 体素 / 探针 / SDFGI / SSIL**」五件套，Unity 是「**烘焙 / Enlighten / 探针组 / 探针体积 / 屏幕空间**」。**机制差异**：Unity 的 Enlighten 是**中间件**（独立产品、需授权），Godot 的 SDFGI 是**引擎内建**（但只有 Forward+ 能用）。**可执行建议**：
> 1. 重度依赖 Enlighten 的项目迁到 Godot，只能用 `LightmapGI` + `VoxelGI` + `LightmapProbe` 组合替代，**要重新烘焙**；
> 2. 依赖 Adaptive Probe Volumes 自动布点的项目，必须**重新设计探针分布** —— Godot 4.7.2 仍没有"按密度自动摆探针 + 逐像素采样"的等价物；
> 3. 目标含 Web 的项目要接受"只有烘焙 GI"（SDFGI / SSIL 在 Compatibility 下都没有）。

### 3.10 阴影方案全景

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 定向光模式 | `DirectionalLight3D.directional_shadow_mode`：`SHADOW_ORTHOGONAL` / `SHADOW_PARALLEL_2_SPLITS` / `SHADOW_PARALLEL_4_SPLITS` | Cascaded Shadow Maps，级联数 1 ~ 4 |
| 分割距离 | `directional_shadow_split_1` / `_2` / `_3` + `directional_shadow_max_distance` | 各级联的分割距离，以官方文档为准 |
| 级联混合 | `directional_shadow_blend_splits` + `directional_shadow_fade_start` | 以官方文档为准 |
| 阴影视锥 | `directional_shadow_pancake_size` | 以官方文档为准 |
| 软阴影 | `Light3D.shadow_blur` + `light_size` / `light_angular_distance`（PCSS 风格） | 以官方文档为准 |
| 阴影偏移 | `Light3D.shadow_bias` / `shadow_normal_bias` | 以官方文档为准 |
| 阴影贴图管理 | Shadow Atlas（所有阴影图打进图集，容量有限） | 按灯 / 按级联分开管理 |
| 投射开关 | `GeometryInstance3D.cast_shadow` | Renderer 的 Cast Shadows 选项 |
| 方差阴影（VSM） | ❌ 4.7.2 无（Godot 3.x 也没有） | 以官方文档为准 |
| 接触阴影 | ❌ 4.7.2 无此特性 | ✅ |
| 调试可视化 | `Viewport.DebugDraw` 的 `DEBUG_DRAW_SHADOW_ATLAS` / `DEBUG_DRAW_PSSM_SPLITS` | 官方 Debug 视图 |

> 💡 **结论**：两边的平行光阴影思路几乎一样（**级联分割 + 多张贴图**），只是 Godot 叫 PSSM、Unity 叫 CSM。**机制差异**：Godot 把所有阴影图塞进一张 **Shadow Atlas**，Unity 按灯分张。**可执行建议**：Godot 里灯一多或阴影图一大就可能装不进图集 —— 表现是部分物体的阴影突然消失；排查时用 `DEBUG_DRAW_SHADOW_ATLAS` 看图集占用。

### 3.11 后处理与自定义管线全景

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 效果开关载体 | 一个 `Environment` 资源（通常挂在 `WorldEnvironment` 上） | `Volume` 组件 + 后处理 Profile |
| 局部覆盖 | 按相机指定 `Environment`，或用 `WorldEnvironment` + 相机切换 | Volume 可按区域 / 按相机叠加，权重可混合 |
| 泛光 | `Environment.glow_enabled` 等（7 级 `glow_levels`） | Bloom 效果 |
| 景深 | `CameraAttributesPractical` 的 dof 参数 | URP / HDRP 的 Depth of Field |
| 自动曝光 | `CameraAttributesPractical` 的 auto_exposure 参数 | 以官方文档为准 |
| 色调映射 | `Environment.tonemap_mode` / `tonemap_exposure` / `tonemap_white` | 管线资产里的 Tone Mapping |
| 色彩调整 | `Environment.adjustment_brightness` 等（亮度 / 对比度 / 饱和度 / 曲线贴图） | 后处理 Profile 里的 Color Adjustments |
| 自定义 pass | `Compositor` + `CompositorEffect`（5 个注入点） | `ScriptableRenderPass` / `RendererFeature` |
| 自定义 pass 的依赖 | 依赖 `RenderingDevice` → Compatibility 不可用 | 以官方文档为准 |
| 效果顺序 | 由渲染器内建的 pass 顺序决定（见第 14 篇） | 由管线资产里的 Renderer Feature 顺序决定 |

> 💡 **结论**：Godot 的后处理是「**一个 `Environment` 资源上的开关集合**」，Unity 的后处理是「**Volume 组件驱动的效果栈**」。**机制差异**：Unity 的 Volume 可以按相机 / 按区域叠加不同效果覆盖，Godot 的 `Environment` 通常是全局的，或按 `Camera` 指定。**可执行建议**：需要"走进一个房间就换一套后处理"的玩法，Godot 侧要靠 `WorldEnvironment` + 相机切换，或用 `CompositorEffect` 自己实现 —— 不要假设效果可以自由叠加。

### 3.12 透明与排序

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 透明物体排序 | 按相机距离由远及近 | 以官方文档为准 |
| 排序键 | 材质键（`sort_key1` / `sort_key2`）+ 深度 | 以官方文档为准 |
| 深度预通道 | Forward+ 有（见第 14 篇） | 以官方文档为准 |
| Alpha 裁剪 | `BaseMaterial3D.alpha_scissor_threshold` | Alpha Clipping 选项 |
| Alpha 抗锯齿 | `BaseMaterial3D.alpha_antialiasing_mode` / `alpha_antialiasing_edge` | 以官方文档为准 |
| 混合模式 | `BaseMaterial3D.blend_mode` | 以官方文档为准 |
| 排序实现 | `RenderForwardClustered::RenderList` 的排序比较器（源码见第 14 篇） | 以官方文档为准 |

> 💡 **结论**：透明物体的**排序机制**两边都是"按距离 + 按材质"，差别在 Godot 把排序键显式做成了两个 64 位字段，Unity 则由管线内部决定。**可执行建议**：半透明物体排序出问题时，先查"是否与不透明物体共用了排序键"，再查 `sort_key1` / `sort_key2` 是否被自定义过。

---

### 3.13 贴花（Decal）

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 节点 | `Decal` | Decal Projector（以官方文档为准） |
| 贴花通道 | `texture_albedo` / `texture_normal` / `texture_orm` / `texture_emission` | 以官方文档为准 |
| 尺寸 | `size`（三维盒） | 以官方文档为准 |
| 淡出 | `upper_fade` / `lower_fade` / `normal_fade` | 以官方文档为准 |
| 距离淡出 | `distance_fade_enabled` / `distance_fade_begin` / `distance_fade_length` | 以官方文档为准 |
| 反照率混合 | `albedo_mix` | 以官方文档为准 |
| 自发光 | `emission_energy` | 以官方文档为准 |
| 剔除掩码 | `cull_mask` | 以官方文档为准 |
| 渲染器支持 | 三种渲染器都支持 | 以官方文档为准 |

> 💡 **结论**：Godot 的 `Decal` 用**一个三维盒**做投影范围，通道配置（albedo / normal / ORM / emission）集中在同一个节点上。**机制差异**：Unity 的 Decal Projector 同样用盒体投影，但参数分散在不同组件上。**可执行建议**：贴花是 Godot 侧**三种渲染器都支持**的特性，迁移时不必为 Web 单独做一套替代方案 —— 这在屏幕空间效果普遍缺失的 Compatibility 路径下是个好消息。

### 3.14 2D 渲染路径

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 2D 基类 | `CanvasItem`（`Node2D` / `Control` / `Sprite2D` 都继承它） | SpriteRenderer / UI（两套体系） |
| 自定义绘制 | 覆写 `_draw()`，用绘制命令 | OnGUI / UI Toolkit / 自定义 Graphic |
| 材质与混合 | `CanvasItemMaterial.blend_mode` | UI / Sprite 的材质设置 |
| 2D 光照 | `PointLight2D` / `DirectionalLight2D` + `CanvasModulate` | 2D 光照设置（以官方文档为准） |
| 层级 | `CanvasLayer`（独立于 3D 相机的层） | 以官方文档为准 |
| 缩放与拉伸 | `CanvasItem` 的变换 + `Viewport` 的 `canvas_transform` | Canvas Scaler（以官方文档为准） |
| 2D 合批 | **Godot 4 没有 2D 合批器**（3.x 的 batcher 已移除），见第 18 篇 | Sprite Atlas / 2D Batcher（以官方文档为准） |

> 💡 **结论**：Godot 的 2D 是一套**独立于 3D 的渲染路径**（`CanvasItem`），Unity 的 2D 也是独立体系（SpriteRenderer 与 UI 各自一套）。**机制差异**：Godot 4 **没有** 2D 合批器 —— 这与 3D 一样，"自动合批"这条路两边都断了。**可执行建议**：从 Unity 迁过来时，Sprite Atlas 式的合批要改用 Godot 侧的等价手段（减少节点、共享材质、静态合面），细节见**第 18 篇《2D 渲染》**。

### 3.15 可见性剔除与距离 LOD

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 距离可见范围 | `GeometryInstance3D.visibility_range_begin` / `visibility_range_end` | LOD Group + 距离裁剪（以官方文档为准） |
| 淡出方式 | `GeometryInstance3D.visibility_range_fade_mode` | 以官方文档为准 |
| LOD 偏置 | `GeometryInstance3D.lod_bias` | LOD Bias（以官方文档为准） |
| 遮挡剔除 | `rendering/occlusion_culling/use_occlusion_culling` + `OccluderInstance3D` | 官方遮挡剔除方案（以官方文档为准） |
| 视锥剔除 | 引擎内建 | 引擎内建 |
| 关闭遮挡剔除 | `GeometryInstance3D.ignore_occlusion_culling` | 以官方文档为准 |
| 自定义 AABB | `GeometryInstance3D.custom_aabb` | 以官方文档为准 |
| 合批替代 | `MultiMesh` + 共享材质 | SRP Batcher / GPU Instancing |

> 💡 **结论**：Godot 4.3 **没有 `LOD3D` 这样的 LOD 节点**（4.3 的类参考里没有这个类），LOD 完全靠 `GeometryInstance3D` 的 `lod_bias` + `visibility_range` 两个属性实现。**机制差异**：Godot 把 LOD 做成了**属性**而不是**节点**，因此同一套网格在不同实例上可以有不同策略，但也没有"一个 LOD Group 管一批物体"的组织方式。**可执行建议**：迁移时如果原项目重度依赖 LOD Group 的组织结构，需要改成"给每个实例配 `visibility_range`"；这会让 prefab 的参数面板变复杂，但引擎侧更灵活。

---

### 3.16 光源类型与衰减

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 平行光 | `DirectionalLight3D` | Directional Light |
| 全向光 | `OmniLight3D`（`omni_range`） | Point Light |
| 聚光灯 | `SpotLight3D`（`spot_range` / `spot_angle`） | Spot Light |
| 能量 | `light_energy` | 以官方文档为准 |
| 物理单位 | `light_intensity_lumens` / `light_intensity_lux` | 以官方文档为准 |
| 衰减曲线 | `Light3D.PARAM_ATTENUATION` / `Light3D.PARAM_SPOT_ATTENUATION` | 以官方文档为准 |
| 参与烘焙 | `light_bake_mode`（`BAKE_DISABLED` / `BAKE_STATIC` / `BAKE_DYNAMIC`） | 混合光照设置（以官方文档为准） |
| 阴影开关 | `shadow_enabled` | Cast Shadows |
| 阴影偏移 | `shadow_bias` / `shadow_normal_bias` | 以官方文档为准 |
| 规格与颜色 | `light_specular` / `light_color` / `light_temperature` | 以官方文档为准 |

> 💡 **结论**：Godot 把"是否参与烘焙"放在**灯自己身上**（`light_bake_mode`），Unity 放在**场景的混合光照设置**里。**机制差异**：Godot 的逐灯设置更直观，但要注意 —— 一盏灯不设 `BAKE_STATIC` 就**不会**进入烘焙，这是迁移时最容易漏的一步。**可执行建议**：迁移脚本里逐盏灯检查 `light_bake_mode`，确认静态灯已经设成 `BAKE_STATIC`、动态灯设成 `BAKE_DYNAMIC`。

### 3.17 网格与实例化细节

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 网格资源 | `Mesh` / `ArrayMesh` / `PrimitiveMesh` | Mesh 资产 |
| 表面数组 | `Mesh.ARRAY_VERTEX` / `ARRAY_NORMAL` / `ARRAY_TEX_UV` / `ARRAY_INDEX` | 顶点属性布局（以官方文档为准） |
| 顶点格式（RD 路径） | `vertex_format_create()` | 以官方文档为准 |
| 实例化 | `MultiMesh` + `MultiMeshInstance3D` | GPU Instancing / DrawMeshInstanced |
| 每实例颜色 | `MultiMesh.set_instance_color()` | 以官方文档为准 |
| 每实例自定义数据 | `MultiMesh.set_instance_custom_data()` | 以官方文档为准 |
| 可见实例数 | `MultiMesh.visible_instance_count` | 以官方文档为准 |
| 自定义包围盒 | `MultiMesh.custom_aabb` | 以官方文档为准 |
| 2D 变换格式 | `MultiMesh.transform_format`（`TRANSFORM_2D` / `TRANSFORM_3D`） | 以官方文档为准 |

> 💡 **结论**：**`MultiMesh` 是 Godot 侧唯一能真正减少 draw call 的手段**（对应 Unity 的 GPU Instancing）。**机制差异**：Unity 的 SRP Batcher 优化的是 CPU 端的 render state 变更，Godot 侧**没有**对应物 —— 迁移时凡是靠 SRP Batcher 撑住的场景，都要用 `MultiMesh` 重新组织。**可执行建议**：把 Unity 项目里"只靠 SRP Batcher 合批"的物体列出来，逐个评估能否改成 `MultiMesh`（同网格多实例）或减少节点数。

---

## 四、性能对比

### 4.1 Draw Call

> ⚠️ 下表为示意数据（未附测试环境与场景构成），仅供建立数量级概念。
> 实际 Draw Call 取决于场景拆分、材质与光照配置，请在目标平台实测。

| 场景 | Godot | Unity |
|------|-------|-------|
| **简单场景** | ~100 | ~150 |
| **中等场景** | ~500 | ~800 |
| **复杂场景** | ~2000 | ~3000 |

### 4.2 帧率对比

| 平台 | Godot | Unity |
|------|-------|-------|
| **PC** | 优秀 | 优秀 |
| **移动** | 优秀 | 良好 |
| **Web** | 良好 | 良好 |

---

> 💡 **结论（4.1 / 4.2 性能对比）**：**不要把两个引擎的帧率数字直接对比** —— 表格里的 Draw Call 与帧率都是示意数据，场景构成、分辨率、阴影与光照配置一变就完全不成立。**机制差异**：两边的性能瓶颈分布不同，Unity 的 CPU 端开销常被 SRP Batcher 摊薄，Godot 的 CPU 端开销则更直接地落在剔除与状态切换上。**可执行建议**：迁移后第一件事不是看帧率，而是先在**同一台机器、同一个场景**里重建基线，再决定要不要为性能改架构。

### 4.3 调试与性能分析工具

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 内建帧调试 | 编辑器 **Visual Profiler**（逐 pass 的 GPU / CPU 耗时；数据来自 C++ 层 `RenderingServer::get_frame_profile()`，4.3 未导出为脚本方法） | ✅ **Frame Debugger**（Window ▸ Analysis ▸ Frame Debugger），显示渲染事件树并可逐事件回放 |
| 内建性能面板 | 调试器 Monitors（`Performance.get_monitor()`） | ✅ Profiler（CPU / GPU / 渲染线程分列） |
| 第三方抓帧 | RenderDoc、apitrace 等（Vulkan 下直接可用） | RenderDoc 等（引擎切到 Vulkan 时同样可用） |
| 场景级统计 | `RenderingServer.get_rendering_info()` / `viewport_get_render_info()` | Profiler 与 Frame Debugger 的事件计数 |
| 渲染可视化 | `Viewport.DebugDraw`（4.3 共 27 项，含 overdraw、光照、PSSM 分割等） | 各类 Debug 视图与自定义 Render Feature |

> 💡 **结论**：Unity 的 **Frame Debugger** 在「看清一帧里到底画了什么」这件事上更成熟；Godot 的 **Visual Profiler** 在「看清每个 pass 花了多少 GPU 时间」这件事上更直接。**机制差异**：Frame Debugger 展示的是**命令流**（可以回放到任意事件），Visual Profiler 展示的是**时间条**（不可回放）。**可执行建议**：排查渲染问题时两边最好都装 —— Godot 侧用 RenderDoc 抓帧，Unity 侧用 Frame Debugger 走事件流，迁移后对照着看更省事。

### 4.4 平台与 VR 支持

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| XR 抽象 | `XRInterface` 基类 + `XRServer`；类参考明确写明实现「should be implemented as C++ modules or GDExtension modules」 | ✅ XR 插件框架（XR Plug-in Management）+ 官方 XR 包 |
| OpenXR 的位置 | **4.3 已从核心移出**：`doc/classes/OpenXRInterface.xml` 与 `xr/openxr/openxr_interface.h` 在 4.3 分支上均不存在，改由官方 OpenXR **GDExtension** 提供 | 官方 XR 包体系内提供 |
| 移动 VR | ✅（Vulkan / Mobile 渲染器） | ✅（Android XR 包 + Vulkan / OpenGL ES） |
| 主机 | 需自行移植，无官方支持 | ✅ 官方主机 SDK（需授权，**以官方文档为准**） |
| 图形 API 可选性 | 桌面基本固定（Vulkan / D3D12），没有「用 DX11 跑」的选项 | DX11 / DX12 / Metal / Vulkan / OpenGL Core 可在 Player Settings 里挑 |

> 💡 **结论**：**XR 是 Godot 4.3 最需要留意的一处版本差异** —— OpenXR 已从核心模块变成 GDExtension。**机制差异**：Godot 4.3 的核心只保留 `XRInterface` / `XRServer` 这层抽象，具体运行时由扩展提供；Unity 则把 XR 做成插件包生态。**可执行建议**：做 XR 的项目，**先确认目标 Godot 版本**再决定要不要装 OpenXR 扩展 —— 按 4.2 的教程（内置 OpenXR）去配 4.3 会直接踩空。

### 4.5 性能调优入口对照

| 想优化什么 | Godot 4.3 的入口 | Unity（以官方文档为准）的入口 |
|------------|------------------|----------------------------------|
| 减少绘制调用 | `MultiMesh` / `MultiMeshInstance3D`；共享材质；减少节点数 | SRP Batcher / GPU Instancing / 合批 |
| 减少渲染对象 | `GeometryInstance3D.visibility_range_begin` / `_end`、`lod_bias` | LOD Group / 距离剔除设置 |
| 减少阴影成本 | 缩小 `directional_shadow_max_distance`、降低 `directional_shadow_mode` 的级联数、`GeometryInstance3D.cast_shadow` | 阴影分辨率 / 级联数 / 投射列表 |
| 减少光照成本 | Mobile 渲染器；控制"同时影响同一物体的灯数"；用 `Light3D.light_bake_mode` 把静态灯烘掉 | 混合光照 / 烘焙 / 减少实时光源数 |
| 减少 GI 成本 | 关掉 `Environment.sdfgi_enabled`；降低 `sdfgi_cascades`；改用 `LightmapGI` | 关闭实时 GI / 降低 Enlighten 分辨率 |
| 减少后处理成本 | 关掉 `Environment.volumetric_fog_enabled` / `ssil_enabled` / `ssr_enabled`；降低 `glow_levels` | 精简 Volume 效果栈 |
| 降低分辨率 | `Viewport.scaling_3d_mode` / `scaling_3d_scale` | Render Scale / Dynamic Resolution |
| 抗锯齿 | `Viewport.msaa_3d` / `screen_space_aa` / `use_taa` | MSAA / TAA / FSR 等 |
| 观测数据 | 编辑器 Visual Profiler、`Performance` 计数器、RenderDoc | Profiler / Frame Debugger / RenderDoc |

> 💡 **结论**：**Godot 的调优入口更"资源导向"**（改 `Environment` 上的开关、改 `GeometryInstance3D` 的属性），**Unity 的调优入口更"管线导向"**（改管线资产设置）。**机制差异**：Unity 的一切多半挂在管线资产上，Godot 的一切多半挂在 `Environment` 与节点属性上。**可执行建议**：迁移时把 Unity 的"渲染设置"逐条翻译成 Godot 的"节点属性 + `Environment` 开关"，而不是去找一个对应的"渲染设置面板" —— Godot 没有这个东西。

### 4.6 GPU 侧能力与硬限制

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 底层抽象 | `RenderingDevice`（`RenderingDeviceDriver` → 后端） | SRP 之下的内部抽象 |
| 能力查询 | `RenderingDevice.limit_get()` / `get_device_name()` / `get_driver_resource()` | SystemInfo 系列（以官方文档为准） |
| 显存统计 | `RenderingDevice.get_memory_usage()` | Profiler 的内存模块（以官方文档为准） |
| 计算着色器 | ✅（`shader_type compute`） | ✅ |
| 图形 API 可选性 | 桌面基本固定（Vulkan / D3D12） | DX11 / DX12 / Metal / Vulkan / OpenGL Core 可在 Player Settings 里挑 |
| Web 图形 API | 只有 WebGL 2 | WebGL2 与 WebGPU（可选，浏览器支持有限） |
| 时间戳查询 | `RenderingDevice.get_captured_timestamp_gpu_time` 等（RD 路径） | 以官方文档为准 |
| 管线缓存 | `RenderingDevice.get_device_pipeline_cache_uuid()` | 以官方文档为准 |

> 💡 **结论**：Godot 把"能力查询"做成了 RD 的一等公民（`limit_get()` 返回几十项硬件上限），Unity 则通过 SystemInfo 暴露设备信息。**可执行建议**：如果你的项目里有跨设备的能力自适应逻辑（"低端机降级"），Godot 侧可以读 `RenderingDevice.limit_get()` 与 `get_device_name()`，比读项目设置更贴近真实硬件。

---

### 4.7 抓帧与帧分析工具链

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 逐 pass 耗时 | 编辑器 **Visual Profiler**（数据来自 C++ 层 `RenderingServer::get_frame_profile()`，4.3 未导出为脚本方法） | ✅ Profiler（CPU / GPU / 渲染线程分列） |
| 命令流回放 | ❌ 无内建命令流查看器 | ✅ **Frame Debugger**（Window ▸ Analysis ▸ Frame Debugger） |
| 第三方抓帧 | RenderDoc、apitrace（Vulkan 下直接可用） | RenderDoc（引擎切到 Vulkan 时同样可用） |
| 场景级统计 | `Performance.get_monitor()` / `RenderingServer.get_rendering_info()` | Profiler 计数 |
| 可视化开关 | `Viewport.debug_draw`（4.3 共 27 项） | 各类 Debug 视图 + 自定义 Render Feature |
| 帧时间口径 | `Performance.TIME_PROCESS` 只算主循环 | Profiler 分列（以官方文档为准） |
| GPU 时间戳 | `RenderingDevice.get_captured_timestamp_gpu_time`（RD 路径） | 以官方文档为准 |
| 着色器调试 | 渲染器自带可视化（不透明 / 法线 / 粗糙度等）+ `Viewport.debug_draw` | Frame Debugger / Debug 视图 |

> 💡 **结论**：Unity 的 **Frame Debugger** 在"看清一帧里到底画了什么"这件事上更成熟；Godot 的 **Visual Profiler** 在"看清每个 pass 花了多少 GPU 时间"这件事上更直接。**机制差异**：Frame Debugger 展示的是**命令流**（可以回放到任意事件），Visual Profiler 展示的是**时间条**（不可回放）。**可执行建议**：排查渲染问题时两边最好都装 —— Godot 侧用 RenderDoc 抓帧，Unity 侧用 Frame Debugger 走事件流，迁移后对照着看更省事。

---

### 4.8 内存与资源加载

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 运行时加载 | `ResourceLoader` + `load()` 按路径加载 | Addressables / AssetBundle（以官方文档为准） |
| 渲染资源释放 | RID 需显式 `RenderingServer.free_rid()` | 资源对象引用计数自动回收 |
| 显存观测 | `RenderingDevice.get_memory_usage()` | Profiler 内存模块（以官方文档为准） |
| 纹理流式加载 | 导入时选压缩格式，运行时按需加载资源 | 以官方文档为准 |
| 场景切换 | 切换场景节点 / `SubViewport` | Addressables 场景（以官方文档为准） |
| 卸载整个场景 | 释放场景树 → 节点释放其持有的 RID | 卸载场景 → 资源引用计数下降 |

> 💡 **结论**：Godot 的渲染资源是**"显式句柄 + 显式释放"**，Unity 是**"共享对象 + 引用计数"**。**机制差异**：Godot 侧用 `RenderingServer` 手动建的资源，忘记 `free_rid()` 就会泄漏；用节点/资源承载的则会随节点销毁自动释放。**可执行建议**：迁移时把"手动建 RID"的代码全部标出来，逐个确认释放路径；这是长时间运行后显存持续上涨的唯一常见原因。

---

## 五、工程流程与资产管线

### 5.1 资产导入与渲染资源

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 导入入口 | 编辑器导入器（`.import` 文件 + 导入预设） | Asset Import Pipeline |
| 纹理压缩 | 导入时选 VRAM 压缩（BC / ETC / ASTC，取决于目标平台） | 平台相关的纹理压缩设置 |
| 网格导入 | 表面工具 / 导入预设 | Model Importer |
| 材质 | `BaseMaterial3D` / `ShaderMaterial` 资源 | Material 资产 |
| 烘焙产物 | `LightmapGIData` / `VoxelGIData` 资源 | Lightmap 资产 / Lighting Data Asset |
| 版本控制友好度 | 资源是独立文件，`.import` 需入库 | Meta 文件需入库 |

### 5.2 平台与构建

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 渲染器选择时机 | **启动时**读 `rendering/renderer/rendering_method`（另有 `.mobile` / `.web` 平台覆盖项） | 构建/平台设置里选管线资产 |
| 平台覆盖 | 同一份工程按平台切换渲染器 | 按平台切管线资产 |
| 主机支持 | 需自行移植，无官方支持 | 官方主机 SDK（需授权） |
| Web 导出 | 只能走 Compatibility（WebGL 2） | WebGL2 或 WebGPU（实验性） |
| C# 支持 | ✅ | ✅（引擎本体用 C#） |
| 渲染后端可移植性 | 同一套代码跨平台 | 需维护平台构建配置 |

> 💡 **结论**：Godot 的"一份工程、多个渲染器"是**平台级**切换（构建时按平台选），Unity 的"多管线"是**资产级**切换（每个平台一套管线资产）。**机制差异**：Godot 切渲染器不产生资产分叉，Unity 切管线通常要维护多套材质与后处理 Profile。**可执行建议**：从 Unity 迁过来后，如果原项目里有多套 URP / HDRP 资产，这份维护成本会直接消失 —— 这是 Godot 相对 Unity 最实在的一处优势。

---

### 5.3 资产导入与版本控制

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 导入元数据 | 每个资源旁边的 `.import` 文件 | 每个资源旁边的 `.meta` 文件 |
| 导入缓存 | `.godot/` 目录（**不应入库**） | `Library/` 目录（**不应入库**） |
| 纹理压缩 | 导入预设里选目标平台格式（BC / ETC / ASTC） | 平台相关的纹理压缩设置 |
| 网格导入 | 导入预设 + 表面工具（`SurfaceTool`） | Model Importer |
| 材质资产 | `.tres` 资源 | Material 资产 |
| 烘焙产物 | `LightmapGIData` / `VoxelGIData` | Lightmap / Lighting Data Asset |
| 着色器资产 | `.gdshader` 文本文件（**天然可 diff**） | ShaderLab（同样是文本） |
| 导入结果可复现性 | 导入预设入库即可复现 | 依赖 Library 缓存与导入设置 |

> 💡 **结论**：两边的版本控制策略几乎一致 —— **元数据入库、缓存忽略**。**机制差异**：Godot 的着色器是纯文本的 `.gdshader`，diff 友好；Unity 的 ShaderLab 同样是文本，但材质与管线资产之间的引用关系更复杂。**可执行建议**：迁移项目时优先把**材质依赖图**梳理清楚 —— Godot 侧材质不再绑定管线后，这张图会显著变简单。

---

### 5.4 团队协作与持续集成

| 维度 | Godot 4.3 | Unity（以官方文档为准） |
|------|-----------|------------------------|
| 命令行导入 | `--import`（或 `--editor --quit`） | `-batchmode -quit` |
| 无头导出 | `--headless --export-release` | `-batchmode -buildTarget` |
| 渲染相关自动化 | headless 下**没有 `RenderingDevice`** → 画面回归需另建方案 | 以官方文档为准 |
| 导入缓存复用 | `.godot/` 目录可缓存并复用 | Library 缓存 |
| 着色器编译检查 | 导入期编译 `.gdshader` | 导入期编译 ShaderLab |
| 资源导入一致性 | 导入预设入库即可复现 | 依赖导入设置与 Library |
| 单元测试 | 第三方测试框架 | 官方测试框架（以官方文档为准） |

> 💡 **结论**：两边的 CI 流程可以一一对应，**唯一真正的差异**是 Godot 的 headless 模式**没有 `RenderingDevice`**，因此"渲染画面"的自动化测试要在有图形设备的环境里跑。**机制差异**：Unity 的批处理模式同样不带图形上下文，两边在这点上是对称的。**可执行建议**：把"画面回归"与"逻辑回归"分成两条 CI 流水线 —— 后者跑 headless，前者跑在带 GPU 的机器上。

## 六、迁移检查清单

### 6.1 渲染相关逐项核对

| # | 核对项 | Godot 侧的落点 | 常见坑 |
|---|--------|----------------|--------|
| 1 | 实时 GI | `Environment.sdfgi_enabled`（仅 Forward+） | 目标含 Web / 移动低端机时没有等价物 |
| 2 | 烘焙 GI | `LightmapGI` + `LightmapGIData` | 需要重新烘焙，Unity 的 Lightmap 不能直接搬 |
| 3 | 探针布置 | `LightmapProbe`（手工）或 `LightmapGI.generate_probes_subdiv`（自动） | 没有"按密度自动布点 + 逐像素采样"的等价物 |
| 4 | 反射探针 | `ReflectionProbe` | `update_mode` 与 `box_projection` 语义要对齐 |
| 5 | 定向光阴影 | `DirectionalLight3D.directional_shadow_mode` / `directional_shadow_split_1..3` | 4.3 最多 4 级；没有 VSM |
| 6 | 软阴影质量 | `Light3D.shadow_blur` + `light_size` | `light_size` 与 Unity 的软阴影参数不是一一对应 |
| 7 | 接触阴影 | ❌ 无 | 需要自己用 `CompositorEffect` 近似 |
| 8 | 屏幕空间反射 | `Environment.ssr_enabled` | Mobile / Compatibility 下没有 |
| 9 | 屏幕空间间接光 | `Environment.ssil_enabled` | 同上 |
| 10 | 体积雾 | `Environment.volumetric_fog_enabled` | 同上 |
| 11 | 泛光 | `Environment.glow_enabled` / `glow_levels` | 7 级 `glow_levels` 与 Unity 的 Bloom 档位不对应 |
| 12 | 景深 / 自动曝光 | `CameraAttributesPractical` | 挂在相机属性上，不在 `Environment` 上 |
| 13 | 色调映射 | `Environment.tonemap_mode` / `tonemap_exposure` | 挂在 `Environment` 上，不在相机上 |
| 14 | 自定义后处理 | `Compositor` + `CompositorEffect` | 固定 5 个注入点；Compatibility 下不可用 |
| 15 | 计算着色器 | `shader_type compute` + `RenderingDevice` | Compatibility / headless 下不可用 |
| 16 | GPU 粒子 | `GPUParticles3D` / `GPUParticles2D` | Compatibility 下回退 CPU 粒子 |
| 17 | 合批 | `MultiMesh` / `MultiMeshInstance3D` / 共享材质 | **没有 SRP Batcher 等价物**，要重做 draw call 预算 |
| 18 | 渲染线程 | `rendering/driver/threads/thread_model` | 只有 `RENDER_SEPARATE_THREAD` 才真的开线程 |

### 6.2 风险排序

| 风险等级 | 项目 | 判断依据 |
|----------|------|----------|
| 🔴 高 | 实时 GI（Enlighten → SDFGI） | 机制完全不同，且 SDFGI 仅 Forward+ 可用 |
| 🔴 高 | 合批（SRP Batcher → 无） | 直接影响 CPU 端开销与 draw call 预算 |
| 🟠 中 | 探针自动布点（APV → 手工） | 需要重新设计探针分布，工作量可估但不可省 |
| 🟠 中 | 自定义渲染管线（自定义 SRP → 固定注入点） | 架构级限制，要重新设计实现路径 |
| 🟡 低 | 阴影、雾、泛光、色调映射 | 两边都有，只是参数位置与命名不同 |
| 🟡 低 | 材质与着色器 | 语法不通用但结构对应，纯粹是重写工作量 |

### 6.3 迁移执行顺序建议

| 阶段 | 做什么 | 验收标准 |
|------|--------|----------|
| 1 · 建基线 | 同一台机器、同一场景，两边各跑一遍 | 记录帧时间、draw call、显存占用三组数字 |
| 2 · 换资源 | 网格 / 贴图 / 动画导入 Godot | 比例、坐标轴、法线朝向正确 |
| 3 · 材质重写 | 用 `StandardMaterial3D` 对齐 PBR 参数；自定义材质用 `.gdshader` 重写 | 同一光照下的画面观感接近 |
| 4 · 光照 | 烘焙 GI + 布置探针 | 确认"同时影响同一物体的灯数"不超 8 |
| 5 · 后处理 | 把 Volume 栈翻译成 `Environment` 开关 + `CompositorEffect` | 每个效果有明确的落点，没有"静默失效"的开关 |
| 6 · 性能 | 用 `MultiMesh` / `visibility_range` 重做 draw call 预算 | draw call 回到基线量级 |
| 7 · 平台 | 含 Web 时确认 Compatibility 下要降级的特性 | 降级清单逐条确认，且不依赖 RD 的代码有兜底 |

> 💡 **结论**：迁移的**关键顺序**是"先资源、再材质、后光照、最后后处理与性能"。**机制差异**：Unity 的很多效果挂在 Volume 与管线资产上，翻译到 Godot 时要落到 `Environment` 与节点属性上，这个映射工作放在后期做，返工成本最低。**可执行建议**：第 5 阶段务必做一次"静默失效"排查 —— Godot 的 `Environment` 上那些 RD 专属开关在 Compatibility 下**不会报错**，只会不生效。

### 6.4 常见迁移坑位速查

| 现象 | Godot 侧的原因 | 处理方式 |
|------|----------------|----------|
| 部分物体的阴影突然消失 | Shadow Atlas 装不下 | 调小阴影图尺寸 / 减少同时投影的灯 |
| 远处物体忽然不亮 | per-object 的 8 盏上限触顶 | 减少同一物体附近的灯数，或改用 Forward+ |
| 半透明物体互相穿插 | 透明物体按深度排序 | 拆小透明物体 / 改用 Alpha 裁剪（`alpha_scissor_threshold`） |
| Web 上没有 SSR / 体积雾 / SSIL | Compatibility 通路不经过 RD | 改用烘焙方案，或在移动端用 Mobile 渲染器 |
| 自定义后处理完全不执行 | `CompositorEffect` 依赖 `RenderingDevice` | Compatibility 下不可用，需另做降级 |
| 粒子突然变卡 | Compatibility 下 GPU 粒子回退为 CPU 粒子 | 改用 `CPUParticles3D` 并调整 `amount` |
| 烘焙 GI 里少了静态物体 | 该灯没有设 `light_bake_mode` | 设为 `BAKE_STATIC` 后重新烘焙 |
| 显存持续上涨 | 手动创建的 RID 没有 `free_rid()` | 补释放路径 |
| 物体在远处"闪一下才出现" | `visibility_range` 淡出设置 | 检查 `visibility_range_fade_mode` 与 `visibility_range_begin_margin` |
| 阴影有"黑边" | `shadow_bias` / `shadow_normal_bias` 不合适 | 调这两个参数（不是调阴影贴图大小） |

> 💡 **结论**：这十条覆盖了 Godot ↔ Unity 渲染迁移里最常见的十种"看起来像引擎 bug、其实是机制差异"的现象。**机制差异**：其中六条（阴影图集容量、8 盏上限、透明排序、无 RD 通路、GPU 粒子回退、烘焙参与标记）在 Unity 侧**没有对应物**，因为 Unity 的实现路径不同。**可执行建议**：把这张表存进项目的迁移笔记，遇到现象先查表，再怀疑引擎。


### 6.5 迁移自检清单（可打印）

逐条打勾，全绿再上线：

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 渲染器选择 | 目标平台对应的 `rendering/renderer/rendering_method` 与平台覆盖项已确认 |
| 2 | 失效特性 | `Environment` 上所有 RD 专属开关在目标渲染器下的行为已确认（不会静默失效） |
| 3 | 灯光上限 | 场景中"同时影响同一物体"的灯数不超过 8 |
| 4 | 阴影容量 | Shadow Atlas 在最坏场景下装得下（用 `DEBUG_DRAW_SHADOW_ATLAS` 复核） |
| 5 | 烘焙覆盖 | 所有静态灯已设 `light_bake_mode = BAKE_STATIC`，且已重新烘焙 |
| 6 | 探针 | `LightmapProbe` / `LightmapGI.generate_probes_subdiv` 的覆盖已验证，无明显"黑洞" |
| 7 | draw call 预算 | 与 Unity 基线同量级（用 `MultiMesh` / `visibility_range` 补足） |
| 8 | 离屏渲染 | 所有"摄像机 + Render Texture"已改写为 `SubViewport` + `Camera3D` |
| 9 | 平台降级 | Web / headless 路径下不依赖 `RenderingDevice` 的代码已就绪 |
| 10 | 抓帧基线 | 已用 RenderDoc / Visual Profiler 抓过一遍，与基线逐 pass 对比 |

## 七、总结

## 核心要点

1. **架构不同**：RenderingServer vs SRP —— Godot 的 `RenderingServer` 是常驻服务，Unity 的 SRP 是每帧被调用的脚本。
2. **管线不同**：Forward+/Mobile/Compatibility vs URP/HDRP/Built-in —— Godot 按**平台能力**切，Unity 按**画质档位**切。
3. **2D 渲染**：Godot 原生 vs Unity 3D 模拟
4. **性能相当**：各有优劣，但两个引擎的帧率数字**不可直接对比**
5. **差异集中在实现粒度，不在功能有无**：GI、阴影、后处理三块两边的能力清单高度重合；真正拉开差距的是**渲染线程模型**、**材质与管线的绑定关系**、**有没有运行时合批器**这三件事
6. **GI 的机制完全对不上**：SDFGI / LightmapGI / VoxelGI / LightmapProbe 对应的是 Enlighten / Progressive Lightmapper / 探针体积，迁移必须重新烘焙、重新布探针
7. **Godot 4.7.2 仍没有运行时合批器**：SRP Batcher 的作用在 Godot 侧没有对应物，要用「`MultiMesh` + 共享材质 + `visibility_range`」重做 draw call 预算
8. **迁移前按"资源归属"逐项对照**：不要按"特性有没有"列清单，要按"这个特性在我的场景里由哪个资源承担"逐项核对，并排出风险优先级

---

## 📚 Unity 官方文档索引

- **Unity 官方文档**: [渲染管线总览](https://docs.unity3d.com/Manual/render-pipelines.html)、[Built-in 渲染管线](https://docs.unity3d.com/Manual/built-in-render-pipeline.html)、[SRP Batcher](https://docs.unity3d.com/Manual/SRPBatcher.html)、[GPU Instancing](https://docs.unity3d.com/Manual/gpu-instancing-enable.html)、[优化 draw call](https://docs.unity3d.com/Manual/optimizing-draw-calls.html)、[静态合批](https://docs.unity3d.com/Manual/static-batching-enable.html)、[阴影级联](https://docs.unity3d.com/Manual/shadow-cascades.html)、[光烘焙后端](https://docs.unity3d.com/Manual/progressive-lightmapper.html)、[Enlighten 实时 GI](https://docs.unity3d.com/Manual/realtime-gi-using-enlighten.html)、[Adaptive Probe Volumes](https://docs.unity3d.com/Manual/urp/probevolumes-concept.html)、[渲染路径](https://docs.unity3d.com/Manual/rendering-paths-introduction.html)、[URP 渲染路径对比](https://docs.unity3d.com/Manual/urp/rendering-paths-comparison.html)、[Scriptable Render Pass](https://docs.unity3d.com/Manual/urp/renderer-features/intro-to-scriptable-render-passes.html)、[Full Screen Pass Renderer Feature](https://docs.unity3d.com/Manual/urp/renderer-features/renderer-feature-full-screen-pass.html)、[Frame Debugger](https://docs.unity3d.com/Manual/frame-debugger-window.html)、[Web 图形 API](https://docs.unity3d.com/Manual/web-graphics-apis-intro.html)、[Vulkan 平台支持](https://docs.unity3d.com/Manual/vulkan.html)、[Metal 平台支持](https://docs.unity3d.com/Manual/metal-requirements-and-compatibility.html)、[XR 总览](https://docs.unity3d.com/Manual/xr-support-landing.html)

## 🔗 延伸阅读

- **官方文档**: [渲染器总览（Renderers）](https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html)
- **类参考**: [RenderingServer](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html)、[LightmapGI](https://docs.godotengine.org/en/stable/classes/class_lightmapgi.html)、[VoxelGI](https://docs.godotengine.org/en/stable/classes/class_voxelgi.html)、[Environment](https://docs.godotengine.org/en/stable/classes/class_environment.html)
- **官方教程**: [3D 灯光与阴影](https://docs.godotengine.org/en/stable/tutorials/3d/lights_and_shadows.html)
- **源码位置**: `servers/rendering/`、`scene/3d/lightmap_gi.cpp`

---

## 📋 下一章预告

**第 14 篇：场景渲染流程**

- 从场景更新到提交 GPU 的完整帧流程
- 可见性剔除：视锥体、距离、遮挡
- 渲染列表排序：材质键、深度、透明度
- 用 MultiMesh 与可见性范围替代"自动合批"

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 12 篇：Vulkan 渲染后端深度解析](/articles/12-vulkan-backend.md)
**下一篇**: [第 14 篇：场景渲染流程](/articles/14-scene-rendering-flow.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
