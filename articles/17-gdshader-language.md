# 第 17 篇：GDShader 语言

> **本章导读**：
> 这一章把 GDShader 从"能写"讲到"写对"。先把六种 `shader_type` 的入口函数摊开，再逐张列出每种类型的内置变量、可用 `render_mode`、类型转换规则与内置函数表。
> 接着落到工程侧：`uniform` / `varying` / `group_uniforms`（uniform 分组）的组织方式，`Shader` 与 `ShaderMaterial` 的运行时接口，以及 3.x → 4.x 的内置名迁移对照。
> 读完你应该能拿着这份表逐条核对官方参考，而不是"抄一段能跑就算"。

> **前置知识**：第 16 篇《材质系统》
> **难度**：进阶

---

## 一、着色器类型

### 1.1 六种 shader_type 对照

Godot 的着色器语言是**一语言、多后端**的：同一套语法被编译到不同后端（GLSL ES 3.0 / SPIR-V / GLSL），但 `shader_type` 决定了编译器往你的代码里注入哪些内置变量、开放哪些入口函数。

Godot 4.3 一共支持 **5 种** `shader_type`，第 6 种（计算着色器）是 4.4 才加进来的：

| `shader_type` | 用途 | 可写的入口函数 | 4.3 是否可用 |
|---|---|---|---|
| `spatial` | 3D 表面着色 | `vertex()` / `fragment()` / `light()` | ✅ |
| `canvas_item` | 2D 精灵、UI、粒子 | `vertex()` / `fragment()` / `light()` | ✅ |
| `particles` | 粒子模拟与绘制 | `start()` / `process()` | ✅ |
| `sky` | 天空 / 全景环境 | `sky()` | ✅ |
| `fog` | 体积雾 / 深度雾 | `fog()` | ✅ |
| `compute` | 通用计算（GPGPU） | — | ❌ 截至 4.7.2 未提供（见 3.6） |

对应的枚举值在 `Shader.Mode` 里（`Shader.MODE_SPATIAL`、`Shader.MODE_CANVAS_ITEM`、`Shader.MODE_PARTICLES`、`Shader.MODE_SKY`、`Shader.MODE_FOG`），可以用 `Shader.get_mode()` 在运行时读回。

> ⚠️ `compute` 着色器**截至本书基线 4.7.2 仍未提供**——官方着色器类型注册表里只有六种类型，写 `shader_type compute;` 会直接报"未知 shader 类型"。社区里"Godot 4.4 加了 compute 着色器"的说法不成立，证据与替代方案见 3.6 节。

### 1.2 Shader 结构

一个 `.gdshader` 文件的结构是固定的：**类型声明 → render_mode → 全局声明 → 函数**。

```glsl
shader_type spatial;
render_mode unshaded;

uniform vec4 albedo : source_color;
uniform float metallic;
uniform float roughness;

void vertex() {
    // 顶点处理
}

void fragment() {
    // 片元处理
    // 注意：spatial 着色器没有 COLOR 内置输出——COLOR 是 canvas_item 的。
    // spatial 的输出是 ALBEDO / ALPHA / METALLIC / ROUGHNESS / NORMAL / EMISSION ...
    ALBEDO = albedo.rgb;
    ALPHA = albedo.a;
    METALLIC = metallic;
    ROUGHNESS = roughness;
}
```

> `shader_type spatial;` 的片元函数里写 `COLOR = albedo;` 是**着色器编译错误**：`COLOR` 是 `shader_type canvas_item;` 的内置输出变量。
>
> 反过来也成立：`canvas_item` 着色器里**没有** `ALBEDO`。两个类型的内置量不可混用——详见第三节的全表。

### 1.3 入口函数一览

不同 `shader_type` 允许写的函数名是**白名单**。写错函数名不会被当成"自定义函数"，而是直接报"该 shader 类型没有这个函数"。

| `shader_type` | 入口函数 | 什么时候被调用 | 典型用途 |
|---|---|---|---|
| `spatial` | `vertex()` | 每个顶点一次 | 顶点位移、公告板、蒙皮 |
| `spatial` | `fragment()` | 每个片元一次 | 写 `ALBEDO` / `NORMAL` / `EMISSION` |
| `spatial` | `light()` | 每个受光片元一次 | 自定义光照响应 |
| `canvas_item` | `vertex()` | 每个顶点一次 | 2D 顶点动画 |
| `canvas_item` | `fragment()` | 每个片元一次 | 写 `COLOR` / `NORMAL` |
| `canvas_item` | `light()` | 每个受光片元一次 | 自定义 2D 光照响应 |
| `particles` | `start()` | 粒子诞生时一次 | 初始化 `TRANSFORM` / `VELOCITY` / `COLOR` |
| `particles` | `process()` | 每帧一次 | 更新 `TRANSFORM` / `VELOCITY` |
| `sky` | `sky()` | 天空 pass 每个片元一次 | 写 `COLOR` / `ALPHA` |
| `fog` | `fog()` | 雾 pass 每个片元一次 | 写 `ALBEDO` / `DENSITY` / `EMISSION` |

> `particles` / `sky` / `fog` **不允许写 `varying`**，也**不允许 `discard`**。这是 4.3 词法表里写死的限制（`varying` 的排除类型是 `particles` / `sky` / `fog`，`discard` 同样排除这三类且只允许出现在 `fragment`）。
>
> `light()` 里的 `discard` 是允许的（`spatial` 与 `canvas_item` 的 `light` 入口都带 `can_discard = true`）。

---

## 二、着色器语法

### 2.1 全局作用域：只能放这几样

Godot 着色器语言的**全局作用域**只允许出现：

| 允许 | 例子 | 说明 |
|---|---|---|
| `shader_type` | `shader_type spatial;` | 整份文件只能有一个，且必须在最前 |
| `render_mode` | `render_mode cull_disabled;` | 可写多行 |
| `uniform` | `uniform float speed;` | 可带 `instance` / `global` 限定符 |
| `group_uniforms` | `group_uniforms MyGroup;` | 4.3 的 uniform 分组机制，见 2.7 |
| `varying` | `varying vec2 v_uv;` | `particles` / `sky` / `fog` 不可用 |
| `const` | `const float PI = 3.14159265;` | 编译期常量 |
| `struct` | `struct Light { ... };` | 结构体 |
| 函数定义 | `float my_func(float x) { ... }` | 用户自定义函数 |

**裸的变量声明是编译错误。** 例如在全局作用域写：

```glsl
// ❌ 全部是编译错误：全局作用域不允许裸变量声明
float value;
vec2 uv;
vec3 color;
vec4 position;
```

正确写法是把它们变成 `uniform`、`varying`、`const`，或者挪进函数体：

```glsl
// ✅ uniform：由脚本或材质面板赋值
uniform float speed;
uniform vec3 light_color;

// 注意：不要把 uniform 命名为 texture
// —— texture 是着色器语言的内置全局函数（同名会把它遮蔽掉）
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap;

// varying：在 vertex() 与 fragment() 之间传递
varying vec2 v_uv;
varying vec3 v_normal;

// const：编译期常量
const float PI = 3.14159265;

// 局部变量必须写在函数体内
void fragment() {
    float value = 0.5;            // float
    vec2 uv = UV;                 // UV：当前片元的纹理坐标
    vec3 color = NORMAL;          // NORMAL：视空间法线
    vec4 position = vec4(VERTEX, 1.0);
}
```

### 2.2 类型系统与类型转换

#### 2.2.1 全部合法类型

4.3 词法表（`servers/rendering/shader_language.cpp` 的 `keyword_list`）里登记的类型一共这些：

| 类别 | 类型名 |
|---|---|
| 无返回值 | `void` |
| 布尔 | `bool`、`bvec2`、`bvec3`、`bvec4` |
| 整数 | `int`、`ivec2`、`ivec3`、`ivec4`、`uint`、`uvec2`、`uvec3`、`uvec4` |
| 浮点 | `float`、`vec2`、`vec3`、`vec4` |
| 矩阵 | `mat2`、`mat3`、`mat4` |
| 采样器 | `sampler2D`、`sampler2DArray`、`sampler3D`、`samplerCube`、`samplerCubeArray` |
| 整数采样器 | `isampler2D`、`isampler2DArray`、`isampler3D` |
| 无符号采样器 | `usampler2D`、`usampler2DArray`、`usampler3D` |

另外还有两类修饰符：

- **精度限定符**：`lowp`、`mediump`、`highp`（主要对移动端 GLES3 后端有意义）；
- **插值限定符**：`flat`（不插值，整数/布尔 varying 用它）、`smooth`（默认，会插值）。

```glsl
varying flat int v_instance_index;   // flat：不做插值
varying smooth vec3 v_world_pos;     // smooth：默认行为
```

#### 2.2.2 隐式转换只有一条

Godot 的着色器语言**不是** GLSL。绝大多数类型转换必须**显式**用构造函数完成：

> **唯一允许的隐式转换：`int` → `float`。**

```glsl
void fragment() {
    int i = 3;
    float f = i;      // ✅ 唯一允许的隐式转换：int → float
    // float g = 1.5;
    // int j = g;      // ❌ 编译错误：float → int 必须显式
    int k = int(g);   // ✅ 显式转换，向零截断（1.9 → 1，-1.9 → -1）
}
```

这条规则在引擎源码里写得很直白：`ShaderLanguage::convert_constant()` 里只处理 `TYPE_INT → TYPE_FLOAT` 这一种自动转换，其余全靠构造函数的参数签名表来匹配。

#### 2.2.3 构造函数即类型转换

构造函数的可用签名是**逐个登记**的，因此能写什么不能写什么一眼可查：

| 目标类型 | 合法参数组合 |
|---|---|
| `float(x)` | `float`、`bool`、`int`、`uint` |
| `int(x)` | `int`、`bool`、`uint`、`float`（截断） |
| `bool(x)` | `bool`、`int`、`uint`、`float`（0 为假） |
| `uint(x)` | `uint`、`bool`、`int`、`float` |
| `vec2(...)` | `float` / `(float,float)` / `bvec2` / `ivec2` / `uvec2` / `vec2` |
| `vec3(...)` | `float` / `(f,f,f)` / `(vec2,float)` / `(float,vec2)` / `bvec3` / `ivec3` / `uvec3` / `vec3` |
| `vec4(...)` | `float` / `(f,f,f,f)` / `(float,vec2,float)` / `(vec2,float,float)` / `(float,float,vec2)` / `(float,vec3)` / `(vec3,float)` / `(vec2,vec2)` / `bvec4` / `ivec4` / `uvec4` / `vec4` |
| `ivec2 / uvec2 / bvec2` | 对应的标量组合 + 同族向量互转 + `vec2` 互转 |
| `mat3(...)` | `(vec3,vec3,vec3)` / `float`（对角阵）/ `mat2` / `mat4` |

几个容易踩的点：

```glsl
void fragment() {
    // ❌ 没有 vec3(vec2) 这个重载——不能靠 vec2 直接"升"成 vec3
    // vec3 a = vec3(some_vec2);

    // ✅ 补一个分量
    vec3 a = vec3(some_vec2, 0.0);
    vec3 b = vec3(0.0, some_vec2);

    // ✅ 标量广播：单参数 vec3(float) 会把三个分量都填成它
    vec3 c = vec3(0.5);          // (0.5, 0.5, 0.5)

    // ✅ 向量拼接：vec4(vec3, float) 是合法重载
    vec4 d = vec4(a, 1.0);

    // ✅ 整向量到标量：取 .x（也可以 .y / .z / .w）
    float e = a.x;
}
```

#### 2.2.4 数组与结构体

4.3 支持定长数组和 `struct`：

```glsl
// 定长数组 uniform
uniform float weights[4];

// 结构体
struct SurfaceData {
    vec3 albedo;
    float roughness;
    float metallic;
};

uniform SurfaceData surface;

void fragment() {
    float total = weights[0] + weights[1] + weights[2] + weights[3];
    ALBEDO = surface.albedo * total;
    ROUGHNESS = surface.roughness;
}
```

> 结构体成员不能包含采样器，也不能是 `varying`。

### 2.3 内置函数

4.3 的全局内建函数共 **127 个**（`servers/rendering/shader_language.cpp` 的函数注册表，去重后统计）。按用途归类如下。

#### 2.3.1 数学与三角

| 函数 | 说明 |
|---|---|
| `abs` / `sign` | 绝对值 / 符号 |
| `floor` / `ceil` / `round` / `roundEven` / `trunc` / `fract` | 取整族（`fract(x) = x - floor(x)`，始终非负） |
| `min` / `max` / `clamp` | 逐分量比较 |
| `mix(a, b, t)` | 线性插值；`t` 是标量时按比例混合整个向量 |
| `step(edge, x)` | `x < edge ? 0 : 1` |
| `smoothstep(e0, e1, x)` | 平滑阶跃；`e0 == e1` 时结果未定义 |
| `mod(x, y)` / `fposmod(x, y)` | 取模；`fposmod` 的结果与 `y` 同号 |
| `pow` / `exp` / `exp2` / `log` / `log2` | 幂与对数 |
| `sqrt` / `inversesqrt` | 平方根与其倒数 |
| `sin` / `cos` / `tan` / `asin` / `acos` / `atan` / `atan2` | 三角函数（弧度制） |
| `sinh` / `cosh` / `tanh` / `asinh` / `acosh` / `atanh` | 双曲函数 |
| `degrees` / `radians` | 角度 ↔ 弧度 |
| `cross(a, b)` | 叉积（只对 `vec3`） |
| `dot(a, b)` | 点积 |
| `distance(a, b)` | 欧氏距离 |
| `length(v)` | 向量长度 |
| `normalize(v)` | 归一化 |
| `reflect(I, N)` | 反射方向 |
| `refract(I, N, eta)` | 折射方向 |
| `faceforward(N, I, Nref)` | 翻转法线使其朝向观察者 |
| `outerProduct(c, r)` | 外积（`mat` × `vec`） |

#### 2.3.2 向量与矩阵

| 函数 | 说明 |
|---|---|
| `matrixCompMult(a, b)` | 矩阵逐元素相乘（不是矩阵乘） |
| `transpose(m)` | 转置 |
| `determinant(m)` | 行列式 |
| `inverse(m)` | 逆矩阵 |
| `outerProduct` | 外积 |

#### 2.3.3 比较与逻辑

`equal` / `notEqual` / `lessThan` / `lessThanEqual` / `greaterThan` / `greaterThanEqual` / `any` / `all` / `not`。

向量的比较是**逐分量**的，结果是 `bvec*`；要聚合成一个布尔要用 `any()` 或 `all()`：

```glsl
void fragment() {
    vec3 a = vec3(1.0, 2.0, 3.0);
    bvec3 mask = lessThan(a, vec3(2.0));   // (true, false, false)
    if (any(mask)) {
        ALBEDO = vec3(1.0, 0.0, 0.0);
    }
}
```

#### 2.3.4 纹理采样

| 函数 | 说明 |
|---|---|
| `texture(s, coords)` | 采样；带 LOD 偏置的 12 个重载覆盖 `sampler2D` / `sampler2DArray` / `sampler3D` / `samplerCube` / `samplerCubeArray` × `float` / `isampler` / `usampler` |
| `textureLod(s, coords, lod)` | 显式指定 LOD（顶点着色器里必须用它） |
| `textureGrad(s, coords, dPdx, dPdy)` | 显式指定梯度 |
| `textureProj(s, coords)` | 投影采样 |
| `textureProjLod` / `textureProjGrad` | 投影采样的 LOD / 梯度变体 |
| `textureSize(s, lod)` | 纹理尺寸（`ivec2` / `ivec3`） |
| `textureQueryLevels(s)` | mip 层数 |
| `textureQueryLod(s, coords)` | 查询当前 LOD |
| `texelFetch(s, coords, lod)` | 按整数坐标取像素，不做过滤 |
| `textureGather(s, coords)` | 收集一个 2×2 邻域 |

> `texture` 是**全局内建函数**，4.3 一共登记了 22 条重载（其中全局可用的采样器组合 12 条）。**不要把 uniform 命名为 `texture`**——同名 uniform 会把这个函数遮蔽掉，之后再写 `texture(TEXTURE, UV)` 就会报"找不到匹配的函数"。这正是 Godot 3.x 教程里 `uniform sampler2D texture;` 这种写法在 4.x 会踩的坑。

#### 2.3.5 导数与插值

| 函数 | 说明 |
|---|---|
| `dFdx(p)` / `dFdy(p)` | 屏幕空间横 / 纵导数 |
| `dFdxCoarse` / `dFdyCoarse` | 粗粒度版本（quad 级） |
| `dFdxFine` / `dFdyFine` | 细粒度版本（pixel 级） |
| `fwidth(p)` | `abs(dFdx(p)) + abs(dFdy(p))` |

#### 2.3.6 位运算与整数扩展

`bitCount` / `bitfieldExtract` / `bitfieldInsert` / `bitfieldReverse` / `findLSB` / `findMSB` / `uaddCarry` / `usubBorrow` / `umulExtended` / `imulExtended` / `frexp` / `ldexp` / `modf` / `packHalf2x16` / `unpackHalf2x16` / `packSnorm2x16` / `unpackSnorm2x16` / `packUnorm2x16` / `unpackUnorm2x16` / `packSnorm4x8` / `unpackSnorm4x8` / `packUnorm4x8` / `unpackUnorm4x8` / `floatBitsToInt` / `floatBitsToUint` / `intBitsToFloat` / `uintBitsToFloat`。

#### 2.3.7 常用示例

```glsl
// 数学函数
float result = sin(TIME);                              // TIME：着色器启动以来的秒数
vec3 normalized = normalize(NORMAL);                    // 归一化
float dot_product = dot(NORMAL, vec3(0.0, 0.0, 1.0));  // 点积

// 纹理采样：Godot 4 的 spatial 着色器**没有**内置采样器，必须自己声明
uniform sampler2D albedo_texture : source_color;
uniform sampler2D normal_texture : hint_normal;

void fragment() {
    // 引擎按同名把 BaseMaterial3D 的贴图槽绑给这两个 uniform
    ALBEDO = texture(albedo_texture, UV).rgb;
    NORMAL_MAP = texture(normal_texture, UV).rgb;
}
```

> ⚠️ `albedo_texture` / `normal_texture` 是 **Godot 3.x** 的**内置**小写采样器名。4.x 把它们**彻底移除了**——spatial 着色器里**没有任何**内置纹理采样器，必须自己 `uniform sampler2D` 声明，再按变量名采样。
>
> 容易混的是：4.7.2 的 spatial 内置量里确实有一个 `NORMAL_MAP`，但它是 **`vec3`（法线贴图方向，可写）**，`NORMAL_MAP_DEPTH` 是 **`float`**（`servers/rendering/shader_types.cpp:145-146`）——**不是采样器，不能 `texture(NORMAL_MAP, UV)`**。

### 2.4 uniform 与 hint

`uniform` 是着色器和脚本之间唯一的数据通道。类型决定它能接什么资源，hint 决定编辑器面板怎么画。

| hint / filter / repeat | 作用 |
|---|---|
| `source_color` | 按 sRGB 采样（颜色贴图必须加） |
| `hint_range(min, max[, step])` | 滑杆范围 |
| `hint_normal` | 按法线贴图解释（切线空间） |
| `hint_default_white` / `hint_default_black` / `hint_default_transparent` | 缺省贴图的颜色 |
| `hint_anisotropy` | 各向异性方向图 |
| `hint_roughness_r` / `_g` / `_b` / `_a` / `_gray` | 粗糙度取哪个通道 |
| `hint_roughness_normal` | 粗糙度 + 法线合并贴图 |
| `hint_screen_texture` | 屏幕纹理（后处理用） |
| `hint_normal_roughness_texture` | 法线 + 粗糙度合并贴图 |
| `hint_depth_texture` | 深度纹理 |
| `filter_nearest` / `filter_linear` | 采样过滤 |
| `filter_nearest_mipmap` / `filter_linear_mipmap` | 带 mipmap 的过滤 |
| `filter_nearest_mipmap_anisotropic` / `filter_linear_mipmap_anisotropic` | 各向异性过滤 |
| `repeat_enable` / `repeat_disable` | 寻址模式 |
| `instance_index` | 实例索引 uniform |

```glsl
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float roughness : hint_range(0.0, 1.0, 0.01) = 0.5;
uniform vec4 tint : source_color = vec4(1.0);
```

`uniform` 还有两个限定符：

- `instance uniform` —— 每个实例一份的值（配合实例化渲染）；
- `global uniform` —— 全局着色器参数，用 `RenderingServer.global_shader_parameter_add()` 注册。

```glsl
global uniform vec3 fog_color;
instance uniform float instance_seed;
```

### 2.5 varying 的数据流

`varying` 是 `vertex()` → `fragment()` 之间唯一的数据通道。规则：

1. 声明必须在**全局作用域**；
2. 两端**类型必须完全一致**（`float` 配 `float`，不能一边 `float` 一边 `vec3`）；
3. 整数与布尔类型的 varying 必须加 `flat`，否则插值无意义；
4. `particles` / `sky` / `fog` 三种类型**不允许**写 `varying`。

```glsl
shader_type spatial;

varying vec3 v_world_pos;
varying flat int v_face_id;

void vertex() {
    v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    v_face_id = VERTEX_ID;
}

void fragment() {
    ALBEDO = vec3(v_face_id % 2);
}
```

### 2.6 const 与编译期常量

`const` 声明的量在编译期求值，可以参与数组长度、循环边界等需要常量的场合：

```glsl
const float PI = 3.14159265;
const float TAU = 2.0 * PI;
const int MAX_STEPS = 8;
const float weights[MAX_STEPS] = float[MAX_STEPS](0.125);
```

> `PI` / `TAU` / `E` 这三个常量**内置**在每种 shader 类型里（`constants` 作用域），不需要自己声明。

### 2.7 uniform 分组：group_uniforms

4.3 提供了一个关键字，把若干 uniform **归到同一组**（group），让编辑器检查器把它们折叠成一块显示。

关键词是 **`group_uniforms`**（不是 `uniform_group`）：

```glsl
shader_type spatial;

// 打开一个 uniform 分组
group_uniforms Scene;
uniform vec3 light_direction;
uniform vec3 light_color;
uniform float light_energy;

// 打开一个子组
group_uniforms Scene.Surface;
uniform vec4 tint;
uniform float roughness;

// 关闭当前组
group_uniforms;

void fragment() {
    ALBEDO = tint.rgb * light_color * light_energy;
    ROUGHNESS = roughness;
}
```

语法规则（来自 4.3 解析器 `TK_UNIFORM_GROUP` 分支）：

| 写法 | 含义 |
|---|---|
| `group_uniforms Name;` | 打开名为 `Name` 的组（后续 uniform 归入该组） |
| `group_uniforms Name.Sub;` | 打开名为 `Name.Sub` 的子组 |
| `group_uniforms;` | 关闭当前组（必须先打开过，否则报 "Group needs to be opened before."） |

> 组名与子组名会写进 `ShaderNode::Uniform` 的 `group` / `subgroup` 字段（见 `servers/rendering/shader_language.cpp` 的解析分支）。**是否真的合并成一块 uniform buffer，由渲染后端决定**——RD 后端与 GLES3 后端的行为可能不同，写之前先用 `Shader.get_shader_uniform_list()` 核对自己这版引擎的 uniform 清单，再决定要不要依赖分组。
>
> 另外注意 `group_uniforms` 是 4.x 才出现的关键字：Godot 3.x 的着色器语言里没有它，3.x 时代的 shader 直接搬过来是编译错误。

---

## 三、内置变量全表

这一节是本章的**核心参考**。内置变量的权威来源是 `servers/rendering/shader_types.cpp` 里 `ShaderTypes::ShaderTypes()` 的注册表——每个 `shader_type` × 每个入口函数，都有一张 `built_ins` 表。下面的表按这份注册表逐条抄写。

### 3.1 spatial

#### 3.1.1 全局（`global` 作用域）

| 变量 | 类型 | 说明 |
|---|---|---|
| `TIME` | `float` | 着色器启动以来的秒数 |
| `EXPOSURE` | `float` | 曝光值（常量） |

`constants` 作用域另有 `PI` / `TAU` / `E`。

#### 3.1.2 `vertex()` 输入

| 变量 | 类型 | 说明 |
|---|---|---|
| `VERTEX` | `vec3` | 模型空间顶点位置（**可写**） |
| `NORMAL` | `vec3` | 模型空间法线（**可写**） |
| `TANGENT` | `vec3` | 切线（**可写**） |
| `BINORMAL` | `vec3` | 副切线（**可写**） |
| `POSITION` | `vec4` | 裁剪空间坐标（**只读**） |
| `UV` | `vec2` | 主 UV（**可写**） |
| `UV2` | `vec2` | 第二套 UV（**可写**） |
| `COLOR` | `vec4` | 顶点色（**可写**） |
| `POINT_SIZE` | `float` | 点大小（**可写**） |
| `INSTANCE_ID` | `int` | 实例索引（常量） |
| `INSTANCE_CUSTOM` | `vec4` | 实例自定义数据（**可写**） |
| `VERTEX_ID` | `int` | 顶点索引（常量） |
| `ROUGHNESS` | `float` | 粗糙度（**可写**） |
| `BONE_INDICES` | `uvec4` | 骨骼索引（**可写**） |
| `BONE_WEIGHTS` | `vec4` | 骨骼权重（**可写**） |
| `CUSTOM0` ~ `CUSTOM3` | `vec4` | 自定义实例数据（**可写**） |

矩阵与相机相关（`vertex()` 中可用）：

`MODEL_MATRIX`（`mat4`）、`MODEL_NORMAL_MATRIX`（`mat3`）、`VIEW_MATRIX`（`mat4`）、`INV_VIEW_MATRIX`（`mat4`）、`PROJECTION_MATRIX`（`mat4`）、`INV_PROJECTION_MATRIX`（`mat4`）、`MODELVIEW_MATRIX`（`mat4`）、`MODELVIEW_NORMAL_MATRIX`（`mat3`）、`VIEWPORT_SIZE`（`vec2`）、`OUTPUT_IS_SRGB`（`bool`）、`MAIN_CAM_INV_VIEW_MATRIX`（`mat4`）、`NODE_POSITION_WORLD`（`vec3`）、`CAMERA_POSITION_WORLD`（`vec3`）、`CAMERA_DIRECTION_WORLD`（`vec3`）、`CAMERA_VISIBLE_LAYERS`（`uint`）、`NODE_POSITION_VIEW`（`vec3`）、`VIEW_INDEX`（`int`）、`VIEW_MONO_LEFT`（`int`）、`VIEW_RIGHT`（`int`）、`EYE_OFFSET`（`vec3`）。

#### 3.1.3 `fragment()` 输入与输出

**输入**（只读）：

| 变量 | 类型 | 说明 |
|---|---|---|
| `VERTEX` | `vec3` | 视空间顶点位置 |
| `LIGHT_VERTEX` | `vec3` | 光照顶点 |
| `FRAGCOORD` | `vec4` | 视口内片元坐标（`xy` 是像素，`z` 是深度，`w` 是 `1/宽度`） |
| `FRONT_FACING` | `bool` | 是否正面朝向相机 |
| `NORMAL` | `vec3` | 视空间法线（**可写**） |
| `TANGENT` / `BINORMAL` | `vec3` | 视空间切线 / 副切线（**可写**） |
| `VIEW` | `vec3` | 指向相机的向量（常量） |
| `NORMAL_MAP` | `vec3` | 法线贴图方向（**可写**） |
| `NORMAL_MAP_DEPTH` | `float` | 法线贴图深度（**可写**） |
| `UV` / `UV2` | `vec2` | UV（**可写**） |
| `COLOR` | `vec4` | 顶点色（**可写**） |
| `SCREEN_UV` | `vec2` | 屏幕空间 UV |
| `POINT_COORD` | `vec2` | 点图元内的归一化坐标 |
| `DEPTH` | `float` | 视空间深度 |
| `FOG` | `vec4` | 雾贡献（常量） |
| `RADIANCE` / `IRRADIANCE` | `vec4` | 探针辐照度 / 辐射度（常量） |
| `AO` | `float` | 环境光遮蔽（**可写**） |
| `AO_LIGHT_AFFECT` | `float` | AO 对直接光的影响（**可写**） |
| `ALPHA_SCISSOR_THRESHOLD` | `float` | Alpha 裁剪阈值（**可写**） |
| `ALPHA_HASH_SCALE` | `float` | Alpha 哈希缩放（**可写**） |
| `ALPHA_ANTIALIASING_EDGE` | `float` | Alpha 抗锯齿边缘因子（**可写**） |
| `ALPHA_TEXTURE_COORDINATE` | `vec2` | Alpha 裁剪/哈希用的纹理坐标（**可写**） |
| `PREMUL_ALPHA_FACTOR` | `float` | 预乘 alpha 因子（**可写**） |

**输出**（**可写**，不写就用材质默认值）：

| 变量 | 类型 | 说明 |
|---|---|---|
| `ALBEDO` | `vec3` | 基础色（线性空间） |
| `ALPHA` | `float` | 不透明度 |
| `METALLIC` | `float` | 金属度 |
| `SPECULAR` | `float` | 镜面反射强度 |
| `ROUGHNESS` | `float` | 粗糙度 |
| `RIM` | `float` | 边缘光强度 |
| `RIM_TINT` | `float` | 边缘光染色（0 = 白，1 = 保留原色） |
| `CLEARCOAT` | `float` | 清漆层强度 |
| `CLEARCOAT_ROUGHNESS` | `float` | 清漆层粗糙度 |
| `ANISOTROPY` | `float` | 各向异性强度 |
| `ANISOTROPY_FLOW` | `vec2` | 各向异性方向（切线空间） |
| `SSS_STRENGTH` | `float` | 次表面散射强度 |
| `SSS_TRANSMITTANCE_COLOR` | `vec4` | 透射颜色 |
| `SSS_TRANSMITTANCE_DEPTH` | `float` | 透射深度 |
| `SSS_TRANSMITTANCE_BOOST` | `float` | 透射增强 |
| `BACKLIGHT` | `vec3` | 背光颜色 |
| `EMISSION` | `vec3` | 自发光颜色 |

> **再次强调**：`COLOR` **不在** spatial 的片元输出表里。spatial 的输出是 `ALBEDO` / `ALPHA` / `METALLIC` / `SPECULAR` / `ROUGHNESS` / `RIM` / `CLEARCOAT` / `ANISOTROPY` / `SSS_*` / `BACKLIGHT` / `AO` / `EMISSION`。`COLOR` 只在 `vertex()` 里作为顶点色输入存在。
>
> 同样，spatial 的 `vertex()` 里**没有** `ALBEDO`（基础色是在片元阶段决定的）。

#### 3.1.4 `light()` 输入与输出

`light()` 是自定义光照函数，引擎在光照 pass 里调用它。

**输入**：`MODEL_MATRIX`、`VIEW_MATRIX`、`INV_VIEW_MATRIX`、`PROJECTION_MATRIX`、`INV_PROJECTION_MATRIX`、`VIEWPORT_SIZE`、`FRAGCOORD`、`NORMAL`（`vec3`）、`UV` / `UV2`（`vec2`）、`VIEW`（`vec3`）、`LIGHT`（`vec3`，指向光源的方向）、`LIGHT_COLOR`（`vec3`）、`LIGHT_IS_DIRECTIONAL`（`bool`）、`ATTENUATION`（`float`，衰减）、`SPECULAR_AMOUNT`（`float`）、`ALBEDO`（`vec3`）、`BACKLIGHT`（`vec3`）、`METALLIC`（`float`）、`ROUGHNESS`（`float`）、`OUTPUT_IS_SRGB`（`bool`）、`ALPHA`（`float`）。

**输出**：`DIFFUSE_LIGHT`（`vec3`）、`SPECULAR_LIGHT`（`vec3`）。

```glsl
shader_type spatial;
render_mode unshaded;

uniform vec3 light_tint = vec3(1.0);

void light() {
    DIFFUSE_LIGHT = LIGHT_COLOR * light_tint * ATTENUATION;
    SPECULAR_LIGHT = vec3(0.0);
}
```

### 3.2 canvas_item

#### 3.2.1 全局

`global` 作用域只有 `TIME`（`float`）；`constants` 作用域有 `PI` / `TAU` / `E`。

#### 3.2.2 `vertex()` 输入

| 变量 | 类型 | 说明 |
|---|---|---|
| `VERTEX` | `vec2` | 局部空间顶点（**可写**） |
| `UV` | `vec2` | UV（**可写**） |
| `COLOR` | `vec4` | 顶点色（**可写**） |
| `POINT_SIZE` | `float` | 点大小（**可写**） |
| `MODEL_MATRIX` | `mat4` | 模型矩阵 |
| `CANVAS_MATRIX` | `mat4` | 画布矩阵 |
| `SCREEN_MATRIX` | `mat4` | 屏幕矩阵 |
| `INSTANCE_CUSTOM` | `vec4` | 实例自定义数据（**可写**） |
| `INSTANCE_ID` | `int` | 实例索引 |
| `VERTEX_ID` | `int` | 顶点索引 |
| `AT_LIGHT_PASS` | `bool` | 当前是否处于光照 pass |
| `TEXTURE_PIXEL_SIZE` | `vec2` | 1 / 贴图尺寸 |
| `CUSTOM0` / `CUSTOM1` | `vec4` | 自定义实例数据（**可写**） |

#### 3.2.3 `fragment()` 输入与输出

**输入**：

| 变量 | 类型 | 说明 |
|---|---|---|
| `VERTEX` | `vec2` | 局部空间顶点 |
| `SHADOW_VERTEX` | `vec2` | 阴影 pass 的顶点 |
| `LIGHT_VERTEX` | `vec3` | 光照 pass 的顶点 |
| `FRAGCOORD` | `vec4` | 视口内片元坐标 |
| `NORMAL` | `vec3` | 法线（**可写**） |
| `NORMAL_MAP` | `vec3` | 法线贴图方向（**可写**） |
| `NORMAL_MAP_DEPTH` | `float` | 法线贴图深度（**可写**） |
| `UV` | `vec2` | UV（**可写**） |
| `COLOR` | `vec4` | 顶点色 × 节点 modulate（**可写**） |
| `TEXTURE` | `sampler2D` | **内置采样器**：主贴图 |
| `TEXTURE_PIXEL_SIZE` | `vec2` | 1 / 贴图尺寸 |
| `NORMAL_TEXTURE` | `sampler2D` | 内置采样器：法线贴图 |
| `SPECULAR_SHININESS_TEXTURE` | `sampler2D` | 内置采样器：高光贴图 |
| `SPECULAR_SHININESS` | `vec4` | 高光参数（**可写**） |
| `SCREEN_UV` | `vec2` | 屏幕空间 UV |
| `SCREEN_PIXEL_SIZE` | `vec2` | 1 / 屏幕尺寸 |
| `POINT_COORD` | `vec2` | 点图元内归一化坐标 |
| `AT_LIGHT_PASS` | `bool` | 是否处于光照 pass |

**输出**：`COLOR`（`vec4`）——这才是 `canvas_item` 着色器的主输出。

> `canvas_item` 的 `TEXTURE` / `NORMAL_TEXTURE` / `SPECULAR_SHININESS_TEXTURE` 是**引擎注入的采样器**，在 `shader_types.cpp` 里被登记为 `TYPE_SAMPLER2D`。你**不需要**也不能重复声明它们，直接 `texture(TEXTURE, UV)` 即可。
>
> 而 **spatial 没有任何内置采样器**——`servers/rendering/shader_types.cpp` 的 spatial 段（:100-180）里只有一个 `NORMAL_MAP`，登记的是 **`vec3` 的 inout**（法线贴图方向，可写）和 `NORMAL_MAP_DEPTH`（`float`），**不是采样器**。`TEXTURE` / `NORMAL_TEXTURE` 这些采样器只存在于 `canvas_item` 段（:270-272、:317-318）。
>
> 所以 spatial 要用贴图，必须自己声明 `uniform sampler2D ...`，引擎再按**同名**把 `BaseMaterial3D` 的贴图槽绑给你（绑定逻辑在 `servers/rendering/renderer_rd/storage_rd/material_storage.cpp`）。

#### 3.2.4 `light()` 输入与输出

`light()` 可用：`FRAGCOORD`（`vec4`）、`NORMAL`（`vec3`）、`COLOR`（`vec4`）、`UV`（`vec2`）、`SPECULAR_SHININESS`（`vec4`）、`LIGHT_COLOR`（`vec4`）、`LIGHT_POSITION`（`vec3`）、`LIGHT_DIRECTION`（`vec3`）、`LIGHT_ENERGY`（`float`）、`LIGHT_IS_DIRECTIONAL`（`bool`）、`LIGHT_VERTEX`（`vec3`）、`LIGHT`（`vec4`）、`SHADOW_MODULATE`（`vec4`）、`SCREEN_UV`（`vec2`）、`TEXTURE`（`sampler2D`）、`TEXTURE_PIXEL_SIZE`（`vec2`）、`POINT_COORD`（`vec2`）。

**输出**：`LIGHT`（`vec4`）与 `SHADOW_MODULATE`（`vec4`）。

### 3.3 particles

粒子着色器有两个入口：`start()`（粒子诞生）和 `process()`（每帧）。

#### 3.3.1 `start()` 输入与输出

**输入**（全部**可写**）：`COLOR`（`vec4`）、`VELOCITY`（`vec3`）、`MASS`（`float`）、`ACTIVE`（`bool`）、`CUSTOM`（`vec4`）、`USERDATA1` ~ `USERDATA6`（各 `vec4`）、`TRANSFORM`（`mat4`）、`LIFETIME`（`float`）、`DELTA`（`float`）、`NUMBER`（`uint`）、`INDEX`（`uint`）、`EMISSION_TRANSFORM`（`mat4`）、`EMITTER_VELOCITY`（`vec3`）、`INTERPOLATE_TO_END`（`float`）、`RANDOM_SEED`（`uint`）、`FLAG_EMIT_POSITION`（`uint`）、`FLAG_EMIT_ROT_SCALE`（`uint`）、`FLAG_EMIT_VELOCITY`（`uint`）、`FLAG_EMIT_COLOR`（`uint`）、`FLAG_EMIT_CUSTOM`（`uint`）、`RESTART_POSITION`（`bool`）、`RESTART_ROT_SCALE`（`bool`）、`RESTART_VELOCITY`（`bool`）、`RESTART_COLOR`（`bool`）、`RESTART_CUSTOM`（`bool`）、`AMOUNT_RATIO`（`float`）。

#### 3.3.2 `process()` 输入与输出

**输入**（全部**可写**）：`COLOR`、`VELOCITY`、`MASS`、`ACTIVE`、`RESTART`（`bool`）、`CUSTOM`、`USERDATA1` ~ `USERDATA6`、`TRANSFORM`、`LIFETIME`、`DELTA`、`NUMBER`、`INDEX`、`EMISSION_TRANSFORM`、`EMITTER_VELOCITY`、`INTERPOLATE_TO_END`、`RANDOM_SEED`、`FLAG_EMIT_POSITION`、`FLAG_EMIT_ROT_SCALE`、`FLAG_EMIT_VELOCITY`、`FLAG_EMIT_COLOR`、`FLAG_EMIT_CUSTOM`、`COLLIDED`（`bool`）、`COLLISION_NORMAL`（`vec3`）、`COLLISION_DEPTH`（`float`）、`ATTRACTOR_FORCE`（`vec3`）、`AMOUNT_RATIO`。

```glsl
shader_type particles;

uniform float gravity_strength = 9.8;

void start() {
    TRANSFORM[3].xyz = vec3(0.0, 1.0, 0.0);
    VELOCITY = vec3(0.0, 0.0, 0.0);
    COLOR = vec4(1.0);
}

void process() {
    VELOCITY += vec3(0.0, -gravity_strength * DELTA, 0.0);
    TRANSFORM[3].xyz += VELOCITY * DELTA;
}
```

> 粒子着色器的详细用法（`CUSTOM` / `USERDATA` / 绘制 pass 的分工）属于第 20 篇《粒子渲染》的范围，本章只给内置量对照表。

### 3.4 sky

天空着色器只有一个入口 `sky()`。

**`global` 作用域**（可用 `TIME`、`POSITION`、光源信息等）：

| 变量 | 类型 | 说明 |
|---|---|---|
| `TIME` | `float` | 秒数 |
| `POSITION` | `vec3` | 观察方向（世界空间） |
| `RADIANCE` | `samplerCube` | 辐射度探针立方图（**可写**） |
| `AT_HALF_RES_PASS` | `bool` | 当前是半分辨率 pass |
| `AT_QUARTER_RES_PASS` | `bool` | 当前是四分之一分辨率 pass |
| `AT_CUBEMAP_PASS` | `bool` | 当前是 cubemap 生成 pass |
| `LIGHT0_ENABLED` ~ `LIGHT3_ENABLED` | `bool` | 四个方向光的启用状态 |
| `LIGHT0_DIRECTION` ~ `LIGHT3_DIRECTION` | `vec3` | 方向光方向 |
| `LIGHT0_ENERGY` ~ `LIGHT3_ENERGY` | `float` | 方向光能量 |
| `LIGHT0_COLOR` ~ `LIGHT3_COLOR` | `vec3` | 方向光颜色 |
| `LIGHT0_SIZE` ~ `LIGHT3_SIZE` | `float` | 太阳角度大小 |

**`sky()` 输入与输出**：

| 变量 | 类型 | 说明 |
|---|---|---|
| `EYEDIR` | `vec3` | 视线方向（**可写**） |
| `SCREEN_UV` | `vec2` | 屏幕 UV |
| `FRAGCOORD` | `vec4` | 视口内片元坐标 |
| `SKY_COORDS` | `vec2` | 天空贴图坐标（**可写**） |
| `HALF_RES_COLOR` | `vec4` | 半分辨率 pass 的颜色（**可写**） |
| `QUARTER_RES_COLOR` | `vec4` | 四分之一分辨率 pass 的颜色（**可写**） |
| `FOG` | `vec4` | 雾贡献（**可写**） |
| `COLOR` | `vec3` | **输出**：天空颜色 |
| `ALPHA` | `float` | **输出**：天空透明度 |

```glsl
shader_type sky;

uniform vec3 top_color : source_color = vec3(0.3, 0.5, 0.9);
uniform vec3 horizon_color : source_color = vec3(0.8, 0.85, 0.95);

void sky() {
    float h = clamp(EYEDIR.y, 0.0, 1.0);
    COLOR = mix(horizon_color, top_color, h);
}
```

### 3.5 fog

雾着色器只有一个入口 `fog()`。

**输入**（全部**可写**）：

| 变量 | 类型 | 说明 |
|---|---|---|
| `WORLD_POSITION` | `vec3` | 世界坐标位置 |
| `OBJECT_POSITION` | `vec3` | 物体空间位置 |
| `UVW` | `vec3` | 3D 纹理坐标 |
| `SIZE` | `vec3` | 体积雾盒尺寸 |
| `SDF` | `float` | 有向距离场值 |
| `DENSITY` | `float` | 雾密度 |

**输出**：`ALBEDO`（`vec3`，雾的颜色）、`EMISSION`（`vec3`，雾的自发光）。

```glsl
shader_type fog;

uniform vec4 fog_color : source_color = vec4(0.5, 0.6, 0.7, 1.0);

void fog() {
    ALBEDO = fog_color.rgb;
    EMISSION = vec3(0.0);
    DENSITY = 1.0;
}
```

### 3.6 compute：截至 4.7.2 仍未提供

⚠️ **先纠正一个流传很广的说法**：Godot **4.4 并没有**引入通用计算着色器。截至本书基线 **4.7.2**，`shader_type compute;` 依然无法使用。证据有两处，都在官方源码里：

- 着色器类型注册表（`servers/rendering/shader_types.cpp` 的 `shader_types_list`）只登记了六种：`spatial` / `canvas_item` / `particles` / `sky` / `fog` / `texture_blit`；
- C++ 侧的 `ShaderMode` 枚举（`servers/rendering/rendering_server_enums.h`）与之严格同步，**没有** `SHADER_COMPUTE`；脚本侧的 `Shader.Mode` 枚举同样**没有** `MODE_COMPUTE`（4.7.2 里是 `MODE_SPATIAL` / `MODE_CANVAS_ITEM` / `MODE_PARTICLES` / `MODE_SKY` / `MODE_FOG` / `MODE_TEXTURE_BLIT` 六项）。

写 `shader_type compute;` 会直接报"未知 shader 类型"——这一点在 4.3 与 4.7.2 上表现一致。

**那 GPGPU 怎么做？** 走 `RenderingDevice` 的底层路线，而不是着色器语言：

1. 自己准备计算着色器源码（GLSL 或 SPIR-V），用 `RenderingDevice.shader_compile_spirv_from_source()` / `shader_create_from_spirv()` 编译；
2. 用 `compute_pipeline_create()` 建管线，`compute_list_begin()` / `compute_list_dispatch()` 提交工作组；
3. 描述符集与缓冲绑定自己管（`compute_list_bind_compute_pipeline()` / `compute_list_bind_uniform_set()` / `compute_list_set_push_constant()`）。

代价是彻底脱离引擎的场景图与资源管理：没有 `Node`、没有自动资源生命周期、没有编辑器预览。这条路的定位是"把 GPGPU 塞进引擎内部"，而不是"给美术一个方便的 compute 节点"。

本章的其余内容都以 4.7.2 为基线。

---

## 四、render_mode 全表

`render_mode` 控制**渲染管线**的行为，不改变着色器数学。4.7.2 的注册表（`shader_types.cpp` 里的 `modes.push_back(...)`）一共登记了 **37 条**：`spatial` 23 条、`canvas_item` 5 条、`particles` 4 条、`sky` 4 条、`texture_blit` 1 条。

带选项的写法是 `render_mode <名字>_<选项>`，例如 `cull` 的选项是 `back` / `front` / `disabled`，对应 `cull_back` / `cull_front` / `cull_disabled`。

### 4.1 spatial（22 条）

| `render_mode` | 取值 | 作用 |
|---|---|---|
| `blend` | `mix` / `add` / `sub` / `mul` / `premul_alpha` | 混合模式；默认 `mix` |
| `depth_draw` | `opaque` / `always` / `never` | 深度写入策略；默认 `opaque` |
| `depth_prepass_alpha` | 开关 | 开启 alpha 深度预通道 |
| `depth_test_disabled` | 开关 | **关闭深度测试**（绘制顺序完全由引擎决定） |
| `sss_mode_skin` | 开关 | 次表面散射使用皮肤模型 |
| `cull` | `back` / `front` / `disabled` | 背面剔除；默认 `back`，`cull_disabled` 表示双面 |
| `unshaded` | 开关 | **不受光照**（自发光式输出） |
| `wireframe` | 开关 | 线框渲染 |
| `diffuse` | `lambert` / `lambert_wrap` / `burley` / `toon` | 漫反射模型 |
| `specular` | `schlick_ggx` / `toon` / `disabled` | 高光模型 |
| `skip_vertex_transform` | 开关 | 跳过顶点变换（自己算 `POSITION`） |
| `world_vertex_coords` | 开关 | `VERTEX` 改用世界坐标 |
| `ensure_correct_normals` | 开关 | 在 `vertex()` 修改法线后自动重建切线 |
| `shadows_disabled` | 开关 | **不参与阴影投射与接收** |
| `ambient_light_disabled` | 开关 | 忽略环境光 |
| `shadow_to_opacity` | 开关 | 用阴影强度调制 `ALPHA` |
| `vertex_lighting` | 开关 | 逐顶点光照（更快，质量更低） |
| `particle_trails` | 开关 | 粒子拖尾 |
| `alpha_to_coverage` | 开关 | Alpha 转覆盖率（MSAA） |
| `alpha_to_coverage_and_one` | 开关 | Alpha 转覆盖率并保留一个样本 |
| `debug_shadow_splits` | 开关 | 调试用：可视化阴影级联分割 |
| `fog_disabled` | 开关 | 不受雾影响 |

### 4.2 canvas_item（5 条）

| `render_mode` | 取值 | 作用 |
|---|---|---|
| `skip_vertex_transform` | 开关 | 跳过顶点变换 |
| `blend` | `mix` / `add` / `sub` / `mul` / `premul_alpha` / `disabled` | 混合模式；默认 `mix` |
| `unshaded` | 开关 | **不参与 2D 光照** |
| `light_only` | 开关 | 只在光照 pass 绘制（不画普通 pass） |
| `world_vertex_coords` | 开关 | `VERTEX` 改用世界坐标 |

> canvas_item 的 `unshaded` 与 `CanvasItemMaterial.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED` 是同一件事的两种写法：前者写在着色器里，后者写在材质资源上。材质面板上的选项本质上就是给 `ShaderMaterial` 拼 `render_mode` 行。

### 4.3 particles（4 条）

| `render_mode` | 作用 |
|---|---|
| `collision_use_scale` | 粒子碰撞使用缩放后的形状 |
| `disable_force` | 禁用 `ParticleProcessMaterial` 的力（完全自己控制运动） |
| `disable_velocity` | 禁用速度积分（只改 `TRANSFORM`） |
| `keep_data` | 粒子结束后保留数据（用于 trails / 重新激活） |

### 4.4 sky（4 条）

| `render_mode` | 作用 |
|---|---|
| `use_half_res_pass` | 允许半分辨率 pass |
| `use_quarter_res_pass` | 允许四分之一分辨率 pass |
| `disable_fog` | 不参与雾计算 |
| `use_debanding` | 开启去带（debanding） |

### 4.5 fog

4.3 的 `fog` 类型**没有注册任何 `render_mode`**。`sky` 有 4 条，`fog` 一条都没有。

---

## 五、Shader 资源与运行时

### 5.1 Shader 与 ShaderMaterial

| API | 说明 |
|---|---|
| `Shader.code` | 着色器源码（`String`） |
| `Shader.get_mode()` | 返回 `Shader.MODE_*` |
| `Shader.get_shader_uniform_list()` | 列出全部 uniform（含类型、hint、默认值、`group` / `subgroup`） |
| `Shader.get_default_texture_parameter()` | 读贴图的默认采样参数 |
| `Shader.set_default_texture_parameter()` | 写贴图的默认采样参数 |
| `ShaderMaterial.shader` | 绑定的 `Shader` 资源 |
| `ShaderMaterial.set_shader_parameter(name, value)` | 设置 uniform |
| `ShaderMaterial.get_shader_parameter(name)` | 读 uniform |

```gdscript
# 运行时切换 shader
var mat := ShaderMaterial.new()
mat.shader = preload("res://shaders/wave.gdshader")
mat.set_shader_parameter("wave_speed", 2.0)
mat.set_shader_parameter("wave_height", 0.75)
$MeshInstance3D.material_override = mat

# 读回 uniform 清单（调试用）
for u in mat.shader.get_shader_uniform_list():
    print(u["name"], " -> ", u["type"])
```

> `ShaderMaterial.set_shader_parameter()` 的第二个参数类型由 uniform 声明决定：颜色要用 `Color`，向量用 `Vector3`，矩阵用 `Transform3D` / `Basis`，贴图用 `Texture2D`。传错类型不会报错，只会静默失效——这是最常见的"参数没反应"原因。

### 5.2 全局着色器参数

用 `global uniform` 声明的参数由渲染服务器统一管理，跨材质共享，**改一次全体生效**：

```gdscript
RenderingServer.global_shader_parameter_add("fog_color", RenderingServer.GLOBAL_VAR_TYPE_COLOR, Color(0.5, 0.6, 0.7))
RenderingServer.global_shader_parameter_set("fog_color", Color(0.2, 0.3, 0.4))
RenderingServer.global_shader_parameter_get("fog_color")
RenderingServer.global_shader_parameter_remove("fog_color")
```

| API | 说明 |
|---|---|
| `RenderingServer.global_shader_parameter_add()` | 注册（同名会报错） |
| `RenderingServer.global_shader_parameter_set()` | 赋值 |
| `RenderingServer.global_shader_parameter_set_override()` | 临时覆盖（不影响全局值） |
| `RenderingServer.global_shader_parameter_get()` | 读值 |
| `RenderingServer.global_shader_parameter_get_list()` | 列出全部 |
| `RenderingServer.global_shader_parameter_get_type()` | 查类型 |
| `RenderingServer.global_shader_parameter_remove()` | 移除 |

> 全局参数在**所有**着色器类型里都可用，因此不要用它们存"每个材质独有"的数据——那会让材质无法独立复用。

### 5.3 材质链：next_pass

一个材质可以挂一个 `next_pass`（后续 pass），用于做描边、菲涅尔、溶解等"第二道工序"：

```gdscript
var base := StandardMaterial3D.new()
base.albedo_color = Color(0.4, 0.6, 0.9)

var outline := StandardMaterial3D.new()
outline.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
outline.albedo_color = Color(0.0, 0.0, 0.0)
outline.cull_mode = BaseMaterial3D.CULL_FRONT
outline.grow = true
base.next_pass = outline
```

`Material.next_pass` 与 `Material.render_priority` 是 `Material` 基类上的成员，`StandardMaterial3D`、`ShaderMaterial`、`CanvasItemMaterial` 都继承它们。

---

## 六、着色器示例

### 6.1 水波效果（spatial）

```glsl
shader_type spatial;

uniform float wave_speed = 1.0;
uniform float wave_height = 0.5;

void vertex() {
    float wave = sin(VERTEX.x * 2.0 + TIME * wave_speed) * wave_height;
    VERTEX.y += wave;
}

void fragment() {
    ALBEDO = vec3(0.0, 0.5, 1.0);
}
```

### 6.2 溶解效果（spatial）

```glsl
shader_type spatial;

uniform sampler2D noise_texture;
uniform float dissolve_amount : hint_range(0, 1);

void fragment() {
    float noise = texture(noise_texture, UV).r;
    if (noise < dissolve_amount) {
        discard;
    }
    ALBEDO = vec3(1.0, 0.0, 0.0);
}
```

### 6.3 描边（spatial，配合 next_pass）

```glsl
shader_type spatial;
render_mode cull_front, unshaded;

uniform float outline_width = 0.02;

void vertex() {
    VERTEX += NORMAL * outline_width;
}

void fragment() {
    ALBEDO = vec3(0.0);
}
```

### 6.4 2D 精灵染色（canvas_item）

```glsl
shader_type canvas_item;

uniform vec4 tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    COLOR = tex * tint;
    COLOR.rgb = mix(COLOR.rgb, vec3(1.0), flash_amount);
}
```

> 注意这里用的是 `TEXTURE`（canvas_item 的内置采样器）和 `COLOR`（canvas_item 的输出）。把同一段代码原样贴进 `shader_type spatial;` 会同时报两个错：`TEXTURE` 在 spatial 里不是内置采样器，`COLOR` 不是 spatial 的输出。

### 6.5 粒子自定义（particles）

```glsl
shader_type particles;
render_mode disable_force;

uniform float lifetime = 2.0;

void start() {
    TRANSFORM[3].xyz = vec3(0.0);
    VELOCITY = vec3(0.0, 1.0, 0.0);
    COLOR = vec4(1.0);
    CUSTOM = vec4(0.0);
}

void process() {
    CUSTOM.x += DELTA;
    float life = CUSTOM.x / lifetime;
    COLOR.a = clamp(1.0 - life, 0.0, 1.0);
}
```

---

## 七、着色器优化

### 7.1 优化技巧

| 技巧 | 说明 |
|------|------|
| **减少纹理采样** | 合并纹理通道（ORM 打包、法线+粗糙度合并） |
| **简化计算** | 使用近似函数；把高频计算挪到 `vertex()` |
| **提前退出** | `discard` 之前先算廉价判据，避免昂贵的 `texture()` |
| **网格 LOD** | 远处换低模（`GeometryInstance3D.lod_bias` + `visibility_range`） |
| **实例化** | GPU 实例化（MultiMesh）+ `instance uniform` |
| **少开分支** | 避免在片元阶段做 divergent 分支 |

> Godot 4 没有"按距离切换着色器"的材质 LOD 机制；能做到的是切换**网格**的 LOD 层级，或用 `visibility_range` 把远处物体整体剔出渲染列表。

### 7.2 性能对比

> ⚠️ 下表为示意数据（未附测试环境），仅用于建立数量级概念。
> 实际 GPU 占用与帧率取决于屏幕分辨率、场景规模与目标硬件，请在目标平台实测。

| Shader 复杂度 | GPU 占用 | 帧率 |
|------------|---------|------|
| 简单 | 10% | 120 FPS |
| 中等 | 30% | 60 FPS |
| 复杂 | 80% | 30 FPS |

---

## 八、3.x → 4.x 迁移对照

Godot 3.x 的内置变量是小写下划线风格，4.x 改成了大写下划线风格。迁移时最容易漏掉的就是这一批：

| Godot 3.x（已移除） | Godot 4.3（真实写法） | 说明 |
|---|---|---|
| `albedo_texture` | 需自行声明 `uniform sampler2D albedo_texture : source_color;` | 4.x 移除了内置基础色采样器 |
| `normal_texture` | 需自行声明 `uniform sampler2D normal_texture : hint_normal;` | 4.x 移除了内置法线采样器 |
| `normal_texture_depth` | `NORMAL_MAP_DEPTH`（`float`） | 4.7.2 的 spatial 内置量，是深度**标量**不是采样器 |
| `specular_shininess_texture` | 需自行声明 | 4.x 移除了内置高光采样器 |
| `VERTEX` / `NORMAL` / `UV` / `COLOR` | 同名保留 | 这几个名字没变 |
| `screen_uv` | `SCREEN_UV` | 屏幕 UV |
| `light_vertex` / `shadow_vertex` | `LIGHT_VERTEX` / `SHADOW_VERTEX` | 光照 / 阴影 pass 顶点 |
| `at_light_pass` | `AT_LIGHT_PASS` | 是否在光照 pass |
| `time` | `TIME` | 秒数 |
| `roughness` / `metallic` / `albedo` | `ROUGHNESS` / `METALLIC` / `ALBEDO` | 输出量改名 |

还有几条**行为**上的变化：

| 3.x 写法 | 4.3 写法 | 说明 |
|---|---|---|
| `uniform sampler2D texture;` | `uniform sampler2D albedo_tex;` | `texture` 与全局内建函数同名，会被遮蔽 |
| 全局作用域写 `float x;` | 改成 `uniform` / `const` / 挪进函数 | 全局作用域不允许裸变量 |
| `render_mode cull_disabled;` | 不变 | 这条 4.x 沿用了 3.x 的写法 |
| `void fragment() { COLOR = ...; }`（spatial） | 改成 `ALBEDO = ...;` | `COLOR` 只属于 canvas_item |

---

## 核心要点

1. **4.7.2 有 6 种 `shader_type`**（spatial / canvas_item / particles / sky / fog / texture_blit），**没有** `compute`——截至 4.7.2 引擎仍未提供通用计算着色器，写上去会直接报"未知 shader类型"（见 3.6）。
2. **全局作用域只允许** `shader_type` / `render_mode` / `uniform` / `group_uniforms` / `varying` / `const` / `struct` / 函数，裸变量声明是编译错误。
3. **隐式类型转换只有 `int` → `float`**，其余（`float` → `int`、`vec2` → `vec3`）必须用构造函数显式转换，且可用重载是登记死的。
4. **内置变量必须按 `shader_type` 对表查**：spatial 的输出是 `ALBEDO` / `ALPHA` / `METALLIC` / `ROUGHNESS` / `NORMAL` / `EMISSION`，`COLOR` 只属于 canvas_item。
5. **内置采样器只有 `canvas_item` 有**：`TEXTURE` / `NORMAL_TEXTURE` / `SPECULAR_SHININESS_TEXTURE`；**spatial 一个都没有**，贴图必须自己声明 `uniform sampler2D`。3.x 的小写内置名已彻底移除。
6. **不要把 uniform 命名为 `texture`**——它是 127 个全局内建函数之一，同名会被遮蔽。
7. **`render_mode` 一共 35 条**（spatial 22 / canvas_item 5 / particles 4 / sky 4），带选项的写法是 `名字_选项`（`cull_disabled`、`depth_draw_opaque`、`blend_add`）。
8. **`group_uniforms` 是 uniform 分组，不是 UBO**（关键字也不是 `uniform_group`），语法是 `group_uniforms Name;` … `group_uniforms;`；4.3 的 RD 着色器编译器里没有任何 group / uniform_buffer 相关代码，分组名最终只变成检查器的 `PROPERTY_USAGE_GROUP`，运行时这些 uniform 仍是各自独立的。

---

## 🔗 延伸阅读

- **官方文档**: [着色器语言参考（Shading Language）](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/shading_language.html)、[空间着色器](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html)、[CanvasItem 着色器](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/canvas_item_shader.html)
- **类参考**: [Shader](https://docs.godotengine.org/en/stable/classes/class_shader.html)、[ShaderMaterial](https://docs.godotengine.org/en/stable/classes/class_shadermaterial.html)、[Material](https://docs.godotengine.org/en/stable/classes/class_material.html)、[BaseMaterial3D](https://docs.godotengine.org/en/stable/classes/class_basematerial3d.html)
- **源码位置**: `servers/rendering/shader_types.cpp`（内置变量与 `render_mode` 注册表）、`servers/rendering/shader_language.cpp`（词法表、内建函数表、类型转换）、`scene/resources/material.cpp`（`StandardMaterial3D` 的代码生成）、`modules/visual_shader/visual_shader.cpp`（可视化着色器节点）

---

## 📋 下一章预告

**第 18 篇：2D 渲染**

- CanvasItem 的绘制命令与 `_draw()` / `queue_redraw()` 生命周期
- 2D 渲染路径源码：`renderer_canvas_cull.cpp` 的裁剪与 z 排序、`renderer_canvas_render_rd.cpp` 的命令提交
- **用实测事实纠正「2D 合批」叙事**：Godot 3 的 batcher 已移除，Godot 4 没有 2D 通用合批器
- 材质与混合模式、可见性与裁剪、多分辨率与 `canvas_transform`
- 2D 光照与阴影

---

**作者**: wangshucheng
**首发平台**: 微信公众号
**写作时间**: 2026 年 3 月
**Godot 版本**: 4.x（基线 4.7.2；本文涉及的版本差异已在行内标注）

---

**上一篇**: [第 16 篇：材质系统](/articles/16-material-system.md)
**下一篇**: [第 18 篇：2D 渲染](/articles/18-2d-rendering.md)

---

*如果你觉得这篇文章有帮助，欢迎转发给更多开发者！*
