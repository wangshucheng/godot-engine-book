#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 Godot 类参考索引 tools/godot_api_index.json。

步骤：
  1. 通过 GitHub tree API 列出 godotengine/godot@<tag> 下所有类参考 XML；
  2. 并行下载（优先 jsDelivr CDN，失败回落 github.com/raw）；
  3. 解析成紧凑索引（类 → 方法 / 属性 / 信号 / 常量 / 枚举 / 属性类型）。

用法:
    python tools/fetch_godot_api.py                # 用默认 tag 4.7.2-stable
    python tools/fetch_godot_api.py --tag 4.7-stable  # 换基线
    python tools/fetch_godot_api.py --index-only    # 只用已下载的 XML 重建索引

注意：raw.githubusercontent.com 在部分网络下不可达，本脚本优先走
      https://cdn.jsdelivr.net/gh/godotengine/godot@<tag>/... 这条 CDN。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_BASE = os.path.join(ROOT, ".audit-tmp", "classxml")
INDEX = os.path.join(ROOT, "tools", "godot_api_index.json")

# 镜像列表：按「当前实测最快」排序，逐个回落。
# 实测（2026-10-21，4.7.2）：github.com raw 1.5s ✓ / gcore.jsdelivr 3.0s ✓ /
# cdn.jsdelivr.net 不通 / raw.githubusercontent.com 超时。
# 镜像可达性会变，所以不写死单条路径，每轮换一条重试。
MIRRORS = [
    "https://github.com/godotengine/godot/raw/refs/tags/{tag}/{path}",
    "https://gcore.jsdelivr.net/gh/godotengine/godot@{tag}/{path}",
    "https://fastly.jsdelivr.net/gh/godotengine/godot@{tag}/{path}",
    "https://cdn.jsdelivr.net/gh/godotengine/godot@{tag}/{path}",
]


def list_paths(tag: str):
    """列出该 tag 下的全部类参考 XML。

    清单落盘到 .audit-tmp/classxml/<tag>.paths.json：
    GitHub tree API 的响应有 1MB+，本机网络经常在传输中途断掉
    （http.client.IncompleteRead），没有缓存 + 重试的话，
    换一次基线就要重赌一次网络运气。
    """
    cache = os.path.join(CACHE_BASE, tag + ".paths.json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return json.load(f)

    url = (f"https://api.github.com/repos/godotengine/godot/git/trees/{tag}"
           "?recursive=1")
    data = None
    last = ""
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8",
                                                       "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            break
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
            print(f"  取清单第 {attempt + 1} 次失败（{last}），重试…")
            time.sleep(2 * (attempt + 1))
    if data is None:
        raise RuntimeError(f"取类参考清单失败：{last}")
    if data.get("truncated"):
        print("  ⚠ GitHub tree 响应被截断，类参考清单可能不完整")

    paths = [t["path"] for t in data.get("tree", []) if t["type"] == "blob"]
    want = [p for p in paths
            if p.endswith(".xml")
            and (p.startswith("doc/classes/")
                 or "/doc_classes/" in p
                 or p.startswith("editor/doc_classes/"))]
    want = sorted(want)
    os.makedirs(CACHE_BASE, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(want, f)
    return want


def cache_dir(tag: str):
    """缓存目录按 tag 隔离。

    历史坑：缓存原本只按「路径」命名（.audit-tmp/classxml/doc__classes__Node.xml），
    换基线时旧版本的 XML 会被当成 "cached" 直接命中，于是两个版本的类参考
    混进同一个索引 —— 判据底座静默失真。
    """
    return os.path.join(CACHE_BASE, tag)


def fetch_one(args):
    path, tag = args
    dest = os.path.join(cache_dir(tag), path.replace("/", "__"))
    if os.path.exists(dest) and os.path.getsize(dest) > 200:
        return (path, "cached")
    last = ""
    for attempt in range(4):
        base = MIRRORS[attempt % len(MIRRORS)]
        url = base.format(tag=tag, path=path)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            if b"<class" not in data[:300] and b"@GlobalScope" not in data[:300]:
                return (path, "notclass")
            os.makedirs(cache_dir(tag), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            return (path, "ok")
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
            time.sleep(0.5 * (attempt + 1))
    return (path, "ERR " + last)


def collect(root):
    out = {"m": set(), "p": set(), "s": set(), "c": set(), "e": {}, "t": {}}
    for tag, key in (("methods", "m"), ("signals", "s")):
        node = root.find(tag)
        if node is None:
            continue
        for child in node:
            n = child.get("name")
            if n:
                out[key].add(n)
    # Godot 4.3 的类 XML 把「枚举成员」也放在 <constants> 里，
    # 用 enum="枚举名" 属性标注所属枚举（4.3 并没有 <enums> 段）
    consts = root.find("constants")
    if consts is not None:
        for child in consts:
            n = child.get("name")
            if not n:
                continue
            out["c"].add(n)
            ename = child.get("enum")
            if ename:
                out["e"].setdefault(ename, []).append(n)
    enums = root.find("enums")
    if enums is not None:  # 兼容 4.4+
        for en in enums:
            ename = en.get("name")
            if not ename:
                continue
            vals = [c.get("name") for c in en if c.get("name")]
            out["e"][ename] = sorted(set(out["e"].get(ename, [])) | set(vals))
    mem = root.find("members")
    if mem is not None:
        for child in mem:
            n = child.get("name")
            if n:
                out["p"].add(n)
                t = child.get("type") or ""
                if t:
                    out["t"][n] = t
    return out


def build_index(tag: str):
    classes = {}
    skipped = []
    cache = cache_dir(tag)
    for fn in sorted(os.listdir(cache)):
        path = os.path.join(cache, fn)
        try:
            root = ET.parse(path).getroot()
        except Exception as e:  # noqa: BLE001
            skipped.append((fn, type(e).__name__))
            continue
        cname = root.get("name")
        if not cname:
            continue
        c = collect(root)
        entry = {
            "inherits": root.get("inherits") or "",
            "m": " ".join(sorted(c["m"])),
            "p": " ".join(sorted(c["p"])),
            "s": " ".join(sorted(c["s"])),
            "c": " ".join(sorted(c["c"])),
        }
        if c["t"]:
            entry["t"] = " ".join(f"{k}:{v}" for k, v in sorted(c["t"].items()))
        if c["e"]:
            entry["e"] = ";".join(k + ":" + " ".join(sorted(v))
                                 for k, v in sorted(c["e"].items()))
        classes[cname] = entry

    glob = classes.pop("@GlobalScope", None)
    global_entry = {"m": "", "c": "", "e": ""}
    if glob:
        global_entry = {"m": glob["m"], "c": glob["c"], "e": glob.get("e", "")}

    singletons = {
        "Input": "Input", "IP": "IP", "OS": "OS", "Engine": "Engine",
        "ProjectSettings": "ProjectSettings", "Performance": "Performance",
        "Time": "Time", "TranslationServer": "TranslationServer",
        "DisplayServer": "DisplayServer", "RenderingServer": "RenderingServer",
        "PhysicsServer2D": "PhysicsServer2D", "PhysicsServer3D": "PhysicsServer3D",
        "NavigationServer2D": "NavigationServer2D",
        "NavigationServer3D": "NavigationServer3D", "AudioServer": "AudioServer",
        "ResourceLoader": "ResourceLoader", "ResourceSaver": "ResourceSaver",
        "JavaScriptBridge": "JavaScriptBridge", "NativeMenu": "NativeMenu",
        "WorkerThreadPool": "WorkerThreadPool", "Geometry2D": "Geometry2D",
        "Geometry3D": "Geometry3D", "Marshalls": "Marshalls",
    }

    out = {
        "version": tag.replace("-stable", ""),
        "source": (f"godotengine/godot @ {tag}: doc/classes/*.xml + "
                   "modules/*/doc_classes/*.xml + editor/doc_classes/*.xml"),
        "class_count": len(classes),
        "classes": classes,
        "global": global_entry,
        "singletons": singletons,
    }
    with open(INDEX, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"索引已生成: {INDEX}")
    print(f"  类数量: {len(classes)}  文件大小: {os.path.getsize(INDEX)} 字节")
    if skipped:
        print(f"  跳过: {len(skipped)} 个无法解析的 XML")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="4.7.2-stable")
    ap.add_argument("--index-only", action="store_true")
    args = ap.parse_args()

    if not args.index_only:
        paths = list_paths(args.tag)
        print(f"目标类参考 XML: {len(paths)} 个")
        ok = bad = 0
        errors = []
        with ThreadPoolExecutor(max_workers=12) as ex:
            for p, st in ex.map(fetch_one, [(x, args.tag) for x in paths]):
                if st in ("ok", "cached"):
                    ok += 1
                else:
                    bad += 1
                    errors.append((p, st))
        print(f"下载完成: {ok} 成功 / {bad} 失败")
        for p, st in errors[:10]:
            print("   ", st, p)
        if bad > len(paths) * 0.02:
            print("失败率过高，请重跑本脚本（CDN 限流时重跑通常即可）")
            return 2
    build_index(args.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
