# 书稿自动门禁

本书是**纯内容仓库**（docsify），没有构建也没有测试。`tools/` 下的工具把评审报告 §6.3
建议的 5 条门禁固化成了可重复执行的脚本：

| 规则组 | 抓什么 | 对应报告条目 |
|---|---|---|
| `structure` | 代码围栏不闭合 / 表格列数不一致 / 内部链接断链 / 裸 LF 行尾 / 篇末四件套缺失 | §6.3「链接与围栏检查」 |
| `api` | 代码块与正文里引用的 Godot 类 / 方法 / 属性 / 常量 / 枚举是否真实存在于 4.3 官方类参考 | §6.3「API 存在性检查」 |
| `stats` | README 与封面的统计读数是否与书稿实测一致 | §6.3「统计读数校验」 |
| `perf` | 性能读数是否带测试条件或「示意数据」标注 | §6.3「性能数字标注检查」 |

## 快速使用

```bash
python tools/verify_book.py                # 跑全部规则（CI 里跑的就是这条）
python tools/verify_book.py --rules api    # 只跑 API 存在性
python tools/verify_book.py --rules structure
python tools/verify_book.py --selftest     # 判据自检（阳性对照）
python tools/verify_book.py --report out.txt
```

退出码：`0` 全通过；`1` 有 error；`2` 门禁自身出错（缺索引等）。

## 文件

| 文件 | 作用 |
|---|---|
| `tools/verify_book.py` | 门禁本体 |
| `tools/godot_api_index.json` | Godot **4.3** 官方类参考索引（由 `doc/classes/*.xml` + `modules/*/doc_classes/*.xml` + `editor/doc_classes/*.xml` 派生） |
| `tools/fetch_godot_api.py` | 重新抓取官方类参考并重建索引（换版本 / 升基线时用） |
| `tools/api_allowlist.txt` | 白名单：书里**有意提及**的、不存在于 4.3 的符号 |

## 索引从哪来

`tools/godot_api_index.json` 由 `tools/fetch_godot_api.py` 生成，流程是：

1. GitHub tree API 列出 `godotengine/godot@4.3-stable` 下的全部类参考 XML（962 个）；
2. 并行下载（优先 `cdn.jsdelivr.net`，回落 `github.com/raw`；
   `raw.githubusercontent.com` 在部分网络下不可达，别用它）；
3. 解析成紧凑索引：每个类一行，记方法 / 属性 / 信号 / 常量 / 枚举 / 属性类型。

> **坑点提醒**：Godot 4.3 的类 XML **没有 `<enums>` 段**——枚举成员写在 `<constants>` 里，
> 用 `enum="枚举名"` 属性标注所属枚举。只解析 `<enums>` 会导致所有枚举**类型名**
> （如 `DirectionalLight3D.ShadowMode`、`Viewport.DebugDraw`）查不到。

重建索引：

```bash
python tools/fetch_godot_api.py                 # 4.3-stable（默认）
python tools/fetch_godot_api.py --tag 4.4-stable # 换基线
python tools/fetch_godot_api.py --index-only     # 只重建，不重下
```

## 判据必须自证有牙

`--selftest` 用一组**已知的历史 P0** 做阳性对照：

- `extends LOD3D`（4.3 无此类）
- `DirectionalLight3D.shadow_max_distance` / `shadow_orthogonal_size`（不存在）
- `LightmapGI.bake_mode`（不存在）
- `LightmapGI.light_data = "res://x.gi"`（类型错，属性是 `LightmapGIData` 资源）
- `EditorResourceImporter.new()`（不存在）
- `Performance.RENDER_TOTAL_DRAW_CALLS`（常量名错）
- `ResourceSaver.save_to_buffer()`（4.3/4.4/4.5/master 全都没有）
- 以及 3 个**阳性对照**（`directional_shadow_mode`、`Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME`、
  `light_color = Color(...)` 必须**不报**）

判据本身出问题时，`--selftest` 会先红。

## 白名单纪律

`tools/api_allowlist.txt` 只允许收「书里有意提及」的符号，每条必须写明依据：

| 类别 | 例子 |
|---|---|
| C++ 引擎内部类型 | `ObjectID`、`MethodBind`、`RendererSceneCull`、`SCsub` |
| 4.4+ / 4.6+ 才引入 | `SpringBoneSimulator3D`（4.4+）、`IKModifier3D`（4.6+） |
| 3.x 已移除（迁移对照） | `ParticleShape3D`、`KinematicBody`、`WebSocketServer` |
| Unity 侧 API | `MonoBehaviour`、`ScriptableRenderPipeline` |
| 书里写「4.x 没有这个 API」的反例 | `ResourceLoader.unload`、`AudioServer.set_hrtf_enabled` |
| 书稿示例里的自定义方法/信号 | `_get_or_create_metrics`、`peer_connected` |

⚠️ **把真实缺陷放进白名单等于关掉门禁**。新增条目前请先确认它确实是「有意提及」，
而不是「写错了」。

## 统计口径

`--rules stats` 的口径（README / 封面必须与之一致）：

- **正文中文字** = 剔除代码围栏后的 CJK 汉字（U+4E00–U+9FFF）
- **代码行** = **带语言标记**的代码块内的非空行（不含围栏本身）
- **代码块** = 全部 ``` 围栏（另计带语言标记的个数）
- **示意图** = 含制表符画框线的图示块（≥3 行连续）
- **表格** = 正文中的 Markdown 表格块

## CI

`.github/workflows/book-check.yml` 在 push / PR 时自动跑：

1. `--selftest`（判据自检）
2. 全量门禁，并上传报告工件

> 仓库 `core.autocrlf=true` 且没有 `.gitattributes`，工作区约定 **CRLF**。
> 改稿后请确认行尾没被写成 LF（`structure` 规则会判红）。
