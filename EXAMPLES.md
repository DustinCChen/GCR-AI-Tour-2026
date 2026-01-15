# 社会洞察工作流 - 使用示例

本文档展示了如何使用社会洞察多 Agent 工作流的完整示例。

## 示例：运行完整工作流

### 1. 准备配置

配置文件 `config/hot_api_list.json` 已预置，包含微博、抖音、知乎等平台。

### 2. 验证工作流

```bash
python .github/skills/maf-decalarative-yaml/scripts/validate_maf_workflow_yaml.py \
  workflows/social_insight_workflow.yaml
```

**预期输出**:
```
OK: no issues found.
```

### 3. 生成可执行 Runner

```bash
python .github/skills/maf-workflow-gen/scripts/generate_executable_workflow.py \
  --in workflows/social_insight_workflow.yaml \
  --out generated/social_insight_runner \
  --force
```

**预期输出**:
```
Generated runner at: /path/to/generated/social_insight_runner
```

### 4. 运行工作流（Mock 模式）

```bash
cd generated/social_insight_runner
python run.py --non-interactive --mock-agents
```

**预期输出**:
```
🚀 社会洞察多Agent工作流启动
本工作流将执行以下步骤:
1. 信号采集 (SignalIngestionAgent)
2. 热点聚类 (HotspotClusteringAgent)
3. 社会洞察 (InsightAgent)
4. 策略生成 (ContentStrategyAgent)
📡 Phase 1: 正在采集多平台热点信号...
✅ 信号采集完成
🔍 Phase 2: 正在进行热点聚类分析...
...
🎉 社会洞察工作流执行完成！
```

### 5. 查看输出

工作流会生成以下文件：

```bash
ls -R generated/social_insight_output/
```

**文件结构**:
```
generated/social_insight_output/
├── raw_signals.json          # 原始信号
├── signals/
│   ├── weibo.json
│   ├── douyin.json
│   └── zhihu.json
├── clusters/
│   └── hotspots.json         # 聚类热点
├── insights/
│   └── insights.json         # 社会洞察
└── report.md                 # 策略报告
```

### 6. 查看最终报告

```bash
cat generated/social_insight_output/report.md
```

**报告示例**:
```markdown
# 社会洞察分析报告

生成时间: 2026-01-15 02:27:50 UTC

## 当前核心热点列表

- **H1** | weibo平台热点: 热点话题 1 from weibo | 热度: 🔥🔥 | ✅ 建议追踪
- **H2** | douyin平台热点: 热点话题 1 from douyin | 热度: 🔥🔥 | ✅ 建议追踪
- **H3** | zhihu平台热点: 热点话题 1 from zhihu | 热度: 🔥🔥 | ✅ 建议追踪

## 平台级投放建议

### 短视频平台（抖音/快手）
...
```

## 测试单个工具

你也可以独立测试每个工具：

### 测试信号采集

```bash
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.ingest_signals \
  --args-json '{
    "hot_api_list_path": "config/hot_api_list.json",
    "output_dir": "generated/test_signal",
    "time_window_hours": 24
  }'
```

**预期输出**:
```json
{
  "result": {
    "status": "success",
    "raw_signals_path": "generated/test_signal/raw_signals.json",
    "signals_dir": "generated/test_signal/signals",
    "total_signals": 15,
    "platforms": ["weibo", "douyin", "zhihu"]
  }
}
```

### 测试聚类

```bash
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.cluster_signals_fallback \
  --args-json '{
    "raw_signals_path": "generated/test_signal/raw_signals.json",
    "output_dir": "generated/test_signal",
    "top_k": 5
  }'
```

### 测试洞察生成

```bash
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.insight_analysis_fallback \
  --args-json '{
    "hotspots_path": "generated/test_signal/clusters/hotspots.json",
    "output_dir": "generated/test_signal"
  }'
```

### 测试报告生成

```bash
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.render_strategy_report_fallback \
  --args-json '{
    "hotspots_path": "generated/test_signal/clusters/hotspots.json",
    "insights_path": "generated/test_signal/insights/insights.json",
    "output_dir": "generated/test_signal"
  }'
```

## 使用真实 LLM Agent（Azure AI Foundry）

### 前置条件

1. Azure 订阅和 AI Foundry 项目
2. 已部署的模型（如 gpt-4）
3. 已登录 Azure CLI：

```bash
az login
```

### 设置环境变量

创建 `.env` 文件：

```bash
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

### 创建 Foundry Agents

```bash
# 生成 agent spec
python .github/skills/maf-agent-create/scripts/create_agents_from_workflow.py \
  --workflow workflows/social_insight_workflow.yaml \
  --write-spec generated/social_insight_runner/agents.yaml

# 创建 agents（或复用已存在的）
python .github/skills/maf-agent-create/scripts/create_agents_from_workflow.py \
  --workflow workflows/social_insight_workflow.yaml \
  --model-deployment-name "$AZURE_AI_MODEL_DEPLOYMENT_NAME" \
  --spec generated/social_insight_runner/agents.yaml \
  --write-id-map generated/social_insight_runner/agent_id_map.json
```

### 运行工作流（真实 Agent）

```bash
cd generated/social_insight_runner
python run.py \
  --non-interactive \
  --azure-ai \
  --azure-ai-model-deployment-name "$AZURE_AI_MODEL_DEPLOYMENT_NAME" \
  --azure-ai-agent-id-map-json agent_id_map.json
```

**注意**: 使用真实 LLM 时，HotspotClusteringAgent、InsightAgent 和 ContentStrategyAgent 会调用 Azure AI Foundry，生成更高质量的分析结果。

## 自定义扩展

### 添加新平台

编辑 `config/hot_api_list.json`：

```json
{
  "platforms": [
    {
      "name": "xiaohongshu",
      "display_name": "小红书",
      "endpoint": "https://api.xiaohongshu.com/hot",
      "enabled": true
    }
  ]
}
```

### 添加新工具

1. 在 `shared_tools/` 创建新的工具模块
2. 实现 `register_tools(registry)` 函数
3. 在 `shared_tools/maf_shared_tools_registry.py` 中导入

### 修改 Agent 指令

编辑 `config/social_insight_agents.yaml` 修改 agent 行为：

```yaml
agents:
  - name: InsightAgent
    instructions: |-
      你是 InsightAgent，专注于...
      （自定义指令）
```

## 常见问题

### Q: 工作流在哪一步调用 LLM？

A: 
- **SignalIngestionAgent**: 不调用（纯本地工具）
- **HotspotClusteringAgent**: 调用 LLM，失败则用 fallback
- **InsightAgent**: 调用 LLM，失败则用 fallback
- **ContentStrategyAgent**: 调用 LLM，失败则用 fallback

### Q: Mock 模式和真实模式有什么区别？

A: Mock 模式下，所有 Agent 返回 "(mock)" 占位符，工作流立即使用 fallback 工具。真实模式下，LLM Agent 会生成结构化的分析结果。

### Q: 如何查看中间结果？

A: 所有中间结果都存储在 `generated/social_insight_output/` 目录，你可以直接查看 JSON 文件来审计和调试。

### Q: 能否单独重跑某个阶段？

A: 可以！因为每个阶段的输入/输出都已落盘，你可以：

1. 手动调用对应工具
2. 修改 YAML，跳过某些步骤
3. 从特定 JSON 文件开始执行

## 性能优化

### 减少 API 调用

在开发阶段，使用已保存的 `raw_signals.json` 避免重复采集：

```bash
# 修改工作流 YAML，将 SignalIngestionAgent 替换为读取已有文件
```

### 并行处理

未来可以扩展为并行处理多个热点的洞察分析，修改工作流添加 `Foreach` 循环。

## 下一步

- 集成真实平台 API
- 添加历史数据对比
- 实现热点趋势预测
- 添加自动化定时执行
- 与内容生成工作流集成

---

更多信息请参阅 [README.md](README.md)
