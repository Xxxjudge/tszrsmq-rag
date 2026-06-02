# serenity-ashare

追踪 Serenity（[@aleabitoreddit](https://x.com/aleabitoreddit)）最新观点，并自动映射到 A 股对标标的。

## 功能

- **WebSearch 拉取**：并行搜索 Serenity 最新帖子（近2周），无需 X API
- **真/伪趋势甄别**：区分产业逻辑驱动 vs 资金避险轮动
- **7层供应链拆解 + L1/L2/L3 分级**：重点挖掘 L3 隐蔽瓶颈
- **7因子打分**：不可替代性×2 + 估值合理性×1.5 的加权评分体系
- **证伪检查**：看多前主动搜索反驳证据
- **行情验证**：联动 `a-share-data` 查实时股价、30日涨跌、换手率、资金流向
- **结构化输出**：含趋势判断表、A股映射表、证伪记录、预判下一焦点、风控检查

## 来源与致谢

整合了以下社区 skill 的方法论：
- [siisee11/serenity-skill](https://github.com/siisee11/serenity-skill)：6步研究流程 + 证伪清单
- [w894781950-netizen/Serenity.skill](https://github.com/w894781950-netizen/Serenity.skill)：7因子打分 + L1/L2/L3 + 游资情绪
- [muxuuu/serenity-skill](https://github.com/muxuuu/serenity-skill)：7层供应链拆解 + 伪趋势识别

## 安装

```bash
mkdir -p ~/.claude/skills/serenity-ashare
cp SKILL.md ~/.claude/skills/serenity-ashare/SKILL.md
```

依赖：同一 skill 目录下需已安装 `a-share-data`。

## 使用

```
使用 serenity-ashare skill 分析 Serenity 最新观点并给出 A 股映射结论。
```

支持输出 HTML 报告（浏览器可直接打印为 PDF）：

```
用 serenity-ashare skill 分析，并生成 HTML 报告保存到桌面。
```

## 输出示例

```
## Serenity 最新动态（2026-06-02）

### 趋势判断
| 主题 | 判断 | 理由 |
| AI CPO | ✅ 真趋势 | 铜互连带宽极限，NVIDIA GB300催化 |

### 核心关注 → A股映射
| 海外标的 | 卡脖子环节 | L级 | A股对标 | 代码 | 7因子得分 | ... |
| $AXTI | InP衬底 | L2 | 云南锗业 | 002428 | 37.5 | ... |

### 预判下一焦点
光模块/GPU（L1）→ InP衬底（L2）→ **铟矿/MBE设备（L3，尚未定价）**
```

## 注意

本 skill 为研究辅助工具，不构成投资建议。
