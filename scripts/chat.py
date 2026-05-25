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
        f'如果以上内容不足以回答，请直接说\u201c我没写过这个话题\u201d。\n\n'
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
