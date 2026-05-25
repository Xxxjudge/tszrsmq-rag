import re
from html import unescape

MIN_TEXT_LEN = 50
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "weibo_posts"


def clean_text(html_text: str) -> str:
    """去除 HTML 标签、话题标签、URL，规范化空白。"""
    text = re.sub(r'<[^>]+>', '', html_text)
    text = unescape(text)
    text = re.sub(r'#[^#]+#', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def chunk_post(text: str, max_len: int = 500, overlap: int = 50) -> list[str]:
    """短文本直接返回；长文本按字符切割，相邻块有 overlap 字重叠。"""
    if len(text) <= max_len:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
        chunks.append(text[start:end])

        if end >= len(text):
            break

        # For the next chunk:
        # If remaining text is less than max_len, overlap back to ensure context
        remaining = len(text) - end
        if remaining < max_len:
            start = max(0, len(text) - max_len)
        else:
            # Otherwise, use the overlap parameter
            start = end - overlap

    return chunks


def prepare_chunks(raw_posts: list[dict]) -> list[dict]:
    """过滤转发和短文，清洗并分块，返回带 id/text/created_at/post_id 的列表。"""
    chunks = []
    for post in raw_posts:
        if post.get("is_repost"):
            continue
        cleaned = clean_text(post["text"])
        if len(cleaned) < MIN_TEXT_LEN:
            continue
        for i, chunk in enumerate(chunk_post(cleaned)):
            chunks.append({
                "id": f"{post['id']}_{i}",
                "text": chunk,
                "created_at": post.get("created_at", ""),
                "post_id": post["id"],
            })
    return chunks
