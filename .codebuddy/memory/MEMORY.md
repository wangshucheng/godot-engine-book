# MEMORY（长期记忆）

## 项目：godot-engine-book（《深入理解 Godot 引擎》中文教程）
- docsify 纯内容仓库；无构建/测试；push 到 main 即发布 GitHub Pages。
- 结构：卷一 01-10 / 卷二 11-22 / 卷三 23-36（含 2D 物理 33、Jolt 34、软体 35、调试 36）/ 卷四 37-44 / 卷五 45-48,59,62 / 卷六 49-52,57 / 卷七 53-56,60 / 卷八 58,61,63-68 / 卷九 69-72（GDExtension/C++ 模块）/ 附录 A-D。共 76 篇（72 编号 + 4 附录）。
- 33-36 曾被远端（PR #2）用作 GDExtension 卷，经合并决策改号 69-72；物理续篇保留 33-36。

## 验证方法
- Godot 事实核验抓源码：`raw.githubusercontent.com/godotengine/godot/<tag>/<路径>`（docs 页面 fetch 只返回导航，且体积巨大，慎用）；
  本机 raw 域名常超时，走 jsDelivr 镜像或 git 浅克隆更稳；GitHub API 会限流，contents API 优先用 `gcore.jsdelivr.net`。
  **书里的源码路径与行号引用已按 4.7.2 官方源码逐处核对**（含第 14 篇两张 pass 顺序表，按 4.7.2 的实际执行顺序重建）；
  API 存在性以 4.7.2 官方类参考为准——两套口径别混。
- 编辑器设置键在 `editor/editor_settings.cpp`；已确认真实键与虚构键清单见 2026-09-12.md。

## 改稿前必跑的门禁（2026-10-21 起）
- `python tools/verify_book.py` —— 书稿自动门禁，四组规则：`structure`（围栏/表格列数/内部链接/CRLF 行尾/篇末四件套）、`api`（比对 `tools/godot_api_index.json` 这份 **Godot 4.7.2 官方类参考**索引）、`stats`（README 与封面的读数校验）、`perf`（性能数字是否带测试条件或「示意数据」）。
- `python tools/verify_book.py --selftest` —— **判据自检**，13 个合成片段做对照。判据本身改动后**先跑这个**，否则可能「看起来是绿的、其实已经不管了」。
- 索引重建 / 换基线：`python tools/fetch_godot_api.py [--tag <tag>-stable]`。
  缓存按 tag 隔离在 `.audit-tmp/classxml/<tag>/`（**换基线前务必确认不是旧版缓存**）；
  镜像逐个回落（github raw → gcore.jsdelivr → fastly.jsdelivr → cdn.jsdelivr）；
  类参考清单缓存在 `.audit-tmp/classxml/<tag>.paths.json`（tree API 响应大、本机易断流）；
  网络实在拉不动时用 `git clone --depth 1 --filter=blob:none --sparse --branch <tag>` + `git sparse-checkout set --no-cone`，
  再与 CDN 版**逐字节比对**才当判据底座。
  换完基线三件事：① `--selftest` 阳性对照仍成立；② 白名单按新基线对账（符号进基线就删条目）；③ 书里「某版本没有 X」的断言逐条重判。
- 白名单纪律：`tools/api_allowlist.txt` 只收「书里**有意提及**」的符号（C++ 引擎内部类型 / 4.4+ 引入 / 3.x 已移除 / Unity 侧 / 书里写明的反例 / 示例占位），**每条必须写明依据**；把真实缺陷放进白名单等于关掉门禁。
- 提交纪律：**每个 commit 都要门禁全绿**。改稿类提交不要拆成"半成品"中间态（拆分后 CI 会红）。
- 工作区行尾为 **CRLF**（`core.autocrlf=true`，无 `.gitattributes`）；新增文件也要按 CRLF 写。

## 用户偏好
- 要求资深专家级内容：所有代码示例必须可在 Godot 4.x 运行；不确定的 API 先查官方源码/文档再写。
- 术语约定：概念用中文（着色器/停靠面板/检查器），API 与代码标识符保持英文。
- 性能数字必须标注测试条件或注明"示意数据"。
- 改稿完成后**提交到本地仓库**（git commit），推送前先问。
