"""
更新微博数据并重建 knowledge/weibo_knowledge.md

用法：
  python scripts/build_knowledge.py

Cookie 配置：
  在项目根目录创建 .cookie 文件，粘贴微博登录 Cookie（一行）：
    echo "your_cookie_here" > .cookie

  获取 Cookie：浏览器打开 https://m.weibo.cn → 登录 → F12 → Network →
  任意请求 → Headers → 复制 Cookie 字段整行
"""
import json
import os
import re
import sys
from html import unescape
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW_PATH = ROOT / "data/raw/weibo.json"
KNOWLEDGE_PATH = ROOT / "knowledge/weibo_knowledge.md"
COOKIE_PATH = ROOT / ".cookie"


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"#[^#]+#", "", text)
    text = re.sub(r"http\S+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def update_weibo():
    if not COOKIE_PATH.exists():
        print(f"[跳过抓取] 未找到 .cookie 文件，使用现有数据。")
        print(f"  如需更新，请执行：echo 'your_cookie' > {COOKIE_PATH}")
        return

    cookie = COOKIE_PATH.read_text().strip()
    if not cookie:
        print("[跳过抓取] .cookie 文件为空。")
        return

    print("[抓取] 正在更新微博数据...")
    scrape = ROOT / "scripts/scrape.py"
    ret = os.system(
        f'python "{scrape}" --cookie "{cookie}" --out "{RAW_PATH}" --max-pages 200'
    )
    if ret != 0:
        print("[警告] 抓取失败，使用现有数据继续。")


def build_knowledge():
    if not RAW_PATH.exists():
        print(f"[错误] 找不到 {RAW_PATH}，请先运行 scrape.py")
        sys.exit(1)

    with open(RAW_PATH, encoding="utf-8") as f:
        posts = json.load(f)

    originals = [p for p in posts if not p.get("is_repost")]
    originals.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    lines = [
        "# 唐史主任司马迁 微博语料库\n",
        f"> 共 {len(originals)} 条原创微博，按时间倒序排列。\n\n---\n",
    ]
    count = 0
    for p in originals:
        c = clean(p["text"])
        if len(c) < 10:
            continue
        date = p.get("created_at", "")[:16]
        lines.append(f"**[{date}]** {c}\n")
        count += 1

    KNOWLEDGE_PATH.parent.mkdir(exist_ok=True)
    KNOWLEDGE_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[完成] 已写入 {count} 条，总字数 {KNOWLEDGE_PATH.stat().st_size:,} bytes → {KNOWLEDGE_PATH}")


if __name__ == "__main__":
    update_weibo()
    build_knowledge()
