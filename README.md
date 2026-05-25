# 唐史主任司马迁 RAG 问答系统

本地 RAG 问答系统，基于微博大V「唐史主任司马迁」的全部原创内容，用其知识和风格回答唐史相关问题。全程本地运行，无需联网。

## 工作原理

```
抓取微博 → 清洗分块 → bge-m3 向量化 → Chroma 存储
                                              ↓
用户提问 → 向量检索 Top-5 → qwen3.5 生成回答
```

## 环境要求

- macOS（Apple Silicon 推荐）
- Python 3.11+
- [Ollama](https://ollama.com/download)

## 快速开始

**1. 安装依赖**

```bash
pip install -r requirements.txt
```

**2. 安装 Ollama 并拉取模型**

```bash
# M 系列 Mac 推荐 MLX 版本
ollama pull qwen3.5:9b-mlx
```

**3. 获取微博 Cookie**

浏览器打开 https://m.weibo.cn 并登录，F12 → Network → 任意请求 → Headers → 复制 `Cookie` 字段整行。

**4. 抓取数据**

```bash
# 先测试 3 页
python scripts/scrape.py --cookie "YOUR_COOKIE" --out data/raw/weibo_test.json --max-pages 3

# 确认正常后抓全量（约 10000+ 条，需要几分钟）
python scripts/scrape.py --cookie "YOUR_COOKIE" --out data/raw/weibo.json --max-pages 200
```

**5. 向量化入库**

```bash
python scripts/process.py --input data/raw/weibo.json
```

首次运行会下载 bge-m3 模型（约 2GB），入库耗时约 10~30 分钟。

**6. 开始对话**

```bash
python scripts/chat.py
```

## 目录结构

```
├── scripts/
│   ├── scrape.py       # 微博数据抓取
│   ├── process.py      # 清洗、分块、向量化入库
│   └── chat.py         # 检索 + 问答交互
├── tests/
│   ├── test_process.py # 清洗/分块单元测试
│   └── test_chat.py    # prompt 构建单元测试
├── data/
│   └── raw/            # 原始抓取数据（不入库）
├── chroma_db/          # 向量数据库（不入库）
└── requirements.txt
```

## 运行测试

```bash
pytest tests/ -v
```

## 切换模型

在 `scripts/chat.py` 第 44 行修改模型名：

```python
model="qwen3.5:9b-mlx",   # M 系列 Mac 推荐
# model="qwen3.5:4b",     # 内存较小时用这个
```
