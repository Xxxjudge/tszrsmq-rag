import argparse
import json
import re
from html import unescape

import chromadb
from FlagEmbedding import BGEM3FlagModel

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


def load_model() -> BGEM3FlagModel:
    """加载 bge-m3 嵌入模型（首次运行会下载约 2GB）。"""
    return BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)


def embed_and_store(chunks: list[dict], model: BGEM3FlagModel) -> None:
    """向量化 chunks 并写入 Chroma，已存在的 id 自动跳过。"""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    existing_ids = set(collection.get()["ids"])
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]

    if not new_chunks:
        print("No new chunks to add.")
        return

    texts = [c["text"] for c in new_chunks]
    print(f"Encoding {len(texts)} chunks with bge-m3...")
    embeddings = model.encode(texts, batch_size=12, max_length=512)["dense_vecs"]

    collection.add(
        ids=[c["id"] for c in new_chunks],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[
            {"created_at": c["created_at"], "post_id": c["post_id"]}
            for c in new_chunks
        ],
    )
    print(f"Stored {len(new_chunks)} chunks. Total in DB: {len(existing_ids) + len(new_chunks)}")


def process_main():
    parser = argparse.ArgumentParser(description="清洗微博并入库")
    parser.add_argument("--input", default="data/raw/weibo.json")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        raw_posts = json.load(f)

    chunks = prepare_chunks(raw_posts)
    print(f"Prepared {len(chunks)} chunks from {len(raw_posts)} posts")

    if not chunks:
        print("No chunks to process.")
        return

    model = load_model()
    embed_and_store(chunks, model)


if __name__ == "__main__":
    process_main()
