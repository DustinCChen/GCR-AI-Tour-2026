# 端到端测试和 Azure 认证 - 完整解决方案

本文档回答问题："执行一次端到端测试。如何提供 azure ai credentials？"

## 问题 1: 执行一次端到端测试

### 快速答案

运行以下命令即可完成端到端测试：

```bash
./scripts/test_e2e.sh mock
```

### 详细说明

我们提供了两个自动化测试脚本：

#### 方案 A: Bash 脚本（推荐）

```bash
# Mock 模式（无需 Azure，使用本地工具）
./scripts/test_e2e.sh mock

# Azure AI 模式（需要认证）
./scripts/test_e2e.sh azure
```

#### 方案 B: Python 脚本

```bash
# Mock 模式
python scripts/test_e2e.py --mode mock

# Azure AI 模式（带详细输出）
python scripts/test_e2e.py --mode azure --verbose
```

### 测试内容

两个脚本都会执行以下 8 个步骤：

1. ✅ **验证 Python 环境** - 确保 Python 3.8+ 可用
2. ✅ **检查必需文件** - 验证配置、工作流、工具文件存在
3. ✅ **验证工作流 YAML** - 检查语法正确性
4. ✅ **测试工具注册表** - 确认 4 个共享工具可用
5. ✅ **生成可执行 runner** - 从 YAML 生成 Python 执行器
6. ✅ **检查 Azure 认证** - 仅 azure 模式，验证凭证
7. ✅ **运行完整工作流** - 执行 4 阶段分析流程
8. ✅ **验证所有输出** - 检查生成的 4 个文件

### 测试输出

成功后会看到：

```
========================================
✓ E2E Test PASSED
========================================

Output directory: generated/social_insight_output

View the final report:
  cat generated/social_insight_output/report.md
```

生成的文件：
- `raw_signals.json` - 15 个模拟信号
- `clusters/hotspots.json` - 3 个聚类热点
- `insights/insights.json` - 3 个社会洞察
- `report.md` - 最终策略报告

### 查看结果

```bash
# 查看完整报告
cat generated/social_insight_output/report.md

# 查看热点数据
cat generated/social_insight_output/clusters/hotspots.json | jq .

# 查看洞察分析
cat generated/social_insight_output/insights/insights.json | jq .
```

---

## 问题 2: 如何提供 Azure AI Credentials

### 快速答案

**生产环境（Azure 部署）**: 使用 Managed Identity（推荐）

```bash
# 1. 启用 Managed Identity
az vm identity assign --name "your-vm" --resource-group "your-rg"

# 2. 授予权限
az role assignment create \
    --assignee <managed-identity-principal-id> \
    --role "Cognitive Services User" \
    --scope /subscriptions/{sub}/resourceGroups/{rg}

# 3. 设置环境变量
export AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
export AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 4. 运行（无需 az login）
./scripts/test_e2e.sh azure
```

**本地开发**: 使用 Azure CLI（最简单）

```bash
# 1. 登录 Azure
az login

# 2. 创建 .env 文件
cp .env.example .env

# 3. 编辑 .env，填入以下两个必需值：
# AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
# AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 4. 运行测试
./scripts/test_e2e.sh azure
```

### 详细说明

我们支持 **4 种认证方法**，适用于不同场景：

#### 方法 1: Managed Identity（推荐生产环境）

**优点**: 
- ✅ 最安全（不需要管理密钥）
- ✅ 自动检测和使用
- ✅ 零配置（在 Azure 环境中）
- ✅ 符合企业安全标准

**适用于**: Azure VM、Container Instances、App Service、AKS、Azure Functions

**步骤**:

1. **启用 Managed Identity**

```bash
# Azure VM (系统分配)
az vm identity assign \
    --name "your-vm-name" \
    --resource-group "your-resource-group"

# Azure Container Instances
az container create \
    --name "social-insight-container" \
    --resource-group "your-resource-group" \
    --image "your-image" \
    --assign-identity

# Azure App Service
az webapp identity assign \
    --name "your-app-name" \
    --resource-group "your-resource-group"
```

2. **授予权限**

```bash
# 获取 Principal ID
PRINCIPAL_ID=$(az vm show --name "your-vm" --resource-group "your-rg" --query identity.principalId -o tsv)

# 授予 Cognitive Services User 角色
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Cognitive Services User" \
    --scope "/subscriptions/{sub-id}/resourceGroups/{rg}"
```

3. **配置环境变量**

只需设置端点和模型名称（不需要密钥）：

```bash
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 可选：强制使用 Managed Identity
USE_MANAGED_IDENTITY=true

# 可选：用户分配的 Managed Identity
AZURE_CLIENT_ID=your-user-assigned-identity-client-id
```

4. **运行测试**

```bash
./scripts/test_e2e.sh azure
```

**自动检测**: 代码会自动检测 Azure 环境并使用 Managed Identity，无需额外配置。

#### 方法 2: Azure CLI（推荐本地开发）

**优点**: 
- ✅ 最安全（不需要管理密钥）
- ✅ 支持 MFA
- ✅ 自动令牌刷新

**步骤**:

1. **安装 Azure CLI**

```bash
# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# 下载安装: https://aka.ms/installazurecliwindows
```

2. **登录**

```bash
az login

# 或使用设备代码（远程服务器）
az login --use-device-code
```

3. **配置环境变量**

创建 `.env` 文件：

```bash
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

4. **运行测试**

```bash
./scripts/test_e2e.sh azure
```

#### 方法 2: 环境变量（推荐用于 CI/CD）

**优点**:
- ✅ 适用于自动化
- ✅ 无需交互式登录

**步骤**:

1. **创建 Service Principal**

```bash
az ad sp create-for-rbac --name "social-insight-workflow" \
    --role "Cognitive Services User" \
    --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group}
```

2. **配置完整环境变量**

在 `.env` 中添加：

```bash
# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# Service Principal 认证
AZURE_CLIENT_ID=<appId>
AZURE_CLIENT_SECRET=<password>
AZURE_TENANT_ID=<tenant>
```

或者使用 Azure OpenAI 直接连接：

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

#### 方法 3: Azure Key Vault（推荐用于生产）

**优点**:
- ✅ 最高安全性
- ✅ 集中管理
- ✅ 审计日志

**步骤**:

1. **创建 Key Vault**

```bash
az keyvault create \
    --name "social-insight-kv" \
    --resource-group "your-rg" \
    --location "eastus"
```

2. **存储密钥**

```bash
az keyvault secret set \
    --vault-name "social-insight-kv" \
    --name "AzureAIProjectEndpoint" \
    --value "https://your-project.api.azureml.ms"

az keyvault secret set \
    --vault-name "social-insight-kv" \
    --name "AzureAIModelDeploymentName" \
    --value "gpt-4"
```

3. **在代码中加载**（需要额外实现）

### 获取所需信息

#### 如何获取 AZURE_AI_PROJECT_ENDPOINT

1. 访问 [Azure AI Foundry Portal](https://ai.azure.com)
2. 选择你的项目
3. 进入 **Settings** → **Project details**
4. 复制 **Project connection string**（格式：`https://xxx.api.azureml.ms`）

#### 如何获取 AZURE_AI_MODEL_DEPLOYMENT_NAME

1. 在 Azure AI Foundry Portal
2. 进入 **Deployments**
3. 查看已部署的模型名称（如 `gpt-4`, `gpt-35-turbo`）
4. 使用该名称作为环境变量值

### 验证配置

运行以下命令验证配置正确：

```bash
# 检查 Azure 登录状态
az account show

# 检查环境变量
cat .env | grep AZURE_AI

# 测试连接（运行 E2E 测试）
./scripts/test_e2e.sh azure
```

---

## 常见问题

### Q1: 首次运行应该用哪个模式？

**A**: 使用 **mock 模式**

```bash
./scripts/test_e2e.sh mock
```

这样可以快速验证工作流逻辑，无需配置 Azure。

### Q2: Mock 模式和 Azure 模式有什么区别？

| 特性 | Mock 模式 | Azure 模式 |
|------|----------|-----------|
| LLM 调用 | ❌ 不调用 | ✅ 调用 Azure AI |
| 输出质量 | 模板生成 | AI 智能分析 |
| 速度 | 快（10-30秒） | 慢（2-5分钟） |
| 成本 | 免费 | 消耗 tokens |
| 认证要求 | 无 | 需要 Azure 凭证 |

### Q3: 测试失败怎么办？

**步骤化排查**:

```bash
# 1. 检查 Python
python3 --version  # 需要 3.8+

# 2. 重新运行测试并查看详细输出
python scripts/test_e2e.py --mode mock --verbose

# 3. 检查单个组件
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py --tool __list__

# 4. 验证 YAML
python .github/skills/maf-decalarative-yaml/scripts/validate_maf_workflow_yaml.py \
  workflows/social_insight_workflow.yaml
```

### Q4: Azure 认证失败？

**常见原因和解决方案**:

```bash
# 原因 1: 未登录
az login

# 原因 2: 环境变量未设置
cat .env
# 确保包含 AZURE_AI_PROJECT_ENDPOINT 和 AZURE_AI_MODEL_DEPLOYMENT_NAME

# 原因 3: 权限不足
az role assignment create \
    --role "Cognitive Services User" \
    --assignee "your-email@company.com" \
    --scope "/subscriptions/{sub}/resourceGroups/{rg}"

# 原因 4: 令牌过期
az logout
az login
```

### Q5: 如何在 CI/CD 中使用？

**GitHub Actions 示例**:

```yaml
name: E2E Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Run Mock Test
        run: python scripts/test_e2e.py --mode mock
      
      # 可选：Azure 测试
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Run Azure Test
        env:
          AZURE_AI_PROJECT_ENDPOINT: ${{ secrets.AZURE_AI_PROJECT_ENDPOINT }}
          AZURE_AI_MODEL_DEPLOYMENT_NAME: ${{ secrets.AZURE_AI_MODEL_DEPLOYMENT_NAME }}
        run: python scripts/test_e2e.py --mode azure
```

---

## 文档索引

完整文档请参阅：

- **[TESTING.md](TESTING.md)** - 测试快速参考
- **[AZURE_CREDENTIALS.md](AZURE_CREDENTIALS.md)** - Azure 认证完整指南（包含 3 种方法详细说明）
- **[README.md](README.md)** - 项目架构和快速开始
- **[EXAMPLES.md](EXAMPLES.md)** - 详细使用示例

---

## 总结

### 端到端测试 ✅

```bash
# 最简单的方式
./scripts/test_e2e.sh mock
```

### Azure 认证 ✅

```bash
# 最推荐的方式（本地开发）
az login
cp .env.example .env
# 编辑 .env 填入 endpoint 和 model name
./scripts/test_e2e.sh azure
```

所有必需的脚本和文档都已准备就绪，开箱即用！
