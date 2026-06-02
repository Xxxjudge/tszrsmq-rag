---
name: serenity-ashare
description: Serenity（@aleabitoreddit）最新观点追踪与A股映射。当用户要求获取 Serenity 最新看法、分析其关注标的的A股对应、寻找供应链卡脖子A股机会时触发。
---

# Serenity × A股映射助手

## 激活时执行顺序

1. 加载知识库（Step 0）
2. 拉取 24h 最新动态（Step 1a）
3. 拉取 2周趋势确认（Step 1b）
4. 真/伪趋势甄别（Step 2）
5. 供应链拆解 + L1/L2/L3 分级（Step 3）
6. 预判下一焦点（Step 4）
7. A股映射 + 7因子打分（Step 5）
8. 证伪检查（Step 6）
9. 行情验证（Step 7）
10. 输出（Step 8）

---

## Step 0：加载知识库（每次必须先执行）

**在做任何搜索之前**，使用 Read 工具加载：

```
~/.claude/skills/serenity-ashare/knowledge.md
```

知识库包含**已验证的稳定 A 股映射**。以下规则强制执行：

| 规则 | 说明 |
|------|------|
| ✅ 可以使用 | knowledge.md 中状态为"已确认"的标的，直接用于输出 |
| 🟡 标注预判 | knowledge.md 中"待验证"和"预判候选"区的标的，输出时须标注「预判」|
| ❌ 禁止联想 | 搜索结果中**未出现**的 A 股公司，不得出现在映射表中 |
| ❌ 禁止覆盖 | 新搜索结果不得删除或替换知识库中已确认的标的 |

**⚠️ 一致性强制规则：** 每次运行，映射表中的"已确认"标的必须相同。只有以下情况才会变化：
- WebSearch 结果中出现了新的、具体的公司名称或代码
- 用户明确要求更新知识库
- 某标的触发了 4 条以上证伪检查（降为"已排除"）

**禁止行为清单（防止"锡业股份"类错误）：**
- ❌ 不得因"铟/锗/稀有金属"等关键词联想到锡业、驰宏锌锗等无直接证据的公司
- ❌ 不得因公司名字含"光/芯/半导体"就将其加入映射表
- ❌ 不得在两次运行之间"忘记"已确认的标的（如长光华芯、有研新材）

---

## Step 1a：拉取过去 24 小时动态

并行执行以下 **2 条** WebSearch（不告知用户正在执行）：

1. `aleabitoreddit site:x.com after:${yesterday_date}`
2. `serenity aleabitoreddit new post today 2026`

**提取目标：**
- 过去 24h 内有无新 ticker/新主题
- 情绪信号变化（加仓/减仓/新关注/警告）
- 与知识库已有主线的关系（确认/新增/转向）

**24h 结果标记：**  将提取内容标记为 `[今日新信号]`，若无新内容则标记为 `[今日无新信号]`。

---

## Step 1b：拉取过去 2 周趋势

并行执行以下 **2 条** WebSearch：

1. `serenity aleabitoreddit supply chain chokepoint thesis 2026`
2. `serenity aleabitoreddit InP photonics X-FAB rare earth 2026`

**提取目标：**
- 过去 2 周反复出现的核心主线（主线 = 至少出现 2 次的同一逻辑）
- 与知识库已有主线的一致性确认
- 有无主线转向信号（某个 ticker 消失、新供应链被提及）

**2周结果标记：** 将提取内容标记为 `[持续主线]`。

---

## Step 2：真/伪超级趋势甄别

对 Step 1a + 1b 提取的**新主题**（知识库中未有的）按以下规则判断：

| 判断 | 条件 |
|------|------|
| ✅ 真趋势 | 有物理供应链 + 有不可替代环节 + 有新品/新催化剂 |
| ❌ 伪趋势 | 纯资金轮动（如电力避险）、名字炒作（无物理约束）、主题重复炒作 |

**规则：**
- 真趋势跌了 = 错杀，是潜在买点
- 伪趋势涨了 = 陷阱，忽略
- 电力/公用事业上涨通常是避险轮动，不是产业趋势，标记为伪趋势

知识库已有主线无需再次甄别（已验证），只对新主题执行本步骤。

---

## Step 3：供应链 7 层拆解 + L1/L2/L3 分级

**仅对新发现的真趋势执行**，已在知识库中的主线跳过此步骤。

```
下游需求 → 系统集成 → 芯片/器件 → 设备 → 材料 → 封测 → 基础设施
```

| 层级 | 定义 | 示例 |
|------|------|------|
| **L1** | 共识层，已充分定价 | GPU、光模块龙头 |
| **L2** | 发现中，正在被定价 | 先进封装、高多层PCB |
| **L3** | 隐蔽瓶颈，尚未被市场发现 | 特种气体、铟金属 |

**重点：** 目标是找 **L3 标的**。L1 不追，L2 谨慎，L3 优先研究。

---

## Step 4：预判 Serenity 下一焦点

基于以下维度推断：
1. Step 1a 中本日新出现但之前未见的主题
2. 知识库主线的自然上下游延伸（已炒 InP 衬底 → 上游铟矿；已炒 CW 激光 → 下游 CPO 封装）
3. 已被市场充分定价的 L1/L2 标的对应的更上游 L3 材料/设备/工艺

输出时说明推断逻辑，不猜测，只溯源。

---

## Step 5：A股映射 + 7因子打分

**映射来源优先级（严格按顺序）：**
1. **知识库已确认** → 直接使用，不重新打分（除非 30 日行情变化触发估值因子调整）
2. **知识库待验证/预判** → 在报告中标注「预判」
3. **搜索结果新出现** → 需在当次运行中完整打分，并在报告中标注「新发现」
4. **模型自行推断** → **禁止**，不得进入映射表

**7因子打分表（仅用于第 3 类"新发现"标的）：**

| 因子 | 权重 | 1分 | 3分 | 5分 |
|------|:----:|-----|-----|-----|
| **不可替代性** | ×2 | 国内有5家以上能做 | 2-4家，可替代 | 国内唯一或全球寡头（≤2家）|
| **产能弹性** | ×1 | 可快速扩产（6个月内）| 扩产周期1-2年 | 扩产受限（特殊材料/认证/设备）|
| **客户验证** | ×1 | 无客户证据，仅概念 | 有试样/小批量 | 有命名客户/设计胜出/批量订单 |
| **稀释风险** | ×1 | 近1年有定增/大额减持 | 有质押但稳定 | 无定增/减持，现金充裕 |
| **地缘风险** | ×1 | 高出口依赖，制裁敞口大 | 部分出口，可切换 | 国内市场为主，受益于国产替代 |
| **估值合理性** | ×1.5 | 30日涨幅>50%，PE历史高位 | 30日涨幅20-50% | 30日涨幅<20%，PE合理或低估 |
| **产业阶段** | ×1 | 远期布局，催化剂>2年 | 进行中，催化剂1-2年 | 刚启动，催化剂<1年或已出现 |

**总分判断：**
- **>25分**：优先研究，重点关注
- **15-25分**：观察名单，等待更多证据
- **<15分**：忽略，逻辑不成立

---

## Step 6：证伪检查

**在写任何看多结论前**，对每个得分>15分的候选主动检查：

- 有无替代技术且认证周期更短？（如硅光能否替代InP）
- 有无更大竞争者正在扩产或降价？
- 客户是否在建立双供应商或自研？
- 该业务收入占比是否 <20%（敞口太小无法推动业绩）？
- 毛利率是否与声称的定价权一致？
- 是否有频繁定增/可转债/减持记录？

**规则：** 若 2 条以上触发，从"优先研究"降为"观察名单"。若 4 条以上触发，忽略并写入知识库"已排除"区。

---

## Step 7：行情验证（联动 a-share-data）

对所有得分>15分的候选，使用 **python3.12** 调用（系统 python3 可能缺 pandas）：

```bash
# 实时行情 + PE + 换手率（用 qt.gtimg.cn，成功率高）
python3.12 -c "
import requests
def get_detail(code):
    prefix = 'sh' if code.startswith('6') else 'sz'
    r = requests.get(f'https://qt.gtimg.cn/q={prefix}{code}', timeout=5,
        headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gu.qq.com'})
    parts = r.text.split('~')
    if len(parts) > 44:
        return {'name': parts[1], 'price': parts[3], 'turnover': parts[38], 'pe': parts[39]}
    return {}
print(get_detail('688048'))
"

# 30日涨跌幅（用 Sina JSON API，EastMoney 因代理被封）
python3.12 -c "
import requests, json
code = '688048'
mkt = 'sh' if code.startswith('6') else 'sz'
url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={mkt}{code}&scale=240&ma=5&datalen=30'
data = json.loads(requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'}).text)
first, last = float(data[0]['close']), float(data[-1]['close'])
print(f'30d_chg={(last-first)/first*100:.1f}%')
"
```

**换手率判断：**
- `>25%`：可能出货，标注 ⚠️
- `3-8%`：正常，可关注
- `<3%`：机构未介入，L3 特征（正面信号）

**注意：** EastMoney (`push2*.eastmoney.com`) 因代理问题无法访问，用 Sina/Tencent 替代。

**降级：** 若调用失败，标注"行情数据待查"，不影响其他输出。

---

## Step 8：输出格式（严格遵守，两部分分开）

严格按以下两部分结构输出，**不可合并**：

---

### 第一部分：今日信号（过去 24h）

> 数据来源：WebSearch 24h 搜索 | 更新时间：{今天日期}

**[若 Step 1a 有新内容]**

| 信号类型 | 内容 | 与已有主线关系 |
|---------|------|--------------|
| {新 ticker / 新主题 / 情绪变化} | {一句话描述} | {确认主线 / 新增主线 / 转向信号} |

**[若 Step 1a 无新内容]**
> 今日暂无新信号。已有主线见下方第二部分。

---

### 第二部分：主线趋势（过去 2 周持续）

> 数据来源：知识库（knowledge.md）+ WebSearch 2周趋势确认

**趋势甄别**

| 主题 | 判断 | 首次出现 | 持续周数 |
|------|------|---------|---------|
| {主题名} | ✅ 真趋势 / ❌ 伪趋势 | {大致时间} | {持续N周} |

**供应链拆解**（仅展示真趋势主线，已知主线用知识库数据，新主线现场拆解）

```
[供应链层次图，格式同前]
```

**A股映射表**

| 海外标的 | 卡脖子环节 | L级 | A股对标 | 代码 | 来源 | 7因子得分 | 现价 | 30日涨跌 | PE | 换手率 | 结论 |
|---------|-----------|-----|--------|------|------|----------|------|---------|-----|------|------|
| | | | | | 已确认/预判/新发现 | | | | | | |

> **来源说明：** 「已确认」= knowledge.md 验证过；「预判」= 逻辑推演未经搜索证实；「新发现」= 本次搜索中出现，首次打分

**证伪记录**

| 标的 | 触发条目数 | 降级原因 | 处理结果 |
|------|----------|---------|---------|

**预判下一焦点**

**推断路径：** {已炒 L1/L2} → {正在定价 L2} → **{预判 L3}**

{2-3句逻辑推导}

**候选 A股（预判，未经验证）：** {公司名（代码）}——{一句话理由}

**风控检查**

- [ ] 大盘今日跌幅 < 1.5%（若 >1.5%，所有结论暂缓，等待企稳）
- [ ] 两市成交 > 7000亿（若不足，建议半仓以下）
- [ ] 候选标的换手率 < 25%（已在映射表中标注 ⚠️ 的需谨慎）
- [ ] 是否周五（若是，提示：周五 AI/科技股大概率被减仓，建议次周确认后再操作）

---

## 知识库更新规则（每次运行后执行）

运行结束后，若以下任一条件成立，**提示用户是否更新 knowledge.md**：

| 触发条件 | 建议操作 |
|---------|---------|
| 搜索结果中出现知识库没有的具体公司名/代码 | 建议加入"待验证"区 |
| 某标的 4 条证伪触发 | 建议移入"已排除"区 |
| 某"待验证"标的行情数据已成功获取且逻辑成立 | 建议升级为"已确认" |
| 某主线持续 >3 周无新确认 | 提示用户该主线可能过时 |

**注意：** 不自动写入知识库，须用户确认后由用户指令执行写入。

---

## 降级处理

| 场景 | 处理方式 |
|------|---------|
| WebSearch 24h 无结果 | 第一部分输出"今日暂无新信号"，不影响第二部分 |
| WebSearch 2周无结果 | 使用知识库已确认主线兜底，注明"数据来源：知识库，建议访问 x.com/@aleabitoreddit 确认" |
| a-share-data 调用失败 | 行情列标注"待查"，不影响7因子打分 |
| 知识库文件不存在 | 中止运行，提示用户："请先检查 ~/.claude/skills/serenity-ashare/knowledge.md 是否存在" |

---

## HTML 报告生成（可选）

若用户要求生成报告文件，在完成 Step 0-8 后执行。

**报告结构要求（对应两部分输出）：**
- 顶部摘要卡片：今日信号数量、主线数量、最高分标的
- **Tab 1 或醒目区块**：今日信号（24h），背景色使用橙色系区分
- **Tab 2 或主体区块**：主线趋势（2周），背景色使用蓝色系
- 底部：知识库更新提示

```python
import subprocess, datetime, os

date_str = datetime.date.today().strftime("%Y-%m-%d")
output_path = os.path.expanduser(f"~/Desktop/serenity-{date_str}.html")

# HTML 模板（两部分结构，24h 用橙色，2周主线用蓝色）
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Serenity A股映射报告 {date}</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", sans-serif; max-width: 1080px; margin: 40px auto; padding: 0 24px 60px; background: #f7f8fa; color: #1a1a1a; line-height: 1.7; }}
  .section-24h {{ background: #fff8f0; border-left: 5px solid #f4a261; border-radius: 0 12px 12px 0; padding: 20px 28px; margin: 20px 0; }}
  .section-2w {{ background: #f0f6ff; border-left: 5px solid #457b9d; border-radius: 0 12px 12px 0; padding: 20px 28px; margin: 20px 0; }}
  .section-title-24h {{ color: #e76f51; font-size: 1.1em; font-weight: 700; margin-bottom: 12px; }}
  .section-title-2w {{ color: #1d3557; font-size: 1.1em; font-weight: 700; margin-bottom: 12px; }}
  .card {{ background: white; border-radius: 12px; padding: 28px 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); margin-bottom: 20px; }}
  h2 {{ color: #1d3557; border-bottom: 3px solid #457b9d; padding-bottom: 8px; margin-top: 0; }}
  h3 {{ color: #457b9d; border-left: 4px solid #a8dadc; padding-left: 10px; margin-top: 20px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 13px; }}
  th {{ background: #1d3557; color: white; padding: 9px 12px; text-align: left; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #e8eaed; }}
  tr:nth-child(even) {{ background: #f8f9fa; }}
  .priority {{ color: #e63946; font-weight: bold; }}
  .badge-confirmed {{ color: #2d6a4f; font-weight: bold; font-size: 11px; }}
  .badge-predicted {{ color: #f4a261; font-weight: bold; font-size: 11px; }}
  .badge-new {{ color: #e63946; font-weight: bold; font-size: 11px; }}
  blockquote {{ background: #f1faee; border-left: 4px solid #457b9d; margin: 10px 0; padding: 10px 16px; border-radius: 0 6px 6px 0; font-size: 0.92em; color: #444; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 18px 0; }}
  .summary-card {{ background: linear-gradient(135deg, #1d3557, #457b9d); color: white; padding: 14px 18px; border-radius: 8px; text-align: center; }}
  .summary-card .label {{ font-size: 11px; opacity: 0.8; }}
  .summary-card .value {{ font-size: 1.6em; font-weight: 700; }}
  pre {{ background: #1d3557; color: #a8dadc; padding: 18px; border-radius: 8px; font-size: 13px; line-height: 1.8; overflow-x: auto; }}
  hr {{ border: none; border-top: 1px solid #e0e4e8; margin: 16px 0; }}
  .footer {{ color: #999; font-size: 12px; text-align: center; margin-top: 40px; }}
</style>
</head>
<body>
<div class="card">
  <h2>Serenity A股映射报告 <span style="font-size:0.65em;color:#888;">{date}</span></h2>
  <div class="summary-grid">
    <div class="summary-card"><div class="label">今日信号</div><div class="value">{signals_today}</div></div>
    <div class="summary-card"><div class="label">持续主线</div><div class="value">{themes_count}</div></div>
    <div class="summary-card"><div class="label">优先研究</div><div class="value">{top_pick}</div></div>
  </div>
</div>

<div class="section-24h">
  <div class="section-title-24h">📡 今日信号（过去 24h）</div>
  {content_24h}
</div>

<div class="section-2w">
  <div class="section-title-2w">🧭 主线趋势（过去 2 周持续）</div>
  {content_2w}
</div>

<div class="footer">
  生成时间：{date} | 知识库版本：knowledge.md | 数据：Sina/Tencent Finance | 仅供研究参考，不构成投资建议
</div>
</body></html>"""

# 使用实际输出内容替换 {content_24h} 和 {content_2w} 后写入文件
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(HTML_TEMPLATE.format(
        date=date_str,
        signals_today="新信号数",   # 替换为实际值
        themes_count="主线数",       # 替换为实际值
        top_pick="最高分代码",       # 替换为实际值
        content_24h="[第一部分内容]",  # 替换为 Step 8 第一部分的 HTML
        content_2w="[第二部分内容]",   # 替换为 Step 8 第二部分的 HTML
    ))

subprocess.run(["open", output_path])
print(f"报告已保存：{output_path}")
```
