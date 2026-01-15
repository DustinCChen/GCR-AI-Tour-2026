# 社会洞察多 Agent 工作流 - 实现总结

## 项目概述

本项目实现了一个基于 Microsoft Agent Framework (Python) 的**社会洞察多 Agent 工作流**，将多平台社交媒体热点信号转化为结构化的内容策略建议。

### 核心价值主张

> **「多平台热点信号」→「可追踪的核心热点」→「结构化社会洞察」→「平台级内容投放决策建议」**

这是一个**分析型 Agent 工作流（Analysis → Insight → Decision）**，而不是生成型内容工厂。

## 实现架构

### 工作流结构

```
[多平台 APIs]
    ↓ (LocalToolExecutorAgent)
SignalIngestionAgent: 信号采集
    ↓ raw_signals.json
HotspotClusteringAgent: 热点聚类 (LLM + fallback)
    ↓ hotspots.json
InsightAgent: 社会洞察 (LLM + fallback)
    ↓ insights.json
ContentStrategyAgent: 策略生成 (LLM + fallback)
    ↓ report.md
```

### 核心设计原则

1. ✅ **Agent 只负责认知决策，不负责 IO**
   - 所有 I/O 操作由 LocalToolExecutorAgent 通过确定性工具执行
   - LLM Agent 专注于分析、判断、决策

2. ✅ **所有关键中间结果必须结构化并落盘**
   - raw_signals.json (原始信号)
   - hotspots.json (聚类热点)
   - insights.json (社会洞察)
   - report.md (策略报告)

3. ✅ **每一步都允许 LLM 失败 → 本地工具兜底**
   - 聚类失败 → cluster_signals_fallback
   - 洞察失败 → insight_analysis_fallback
   - 报告失败 → render_strategy_report_fallback

4. ✅ **最终输出是建议报告，而不是内容成品**
   - 提供策略指导，不是直接可发布的内容
   - 支持人工审核和调整

## 技术实现

### 文件结构

```
gcr-ai-tour/
├── workflows/
│   └── social_insight_workflow.yaml    # 工作流定义 (35 个 action)
├── shared_tools/
│   ├── social_signal_tools.py          # 4 个确定性工具
│   └── maf_shared_tools_registry.py    # 工具注册表
├── config/
│   ├── hot_api_list.json               # 平台 API 配置
│   └── social_insight_agents.yaml      # Agent 规格说明
├── generated/
│   ├── social_insight_runner/          # 生成的可执行 runner
│   └── social_insight_output/          # 工作流输出
├── README.md                           # 完整文档
├── EXAMPLES.md                         # 使用示例
└── .gitignore                          # 排除生成文件
```

### 工具清单

4 个注册工具：
1. `social.ingest_signals` - 信号采集
2. `social.cluster_signals_fallback` - 聚类兜底
3. `social.insight_analysis_fallback` - 洞察兜底
4. `social.render_strategy_report_fallback` - 报告兜底

### Agent 清单

4 个 Agent（定义于 `config/social_insight_agents.yaml`）：
1. `LocalToolExecutorAgent` - 工具执行器（确定性）
2. `HotspotClusteringAgent` - 热点聚类分析师（LLM）
3. `InsightAgent` - 社会洞察分析师（LLM）
4. `ContentStrategyAgent` - 内容策略顾问（LLM）

## 数据契约

### RawSignal（原始信号）
```json
{
  "signal_id": "weibo_1",
  "platform": "weibo",
  "rank": 3,
  "title": "关键词",
  "metrics": { "views": 123456, "engagements": 5000 },
  "url": "https://...",
  "fetched_at": "2026-01-15T02:27:50Z"
}
```

### Hotspot（热点）
```json
{
  "hotspot_id": "H1",
  "title": "一句话概括",
  "summary": "详细摘要",
  "signals": ["signal_id_1", "signal_id_2"],
  "platforms": ["weibo", "douyin"],
  "heat_score": 0.87,
  "should_chase": true
}
```

### Insight（洞察）
```json
{
  "hotspot_id": "H1",
  "why_now": "时机和触发因素",
  "core_audience": ["群体A", "群体B"],
  "emotion_structure": {
    "dominant": "主导情绪",
    "secondary": ["次要情绪1", "次要情绪2"]
  },
  "content_nature": ["内容类型1", "内容类型2"],
  "risk_notes": ["风险点1", "风险点2"]
}
```

### Report（策略报告 Markdown）
```markdown
# 社会洞察分析报告

## 当前核心热点列表
- H1 | 标题 | 热度 🔥🔥🔥 | ✅ 建议追踪

## 平台级投放建议

### 短视频平台
- 适配热点：H1
- 建议角度：...
- 风险提示：...

## 不建议追的热点说明
...
```

## 验证和测试

### ✅ 单元测试

所有工具独立测试通过：
```bash
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py --tool __list__
# 输出：4 个已注册工具

python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.ingest_signals --args-json '{...}'
# 输出：成功生成 raw_signals.json
```

### ✅ 工作流验证

YAML 结构验证通过：
```bash
python .github/skills/maf-decalarative-yaml/scripts/validate_maf_workflow_yaml.py \
  workflows/social_insight_workflow.yaml
# 输出：OK: no issues found.
```

### ✅ 端到端执行

Mock 模式完整执行：
```bash
cd generated/social_insight_runner
python run.py --non-interactive --mock-agents
# 输出：工作流成功完成，生成所有输出文件
```

验证输出：
- ✅ raw_signals.json (15 个信号)
- ✅ hotspots.json (3 个热点)
- ✅ insights.json (3 个洞察)
- ✅ report.md (完整策略报告)

## 扩展性和通用性

本架构设计是**领域无关**的，只需替换工具和 prompt 即可应用于：

| 应用场景   | signals | hotspots | insights  | strategy |
|--------|---------|----------|-----------|----------|
| 社交洞察   | 热点信号    | 核心热点     | 社会洞察      | 内容策略     |
| 投资研究   | 新闻/财报   | 核心事件     | 成因/风险分析   | 投资建议     |
| 舆情监测   | 舆论帖子    | 舆情主题     | 情绪/人群分析   | 公关策略     |
| 技术趋势   | GitHub  | 技术方向     | 成熟度/采用度分析 | 研发决策     |

**Agent 角色逻辑不变，只需调整：**
1. 信号源（API 配置）
2. 工具实现（数据处理逻辑）
3. Agent 指令（领域知识）

## 生产环境优化建议

### 1. 条件化 Fallback
当前实现为简化演示，无条件执行 fallback。生产环境建议：
- 添加 `ConditionGroup` 检查 LLM 输出有效性
- 仅在失败时调用 fallback
- 记录 fallback 使用率用于监控

### 2. 真实 API 集成
- 替换 mock 数据生成为真实平台 API 调用
- 实现错误重试和限流机制
- 添加 API 响应缓存

### 3. 性能优化
- 并行处理多个热点的洞察分析
- 使用异步 I/O 加速文件操作
- 实现增量更新机制

### 4. 监控和告警
- 记录每个阶段的执行时间
- 监控 LLM 成功率
- 设置数据质量告警

### 5. 安全性
- API 密钥使用 Azure Key Vault
- 敏感数据加密存储
- 实现访问控制和审计日志

## 技术栈

- **Framework**: Microsoft Agent Framework (Python)
- **LLM Provider**: Azure AI Foundry (支持 GPT-4 等)
- **Language**: Python 3.8+
- **Data Format**: JSON, YAML, Markdown
- **Authentication**: Azure CLI (DefaultAzureCredential)

## 文档资源

- **README.md**: 完整架构说明、快速开始、数据契约、故障排查
- **EXAMPLES.md**: 详细的使用示例和测试步骤
- **config/social_insight_agents.yaml**: Agent 角色定义和指令
- **workflows/social_insight_workflow.yaml**: 完整工作流定义

## 结论

本实现成功展示了如何使用 Microsoft Agent Framework 构建一个：
- ✅ **结构化** 的多 Agent 协作系统
- ✅ **鲁棒** 的 LLM + 工具混合架构
- ✅ **可追溯** 的分析决策流程
- ✅ **可扩展** 的领域无关设计

所有核心设计原则均已实现，工作流可在 mock 模式下完整运行，为接入真实 API 和 LLM 提供了坚实基础。

---

**实现日期**: 2026-01-15  
**Framework 版本**: Microsoft Agent Framework (Python)  
**总代码量**: 约 1000+ 行（包含工具、配置、文档）  
**验证状态**: ✅ 全部通过
