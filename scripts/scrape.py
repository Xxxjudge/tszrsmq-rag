"""
用法：
  python scripts/scrape.py --cookie "your_cookie_here" --out data/raw/weibo.json

获取 cookie：
  1. 浏览器打开 https://m.weibo.cn 并登录
  2. F12 → Network → 任意请求 → Headers → Cookie 字段，复制整行
"""
import argparse
import json
import time

import requests

UID = "2014433131"
CONTAINERID = f"107603{UID}"
API_URL = "https://m.weibo.cn/api/container/getIndex"
LONGTEXT_URL = "https://m.weibo.cn/statuses/longtext"


def _headers(cookie: str) -> dict:
    return {
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/20A362"
        ),
        "Referer": f"https://m.weibo.cn/u/{UID}",
        "Accept": "application/json, text/plain, */*",
        "MWeibo-Pwa": "1",
    }


def fetch_longtext(post_id: str, cookie: str) -> str | None:
    """获取长微博全文，失败返回 None。"""
    try:
        resp = requests.get(
            LONGTEXT_URL,
            params={"id": post_id},
            headers=_headers(cookie),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("longTextContent")
    except Exception:
        return None


def fetch_page(page: int, cookie: str) -> list[dict]:
    """抓取单页微博，长文自动补全全文。"""
    params = {
        "uid": UID,
        "type": "uid",
        "page": page,
        "containerid": CONTAINERID,
    }
    resp = requests.get(API_URL, params=params, headers=_headers(cookie), timeout=15)
    resp.raise_for_status()
    cards = resp.json().get("data", {}).get("cards", [])

    posts = []
    for card in cards:
        if card.get("card_type") != 9:
            continue
        mblog = card.get("mblog", {})
        text = mblog.get("text", "")

        # 长文截断时补抓全文
        if mblog.get("isLongText") or "全文</a>" in text:
            full = fetch_longtext(mblog.get("id"), cookie)
            if full:
                text = full
            time.sleep(0.5)

        posts.append({
            "id": mblog.get("id"),
            "text": text,
            "created_at": mblog.get("created_at", ""),
            "reposts_count": mblog.get("reposts_count", 0),
            "is_repost": "retweeted_status" in mblog,
        })
    return posts


def scrape_all(cookie: str, max_pages: int = 200, sleep_sec: float = 1.5) -> list[dict]:
    """分页抓取全部微博，遇到空页或重复停止。"""
    all_posts = []
    seen_ids: set[str] = set()

    for page in range(1, max_pages + 1):
        try:
            posts = fetch_page(page, cookie)
        except Exception as e:
            print(f"Page {page} error: {e}, stopping.")
            break

        new_posts = [p for p in posts if p["id"] not in seen_ids]
        if not new_posts:
            print(f"Page {page}: no new posts, stopping.")
            break

        for p in new_posts:
            seen_ids.add(p["id"])
        all_posts.extend(new_posts)
        print(f"Page {page}: +{len(new_posts)} posts, total {len(all_posts)}")
        time.sleep(sleep_sec)

    return all_posts


def main():
    parser = argparse.ArgumentParser(description="抓取微博内容")
    parser.add_argument("--cookie", required=True, help="微博登录 cookie")
    parser.add_argument("--out", default="data/raw/weibo.json")
    parser.add_argument("--max-pages", type=int, default=200)
    args = parser.parse_args()

    posts = scrape_all(args.cookie, max_pages=args.max_pages)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(posts)} posts to {args.out}")


if __name__ == "__main__":
    main()
