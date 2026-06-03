# 唐史主任司马迁 RAG 问答系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 抓取唐史主任司马迁（UID: 2014433131）的全部微博，向量化存入本地 Chroma，用 Qwen2.5:7b 以其风格在命令行回答历史问题。

**Architecture:** 三个串联脚本：scrape.py 调用微博移动端 API 抓取原始数据，process.py 清洗/分块/bge-m3 向量化写入 Chroma，chat.py 检索 Top-5 后让 Ollama 生成回答。嵌入和推理全部本地运行，无需联网。

**Tech Stack:** Python 3.11+, requests, chromadb, FlagEmbedding (bge-m3), ollama, pytest

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `requirements.txt` | 依赖声明 |
| `scripts/scrape.py` | 调用微博移动端 API，分页抓取，保存 JSON |
| `scripts/process.py` | 清洗文本、分块、bge-m3 向量化、写入 Chroma |
| `scripts/chat.py` | 检索 Top-5 + Ollama 生成，命令行问答循环 |
| `tests/test_process.py` | 测试 clean_text、chunk_post、prepare_chunks |
| `tests/test_chat.py` | 测试 build_prompt |

---

### Task 1: 项目初始化

**Files:**
- Create: `requirements.txt`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: 创建目录结构**

```bash
cd ~/learning/tszrsmq
mkdir -p scripts tests data/raw data/cleaned chroma_db
touch scripts/__init__.py tests/__init__.py
```

- [ ] **Step 2: 创建 .gitignore**

```
chroma_db/
data/raw/
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 3: 创建 requirements.txt**

```
requests==2.31.0
chromadb==0.5.23
FlagEmbedding==1.2.10
ollama==0.3.3
pytest==8.3.2
```

- [ ] **Step 4: 安装依赖**

```bash
cd ~/learning/tszrsmq
pip install -r requirements.txt
```

Expected: 所有包安装成功，无 error

- [ ] **Step 5: 安装 Ollama 并拉取模型**（如尚未安装）

从 https://ollama.com/download 下载安装 Ollama，然后：

```bash
ollama pull qwen2.5:7b
```

Expected: 下载完成（约 4.7GB），最后一行显示 `success`

- [ ] **Step 6: 验证 Ollama 正常运行**

```bash
ollama run qwen2.5:7b "你好"
```

Expected: 模型输出任意正常中文回复

- [ ] **Step 7: Commit**

```bash
cd ~/learning/tszrsmq
git init
git add requirements.txt .gitignore scripts/__init__.py tests/__init__.py
git commit -m "chore: init project structure and dependencies"
```

---

### Task 2: 文本清洗和分块（TDD）

**Files:**
- Create: `scripts/process.py`（仅 clean_text、chunk_post、prepare_chunks）
- Create: `tests/test_process.py`

- [ ] **Step 1: 创建失败的测试 tests/test_process.py**

```python
import sys
sys.path.insert(0, '.')

from scripts.process import clean_text, chunk_post, prepare_chunks


def test_clean_removes_html_tags():
    raw = '<a href="/u/123">@某人</a> 这是正文内容，讲述唐朝历史。'
    result = clean_text(raw)
    assert '<' not in result
    assert '这是正文内容' in result


def test_clean_removes_topic_tags():
    raw = '#唐朝历史# 李世民即位后开创贞观之治。'
    result = clean_text(raw)
    assert '#' not in result
    assert '李世民即位后' in result


def test_clean_removes_urls():
    raw = '详见 http://t.cn/abc123 这篇文章分析了安史之乱。'
    result = clean_text(raw)
    assert 'http' not in result
    assert '这篇文章分析了安史之乱' in result


def test_clean_strips_whitespace():
    raw = '  武则天   称帝  '
    result = clean_text(raw)
    assert result == '武则天 称帝'


def test_chunk_short_post_returns_single_chunk():
    text = '贞观之治是唐太宗李世民在位期间出现的政治清明、经济恢复、文化繁荣的局面。'
    chunks = chunk_post(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_long_post_splits_by_length():
    text = '唐朝历史' * 130  # 520 字
    chunks = chunk_post(text, max_len=500, overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 500


def test_chunk_overlap():
    text = 'A' * 450 + 'B' * 450  # 900 字
    chunks = chunk_post(text, max_len=500, overlap=50)
    assert len(chunks) == 2
    assert chunks[1][:50] == 'A' * 50


def test_prepare_chunks_filters_reposts():
    posts = [
        {"id": "1", "text": "原创内容" * 20, "created_at": "2024-01-01", "is_repost": False},
        {"id": "2", "text": "转发内容" * 20, "created_at": "2024-01-02", "is_repost": True},
    ]
    chunks = prepare_chunks(posts)
    assert all(c["post_id"] == "1" for c in chunks)


def test_prepare_chunks_filters_short_posts():
    posts = [
        {"id": "1", "text": "短", "created_at": "2024-01-01", "is_repost": False},
        {"id": "2", "text": "这是一篇足够长的微博内容，详细讲述了唐朝的历史背景和社会制度。" * 3,
         "created_at": "2024-01-02", "is_repost": False},
    ]
    chunks = prepare_chunks(posts)
    assert all(c["post_id"] == "2" for c in chunks)


def test_prepare_chunks_assigns_unique_ids():
    long_text = "唐朝历史" * 130  # 520 字，会被分成多块
    posts = [{"id": "99", "text": long_text, "created_at": "2024-01-01", "is_repost": False}]
    chunks = prepare_chunks(posts)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 2: 运行测试确认全部失败**

```bash
cd ~/learning/tszrsmq
pytest tests/test_process.py -v
```

Expected: 10 个测试 FAILED，错误 `ModuleNotFoundError: No module named 'scripts.process'`

- [ ] **Step 3: 创建 scripts/process.py（清洗和分块部分）**

```python
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
    """短文本直接返回；长文本按段落切割，相邻块有 overlap 字重叠。"""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ''
    for para in text.split('\n'):
        if not para:
            continue
        if len(current) + len(para) + 1 <= max_len:
            current = (current + '\n' + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
                tail = current[-overlap:] if len(current) >= overlap else current
                current = (tail + '\n' + para).strip()
            else:
                for i in range(0, len(para), max_len - overlap):
                    chunks.append(para[i:i + max_len])
                current = ''
    if current:
        chunks.append(current)

    return chunks if chunks else [text]


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
```

- [ ] **Step 4: 运行测试确认全部通过**

```bash
pytest tests/test_process.py -v
```

Expected: 10 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/process.py tests/test_process.py
git commit -m "feat: add text cleaning and chunking with tests"
```

---

### Task 3: 实现 scrape.py

**Files:**
- Create: `scripts/scrape.py`

注意：scrape.py 依赖外部 API 和 cookie，不写自动化测试，改为手动验证。

- [ ] **Step 1: 创建 scripts/scrape.py**

```python
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


def fetch_page(page: int, cookie: str) -> list[dict]:
    """抓取单页微博，返回原始 post 列表。"""
    headers = {
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/20A362"
        ),
        "Referer": f"https://m.weibo.cn/u/{UID}",
        "Accept": "application/json, text/plain, */*",
        "MWeibo-Pwa": "1",
    }
    params = {
        "uid": UID,
        "type": "uid",
        "page": page,
        "containerid": CONTAINERID,
    }
    resp = requests.get(API_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    cards = data.get("data", {}).get("cards", [])

    posts = []
    for card in cards:
        if card.get("card_type") != 9:
            continue
        mblog = card.get("mblog", {})
        posts.append({
            "id": mblog.get("id"),
            "text": mblog.get("text", ""),
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
```

- [ ] **Step 2: 手动验证（需要微博 cookie）**

```bash
# 先只抓 3 页验证连接正常
python scripts/scrape.py --cookie "YOUR_COOKIE" --out data/raw/weibo_test.json --max-pages 3
```

Expected: 控制台输出 `Page 1: +N posts`，`data/raw/weibo_test.json` 包含若干条微博记录

- [ ] **Step 3: Commit**

```bash
git add scripts/scrape.py
git commit -m "feat: add weibo scraper via mobile API"
```

---

### Task 4: 完成 process.py（向量化入库）

**Files:**
- Modify: `scripts/process.py`（追加 load_model、embed_and_store、CLI 入口）

- [ ] **Step 1: 用以下完整内容替换 scripts/process.py**

```python
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
    """短文本直接返回；长文本按段落切割，相邻块有 overlap 字重叠。"""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ''
    for para in text.split('\n'):
        if not para:
            continue
        if len(current) + len(para) + 1 <= max_len:
            current = (current + '\n' + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
                tail = current[-overlap:] if len(current) >= overlap else current
                current = (tail + '\n' + para).strip()
            else:
                for i in range(0, len(para), max_len - overlap):
                    chunks.append(para[i:i + max_len])
                current = ''
    if current:
        chunks.append(current)

    return chunks if chunks else [text]


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

    model = load_model()
    embed_and_store(chunks, model)


if __name__ == "__main__":
    process_main()
```

- [ ] **Step 2: 确认现有测试仍全部通过**

```bash
pytest tests/test_process.py -v
```

Expected: 10 个测试全部 PASSED

- [ ] **Step 3: 用测试数据运行入库**

```bash
python scripts/process.py --input data/raw/weibo_test.json
```

Expected: 输出 `Stored N chunks. Total in DB: N`，`chroma_db/` 目录被创建

- [ ] **Step 4: Commit**

```bash
git add scripts/process.py
git commit -m "feat: add bge-m3 embedding and chroma storage pipeline"
```

---

### Task 5: 实现 chat.py（TDD）

**Files:**
- Create: `tests/test_chat.py`
- Create: `scripts/chat.py`

- [ ] **Step 1: 创建失败的测试 tests/test_chat.py**

```python
import sys
sys.path.insert(0, '.')

from scripts.chat import build_prompt


def test_build_prompt_includes_context():
    docs = ["武则天是唐朝唯一的女皇帝。", "武则天在位期间重用寒门士人。"]
    question = "武则天为何重要？"
    prompt = build_prompt(docs, question)
    assert "武则天是唐朝唯一的女皇帝" in prompt
    assert "武则天在位期间重用寒门士人" in prompt
    assert "武则天为何重要" in prompt


def test_build_prompt_has_system_instruction():
    docs = ["任意内容"]
    prompt = build_prompt(docs, "任意问题")
    assert "唐史主任司马迁" in prompt


def test_build_prompt_includes_all_docs():
    docs = [f"内容片段{i}，关于唐朝历史的描述。" for i in range(5)]
    prompt = build_prompt(docs, "问题")
    for doc in docs:
        assert doc in prompt
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_chat.py -v
```

Expected: 3 个测试 FAILED（`ModuleNotFoundError`）

- [ ] **Step 3: 创建 scripts/chat.py**

```python
"""
用法：
  python scripts/chat.py

前置条件：
  - Ollama 已运行，qwen2.5:7b 已下载
  - process.py 已运行，chroma_db/ 已有数据
"""
import chromadb
import ollama
from FlagEmbedding import BGEM3FlagModel

from scripts.process import CHROMA_PATH, COLLECTION_NAME, load_model


def build_prompt(docs: list[str], question: str) -> str:
    context = "\n\n".join(f"[{i+1}] {doc}" for i, doc in enumerate(docs))
    return (
        f"你是唐史主任司马迁，以下是你写过的相关内容：\n\n"
        f"{context}\n\n"
        f"请用你一贯的风格回答用户的问题。"
        f"如果以上内容不足以回答，请直接说"我没写过这个话题"。\n\n"
        f"用户问题：{question}"
    )


def retrieve(question: str, model: BGEM3FlagModel, n_results: int = 5) -> list[dict]:
    """向量检索，返回 Top-N 结果。"""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    q_vec = model.encode([question], max_length=512)["dense_vecs"][0]
    results = collection.query(query_embeddings=[q_vec.tolist()], n_results=n_results)

    return [
        {"text": doc, "meta": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def answer(question: str, model: BGEM3FlagModel) -> tuple[str, list[dict]]:
    """检索 + 生成，返回 (回答文本, 来源列表)。"""
    hits = retrieve(question, model)
    prompt = build_prompt([h["text"] for h in hits], question)
    response = ollama.chat(
        model="qwen2.5:7b",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.message.content, hits


def main():
    print("正在加载模型，请稍候...")
    model = load_model()
    print("模型加载完成，输入问题开始对话（输入 quit 退出）\n")

    while True:
        question = input("你：").strip()
        if question.lower() in ("quit", "exit", "退出"):
            break
        if not question:
            continue
        reply, hits = answer(question, model)
        print(f"\n唐史主任司马迁：{reply}\n")
        print("--- 参考来源 ---")
        for i, h in enumerate(hits, 1):
            print(f"[{i}] {h['text'][:60]}...")
        print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_chat.py -v
```

Expected: 3 个测试全部 PASSED

- [ ] **Step 5: 运行全部测试**

```bash
pytest tests/ -v
```

Expected: 13 个测试全部 PASSED

- [ ] **Step 6: Commit**

```bash
git add scripts/chat.py tests/test_chat.py
git commit -m "feat: add RAG chat interface with source attribution"
```

---

### Task 6: 全量数据入库与端到端验证

**Files:** 无新文件

- [ ] **Step 1: 抓取全量数据**

```bash
python scripts/scrape.py --cookie "YOUR_COOKIE" --out data/raw/weibo.json --max-pages 200
```

Expected: `Saved NNNN posts to data/raw/weibo.json`（预期 5000~15000 条）

- [ ] **Step 2: 清洗并向量化入库**

```bash
python scripts/process.py --input data/raw/weibo.json
```

Expected: `Stored NNNN chunks. Total in DB: NNNN`（耗时约 10~30 分钟）

- [ ] **Step 3: 端到端问答验证**

```bash
python scripts/chat.py
```

建议测试问题：
- `安禄山为何能发动叛乱？`
- `唐太宗和唐玄宗谁更厉害？`
- `杨贵妃真的很美吗？`

Expected: 回答有历史细节和主观色彩，来源显示具体微博片段

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete RAG pipeline with full dataset"
```

---

## 运行顺序总结

```
1. pip install -r requirements.txt
2. ollama pull qwen2.5:7b
3. python scripts/scrape.py --cookie "..." --out data/raw/weibo.json
4. python scripts/process.py --input data/raw/weibo.json
5. python scripts/chat.py
```
