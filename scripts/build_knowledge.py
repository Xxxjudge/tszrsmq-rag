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
        print("[跳过抓取] 未找到 .cookie 文件，使用现有数据。")
        return

    cookie = COOKIE_PATH.read_text().strip()
    if not cookie:
        print("[跳过抓取] .cookie 文件为空。")
        return

    sys.path.insert(0, str(ROOT))
    from scripts.scrape import scrape_all

    # 加载现有数据（增量模式）or 全量下载
    existing_posts: list[dict] = []
    if RAW_PATH.exists():
        with open(RAW_PATH, encoding="utf-8") as f:
            existing_posts = json.load(f)
        existing_ids = {p["id"] for p in existing_posts}
        print(f"[增量] 已有 {len(existing_posts)} 条，抓取新数据...")
        new_posts = scrape_all(cookie, existing_ids=existing_ids)
    else:
        print("[全量] 首次抓取，下载全部数据...")
        new_posts = scrape_all(cookie)

    if not new_posts:
        if not existing_posts:
            print("[警告] 无数据可用。")
            return
        print("[提示] 没有新帖子，知识库使用现有数据。")
    else:
        # 新帖插到头部，保留历史
        merged = new_posts + existing_posts
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RAW_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"[保存] 新增 {len(new_posts)} 条，总计 {len(merged)} 条 → {RAW_PATH}")


def build_knowledge():
    if not RAW_PATH.exists():
        print(f"[错误] 找不到 {RAW_PATH}，请先运行 scrape.py")
        sys.exit(1)

    with open(RAW_PATH, encoding="utf-8") as f:
        posts = json.load(f)

    from email.utils import parsedate_to_datetime
    def parse_date(p):
        try:
            return parsedate_to_datetime(p.get("created_at", ""))
        except Exception:
            return datetime.min

    from datetime import datetime
    originals = [p for p in posts if not p.get("is_repost")]
    originals.sort(key=parse_date, reverse=True)

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
