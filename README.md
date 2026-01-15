# Social Insight Multi-Agent Workflow

**一句话概述**: 将「多平台热点信号」→「可追踪的核心热点」→「结构化社会洞察」→「平台级内容投放决策建议」

这是一个基于 Microsoft Agent Framework (MAF) 的**分析型 Agent 工作流（Analysis → Insight → Decision）**，而不是生成型内容工厂。

## 核心设计原则

1. **Agent 只负责"认知决策"，不负责 IO**
2. **所有关键中间结果必须结构化并落盘**
3. **每一步都允许 LLM 失败 → 本地工具兜底**
4. **最终输出是"建议报告"，而不是内容成品**

## 工作流架构

```
[多平台 APIs]
    ↓
SignalIngestionAgent (LocalToolExecutorAgent - 确定性工具)
    ↓ raw_signals.json
HotspotClusteringAgent (LLM-first + Tool-fallback)
    ↓ hotspots.json
InsightAgent (高认知密度 LLM)
    ↓ insights.json
ContentStrategyAgent (决策转译 Agent)
    ↓ report.md
```

### Agent 角色

#### 0️⃣ Orchestrator（隐式 / Workflow 层）

通过 YAML 工作流定义执行顺序，注入上下文，决定是否中断或继续 fallback。

#### 1️⃣ SignalIngestionAgent（LocalToolExecutorAgent）

- **类型**: 确定性工具，不调用模型
- **职责**: 把"外部世界的热度噪声"转成**可回放的原始信号集**
- **输入**: `hot_api_list.json` + 时间窗口
- **输出**: `raw_signals.json`, `signals/*.json`

#### 2️⃣ HotspotClusteringAgent

- **类型**: LLM-first + Tool-fallback
- **职责**: 判断「哪些信号其实在说同一件事」（主题判别 + 热度合并）
- **输入**: `raw_signals.json`
- **输出**: `hotspots.json`

#### 3️⃣ InsightAgent

- **类型**: 高认知密度 LLM Agent
- **职责**: 回答「这件事为什么在此刻、以这种方式火了」
- **输入**: `hotspots.json`
- **输出**: `insights.json`

#### 4️⃣ ContentStrategyAgent

- **类型**: 决策转译 Agent
- **职责**: 把洞察翻译成「不同平台该不该追、怎么追、追到什么程度」
- **输入**: `hotspots.json` + `insights.json`
- **输出**: `report.md`

## 快速开始

### 端到端测试（推荐先运行）

最快的方式是运行自动化测试脚本：

```bash
# Mock 模式（无需 Azure 认证，使用本地工具）
./scripts/test_e2e.sh mock

# 或使用 Python 版本
python scripts/test_e2e.py --mode mock
```

测试会自动执行所有步骤并验证输出。详见 [测试指南](#测试和验证)。

### 前置要求

```bash
# 安装 Python 3.8+
python3 --version

# 安装 Microsoft Agent Framework
pip install agent-framework

# （可选）Azure AI Foundry 认证
az login
```

### Azure 认证配置

本项目支持多种认证方式，**推荐在 Azure 环境中使用 Managed Identity**。详细配置指南请参阅：

📖 **[Azure 认证配置指南](AZURE_CREDENTIALS.md)**

#### 快速配置（Managed Identity - 推荐生产环境）

在 Azure VM、Container、App Service 等环境中，Managed Identity 会自动检测和使用：

```bash
# 1. 在 Azure 资源上启用 Managed Identity
az vm identity assign --name "your-vm" --resource-group "your-rg"

# 2. 授予权限
az role assignment create \
    --assignee <managed-identity-principal-id> \
    --role "Cognitive Services User" \
    --scope /subscriptions/{sub-id}/resourceGroups/{rg}

# 3. 设置环境变量（仅需端点和模型）
export AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
export AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 4. 运行 - 无需 az login！
./scripts/test_e2e.sh azure
```

#### 快速配置（Azure CLI - 本地开发）

```bash
# 1. Azure CLI 登录
az login

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 Azure 信息
# AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
# AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 3. 运行测试
./scripts/test_e2e.sh azure
```

**认证优先级**:
1. **Managed Identity** (在 Azure 环境中自动使用)
2. Azure CLI credentials (`az login`)
3. 环境变量 (Service Principal)
4. Azure Key Vault (企业场景)

### 步骤 1: 配置热点 API

编辑 `config/hot_api_list.json` 配置你的平台 API：

```json
{
  "platforms": [
    {
      "name": "weibo",
      "endpoint": "https://api.weibo.com/hot/trending",
      "enabled": true
    }
  ]
}
```

### 步骤 2: 验证工作流 YAML

```bash
python .github/skills/maf-decalarative-yaml/scripts/validate_maf_workflow_yaml.py \
  workflows/social_insight_workflow.yaml
```

### 步骤 3: 生成可执行 Runner

```bash
python .github/skills/maf-workflow-gen/scripts/generate_executable_workflow.py \
  --in workflows/social_insight_workflow.yaml \
  --out generated/social_insight_runner \
  --force
```

### 步骤 4: 创建 Azure AI Foundry Agents（可选）

如果要使用真实的 LLM Agent 而非 mock：

```bash
# 生成 agent spec
python .github/skills/maf-agent-create/scripts/create_agents_from_workflow.py \
  --workflow workflows/social_insight_workflow.yaml \
  --write-spec generated/social_insight_runner/agents.yaml

# 创建/复用 Foundry agents
python .github/skills/maf-agent-create/scripts/create_agents_from_workflow.py \
  --workflow workflows/social_insight_workflow.yaml \
  --model-deployment-name "$AZURE_AI_MODEL_DEPLOYMENT_NAME" \
  --spec generated/social_insight_runner/agents.yaml \
  --write-id-map generated/social_insight_runner/agent_id_map.json
```

### 步骤 5: 运行工作流

#### 选项 A: Mock 模式（快速验证）

```bash
cd generated/social_insight_runner
python run.py --non-interactive --mock-agents
```

#### 选项 B: Azure AI Foundry 真实调用

```bash
cd generated/social_insight_runner
python run.py \
  --non-interactive \
  --azure-ai \
  --azure-ai-model-deployment-name "$AZURE_AI_MODEL_DEPLOYMENT_NAME" \
  --azure-ai-agent-id-map-json agent_id_map.json
```

## 输出文件结构

```
generated/social_insight_output/
├── raw_signals.json          # 原始信号数据
├── signals/                  # 各平台信号
│   ├── weibo.json
│   ├── douyin.json
│   └── zhihu.json
├── clusters/
│   └── hotspots.json         # 聚类后的热点
├── insights/
│   └── insights.json         # 社会洞察分析
└── report.md                 # 最终策略报告
```

## 数据契约

### RawSignal（原始信号）

```json
{
  "signal_id": "weibo_1",
  "platform": "weibo",
  "rank": 3,
  "title": "关键词",
  "metrics": { "views": 123456 },
  "url": "...",
  "fetched_at": "ISO8601"
}
```

### Hotspot（热点）

```json
{
  "hotspot_id": "H1",
  "title": "一句话概括",
  "summary": "发生了什么",
  "signals": ["signal_id_1", "signal_id_7"],
  "platforms": ["weibo", "douyin"],
  "heat_score": 0.87,
  "should_chase": true
}
```

### Insight（洞察）

```json
{
  "hotspot_id": "H1",
  "why_now": "触发机制 / 社会背景",
  "core_audience": ["群体A", "群体B"],
  "emotion_structure": {
    "dominant": "愤怒",
    "secondary": ["焦虑", "戏谑"]
  },
  "content_nature": ["冲突型", "身份认同"],
  "risk_notes": ["争议风险", "平台审核点"]
}
```

## 测试和验证

### 自动化端到端测试

项目提供了完整的端到端测试脚本：

#### Bash 版本

```bash
# Mock 模式（推荐首次运行）
./scripts/test_e2e.sh mock

# Azure AI 模式（需要认证）
./scripts/test_e2e.sh azure
```

#### Python 版本

```bash
# Mock 模式
python scripts/test_e2e.py --mode mock

# Azure AI 模式（带详细输出）
python scripts/test_e2e.py --mode azure --verbose
```

测试脚本会自动：
1. ✅ 验证 Python 环境
2. ✅ 检查必需文件
3. ✅ 验证工作流 YAML
4. ✅ 测试工具注册表
5. ✅ 生成可执行 runner
6. ✅ 检查 Azure 认证（azure 模式）
7. ✅ 运行完整工作流
8. ✅ 验证所有输出文件

### 测试场景

#### Mock 模式
- **用途**: 快速验证工作流逻辑
- **特点**: 不调用 LLM，使用确定性 fallback 工具
- **速度**: 快（约 10-30 秒）
- **成本**: 免费

#### Azure AI 模式
- **用途**: 测试真实 LLM 集成
- **特点**: 调用 Azure AI Foundry agents
- **速度**: 较慢（约 2-5 分钟）
- **成本**: 消耗 Azure tokens

### 查看测试结果

测试成功后，查看生成的报告：

```bash
# 查看完整报告
cat generated/social_insight_output/report.md

# 查看热点聚类
cat generated/social_insight_output/clusters/hotspots.json

# 查看社会洞察
cat generated/social_insight_output/insights/insights.json
```

## 本地工具测试

测试共享工具注册表：

```bash
# 列出所有工具
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py --tool __list__

# 测试信号采集
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.ingest_signals \
  --args-json '{"hot_api_list_path":"config/hot_api_list.json","output_dir":"generated/test","time_window_hours":24}'

# 测试聚类兜底
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.cluster_signals_fallback \
  --args-json '{"raw_signals_path":"generated/test/raw_signals.json","output_dir":"generated/test","top_k":5}'
```

## 扩展性

这个设计是**通用型**的，稍作替换即可应用于其他场景：

| 场景     | signals | hotspots | insights  | strategy |
|--------|---------|----------|-----------|----------|
| 社交洞察   | 热点信号    | 核心热点     | 社会洞察      | 内容策略     |
| 投资研究   | 新闻/财报   | 核心事件     | 成因/风险     | 投资建议     |
| 舆情监测   | 舆论      | 舆情主题     | 情绪/人群     | 公关策略     |
| 技术趋势分析 | GitHub  | 技术方向     | 成熟度/人群    | 研发决策     |

**Agent 角色不变，只换工具和 prompt。**

## 设计说明

### 关于 Fallback 执行策略

当前实现中，每个 LLM Agent 步骤都会**无条件执行 fallback 工具**。这是为了：

1. **演示目的**: 确保 mock 模式下能生成完整输出
2. **鲁棒性**: 保证即使 LLM 失败也有有效输出
3. **可预测性**: 统一的执行路径便于调试和测试

**生产环境优化建议**:
- 在工作流 YAML 中添加 `ConditionGroup` 判断 LLM 输出有效性
- 仅在 LLM 失败或输出无效时才调用 fallback
- 可以通过检查输出的 JSON 结构或特定字段来判断成功与否

### 关于中文内容

本工作流专门针对中国社交平台（微博、抖音、知乎等）设计，因此：
- 工作流消息、报告内容使用中文
- 数据契约字段名使用英文（便于编程处理）
- Agent 指令混合中英文（英文结构定义，中文任务说明）

如需国际化版本，建议：
- 提取所有文本到配置文件
- 使用模板系统支持多语言
- Agent 指令完全使用英文

## 故障排查

### YAML 无法加载

- 检查缩进（使用空格，不用 Tab）
- 确保根节点是 `kind: Workflow`
- 确保有 `trigger.actions`

### Runner 在 --non-interactive 模式下失败

- 确保通过 `--set` 提供了所有必需的 `Question` 变量

### Foundry 错误 (401/403)

- 运行 `az login`
- 检查 RBAC 权限
- 验证 `AZURE_AI_MODEL_DEPLOYMENT_NAME` 和 `AZURE_AI_PROJECT_ENDPOINT`
- 详见 [Azure 认证配置指南](AZURE_CREDENTIALS.md)

### 工具未找到

- 检查 `shared_tools/maf_shared_tools_registry.py` 是否正确加载
- 运行 `python shared_tools/maf_shared_tools_registry.py` 查看已注册工具

### 端到端测试失败

- 运行 `./scripts/test_e2e.sh mock` 查看详细错误
- 检查所有必需文件是否存在
- 确保 Python 3.8+ 已安装

## 文档索引

- **[README.md](README.md)** - 本文档：架构说明、快速开始
- **[EXAMPLES.md](EXAMPLES.md)** - 详细使用示例和测试步骤
- **[AZURE_CREDENTIALS.md](AZURE_CREDENTIALS.md)** - Azure 认证配置完整指南
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - 技术实现细节

## 许可证

本项目遵循 MIT 许可证。

## 参考资料

- [Microsoft Agent Framework 文档](https://learn.microsoft.com/agent-framework/overview/agent-framework-overview)
- [Microsoft Agent Framework Python](https://github.com/microsoft/agent-framework/tree/main/python)
- [MAF Python 示例](https://github.com/microsoft/agent-framework/tree/main/python/samples)
- [Azure AI Foundry Portal](https://ai.azure.com)
- [Azure CLI 文档](https://docs.microsoft.com/cli/azure/)
