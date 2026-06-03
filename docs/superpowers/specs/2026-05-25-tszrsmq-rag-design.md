# 唐史主任司马迁微博 RAG 问答系统设计

**日期：** 2026-05-25  
**目标：** 抓取唐史主任司马迁的全部微博，构建本地 RAG 问答系统，以其知识和风格回答历史问题。

---

## 架构总览

```
微博数据抓取  →  文本清洗/分块  →  向量化入库
                                      ↓
用户提问  →  向量检索（Top-5 相关段落）  →  本地 LLM 生成回答
```

**核心组件：**

| 组件 | 工具 | 说明 |
|------|------|------|
| 数据抓取 | weibo-scraper | Python 库，需登录 cookie |
| 向量数据库 | Chroma | 本地文件存储，`./chroma_db/` |
| 嵌入模型 | bge-m3 | 本地运行，中文优化 |
| 生成模型 | Ollama + qwen2.5:7b | 本地推理，支持 Apple Silicon |
| 交互界面 | Python 命令行脚本 | 循环问答 |

---

## 第一步：数据获取

- 目标账号：唐史主任司马迁，微博 UID `2014433131`
- 工具：`weibo-scraper`（`pip install weibo-scraper`，如不可用可改用 `weibo`）
- 抓取内容：全部微博原文，保存为 JSON
- 每条记录字段：`id`、`text`、`created_at`、`reposts_count`
- 预估数据量：1~3 万条，原始 JSON 约 20~50MB
- 需要：从浏览器复制微博登录 cookie

---

## 第二步：文本清洗与分块

**清洗规则：**
- 只保留原创微博，过滤转发内容
- 去除 URL、表情符号、话题标签（`#xxx#`）
- 过滤少于 50 字的短微博

**分块策略：**
- 普通微博：每条作为一个独立 chunk
- 长微博（>500 字）：按段落切割，50 字重叠
- 每个 chunk 保留元数据：`id`、`created_at`、`original_text`

---

## 第三步：向量化入库

- 使用 `bge-m3` 对每个 chunk 生成向量
- 写入本地 Chroma 数据库（`./chroma_db/`）
- 持久化存储，重启不丢失，支持增量追加

---

## 第四步：问答交互

**检索策略：**
- 用户提问 → bge-m3 向量化 → 检索 Top-5 最相关 chunk
- 将 5 条原文拼入 prompt

**系统 Prompt：**
```
你是唐史主任司马迁，以下是你写过的相关内容：

{检索到的5条原文}

请用你一贯的风格回答用户的问题。如果以上内容不足以回答，
请直接说"我没写过这个话题"。
```

**交互方式：**
- 命令行循环问答
- 每次输出：回答正文 + 来源微博摘要（id + 前 50 字）
- 输入 `quit` 退出

---

## 目录结构

```
~/learning/tszrsmq/
├── data/
│   ├── raw/          # 原始抓取 JSON
│   └── cleaned/      # 清洗后数据
├── chroma_db/         # 向量数据库
├── scripts/
│   ├── scrape.py     # 数据抓取
│   ├── process.py    # 清洗与入库
│   └── chat.py       # 问答交互
├── docs/
│   └── superpowers/specs/
└── requirements.txt
```

---

## 依赖

```
weibo-scraper
chromadb
FlagEmbedding      # bge-m3
ollama             # Python SDK
```

Ollama 需单独安装（https://ollama.com），并拉取模型：
```bash
ollama pull qwen2.5:7b
```
