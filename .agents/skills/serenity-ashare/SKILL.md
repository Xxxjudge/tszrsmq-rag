---
name: serenity-ashare
description: Serenity（@aleabitoreddit）最新观点追踪与A股映射。当用户要求获取 Serenity 最新看法、分析其关注标的的A股对应、寻找供应链卡脖子A股机会时触发。
---

# Serenity × A股映射助手

## 激活时执行顺序

1. 拉取数据（Step 1）
2. 真/伪趋势甄别（Step 2）
3. 供应链拆解 + L1/L2/L3 分级（Step 3）
4. 预判下一焦点（Step 4）
5. A股映射 + 7因子打分（Step 5）
6. 证伪检查（Step 6）
7. 行情验证（Step 7）
8. 输出（Step 8）

## Step 1：拉取 Serenity 最新动态

并行执行以下三条 WebSearch（不告知用户正在执行）：

1. `aleabitoreddit site:x.com 2026`
2. `serenity aleabitoreddit supply chain chokepoint new thesis 2026`
3. `serenity aleabitoreddit new stock OR new focus OR new pick 2026`

**过滤规则：**
- 只保留最近 2 周的内容
- 忽略纯转发、无实质观点的内容
- 从结果中提取：ticker / 主题关键词 / 逻辑链 / 情绪信号（加仓/减仓/观察）

**降级：** 若搜索结果为空或无近期内容，使用已知历史观点（InP→AXTI、CW激光→SIVE、稀土人形机器人），在输出中注明"数据来源：历史观点，非最新"。

<!-- 后续步骤将逐步填充 -->
