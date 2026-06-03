# 唐史主任司马迁·投资思维助手

基于微博博主「唐史主任司马迁」全部原创内容构建的 Claude Code Skill，以其视角和风格回答 A 股市场、科技投资、地缘政治等问题。支持每次激活时自动抓取最新微博。

## 安装 Skill

```bash
npx skills add Xxxjudge/tszrsmq-rag
```

安装后在 Claude Code 对话中直接提问即可，无需其他配置。

## 配置自动更新（可选）

如需每次激活时自动拉取最新微博，配置 Cookie：

**第一步：获取 Cookie**

浏览器打开 https://m.weibo.cn 并登录，`F12` → `Network` → 任意请求 → `Headers` → 复制 `Cookie` 字段整行。

**第二步：写入 `.cookie` 文件**

```bash
nano ~/learning/tszrsmq/.cookie
# 粘贴 Cookie 内容，Ctrl+O 保存，Ctrl+X 退出
```

配置后，每次 Skill 激活时会自动抓取最新微博并重建知识库。`.cookie` 文件不会提交到 Git。

## 手动更新知识库

```bash
cd ~/learning/tszrsmq
python scripts/build_knowledge.py
```

## 工作原理

```
Skill 激活
    ↓
运行 build_knowledge.py
    ├── .cookie 存在 → 抓取最新微博（含长文全文）→ 重建 knowledge/weibo_knowledge.md
    └── .cookie 不存在 → 使用现有知识库
    ↓
Claude 读取知识库，以唐史主任司马迁的视角回答问题
```

## 目录结构

```
├── SKILL.md                    # Claude Code Skill 主文件
├── knowledge/
│   └── weibo_knowledge.md      # 清洗后的微博知识库（自动生成）
├── scripts/
│   ├── scrape.py               # 微博抓取（支持长文全文）
│   ├── build_knowledge.py      # 更新数据 + 重建知识库
│   ├── process.py              # 文本清洗/分块/向量化（RAG 备用）
│   └── chat.py                 # 命令行问答（RAG 备用）
├── tests/
│   ├── test_process.py
│   └── test_chat.py
├── .cookie                     # 微博 Cookie（本地，不提交）
└── requirements.txt
```

## 本地开发

```bash
pip install -r requirements.txt
pytest tests/ -v
```
