# 第 12 篇：Vulkan 渲染后端深度解析

> **摘要**：Godot 4.x 使用 Vulkan 作为主要渲染后端。本文将深入分析 Godot 的 Vulkan 实现、Forward+ 渲染器、Mobile 渲染器。
>
> **本章导读**：Vulkan 只是整条栈的最底层。引擎真正对外暴露的图形抽象是 `RenderingDevice`（脚本可用）与 `RenderingDeviceDriver`（C++ 纯虚接口），本章把这两层拆开讲：命令队列与命令池、屏障为什么是自动插入的、uniform set 与资源布局、纹理格式与用法位、显存与堆，以及一次 compute 派发从 SPIR-V 到提交的完整路径。读完本章，你能看懂 `drivers/vulkan/` 的两个类，能判断一个需求该不该下沉到 RD，也能在 Compatibility 与 headless 环境下正确降级。
> **前置知识**：第 11 篇《Godot 渲染架构概述》。
> **难度**：⭐⭐⭐⭐ 高级

---

## 一、Vulkan 概述

### 1.1 什么是 Vulkan

Vulkan 是 Khronos Group 开发的现代图形 API：

| 特性 | 说明 |
|------|------|
| **类型** | 低级图形 API |
| **平台** | Windows/Linux/macOS/Android |
| **优势** | 高性能、低开销、跨平台 |
| **对比** | DirectX 12、Metal |

### 1.2 Vulkan 优势

- ✅ 低 CPU 开销
- ✅ 多线程友好
- ✅ 跨平台
- ✅ 显式控制

---

## 二、Godot Vulkan 实现

### 2.1 源码结构

**源码位置**：`drivers/vulkan/`（Godot 4.3 实际只有 9 个文件）

```
drivers/vulkan/
├── SCsub
├── godot_vulkan.h
├── rendering_context_driver_vulkan.cpp
├── rendering_context_driver_vulkan.h
├── rendering_device_driver_vulkan.cpp
├── rendering_device_driver_vulkan.h
├── vulkan_hooks.cpp
└── vulkan_hooks.h
```

Godot 4.x 把 Vulkan 驱动拆成**两个职责不同**的类：

| 类 | 头文件 | 职责 |
|----|--------|------|
| `RenderingContextDriverVulkan` | `rendering_context_driver_vulkan.h` | **实例 / 上下文 / 表面 / 交换链**这一侧（窗口、显示、呈现） |
| `RenderingDeviceDriverVulkan` | `rendering_device_driver_vulkan.h` | **设备 / 队列 / 资源 / 提交**这一侧（计算与绘制） |

> `godot_vulkan.h` 只是 Vulkan 头文件的引入与宏定义；`vulkan_hooks.cpp/.h` 用于在 Vulkan 官方头文件里插桩（调用统计、内存分配跟踪等），本身不是驱动实现。

### 2.2 RenderingDeviceDriverVulkan

```cpp
// Godot 4.3 源码 - drivers/vulkan/rendering_device_driver_vulkan.h:50
class RenderingDeviceDriverVulkan : public RenderingDeviceDriver {
	struct Queue {
		VkQueue queue = VK_NULL_HANDLE;
		uint32_t virtual_count = 0;
		BinaryMutex submit_mutex;
	};

protected:
	// 逻辑设备
	VkDevice vk_device = VK_NULL_HANDLE;

	// 显示侧驱动（实例 / 表面 / 交换链）
	RenderingContextDriverVulkan *context_driver = nullptr;

	// 按队列族组织的队列：每一族可以有多条虚拟队列
	TightLocalVector<TightLocalVector<Queue>> queue_families;

	// 管线缓存
	PipelineCache pipelines_cache;

	// ...
};
```

> **注意（这是 4.x 真实结构，与 Godot 3.x 的印象不同）**：
> 1. 驱动**不是**持有"一条 `VkQueue queue` + 一个 `VkCommandPool vk_command_pool`"—— 队列是**按队列族分组**的（`queue_families`，每族可有多条虚拟队列，各自带 `submit_mutex`）；
> 2. 命令池不作为驱动成员长期持有，而是按需从池中分配；
> 3. 显示侧（实例 / 表面 / 交换链）通过 `context_driver` 指针委托给 `RenderingContextDriverVulkan`；
> 4. 驱动**没有** `graphics_queue` / `compute_queue` 两条独立队列成员的说法——"计算队列"是由队列族 + 命令类型决定的，不是两个成员。

### 2.3 初始化流程（两条并行的链）

Godot 4.x 不再是"一条线性流程"，而是**上下文侧**与**设备侧**各自初始化，再由 `RenderingDevice` 把二者接起来：

**（一）实例 / 上下文初始化（`RenderingContextDriverVulkan`）**

```
1. 创建 VkInstance（加载 Vulkan 扩展、启用 surface 扩展）
   ↓
2. 创建 VkSurfaceKHR（把窗口系统句柄转成 Vulkan 表面）
   ↓
3. 枚举物理设备并挑选目标 GPU
   ↓
4. 创建 VkDevice 并取得 VkQueue
   ↓
5. 创建交换链（Swapchain）与命令缓冲
```

**（二）设备 / 队列初始化（`RenderingDeviceDriverVulkan`）**

```
1. 读取物理设备的队列族（queue families）
   ↓
2. 创建逻辑设备 VkDevice
   ↓
3. 取得队列句柄 VkQueue
   ↓
4. 创建命令池 VkCommandPool
   ↓
5. 创建描述符池、渲染通道、管线缓存等 RD 层资源
```

**（三）Pass 依赖由 RenderGraph 描述**

Godot 4.x 不再手写固定的 pass 顺序，而是用 **RenderGraph**（`servers/rendering/rendering_device_graph.h`）声明每个 pass 读写哪些资源，由引擎在运行时推导出执行顺序、屏障（barrier）与资源切换。这正是 4.x 能让 Forward+ 与 Mobile 共用同一套效果代码的原因。

---

## 三、Forward+ 渲染器

### 3.1 什么是 Forward+

Forward+ 是 Godot 4.x 的主要渲染器：

```
传统 Forward 渲染
    ↓
分块光照剔除（+）
    ↓
Forward+ 渲染
```

### 3.2 Forward+ 特点

| 特性 | 说明 |
|------|------|
| **光照** | 每像素光照 |
| **阴影** | PCF 软阴影、PSSM 级联平行阴影 |
| **全局光照** | SDFGI（实时）、LightmapGI / VoxelGI（烘焙） |
| **反射** | SSR、SSIL |
| **雾效** | 体积雾 |

> **没有 VSM**：Godot 4.3 的 `DirectionalLight3D.ShadowMode` 只有 `SHADOW_ORTHOGONAL(0)` / `SHADOW_PARALLEL_2_SPLITS(1)` / `SHADOW_PARALLEL_4_SPLITS(2)` 三种，Godot 3.x 同样没有方差阴影（VSM）。Godot 4 的软阴影来自 PCF + 多重采样（`Light3D.shadow_blur`，以及 `light_size` / `light_angular_distance` 控制的 PCSS）。

### 3.3 源码位置

**基类**：`servers/rendering/renderer_rd/renderer_scene_render_rd.cpp/.h`
**Forward+ 实现**：`servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.cpp/.h`
**Mobile 实现**：`servers/rendering/renderer_rd/forward_mobile/render_forward_mobile.cpp/.h`
**簇构建**：`servers/rendering/renderer_rd/cluster_builder_rd.cpp/.h`

```cpp
// Godot 4.3 源码 - servers/rendering/renderer_rd/forward_clustered/render_forward_clustered.h
namespace RendererSceneRenderImplementation {

class RenderForwardClustered : public RendererSceneRenderRD {
	friend SceneShaderForwardClustered;

	enum RenderListType {
		RENDER_LIST_OPAQUE,    // 不透明物体
		RENDER_LIST_MOTION,    // 需要输出运动矢量的不透明物体
		RENDER_LIST_ALPHA,     // 透明物体
		RENDER_LIST_SECONDARY, // 阴影等次级 pass
		RENDER_LIST_MAX
	};

	// 簇（光源集合）的构建器
	ClusterBuilderRD *cluster_builder = nullptr;

	// ...
	virtual void _render_scene(RenderDataRD *p_render_data, const Color &p_default_bg_color) override;
};

} // namespace RendererSceneRenderImplementation
```

> `servers/rendering/renderer_scene_render_forward.cpp` 在 4.3 **不存在**——4.x 把 Forward+ 与 Mobile 拆到了 `renderer_rd/forward_clustered/` 与 `renderer_rd/forward_mobile/` 两个子目录，公共部分上移到 `renderer_rd/renderer_scene_render_rd.cpp/.h`。

---

## 四、Mobile 渲染器

### 4.1 Mobile 优化

Mobile 渲染器针对移动设备优化：

| 优化 | 说明 |
|------|------|
| **Tile-based** | 分块渲染 |
| **带宽优化** | 减少内存访问 |
| **功耗优化** | 降低功耗 |
| **兼容性** | Vulkan SC 支持 |

### 4.2 Mobile vs Forward+

| 维度 | Forward+ | Mobile |
|------|---------|--------|
| **平台** | PC | 移动设备 |
| **特性** | 完整 | 精简 |
| **性能** | 高性能 | 功耗优化 |
| **带宽** | 高 | 低 |

> Mobile 渲染器为**每个几何实例单独做光照剔除**，而不是构建三维簇。源码中 `RenderForwardMobile::MAX_RDL_CULL = 8` 表示每个物体最多保留 8 个反射探针 / 贴花 / 灯光——这是 **per-object** 上限，灯具一多就容易触顶。

---

## 五、与 Unity Vulkan 对比

### 5.1 对比表

| 维度 | Godot Vulkan | Unity Vulkan |
|------|-------------|--------------|
| **后端** | 自研 | SRP + Vulkan |
| **特性** | Forward+ | URP/HDRP |
| **移动端** | Mobile 渲染器 | Vulkan + ES |
| **自定义** | 需改源码 | Custom SRP |
| **性能** | 优秀 | 优秀 |

### 5.2 代码对比

**Godot 方式**：

```gdscript
# 设置渲染器
# 注意：ProjectSettings 在 4.3 没有 set() 方法，只有 set_setting()。
#       ProjectSettings.set(a, b) 会落到 Object.set(property, value)，
#       把"设置键"当成属性名，结果什么也不会生效。
ProjectSettings.set_setting("rendering/renderer/rendering_method", "forward_plus")

# 移动设备（平台覆盖项）
ProjectSettings.set_setting("rendering/renderer/rendering_method.mobile", "mobile")
```

> **渲染方法在启动时确定**：运行时用 `set_setting()` 改 `rendering/renderer/rendering_method` 不会切换渲染器，必须重启进程（或重启编辑器）才生效。`rendering/renderer/rendering_method.mobile` 与 `.web` 同理，都是启动时读取的平台覆盖项。

**Unity 方式**：

```csharp
// 设置渲染管线
GraphicsSettings.defaultScriptableRenderPipelineType = typeof(UniversalRenderPipeline);
```

---

## 六、RenderingDevice 与 RD 渲染驱动

前六章讲的是 **Vulkan 驱动本身**（`drivers/vulkan/`）。但 Vulkan 只是整条栈里最底下的一层。引擎自己抽象出来的图形层其实有两级，这一章把它们补齐：

```
┌─────────────────────────────────────────────────────────────────┐
│  上层：场景与资源                                               │
│    Node3D / MeshInstance3D / StandardMaterial3D / Shader        │
│    RenderingServer（引擎自有的渲染子系统）                      │
├─────────────────────────────────────────────────────────────────┤
│  中层：现代图形抽象层                                           │
│    RenderingDevice（servers/rendering/rendering_device.h）      │
│      ├─ 命令缓冲 / 计算列表 / 描述符集 / 存储缓冲 / 管线缓存    │
│      └─ RenderGraph（rendering_device_graph.h）描述 pass 依赖   │
├─────────────────────────────────────────────────────────────────┤
│  底层：后端抽象                                                 │
│    RenderingDeviceDriver（rendering_device_driver.h）           │
│      └─ RenderingDeviceDriverVulkan（drivers/vulkan/…）         │
└─────────────────────────────────────────────────────────────────┘
```

### 6.1 `RenderingDevice` 与 `RenderingServer` 的分工

`RenderingDevice` 的类参考摘要只有一句话（`doc/classes/RenderingDevice.xml`）：

> [RenderingDevice] is an abstraction for working with modern low-level graphics APIs such as Vulkan. Compared to [RenderingServer] (which works with Godot's own rendering subsystems), [RenderingDevice] is much lower-level and allows working more directly with the underlying graphics APIs.

| | `RenderingServer` | `RenderingDevice` |
|---|---|---|
| 面向谁 | 引擎内部 + 日常业务代码 | 直接写图形代码的底层用户 |
| 抽象层级 | 引擎自有的渲染子系统（材质、网格、场景实例、后处理） | 贴近 Vulkan / D3D12 / Metal 的命令级 API |
| 能做什么 | 网格 / 材质 / 纹理 / 灯光 / 视口 / 后处理 / 合成器 | 命令缓冲、计算列表、描述符集、管线、存储缓冲、交换链 |
| 谁在用 | 几乎所有游戏项目 | 自定义 compute、自定义 GPU 后处理、高级工具链 |

**全局 RD 与本地 RD**：引擎启动时会创建一个全局 `RenderingDevice`，用 `RenderingServer.get_rendering_device()` 取回。

```gdscript
var rd := RenderingServer.get_rendering_device()   # 全局 RD，负责画到屏幕
```

还可以另外创建"本地" RD，让它在**独立线程**上跑 compute：

```gdscript
var local_rd := RenderingServer.create_local_rendering_device()
```

`create_local_rendering_device()` 的官方说明写得很清楚：

> Creates a RenderingDevice that can be used to do draw and compute operations on a separate thread. **Cannot draw to the screen nor share data with the global RenderingDevice.**

### 6.2 `RenderingDeviceDriver`：后端抽象

`RenderingDeviceDriver`（`servers/rendering/rendering_device_driver.h:120`）是一个**纯虚接口**：

```cpp
// Godot 4.3 源码 - servers/rendering/rendering_device_driver.h:120
class RenderingDeviceDriver : public RenderingDeviceCommons {
public:
	// 资源
	virtual BufferID buffer_create(uint64_t p_size, BitField<BufferUsageBits> p_usage,
								MemoryAllocationType p_allocation_type) = 0;
	virtual TextureID texture_create(const TextureFormat &p_format, const TextureView &p_view) = 0;
	// 队列与命令
	virtual CommandQueueID command_queue_create(CommandQueueFamilyID p_family, bool p_as_main = false) = 0;
	virtual CommandBufferID command_buffer_create(CommandPoolID p_cmd_pool) = 0;
	// 描述符集
	virtual UniformSetID uniform_set_create(VectorView<BoundUniform> p_uniforms,
											 ShaderID p_shader, uint32_t p_set_index) = 0;
	// 管线缓存
	virtual bool pipeline_cache_create(const Vector<uint8_t> &p_data) = 0;
	// ...
};
```

`RenderingDeviceDriverVulkan`（`drivers/vulkan/rendering_device_driver_vulkan.h:50`）是它的 Vulkan 实现：

```cpp
// Godot 4.3 源码 - drivers/vulkan/rendering_device_driver_vulkan.h:50
class RenderingDeviceDriverVulkan : public RenderingDeviceDriver {
	struct Queue {
		VkQueue queue = VK_NULL_HANDLE;
		uint32_t virtual_count = 0;
		BinaryMutex submit_mutex;
	};
	...
	VkDevice vk_device = VK_NULL_HANDLE;
	RenderingContextDriverVulkan *context_driver = nullptr;
	TightLocalVector<TightLocalVector<Queue>> queue_families;
	PipelineCache pipelines_cache;
};
```

> 📌 **对第 2.2 节那段类体示意的一处更正**：真实结构里**没有**一个裸的 `VkQueue queue;` 成员，也没有 `VkCommandPool vk_command_pool;` 这样的裸 Vulkan 句柄成员。队列是 `TightLocalVector<TightLocalVector<Queue>> queue_families` —— **先按 queue family 分组，再按虚拟队列（virtual queue）展开**；命令池在驱动层被抽象成了 `RDD::CommandPoolID`，真正的 `VkCommandPool` 藏在实现内部。

### 6.3 两层的接口形状

| 概念 | `RenderingDevice`（脚本可用） | `RenderingDeviceDriver`（C++ 纯虚） |
|------|------------------------------|-----------------------------------|
| 命令缓冲 | `draw_list_begin()` / `draw_list_end()` / `draw_list_draw()` | `command_buffer_create()` / `command_buffer_begin()` / `command_buffer_end()` |
| 计算列表 | `compute_list_begin()` / `compute_list_dispatch()` / `compute_list_end()` | `command_bind_compute_pipeline()` / `command_compute_dispatch()` |
| 描述符集 | `uniform_set_create(uniforms, shader, set_index)` | `uniform_set_create(VectorView<BoundUniform>, ShaderID, uint32_t)` |
| 存储缓冲 | `storage_buffer_create(size, data, usage)` | `buffer_create(size, usage, allocation_type)` |
| 纹理格式 | `texture_create(format, view)` / `texture_is_format_supported_for_usage()` | `texture_create(TextureFormat, TextureView)` |
| 管线 | `render_pipeline_create()` / `compute_pipeline_create()` | 由驱动侧管线缓存与 `PipelineCache` 承接 |
| 资源回收 | `free_rid(rid)` | 各 `*_free()` 家族 |

几个容易踩的点，全部来自官方类参考：

- **`barrier()` 与 `full_barrier()` 是空操作**，而且已被标记为 deprecated：
  > This method does nothing. （deprecated 原因："Barriers are automatically inserted by RenderingDevice."）
- **`submit()` 与 `sync()` 只在本地 RD 上可用**：
  > Pushes the frame setup and draw command buffers then marks the local device as currently processing (which allows calling [method sync]). [b]Note:[/b] Only available in local RenderingDevices.
  > `sync()` — Forces a synchronization between the CPU and GPU, which may be required in certain cases. Only call this when needed, as CPU-GPU synchronization has a performance cost.
- **`draw_list_begin_for_screen()` 在本地 RD 上返回 `INVALID_ID`**（本地 RD 没有屏幕）。
- **`get_frame_delay()`**：主 RD 在三缓冲 V-Sync 下通常是 3，本地 RD 只有 1。

### 6.4 `RenderGraph`：用依赖关系描述 pass

4.x 不再手写固定的 pass 顺序，而是用 **RenderGraph** 声明"每个 pass 读写哪些资源"，由引擎推导出执行顺序、屏障与资源切换。

```cpp
// Godot 4.3 源码 - servers/rendering/rendering_device_graph.h:46
class RenderingDeviceGraph {
public:
	...
	void begin();
	void add_compute_list_bind_uniform_set(RDD::ShaderID p_shader, RDD::UniformSetID p_uniform_set, uint32_t set_index);
	void add_compute_list_end();
	void add_draw_list_bind_pipeline(RDD::PipelineID p_pipeline, BitField<RDD::PipelineStageBits> p_pipeline_stage_bits);
	...
};
```

每个 `add_*` 调用都带着**资源追踪器**（`ResourceTracker *`）与**资源用途**（`ResourceUsage`），例如：

```cpp
						 Rect2i p_region, VectorView<RDD::RenderPassClearValue> p_clear_values,
						 bool p_uses_color, bool p_uses_depth);
```

Graph 据此算出"写 → 读"的先后关系，并在需要时插入资源状态转换与屏障。**这正是 Forward+ 与 Mobile 能共用同一套后处理代码的原因**：两者只是"声明了不同的 pass 图"，而不是"走了两条硬编码的分支"。

### 6.5 两条硬限制：headless 与 Compatibility

`doc/classes/RenderingDevice.xml` 的 Note 段原文：

> [b]Note:[/b] [RenderingDevice] is not available when running in headless mode or when using the Compatibility rendering method.

也就是说：

| 运行模式 | `RenderingDevice` 可用？ | 原因 |
|----------|----------------------|------|
| Forward+（Vulkan / D3D12 / Metal） | ✅ | 走 RD 通路 |
| Mobile（Vulkan / D3D12 / Metal） | ✅ | 同上，只是渲染器不同 |
| Compatibility（OpenGL 3.3 / GLES 3 / WebGL 2） | ❌ | 不经过 RD，走 OpenGL 直通路径 |
| headless（`--headless`） | ❌ | 没有图形设备 |
| Web（WebGL 2） | ❌ | 同 Compatibility |

> ⚠️ 这意味着**任何依赖 `RenderingDevice` 的代码，在 Compatibility 与 headless 下都不能运行**。如果你的项目要同时支持 Web，就必须为这些路径准备降级方案（例如用 `Image` + `Texture2D` 的 CPU 端替代）。

### 6.6 实操建议：什么时候才该直接用 RD

**绝大多数项目不应该碰 `RenderingDevice`。** 正确的抽象层级是：

| 需求 | 推荐的抽象层级 |
|------|--------------|
| 换贴图、改颜色、改粗糙度 | `StandardMaterial3D` / `ORMMaterial` 的属性 |
| 改光照响应、写自定义 BRDF | `.gdshader`（`shader_type spatial`） |
| 后处理（泛光、景深、色调映射） | `Environment` 资源上的开关 |
| 自定义后处理 pass | `Compositor` + `CompositorEffect`（见第 14 篇第五章） |
| 大量重复物体 | `MultiMesh` / `MultiMeshInstance3D` |
| 粒子、天空、体积雾、SSAO | `Environment` / `GPUParticles3D` / `Sky` 资源 |
| **自定义 compute**（物理、流体、AI 群体、GPU 剔除） | ✅ `RenderingDevice` + `compute` 着色器 |
| **完全自管渲染管线**（自研后处理链、自定义延迟渲染） | ✅ `RenderingDevice` |

`RenderingDevice` 的官方描述也把它的定位说得很清楚：

> [RenderingDevice] can also be used in your own projects to perform things that are not exposed by [RenderingServer] or high-level nodes, such as using compute shaders.

一个最小可用的 compute 骨架（**只在 Forward+/Mobile 下可用**）：

```glsl
// 计算着色器写在 .gdshader 文件里，shader_type compute。
// Godot 4 没有 ComputeShader 资源类，也没有 @compute_shader 注解——
// 着色器只能由 RenderingDevice 从预编译的 SPIR-V 装载。
shader_type compute;

@group(0) @binding(0) var<storage, read_write> data : array<float>;

void compute() {
    for (uint i = 0u; i < data.size(); i++) {
        data[i] = data[i] * 2.0;
    }
}
```

```gdscript
var rd := RenderingServer.get_rendering_device()

# 1) 拿到 SPIR-V：.glsl / .spirv 导入后是 RDShaderFile 资源
var rd_file: RDShaderFile = load("res://my_compute.glsl")
var spirv := rd_file.get_spirv()          # Dictionary：stage → SPIR-V 字节
var shader := rd.shader_create_from_spirv(spirv)

# 2) 建资源：存储缓冲、uniform set、compute 管线
var buf := rd.storage_buffer_create(data_size)
var uniform_set := rd.uniform_set_create(uniforms, shader, 0)
var pipeline := rd.compute_pipeline_create(shader)

# 3) 录制计算列表并派发
var list := rd.compute_list_begin()
rd.compute_list_bind_compute_pipeline(list, pipeline)
rd.compute_list_bind_uniform_set(list, uniform_set, 0)
rd.compute_list_dispatch(list, groups_x, groups_y, groups_z)
rd.compute_list_end()
```

> `RDShaderFile` 在 4.3 只提供 `get_spirv()` / `get_version_list()` / `set_bytecode()` 三个成员；`RDShaderFile.get_spirv()` 返回的是"stage → SPIR-V 字节"的字典，而 `RenderingDevice.shader_create_from_spirv()` 接收的是 `Vector[ShaderStageSPIRVData]`，两者之间需要你自己做一次格式转换。

> 💡 **性能提示**：`RenderingDevice` 的资源是 **RID 引用计数**，`free_rid()` 不会被自动调用，忘记释放会泄漏。同时本地 RD 的 `submit()` / `sync()` 会强制 CPU-GPU 同步，代价不低。

### 6.7 命令队列模型：族、虚拟队列与提交互斥

前面 §2.2 摆出了驱动里的队列结构，但没说清"为什么要这么绕"。这一节把它讲透。

**Vulkan 侧的硬性事实**：队列不是一条，而是**按队列族（queue family）分组**的。每个队列族由 VkQueueFamilyProperties 描述它**是否支持** graphics / compute / transfer / 光线追踪等能力。显卡通常只提供 1~3 个族：

| 队列族 | 常见能力 | 典型用途 |
|--------|----------|----------|
| Graphics | graphics + compute + transfer | 主渲染队列（画面 + 阴影 + 后处理） |
| Compute | compute + transfer | 独立计算队列（compute shader、GPU 剔除） |
| Transfer | transfer | 显存搬运（资源上传 / 回读） |

**Godot 在这之上又加了一层"虚拟队列"**：

```cpp
// Godot 4.3 源码 - drivers/vulkan/rendering_device_driver_vulkan.h
class RenderingDeviceDriverVulkan : public RenderingDeviceDriver {
	struct Queue {
		VkQueue queue = VK_NULL_HANDLE;   // 真实的 Vulkan 队列句柄
		uint32_t virtual_count = 0;        // 这个族里有多少条"逻辑队列"
		BinaryMutex submit_mutex;          // 同一族内的提交互斥
	};
	// 先按族分组，再按族内逻辑队列展开
	TightLocalVector<TightLocalVector<Queue>> queue_families;
	// ...
};
```

| 结构 | 含义 | 为什么需要 |
|------|------|-----------|
| `queue_families`（外层） | 队列**族** | 能力由族决定；同族队列能力完全相同 |
| `queue_families`（内层） | 族内的**逻辑队列** | 显卡常常给同一个族分配多条物理队列；Godot 把它们合并成一条逻辑队列并行使用 |
| `virtual_count` | 这条逻辑队列背后有几条物理队列 | 决定理论并行度 |
| `submit_mutex` | 提交互斥锁 | 同一逻辑队列上的提交必须串行，否则 Vulkan 会报"队列正在使用" |

> 💡 **一句话总结**：Vulkan 的队列是"按能力分组、组内多条"；Godot 把同能力的若干条物理队列**虚拟化成一条逻辑队列**，用 `submit_mutex` 保证提交串行、用 `virtual_count` 记录背后有多少条硬件队列可以并行工作。
>
> 这也解释了为什么 4.3 的驱动里**没有** `graphics_queue` / `compute_queue` 两个成员 —— "计算队列"是由**队列族的 `queueFlags`** 决定的，不是两个成员变量。

**脚本层能观察到的队列信息**：

| 接口 | 含义 |
|------|------|
| `RenderingDevice.get_frame_delay()` | 图形 API 保留的帧数；主 RD 在三缓冲 VSync 下通常是 3，本地 RD 只有 1 |
| `RenderingDevice.get_driver_resource(RenderingDevice.DRIVER_RESOURCE_QUEUE_FAMILY)` | 取队列族索引（底层对象 ID） |
| `RenderingDevice.get_driver_resource(RenderingDevice.DRIVER_RESOURCE_COMMAND_QUEUE)` | 取命令队列的底层 ID |

### 6.8 命令缓冲、命令池与"屏障是自动插入的"

**两层命令模型**：

| 层 | 脚本可见 | C++ 驱动可见 |
|----|----------|--------------|
| 列表 | `draw_list_begin()` → `draw_list_end()`；`compute_list_begin()` → `compute_list_end()` | `command_buffer_create()` / `command_buffer_begin()` / `command_buffer_end()` |
| 提交 | `submit()`（仅本地 RD） | `command_buffer_submit()` + `vkQueueSubmit` |
| 屏障 | `barrier()` / `full_barrier()`（**均为空操作**） | `command_barrier()` → `vkCmdPipelineBarrier` |

**最反直觉的一点：屏障不需要你写。**

官方类参考对 `barrier()` 的说明原文是：

> This method does nothing.

并标注了废弃原因：

> Barriers are automatically inserted by RenderingDevice.

也就是说：**资源状态转换与屏障由 `RenderingDevice` / `RenderGraph` 依据 pass 之间的读写关系自动推导并插入**。你在脚本里写 `barrier()` 不会报错，但什么也不会发生（方法已标记为 deprecated）。

**那"读一张刚写入的纹理"这种依赖怎么表达？** 靠**描述资源的读写用途**，而不是靠手写屏障：

| 机制 | 作用 | 典型取值 |
|------|------|----------|
| `RenderingDevice.InitialAction` | pass **开始前**帧缓冲附件的状态 | `INITIAL_ACTION_CLEAR` / `INITIAL_ACTION_LOAD` / `INITIAL_ACTION_DISCARD` / `INITIAL_ACTION_KEEP` / `INITIAL_ACTION_CONTINUE` / `INITIAL_ACTION_DROP` |
| `RenderingDevice.FinalAction` | pass **结束后**帧缓冲附件的状态 | `FINAL_ACTION_STORE` / `FINAL_ACTION_DISCARD` / `FINAL_ACTION_READ` / `FINAL_ACTION_CONTINUE` |
| `RenderingDevice.BarrierMask` | 队列级屏障的作用域 | `BARRIER_MASK_RASTER` / `BARRIER_MASK_COMPUTE` / `BARRIER_MASK_VERTEX` / `BARRIER_MASK_FRAGMENT` / `BARRIER_MASK_TRANSFER` / `BARRIER_MASK_ALL_BARRIERS` / `BARRIER_MASK_NO_BARRIER` |

> ⚠️ `RenderingDevice.InitialAction` / `RenderingDevice.FinalAction` 描述的是**渲染目标附件**在 pass 前后的状态（要不要 clear / 要不要保留内容），`RenderingDevice.BarrierMask` 描述的是**队列级**的同步域。两者不是一回事：前者决定"这份数据还在不在"，后者决定"谁和谁之间需要同步"。

**这条设计带来的直接收益**：Forward+ 与 Mobile 共用同一套后处理代码（见 §6.4），因为它们只是"声明了不同的 pass 图"，而不是"走了两条硬编码的分支"。如果换成一个手写屏障的引擎，每加一个后处理效果就要在两个渲染器里各写一遍同步逻辑。

### 6.9 资源布局：uniform set 与它的九种类型

RD 的资源绑定模型只有两层：**uniform set**（描述符集的等价物）+ **vertex / index array**（顶点输入）。

**一个 uniform set 描述"某个 set 编号下的一组绑定"**：

```gdscript
# 一个 RDUniform = 一个绑定点
var u := RDUniform.new()
u.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER  # 这个绑定点是什么类型
u.binding = 0                                                      # 对应 shader 里的 @binding(0)
u.add_id(buffer_rid)                                               # 绑哪个资源
```

`RDUniform` 的四个成员：

| 成员 | 作用 |
|------|------|
| `uniform_type` | 绑定点的类型（决定着色器怎么读它） |
| `binding` | 绑定点编号，对应 shader 里的 `@binding(N)` |
| `add_id(rid)` | 把一个 RD 资源加入这个绑定点 |
| `clear_ids()` / `get_ids()` | 清空 / 读取已加入的资源列表 |

**九种 uniform 类型**（`RenderingDevice.UniformType`）：

| 类型 | 用途 | 着色器侧对应 |
|------|------|-------------|
| `UNIFORM_TYPE_SAMPLER` | 纯采样器 | `sampler2D` 之类 |
| `UNIFORM_TYPE_SAMPLER_WITH_TEXTURE` | 采样器 + 纹理打包成一个绑定 | `sampler2D` + `texture2D` 组合 |
| `UNIFORM_TYPE_TEXTURE` | 只读纹理（不可写） | `texture2D` |
| `UNIFORM_TYPE_IMAGE` | 可写存储纹理 | `image2D` |
| `UNIFORM_TYPE_TEXTURE_BUFFER` | 只读存储缓冲 | `buffer`（只读） |
| `UNIFORM_TYPE_SAMPLER_WITH_TEXTURE_BUFFER` | 采样器 + 只读存储缓冲 | 组合绑定 |
| `UNIFORM_TYPE_IMAGE_BUFFER` | 可写存储缓冲 | `buffer`（可写） |
| `UNIFORM_TYPE_UNIFORM_BUFFER` | Uniform Buffer（UBO） | `uniform` 块 |
| `UNIFORM_TYPE_INPUT_ATTACHMENT` | 输入附件（帧缓冲内读） | 输入附件 |

**不经过 uniform set 的资源**：

| 资源 | 绑定方式 |
|------|----------|
| 顶点缓冲 | `vertex_buffer_create()` → `vertex_array_create()` → `draw_list_bind_vertex_array()` |
| 索引缓冲 | `index_buffer_create()` → `index_array_create()` → `draw_list_bind_index_array()` |
| 顶点格式 | `vertex_format_create()`（描述顶点里有哪些属性、偏移与步长） |
| Push constant | `draw_list_set_push_constant()` / `compute_list_set_push_constant()`（小数据走常量缓冲，比 UBO 便宜） |

**必须提前查的限制**（建资源前先问驱动）：

| 限制项 | 含义 |
|--------|------|
| `RenderingDevice.LIMIT_MAX_BOUND_UNIFORM_SETS` | 一个着色器最多绑定几个 set |
| `RenderingDevice.LIMIT_MAX_TEXTURES_PER_UNIFORM_SET` | 一个 set 里最多几个纹理 |
| `RenderingDevice.LIMIT_MAX_SAMPLERS_PER_UNIFORM_SET` | 一个 set 里最多几个采样器 |
| `RenderingDevice.LIMIT_MAX_STORAGE_BUFFERS_PER_UNIFORM_SET` | 一个 set 里最多几个存储缓冲 |
| `RenderingDevice.LIMIT_MAX_UNIFORM_BUFFERS_PER_UNIFORM_SET` | 一个 set 里最多几个 UBO |
| `RenderingDevice.LIMIT_MAX_UNIFORM_BUFFER_SIZE` | 单个 UBO 的最大字节数 |
| `RenderingDevice.LIMIT_MAX_PUSH_CONSTANT_SIZE` | 单个 push constant 的最大字节数 |

```gdscript
# 建资源之前先问驱动
var max_sets: int = rd.limit_get(RenderingDevice.LIMIT_MAX_BOUND_UNIFORM_SETS)
var max_ubo: int = rd.limit_get(RenderingDevice.LIMIT_MAX_UNIFORM_BUFFER_SIZE)
print("最多绑定 set 数：", max_sets, "，UBO 上限：", max_ubo, " 字节")
```

### 6.10 纹理格式与用法位

RD 的纹理描述由两个 RefCounted 资源组成：

| 资源 | 成员 | 作用 |
|------|------|------|
| `RDTextureFormat` | `width` / `height` / `depth` / `mipmaps` / `array_layers` / `format` / `texture_type` / `usage_bits` / `samples` | 描述纹理的**规格** |
| `RDTextureView` | `format_override` / `swizzle_r` / `swizzle_g` / `swizzle_b` / `swizzle_a` | 描述**怎么看**这张纹理（视图） |

```gdscript
var fmt := RDTextureFormat.new()
fmt.width = 256
fmt.height = 256
fmt.format = RenderingDevice.DATA_FORMAT_R8G8B8A8_UNORM
fmt.texture_type = RenderingDevice.TEXTURE_TYPE_2D
fmt.usage_bits = RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT | RenderingDevice.TEXTURE_USAGE_CAN_UPDATE_BIT

var view := RDTextureView.new()
var tex: RID = rd.texture_create(fmt, view)
```

**格式（`RenderingDevice.DataFormat`）** 三大类：

| 类别 | 代表格式 | 说明 |
|------|----------|------|
| 未压缩 | `DATA_FORMAT_R8G8B8A8_UNORM` / `DATA_FORMAT_R16G16B16A16_SFLOAT` / `DATA_FORMAT_R32G32B32A32_SFLOAT` | 通用；HDR 用浮点，压缩用 8 位 |
| 深度模板 | `DATA_FORMAT_D32_SFLOAT` / `DATA_FORMAT_D24_UNORM_S8_UINT` / `DATA_FORMAT_X8_D24_UNORM_PACK32` | 深度缓冲与模板 |
| 块压缩 | `DATA_FORMAT_BC1_RGB_UNORM_BLOCK` ~ `DATA_FORMAT_BC7_SRGB_BLOCK`（BC 系列）、`DATA_FORMAT_ETC2_*_BLOCK` / `DATA_FORMAT_EAC_*_BLOCK`（ETC/EAC）、`DATA_FORMAT_ASTC_*_BLOCK`（ASTC） | 显存友好；**具体支持哪些取决于设备** |

**用法位（`RenderingDevice.TextureUsageBits`）决定这张纹理能被怎么用**：

| 用法位 | 含义 | 典型用途 |
|--------|------|----------|
| `TEXTURE_USAGE_SAMPLING_BIT` | 可被采样器读取 | 常规材质贴图 |
| `TEXTURE_USAGE_COLOR_ATTACHMENT_BIT` | 可作颜色附件 | 渲染目标 |
| `TEXTURE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT` | 可作深度/模板附件 | 深度缓冲 |
| `TEXTURE_USAGE_STORAGE_BIT` | 可作存储纹理读写 | compute 的读写目标 |
| `TEXTURE_USAGE_STORAGE_ATOMIC_BIT` | 支持原子操作 | compute 的原子累加 |
| `TEXTURE_USAGE_CPU_READ_BIT` | 可回读到 CPU | 结果取回 |
| `TEXTURE_USAGE_CAN_UPDATE_BIT` | 可被 `texture_update()` 更新 | 动态贴图 |
| `TEXTURE_USAGE_CAN_COPY_FROM_BIT` / `TEXTURE_USAGE_CAN_COPY_TO_BIT` | 可参与拷贝 | 纹理搬运 |
| `TEXTURE_USAGE_INPUT_ATTACHMENT_BIT` | 可作输入附件 | 帧缓冲内读 |

> ⚠️ **用法位不是越多越好**：每多一个位，就多一条驱动要满足的约束。在移动端与 Compatibility 路径上，**建纹理之前必须先查支持情况**：

```gdscript
# 建之前先问：设备支持这个格式 + 这组用法吗？
if rd.texture_is_format_supported_for_usage(
        RenderingDevice.DATA_FORMAT_BC7_SRGB_BLOCK,
        RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT):
    print("支持 BC7 sRGB 采样")
else:
    print("不支持，退回未压缩格式")
```

**采样器（`sampler_create()`）** 的三个关键维度：

| 维度 | 枚举 | 取值 |
|------|------|------|
| 过滤 | `RenderingDevice.SamplerFilter` | `SAMPLER_FILTER_NEAREST` / `SAMPLER_FILTER_LINEAR` |
| 重复 | `RenderingDevice.SamplerRepeatMode` | `SAMPLER_REPEAT_MODE_REPEAT` / `MIRRORED_REPEAT` / `CLAMP_TO_EDGE` / `CLAMP_TO_BORDER` / `MIRROR_CLAMP_TO_EDGE` |
| 过滤兼容性 | — | `sampler_is_format_supported_for_filter(format, filter)` 告诉你某格式能不能用线性过滤 |

> ⚠️ 块压缩格式 + 线性过滤在部分设备上是**硬件降级**的（甚至不支持）。用 `sampler_is_format_supported_for_filter()` 查一次，比上线后看到"贴图糊了"再回头找要快得多。

**多重采样**：`RDTextureFormat.samples` 取 `RenderingDevice.TextureSamples`（`TEXTURE_SAMPLES_1` ~ `TEXTURE_SAMPLES_64`），解析用 `texture_resolve_multisample()`。

**共享与互操作**：

| 方法 | 用途 |
|------|------|
| `texture_create_shared()` / `texture_create_shared_from_slice()` | 把已有纹理（或它的一部分）暴露给 RD，用于跨 API 共享 |
| `texture_is_shared()` | 判断是否共享纹理 |
| `texture_create_from_extension()` | 接管**外部 API** 创建的纹理句柄（Vulkan 互操作等） |
| `texture_get_native_handle()` | 取底层原生句柄（给第三方库用） |

### 6.11 显存、堆与本地 RD

**脚本层能查到的显存口径**：

```gdscript
# 三种口径，单位：字节
var tex_bytes: int = rd.get_memory_usage(RenderingDevice.MEMORY_TEXTURES)
var buf_bytes: int = rd.get_memory_usage(RenderingDevice.MEMORY_BUFFERS)
var total: int = rd.get_memory_usage(RenderingDevice.MEMORY_TOTAL)
```

| `RenderingDevice.MemoryType` | 含义 |
|---------------------------|------|
| `MEMORY_TEXTURES` | 纹理占用 |
| `MEMORY_BUFFERS` | 缓冲占用 |
| `MEMORY_TOTAL` | 总量 |

> ⚠️ 这是**占用量**，不是预算，也不是"还能再放多少"。引擎内部的显存预算与流式加载策略由渲染器与驱动决定，4.3 的 `RenderingDevice` **没有把预算值暴露给脚本**。想知道"离上限还有多远"，实践中的做法是：在目标机型上跑一遍最重的场景，看 `MEMORY_TOTAL` 的峰值，再和该机型的可用显存做减法。

**分配策略在 C++ 层**（脚本层选不了）：

| 分配类型 | 含义 | 典型用途 |
|----------|------|----------|
| 设备本地（device local） | 只能被 GPU 访问，显存中最快 | 渲染目标、频繁采样的贴图 |
| 主机可见（host visible） | CPU 可直接读写，PCIe 访问 | 需要频繁回读 / 上传的缓冲 |
| 共享（shared） | 两者皆可，速度折中 | 通用缓冲 |
| CPU 内存 | 纯 CPU 内存 | 极冷数据 |

> 这套分配类型是 `RenderingDeviceDriver` 层的概念（`RDD::MemoryAllocationType`），**脚本层没有对应参数** —— 脚本创建的资源由引擎按用途自动选。所以"我想让这个缓冲留在显存里"在脚本层是做不到的，只能通过用途（是否被采样、是否被 compute 写）间接影响。

**全局 RD 与本地 RD**：

| | 全局 RD | 本地 RD |
|---|---------|---------|
| 获取方式 | `RenderingServer.get_rendering_device()` | `RenderingServer.create_local_rendering_device()` 或 `RenderingDevice.create_local_device()` |
| 线程 | 渲染线程 | 自己指定的独立线程 |
| 能否画到屏幕 | ✅ | ❌（`draw_list_begin_for_screen()` 在本地 RD 上返回 `INVALID_ID`） |
| 能否与全局 RD 共享数据 | — | ❌ 官方明确写 "Cannot draw to the screen nor share data with the global RenderingDevice" |
| 帧延迟 | 通常 3（三缓冲 VSync） | 1 |
| `submit()` / `sync()` | ❌ 不可用 | ✅ 可用 |

```gdscript
# 本地 RD：独立线程上跑 compute，不影响主渲染线程
var local_rd: RenderingDevice = RenderingServer.create_local_rendering_device()
print("本地 RD 帧延迟：", local_rd.get_frame_delay())   # 恒为 1
```

> 💡 **本地 RD 的典型用途**：把"与画面无关的重计算"（路径规划预计算、网格处理、离线烘焙）挪到独立线程，让它和渲染线程各跑各的，互不阻塞。代价是**不能共享数据** —— 你得自己用文件或网络把结果搬回来。

### 6.12 能力查询接口

在写任何 RD 代码之前，先把"这台设备能做什么"问清楚。4.3 提供了四组查询接口：

| 接口 | 回答什么问题 | 典型用途 |
|------|--------------|----------|
| `limit_get(limit, p_default)` | 某个上限值是多少 | UBO 大小、set 数量、纹理尺寸、compute workgroup 尺寸 |
| `get_device_name()` / `get_device_vendor_name()` | 这是什么卡 | 日志与 bug 报告 |
| `get_device_pipeline_cache_uuid()` | 管线缓存的唯一标识 | 判断"能不能复用别人的管线缓存" |
| `get_driver_resource(driver_resource, p_index)` | 底层对象 ID | 与外部工具 / 互操作层对接 |

**`RenderingDevice.Limit` 枚举的常用项**：

| 限制 | 含义 |
|------|------|
| `LIMIT_MAX_TEXTURE_SIZE_2D` / `_3D` / `_1D` | 单张纹理的最大边长 |
| `LIMIT_MAX_TEXTURE_ARRAY_LAYERS` | 纹理数组最大层数 |
| `LIMIT_MAX_UNIFORM_BUFFER_SIZE` | 单个 UBO 上限 |
| `LIMIT_MAX_PUSH_CONSTANT_SIZE` | push constant 上限 |
| `LIMIT_MAX_VERTEX_INPUT_ATTRIBUTES` / `LIMIT_MAX_VERTEX_INPUT_BINDINGS` | 顶点属性与绑定槽上限 |
| `LIMIT_MAX_COMPUTE_WORKGROUP_SIZE_X` / `_Y` / `_Z` | compute workgroup 尺寸上限 |
| `LIMIT_MAX_COMPUTE_WORKGROUP_COUNT_X` / `_Y` / `_Z` | compute 派发组数上限 |
| `LIMIT_MAX_COMPUTE_SHARED_MEMORY_SIZE` | compute 共享内存上限 |
| `LIMIT_MAX_FRAMEBUFFER_COLOR_ATTACHMENTS` | 颜色附件数量上限 |

```gdscript
# 一次性把关键上限打出来，写进日志便于排查
for limit in [
    RenderingDevice.LIMIT_MAX_TEXTURE_SIZE_2D,
    RenderingDevice.LIMIT_MAX_UNIFORM_BUFFER_SIZE,
    RenderingDevice.LIMIT_MAX_BOUND_UNIFORM_SETS,
    RenderingDevice.LIMIT_MAX_COMPUTE_WORKGROUP_SIZE_X,
]:
    print(limit, " = ", rd.limit_get(limit))
```

**命名资源**：`set_resource_name(rid, name)` 给 RD 资源起名字。这个名字会出现在 RenderDoc、驱动调试器与引擎日志里 —— 排查"到底是哪个资源炸了"时非常有用。

```gdscript
rd.set_resource_name(buffer, "MyComputeOutput")
```

### 6.13 Vulkan 驱动里的对应物

把 RD 的抽象和 Vulkan 的对象对一遍，就知道 Godot 的封装"藏"了什么（下表的 Vulkan 类型名按 Khronos 官方写法）：

| RD 概念 | Vulkan 对象 | 说明 |
|----------|------------|------|
| 逻辑设备 | VkDevice | 驱动成员 `vk_device` |
| 物理设备 | VkPhysicalDevice | 通过 `DRIVER_RESOURCE_PHYSICAL_DEVICE` 取 ID |
| 队列（族 + 虚拟队列） | VkQueue + VkQueueFamilyProperties | 见 §6.7 |
| 命令池 | VkCommandPool | 每条队列一个，驱动内部管理 |
| 命令缓冲 | VkCommandBuffer | 对应 RD 的命令列表 |
| 描述符池 / 描述符集 | VkDescriptorPool / VkDescriptorSet | 对应 RD 的 uniform set |
| 管线缓存 | VkPipelineCache | 驱动成员 `pipelines_cache` |
| 着色器模块 | VkShaderModule | 由 SPIR-V 创建 |
| 缓冲 | VkBuffer + VkDeviceMemory | RD 侧只暴露 RID |
| 纹理 | VkImage + VkImageView + VkSampler | RD 侧拆成三个概念 |
| 帧缓冲 | VkFramebuffer + VkRenderPass | 4.3 用显式 RenderPass 模型 |
| 屏障 | vkCmdPipelineBarrier | 由引擎自动插入（见 §6.8） |
| 提交 | vkQueueSubmit + VkFence | 同一逻辑队列内由 `submit_mutex` 串行化 |

> 💡 **这张表最有价值的一行是"纹理"**：Vulkan 把纹理拆成 image / view / sampler 三件套，RD 也照做了（`RDTextureFormat` / `RDTextureView` / `sampler_create()`）。理解了这层拆分，就能理解为什么"同一个 `RDTextureFormat` 可以配多个 `RDTextureView`"（例如同一张 BC7 纹理，既当普通贴图采样，又当 3D 贴图的切片视图）。

### 6.14 RD 的能力边界

| 需求 | 该用哪一层 | 理由 |
|------|-----------|------|
| 改贴图 / 改颜色 / 改粗糙度 | `StandardMaterial3D` / `BaseMaterial3D` 属性 | RD 抽象层级太低，收益为负 |
| 自定义 BRDF、参与引擎光照 | `.gdshader`（`shader_type spatial`） | 引擎光照通过内置变量参与 |
| 泛光 / 景深 / 色调映射 | `Environment` 上的开关 | 引擎已内建 |
| 自定义后处理 pass | `Compositor` + `CompositorEffect` | 比裸 RD 简单得多（见第 19 篇） |
| 大量重复物体 | `MultiMesh` / `MultiMeshInstance3D` | 实例化是引擎内建能力 |
| 粒子 / 天空 / 体积雾 | `GPUParticles3D` / `Sky` / `Environment` | 同上 |
| **自定义 compute**（物理、流体、群体 AI、GPU 剔除） | ✅ `RenderingDevice` + `shader_type compute` | RD 的主场 |
| **完全自管渲染管线**（自研后处理链、自定义延迟渲染） | ✅ `RenderingDevice` | 需要自己管描述符集、管线、屏障 |

> ⚠️ 每次跨过"用不用 RD"这条线，都要重新检查 §6.5 的两条硬限制：**Compatibility 渲染器与 headless 模式下 `RenderingDevice` 不可用**。Web 导出、服务器端模拟、单元测试 —— 这些环境里 RD 路径的代码必须能被优雅降级。

---

## 七、RD 实战：从 SPIR-V 到一次 compute 派发

前面六节讲的是"是什么"，这一节讲"怎么用一次"。

### 7.1 着色器的三种来源

| 来源 | 接口 | 适用场景 |
|------|------|----------|
| 预编译 SPIR-V | `.glsl` / `.spirv` 导入成 `RDShaderFile` → `get_spirv()` → `shader_create_from_spirv()` | **生产环境的正解**：着色器随资源打包，运行时不编译 |
| 运行时编译源码 | `shader_compile_spirv_from_source()` | 开发期工具链；4.3 已提供，但是否在导出包中可用取决于构建配置 |
| 字节码 / 管线缓存 | `shader_create_from_bytecode()`、`get_device_pipeline_cache_uuid()` | 跨机器复用编译结果，省首次编译卡顿 |
| 占位符 | `shader_create_placeholder()` | 先占住 RID，之后再填内容（引擎内部大量使用） |

> ⚠️ `RDShaderFile.get_spirv()` 返回的是"**stage → SPIR-V 字节**"的字典，而 `RenderingDevice.shader_create_from_spirv()` 接收的是 `Vector[ShaderStageSPIRVData]`。两者之间需要你自己做一次格式转换 —— 这一点 `RDShaderFile` 的类参考里没有明说，是最容易卡住新人的地方。

### 7.2 资源准备

RD 的资源准备顺序是固定的：**先建资源 → 再建 uniform set → 再建管线**。

```gdscript
# 1) 存储缓冲：算出大小，填入初始数据
var data := PackedFloat32Array([1.0, 2.0, 3.0, 4.0])
var buffer: RID = rd.storage_buffer_create(data.size() * 4, data)
rd.set_resource_name(buffer, "MyComputeData")

# 2) uniform：把缓冲绑到 binding 0
var uniforms: Array[RDUniform] = []
var u := RDUniform.new()
u.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
u.binding = 0
u.add_id(buffer)
uniforms.append(u)

# 3) uniform set：把上面这一组绑定打包成 set 0
var uniform_set: RID = rd.uniform_set_create(uniforms, shader, 0)
```

**资源与 uniform 的对应关系**：

| RD 资源 | 承载它的 uniform 类型 | 着色器侧 |
|----------|----------------------|----------|
| 存储缓冲 | `UNIFORM_TYPE_STORAGE_BUFFER` | `buffer` 块 |
| UBO | `UNIFORM_TYPE_UNIFORM_BUFFER` | `uniform` 块 |
| 纹理（只读） | `UNIFORM_TYPE_TEXTURE` | `texture2D` |
| 存储纹理（读写） | `UNIFORM_TYPE_IMAGE` | `image2D` |
| 采样器 | `UNIFORM_TYPE_SAMPLER` | `sampler2D` |
| 顶点缓冲 | **不走 uniform set** | 走 `vertex_array_create()` |

> 💡 **一个常见的错误**：把存储缓冲绑成 `UNIFORM_TYPE_UNIFORM_BUFFER`（或反过来）。前者是可读写的 `buffer` 块，后者是只读的 `uniform` 块 —— 类型不匹配时，着色器编译或运行期校验会直接报出来。**先看 shader 里的声明，再决定 `uniform_type`。**

### 7.3 录制与派发

```gdscript
# 计算列表：绑定管线 → 绑定 uniform → 派发
var list := rd.compute_list_begin()
rd.compute_list_bind_compute_pipeline(list, pipeline)
rd.compute_list_bind_uniform_set(list, uniform_set, 0)
rd.compute_list_dispatch(list, groups_x, groups_y, groups_z)
rd.compute_list_end()
```

**命令列表的三段式**（`begin` → 若干绑定/记录 → `end`）在绘制侧同样成立：

| 阶段 | 接口 | 备注 |
|------|------|------|
| 开始 | `draw_list_begin()` / `draw_list_begin_for_screen()` | 后者画到屏幕，前者画到离屏目标 |
| 绑定 | `draw_list_bind_render_pipeline()` / `draw_list_bind_vertex_array()` / `draw_list_bind_index_array()` / `draw_list_bind_uniform_set()` | 顺序无关，但**同一 set 编号只能绑一次** |
| 状态 | `draw_list_enable_scissor()` / `draw_list_disable_scissor()` / `draw_list_set_blend_constants()` / `draw_list_set_push_constant()` | 状态切换有成本，能免则免 |
| 绘制 | `draw_list_draw()`（分屏绘制用 `draw_list_begin_split()`） | — |
| 结束 | `draw_list_end()` | 必须配对 |

**派发组数的算法**（compute 常见坑）：

```gdscript
# 假设着色器每个线程处理 1 个元素，共 N 个元素
var total: int = data.size()
var per_group: int = 64            # 与着色器里的 workgroup 大小保持一致
var groups: int = (total + per_group - 1) / per_group   # 向上取整
rd.compute_list_dispatch(list, groups, 1, 1)
```

> ⚠️ **派发组数一定要向上取整**。用整除会漏掉最后不满一个 workgroup 的元素 —— 而且这类 bug 往往只在"元素数量不是 64 的整数倍"时才出现，非常难查。`LIMIT_MAX_COMPUTE_WORKGROUP_COUNT_X` 是派发组数的硬上限，超了会直接失败。

### 7.4 提交与同步

| 接口 | 可用范围 | 代价 |
|------|----------|------|
| `submit()` | **仅本地 RD** | 推送帧设置与绘制命令缓冲 |
| `sync()` | **仅本地 RD** | 强制 CPU-GPU 同步，"has a performance cost"（官方原文） |
| `get_frame_delay()` | 全局 / 本地都可用 | 主 RD 通常 3，本地 RD 恒为 1 |

> ⚠️ **全局 RD 上没有 `submit()` / `sync()`**。主 RD 的提交流程由引擎在每帧末尾自动完成，你**不能**在全局 RD 上强制等待 GPU。真正需要"拿到结果再继续"时，正确做法是：
> 1. 用一个**本地 RD** 跑 compute（它有自己的 `submit()` / `sync()`）；
> 2. 或者在全局 RD 上把结果写进一张带 `TEXTURE_USAGE_CPU_READ_BIT` 的纹理，再在**下一帧**回读（这一帧的延迟无法避免）。

### 7.5 一份最小骨架

```gdscript
extends Node

# 最小 compute 骨架：把缓冲区里的每个元素乘 2
# ⚠️ 只在 Forward+ / Mobile 下可用（Compatibility 与 headless 下 rd 为 null）

func _ready() -> void:
    var rd: RenderingDevice = RenderingServer.get_rendering_device()
    if rd == null:
        push_warning("当前渲染方法不支持 RenderingDevice（Compatibility 渲染器与 headless 模式不可用）")
        return

    # 1) 着色器：.glsl 导入后是 RDShaderFile，取出 SPIR-V
    var rd_file: RDShaderFile = load("res://shaders/double.glslinc")
    var spirv: Dictionary = rd_file.get_spirv()
    var shader: RID = rd.shader_create_from_spirv(_to_stage_data(spirv))

    # 2) 资源：存储缓冲 + uniform set
    var data := PackedFloat32Array([1.0, 2.0, 3.0, 4.0])
    var buffer: RID = rd.storage_buffer_create(data.size() * 4, data)
    rd.set_resource_name(buffer, "DoubleData")

    var uniforms: Array[RDUniform] = []
    var u := RDUniform.new()
    u.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
    u.binding = 0
    u.add_id(buffer)
    uniforms.append(u)

    var uniform_set: RID = rd.uniform_set_create(uniforms, shader, 0)

    # 3) 管线 + 录制 + 派发
    var pipeline: RID = rd.compute_pipeline_create(shader)
    var list := rd.compute_list_begin()
    rd.compute_list_bind_compute_pipeline(list, pipeline)
    rd.compute_list_bind_uniform_set(list, uniform_set, 0)
    var groups: int = (data.size() + 63) / 64
    rd.compute_list_dispatch(list, groups, 1, 1)
    rd.compute_list_end()

    # 4) 释放：RID 不会自动回收
    rd.free_rid(uniform_set)
    rd.free_rid(pipeline)
    rd.free_rid(buffer)
    rd.free_rid(shader)

# 把 RDShaderFile.get_spirv() 的字典转成 shader_create_from_spirv() 需要的数组。
# ⚠️ 4.3 的类参考里没有把 ShaderStageSPIRVData 暴露成脚本类，
#    所以这里按"stage + code"的字段结构手写一份；不同 4.x 小版本的字段名可能有差异，
#    以目标版本源码为准。
func _to_stage_data(spirv: Dictionary) -> Array:
    var out: Array = []
    for stage in spirv.keys():
        out.append({"stage": stage, "code": spirv[stage]})
    return out
```

> ⚠️ 上面 `_to_stage_data()` 的返回结构必须与目标版本 `shader_create_from_spirv()` 期望的 `Vector[ShaderStageSPIRVData]` 一致 —— 4.3 的官方类参考**没有把这个结构体列为脚本类**，所以纯 GDScript 里拿不到它的构造器，这也是 4.x 里 RD 计算着色器最常被卡住的一步。完整可跑的转换写法见**第 42 篇《粒子系统》**的 RD 计算着色器示例。

> 💡 **三条最容易踩的坑**：
> 1. **RID 不会自动释放**。`free_rid()` 忘记调用就是泄漏；释放后继续使用则是未定义行为。
> 2. **派发组数要向上取整**，否则漏算尾部元素。
> 3. **不要在全局 RD 上等 GPU**。需要结果就走本地 RD，或者接受一帧延迟。

---

## 八、总结

## 核心要点

1. **Vulkan 驱动在 4.3 被拆成两个类**：`RenderingContextDriverVulkan`（实例 / 表面 / 交换链）与 `RenderingDeviceDriverVulkan`（设备 / 队列 / 资源 / 提交）。
2. **队列按族分组再展开成虚拟队列**：同族的多条物理队列被合并成一条逻辑队列，用 `submit_mutex` 串行化提交、用 `virtual_count` 记录并行度。
3. **屏障不需要手写**：`barrier()` / `full_barrier()` 在 4.3 都是空操作（deprecated），状态转换由 RenderGraph 依据 pass 读写关系自动插入。
4. **资源布局只有两层**：uniform set（九种 `RenderingDevice.UniformType`）与 vertex / index array；建资源前先用 `limit_get()` 查硬件上限。
5. **纹理用 `RDTextureFormat`（规格）+ `RDTextureView`（视图）描述**，用法位决定它能被怎么用；建之前必须查 `texture_is_format_supported_for_usage()`。
6. **显存只有占用量口径**（`get_memory_usage()`），分配策略在 C++ 层；本地 RD 可在独立线程跑 compute，但**不能与全局 RD 共享数据**。
7. **`RenderingDevice` 在 Compatibility 渲染器与 headless 模式下不可用** —— 这是所有 RD 代码的降级红线。
8. **绝大多数项目不该碰 RD**：材质、光照、后处理、实例化都有更高层的正确答案；RD 的主场是自定义 compute 与完全自管的渲染管线。

---

## 🔗 延伸阅读

- **官方文档**: [渲染器总览（Renderers）](https://docs.godotengine.org/en/stable/tutorials/rendering/renderers.html)
- **类参考**: [RenderingServer](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html)、[ProjectSettings](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html)
- **Vulkan 规范**: [Khronos Vulkan Specification](https://www.khronos.org/vulkan/)
- **源码位置**: `drivers/vulkan/`、`servers/rendering/rendering_device.h`、`servers/rendering/renderer_rd/`

---

## 📋 下一章预告

**第 13 篇：Godot vs Unity 渲染对比**

- 两套渲染架构的抽象层与资源所有权差异
- Forward+ / Mobile / Compatibility 与 URP / HDRP / Built-in 的机制差异矩阵
- GI 方案全景：SDFGI / LightmapGI / VoxelGI / LightmapProbe 对应 Enlighten / Progressive Lightmapper / 探针体积
- 阴影、后处理、批量绘制、性能调优入口与迁移检查清单

---

**作者**: wangshucheng
**首发平台**: 微信公众号  
**写作时间**: 2026 年 3 月  
**Godot 版本**: 4.x（基线 4.3；本文涉及的 4.4+ 差异已在行内标注）

---

**上一篇**: [第 11 篇：Godot 渲染架构概述](/articles/11-godot-rendering-architecture.md)
**下一篇**: [第 13 篇：Godot vs Unity 渲染对比](/articles/13-godot-vs-unity-rendering.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
