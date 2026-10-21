# 附录 C：Godot 与 Unity 对照表

## 📋 常用 API 映射

### 核心概念

| Unity | Godot | 说明 |
|-------|-------|------|
| GameObject | Node | 基础对象 |
| Component | Node (带脚本) | 功能组件 |
| Scene | Scene (.tscn) | 场景文件 |
| Prefab | Scene Instance | 预制件 |
| MonoBehaviour | GDScript/Node | 脚本组件 |
| Transform | Transform2D/3D | 变换组件 |
| Tag | Group | 标签系统 |

### 生命周期

| Unity | Godot | 调用时机 |
|-------|-------|---------|
| Awake() | _init() | 对象创建 |
| Start() | _ready() | 首次准备 |
| Update() | _process() | 每帧更新 |
| FixedUpdate() | _physics_process() | 物理帧 |
| LateUpdate() | `await get_tree().process_frame` | Godot 无后置阶段回调；需帧末逻辑时用 await 等待下一帧 |
| OnDestroy() | `queue_free()` / `NOTIFICATION_PREDELETE` | `_exit_tree()` 是"退出场景树"，不是销毁 |
| OnEnable() | _enter_tree() | 进入场景树 |
| OnDisable() | _exit_tree() | 退出场景树 |

### 输入系统

| Unity | Godot | 说明 |
|-------|-------|------|
| Input.GetAxis() | Input.get_action_strength() | 模拟输入 |
| Input.GetKey() | Input.is_key_pressed() | 按键检测 |
| Input.GetMouseButton() | Input.is_mouse_button_pressed() | 鼠标检测 |
| Input.GetTouch() | Input.get_screen_touch_position() | 触摸检测 |

### 物理系统

| Unity | Godot | 说明 |
|-------|-------|------|
| Rigidbody | RigidBody3D | 刚体组件 |
| Collider | CollisionShape3D | 碰撞体 |
| Trigger | Area3D | 触发器 |
| CharacterController | CharacterBody3D | 角色控制器 |
| Physics.Raycast() | PhysicsRayQueryParameters3D | 射线检测 |
| OnCollisionEnter() | `body_entered` 信号 | Area3D / RigidBody3D 的信号（刚体需开 `contact_monitor` + `max_contacts_reported`）；Godot 4 已用信号取代 `_body_entered()` 虚函数 |
| OnTriggerEnter() | Area3D.body_entered | 触发回调 |

### 渲染系统

| Unity | Godot | 说明 |
|-------|-------|------|
| MeshRenderer | MeshInstance3D | 网格渲染 |
| Material | Material/StandardMaterial3D | 材质 |
| Shader | Shader | 着色器 |
| Texture2D | Texture2D | 纹理 |
| Light | Light3D | 光源 |
| Camera | Camera3D | 摄像机 |
| Canvas | CanvasLayer | UI 层 |

### UI 系统

| Unity | Godot | 说明 |
|-------|-------|------|
| Canvas | Control (根) | UI 画布 |
| RectTransform | Control (锚点) | UI 变换 |
| Text (TMP) | Label/RichTextLabel | 文本 |
| Image | TextureRect | 图像 |
| Button | Button | 按钮 |
| InputField | LineEdit/TextEdit | 输入框 |
| Slider | HSlider/VSlider | 滑块 |
| Toggle | CheckBox | 开关 |
| Dropdown | OptionButton | 下拉框 |
| ScrollRect | ScrollContainer | 滚动视图 |
| LayoutGroup | Container | 布局容器 |

### 动画系统

| Unity | Godot | 说明 |
|-------|-------|------|
| Animator | AnimationTree + AnimationPlayer | 混合由 AnimationTree 负责，AnimationPlayer 只负责播放 |
| AnimatorController | AnimationTree | 动画状态机 |
| AnimationClip | Animation | 动画片段 |
| BlendTree | AnimationNodeBlendTree | 混合树 |
| AnimationEvent | `Animation` 的 `TYPE_METHOD` 值轨道 | 轨道类型，而非独立资源 |

### 音频系统

| Unity | Godot | 说明 |
|-------|-------|------|
| AudioSource | AudioStreamPlayer | 音频源 |
| AudioListener | AudioListener3D / AudioListener2D | 音频监听（场景中同一时刻只有一个 current 生效） |
| AudioMixer | AudioBus | 音频混音器 |
| PlayOneShot() | play() | 播放音效 |
| PlayClipAtPoint() | AudioStreamPlayer2D/3D | 空间音频 |

### 网络系统

| Unity | Godot | 说明 |
|-------|-------|------|
| NetworkManager | MultiplayerAPI + MultiplayerSpawner | MultiplayerAPI 是 RPC 传输与权限抽象，不是"管理器"；对象生成用 MultiplayerSpawner |
| NetworkBehaviour | Node (带 RPC) | 网络行为 |
| [Rpc] | @rpc | RPC 注解 |
| NetworkVariable | 手动同步 | 网络变量 |
| NetworkObject.Spawn() | 手动 + RPC | 对象生成 |

### 资源管理

| Unity | Godot | 说明 |
|-------|-------|------|
| Resources.Load() | load() | 加载资源 |
| Resources.LoadAsync() | ResourceLoader.load_threaded_request() | 异步加载 |
| Instantiate() | instantiate() / PackedScene.instantiate() | 实例化 |
| Destroy() | queue_free() | 销毁对象 |
| DontDestroyOnLoad() | Autoload（单例） | 跨场景持久化；Godot 无"场景外独立节点"的等价概念 |

### 场景管理

| Unity | Godot | 说明 |
|-------|-------|------|
| SceneManager.LoadScene() | get_tree().change_scene_to_file() | 加载场景 |
| SceneManager.LoadSceneAsync() | ResourceLoader.load_threaded_request() | 异步加载 |

### 协程

| Unity | Godot | 说明 |
|-------|-------|------|
| IEnumerator | `await` | 协程（`yield` 已在 Godot 4 移除） |
| StartCoroutine() | await get_tree().create_timer() | 启动协程 |
| yield return null | await get_tree().process_frame | 等待一帧 |
| yield return WaitForSeconds | await get_tree().create_timer(t) | 等待时间 |

### 调试

| Unity | Godot | 说明 |
|-------|-------|------|
| Debug.Log() | print() | 打印日志 |
| Debug.LogWarning() | push_warning() | 警告 |
| Debug.LogError() | push_error() | 错误 |
| Debug.Assert() | assert() | 断言 |
| Debug.Break() | breakpoint | 断点 |

---

## 🎯 迁移检查清单

### 项目设置

- [ ] 配置项目分辨率
- [ ] 设置输入映射（Input Map）
- [ ] 配置音频总线
- [ ] 设置自动加载（单例）
- [ ] 配置导出预设

### 场景迁移

- [ ] 转换 Prefab 为 Scene
- [ ] 重新设置层级结构
- [ ] 配置节点类型
- [ ] 重新连接信号

### 脚本迁移

- [ ] C# → GDScript 语法转换
- [ ] MonoBehaviour → Node 生命周期
- [ ] Update → _process
- [ ] 重新实现网络变量
- [ ] 转换协程为 await

### UI 迁移

- [ ] RectTransform → Control 锚点
- [ ] 重新设置布局容器
- [ ] 转换 UI 组件
- [ ] 重新配置主题

### 资源迁移

- [ ] 转换材质
- [ ] 转换着色器
- [ ] 重新导入纹理
- [ ] 转换动画资源

---

**版本**: Godot 4.3–4.7 vs Unity 2022 / 6000 LTS  
**最后更新**: 2026-10-20

---

**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

**上一篇**: [附录 B：GDScript 快速参考](/articles/appendix-b-gdscript-reference.md)
**下一篇**: [附录 D：性能优化清单](/articles/appendix-d-performance-checklist.md)
