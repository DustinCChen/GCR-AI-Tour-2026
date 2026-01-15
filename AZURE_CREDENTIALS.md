# Azure AI 认证配置指南

本文档详细说明如何为 Social Insight Multi-Agent Workflow 配置 Azure AI 认证。

## 目录

- [认证方法概览](#认证方法概览)
- [方法 1: Managed Identity (推荐生产环境)](#方法-1-managed-identity-推荐生产环境)
- [方法 2: Azure CLI (推荐本地开发)](#方法-2-azure-cli-推荐本地开发)
- [方法 3: 环境变量](#方法-3-环境变量)
- [方法 4: Azure Key Vault](#方法-4-azure-key-vault)
- [获取所需信息](#获取所需信息)
- [故障排查](#故障排查)

## 认证方法概览

本项目支持四种 Azure 认证方法：

| 方法 | 适用场景 | 安全性 | 配置难度 |
|------|---------|--------|---------|
| **Managed Identity** | **Azure VM/容器/App Service** | **最高** | **低** |
| Azure CLI | 本地开发 | 高 | 低 |
| 环境变量 | CI/CD、容器 | 中 | 低 |
| Azure Key Vault | 生产环境密钥管理 | 高 | 中 |

> **⚠️ 重要**: 对于生产部署到 Azure，**强烈推荐使用 Managed Identity**。它提供最高安全性，无需管理密钥。

## 方法 1: Managed Identity (推荐生产环境)

**适用于**: Azure VM、Azure Container Instances、Azure App Service、Azure Kubernetes Service (AKS)、Azure Functions

Managed Identity 允许 Azure 资源自动获取 Azure AD 令牌，无需在代码中存储凭据。

### 优点

- ✅ **最安全** - 无需存储或管理密钥
- ✅ **自动轮换** - Azure 自动管理凭据生命周期
- ✅ **零配置** - 在 Azure 环境中自动检测和使用
- ✅ **审计友好** - 所有访问都通过 Azure AD 记录
- ✅ **符合合规要求** - 满足企业安全标准

### 类型

#### System-Assigned Managed Identity (系统分配)

自动创建并绑定到单个 Azure 资源。资源删除时自动删除。

#### User-Assigned Managed Identity (用户分配)

独立创建，可分配给多个 Azure 资源。资源删除后仍然存在。

### 步骤 1: 启用 Managed Identity

#### Azure VM

```bash
# 启用系统分配的托管标识
az vm identity assign \
    --name "your-vm-name" \
    --resource-group "your-resource-group"

# 或创建并分配用户分配的托管标识
az identity create \
    --name "social-insight-identity" \
    --resource-group "your-resource-group"

az vm identity assign \
    --name "your-vm-name" \
    --resource-group "your-resource-group" \
    --identities "/subscriptions/{sub}/resourcegroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/social-insight-identity"
```

#### Azure Container Instances

```bash
# 系统分配
az container create \
    --name "social-insight-container" \
    --resource-group "your-resource-group" \
    --image "your-image" \
    --assign-identity

# 用户分配
az container create \
    --name "social-insight-container" \
    --resource-group "your-resource-group" \
    --image "your-image" \
    --assign-identity "/subscriptions/{sub}/resourcegroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/social-insight-identity"
```

#### Azure App Service

```bash
# 系统分配
az webapp identity assign \
    --name "your-app-name" \
    --resource-group "your-resource-group"

# 用户分配
az webapp identity assign \
    --name "your-app-name" \
    --resource-group "your-resource-group" \
    --identities "/subscriptions/{sub}/resourcegroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/social-insight-identity"
```

### 步骤 2: 授予权限

Managed Identity 需要访问 Azure AI Foundry 的权限：

```bash
# 获取托管标识的 Principal ID
# 对于系统分配的标识:
PRINCIPAL_ID=$(az vm show --name "your-vm-name" --resource-group "your-resource-group" --query identity.principalId -o tsv)

# 对于用户分配的标识:
PRINCIPAL_ID=$(az identity show --name "social-insight-identity" --resource-group "your-resource-group" --query principalId -o tsv)

# 授予 Cognitive Services User 角色
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Cognitive Services User" \
    --scope "/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.CognitiveServices/accounts/{ai-foundry-resource}"

# 或授予更广泛的访问权限（整个资源组）
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Cognitive Services User" \
    --scope "/subscriptions/{subscription-id}/resourceGroups/{resource-group}"
```

### 步骤 3: 配置应用

在 Azure 资源中设置环境变量：

```bash
# 必需：Azure AI Foundry 端点
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms

# 必需：模型部署名称
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 可选：强制使用托管标识（通常自动检测）
USE_MANAGED_IDENTITY=true

# 可选：用户分配的托管标识的 Client ID
AZURE_CLIENT_ID=your-user-assigned-identity-client-id
```

### 步骤 4: 部署和测试

1. 部署应用到 Azure 资源
2. 应用会自动使用 Managed Identity 进行身份验证
3. 无需 `az login` 或存储密钥

```bash
# 在 Azure VM 中运行测试
./scripts/test_e2e.sh azure
```

### 验证 Managed Identity

检查 Managed Identity 是否正常工作：

```bash
# 在 Azure 资源中运行此命令
curl -H "Metadata:true" "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://cognitiveservices.azure.com/"
```

如果返回访问令牌，说明 Managed Identity 配置正确。

### 故障排查

**问题**: "ManagedIdentityCredential authentication failed"

**解决方案**:
1. 确认已启用 Managed Identity
2. 验证权限分配正确
3. 检查 Azure 资源是否在正确的订阅/资源组中

## 方法 2: Azure CLI (推荐本地开发)

**适用于**: 本地开发和测试

### 步骤 1: 安装 Azure CLI

#### macOS
```bash
brew update && brew install azure-cli
```

#### Linux
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

#### Windows
下载并安装: https://aka.ms/installazurecliwindows

### 步骤 2: 登录 Azure

```bash
az login
```

这会打开浏览器窗口，完成登录后自动返回。

**或者**使用设备代码登录（适用于远程服务器）：

```bash
az login --use-device-code
```

### 步骤 3: 选择订阅（如果有多个）

```bash
# 查看所有订阅
az account list --output table

# 设置默认订阅
az account set --subscription "your-subscription-id"
```

### 步骤 4: 验证登录

```bash
az account show
```

### 步骤 5: 配置项目端点

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入：

```bash
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

### 步骤 6: 运行测试

```bash
# 使用 Azure AI
./scripts/test_e2e.sh azure

# 或使用 Python 版本
python scripts/test_e2e.py --mode azure
```

**优点**:
- ✅ 不需要管理密钥
- ✅ 支持多因素认证 (MFA)
- ✅ 自动令牌刷新
- ✅ 符合企业安全策略

**限制**:
- ❌ 需要手动登录（每 90 天一次）
- ❌ 不适用于无人值守的自动化任务

## 方法 2: 环境变量

**适用于**: CI/CD 管道、容器化部署、自动化测试

### 选项 A: 使用 Azure AI Foundry

#### 步骤 1: 获取项目信息

从 Azure AI Foundry Portal 获取：

1. 登录 [Azure AI Foundry](https://ai.azure.com)
2. 选择你的项目
3. 进入 **Settings** > **Project details**
4. 复制 **Project connection string** (即 ENDPOINT)

#### 步骤 2: 配置环境变量

创建 `.env` 文件：

```bash
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

#### 步骤 3: 设置认证

Azure AI Foundry 使用 **Managed Identity** 或 **Azure CLI credentials**。

对于 CI/CD，使用 **Service Principal**:

```bash
# 创建 Service Principal
az ad sp create-for-rbac --name "social-insight-workflow" \
    --role "Cognitive Services User" \
    --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group}

# 输出会包含:
# {
#   "appId": "...",
#   "password": "...",
#   "tenant": "..."
# }
```

设置环境变量：

```bash
AZURE_CLIENT_ID=<appId>
AZURE_CLIENT_SECRET=<password>
AZURE_TENANT_ID=<tenant>
```

### 选项 B: 直接使用 Azure OpenAI

如果不使用 AI Foundry，可以直接连接 Azure OpenAI：

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

#### 获取 API Key:

1. 登录 [Azure Portal](https://portal.azure.com)
2. 找到你的 Azure OpenAI 资源
3. 进入 **Keys and Endpoint**
4. 复制 **Key 1** 或 **Key 2**

**优点**:
- ✅ 适用于自动化场景
- ✅ 配置简单
- ✅ 无需交互式登录

**限制**:
- ❌ 需要安全管理密钥
- ❌ 密钥泄露风险
- ❌ 需要定期轮换密钥

## 方法 3: Azure Key Vault

**适用于**: 生产环境、团队协作

### 步骤 1: 创建 Key Vault

```bash
# 创建 Key Vault
az keyvault create \
    --name "social-insight-kv" \
    --resource-group "your-resource-group" \
    --location "eastus"
```

### 步骤 2: 存储密钥

```bash
# 存储 endpoint
az keyvault secret set \
    --vault-name "social-insight-kv" \
    --name "AzureAIProjectEndpoint" \
    --value "https://your-project.api.azureml.ms"

# 存储 model name
az keyvault secret set \
    --vault-name "social-insight-kv" \
    --name "AzureAIModelDeploymentName" \
    --value "gpt-4"
```

### 步骤 3: 授予访问权限

```bash
# 授予当前用户访问权限
az keyvault set-policy \
    --name "social-insight-kv" \
    --upn "your-email@company.com" \
    --secret-permissions get list

# 或授予 Service Principal 访问权限
az keyvault set-policy \
    --name "social-insight-kv" \
    --spn "<service-principal-app-id>" \
    --secret-permissions get list
```

### 步骤 4: 修改代码读取密钥

创建 `scripts/load_keyvault_secrets.py`:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

def load_secrets_from_keyvault():
    """Load secrets from Azure Key Vault."""
    vault_url = "https://social-insight-kv.vault.azure.net"
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    
    # Load secrets
    endpoint = client.get_secret("AzureAIProjectEndpoint").value
    model = client.get_secret("AzureAIModelDeploymentName").value
    
    # Set environment variables
    os.environ["AZURE_AI_PROJECT_ENDPOINT"] = endpoint
    os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"] = model
    
    print("✓ Secrets loaded from Key Vault")

if __name__ == "__main__":
    load_secrets_from_keyvault()
```

使用：

```bash
# 加载密钥并运行测试
python scripts/load_keyvault_secrets.py && python scripts/test_e2e.py --mode azure
```

**优点**:
- ✅ 集中管理密钥
- ✅ 审计日志
- ✅ 访问控制
- ✅ 自动轮换
- ✅ 符合企业合规要求

**限制**:
- ❌ 需要额外的 Azure 资源
- ❌ 配置相对复杂
- ❌ 额外成本

## 获取所需信息

### 1. Azure AI Project Endpoint

**从 Azure AI Foundry Portal**:
1. 访问 https://ai.azure.com
2. 选择项目
3. Settings → Project details
4. 复制 "Project connection string"

**从 Azure Portal**:
1. 访问 https://portal.azure.com
2. 搜索 "Machine Learning"
3. 选择你的工作区
4. Overview → Workspace endpoint

### 2. Model Deployment Name

**从 Azure AI Foundry Portal**:
1. 访问 https://ai.azure.com
2. 选择项目
3. Deployments → 查看部署列表
4. 复制部署名称（如 `gpt-4`, `gpt-35-turbo`）

**从 Azure Portal**:
1. Azure OpenAI 资源
2. Model deployments
3. 查看部署名称

### 3. 验证配置

```bash
# 测试连接
az cognitiveservices account show \
    --name "your-openai-resource" \
    --resource-group "your-resource-group"
```

## 环境变量完整列表

### 必需变量

```bash
# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 或 Azure OpenAI (直接)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

### 可选变量

```bash
# Service Principal 认证
AZURE_CLIENT_ID=your-app-id
AZURE_CLIENT_SECRET=your-password
AZURE_TENANT_ID=your-tenant-id

# 订阅和资源组
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group

# API 版本
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# TTS 功能
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=eastus

# Web 搜索工具
TAVILY_API_KEY=your-tavily-key
```

## 故障排查

### 问题 1: "az login" 失败

**症状**: `az login` 无法打开浏览器

**解决方案**:
```bash
# 使用设备代码登录
az login --use-device-code

# 或指定租户
az login --tenant "your-tenant-id"
```

### 问题 2: 认证超时

**症状**: "Authentication failed" 或 "Token expired"

**解决方案**:
```bash
# 重新登录
az logout
az login

# 清除缓存
rm -rf ~/.azure
az login
```

### 问题 3: 找不到 ENDPOINT

**症状**: "AZURE_AI_PROJECT_ENDPOINT not found"

**解决方案**:
```bash
# 检查 .env 文件是否存在
ls -la .env

# 检查格式（不要有空格）
cat .env | grep AZURE_AI_PROJECT_ENDPOINT

# 正确格式:
# AZURE_AI_PROJECT_ENDPOINT=https://...
# 
# 错误格式:
# AZURE_AI_PROJECT_ENDPOINT = https://...  # 不要有空格
```

### 问题 4: 权限不足

**症状**: "Forbidden" 或 "Access Denied"

**解决方案**:
```bash
# 检查角色分配
az role assignment list --assignee "your-email@company.com" --output table

# 添加必要角色
az role assignment create \
    --role "Cognitive Services User" \
    --assignee "your-email@company.com" \
    --scope "/subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.CognitiveServices/accounts/{account-name}"
```

### 问题 5: Model 不存在

**症状**: "Model deployment not found"

**解决方案**:
```bash
# 列出所有部署
az cognitiveservices account deployment list \
    --name "your-openai-resource" \
    --resource-group "your-resource-group" \
    --output table

# 确保 AZURE_AI_MODEL_DEPLOYMENT_NAME 匹配实际部署名称
```

## 测试认证配置

运行以下命令测试配置：

```bash
# 快速测试 (mock mode，不需要 Azure)
./scripts/test_e2e.sh mock

# 完整测试 (需要 Azure 认证)
./scripts/test_e2e.sh azure

# Python 版本
python scripts/test_e2e.py --mode azure --verbose
```

## 安全最佳实践

1. **永远不要提交 `.env` 文件到 Git**
   ```bash
   # 确保 .gitignore 包含
   echo ".env" >> .gitignore
   ```

2. **使用最小权限原则**
   - 只授予必要的角色
   - 使用 Cognitive Services User 而不是 Owner

3. **定期轮换密钥**
   ```bash
   # 每 90 天轮换一次
   az cognitiveservices account keys regenerate \
       --name "your-resource" \
       --resource-group "your-resource-group" \
       --key-name key1
   ```

4. **使用 Managed Identity (生产环境)**
   - 在 Azure VM/Container 中自动使用
   - 不需要管理凭证

5. **启用审计日志**
   ```bash
   az monitor diagnostic-settings create \
       --name "audit-logs" \
       --resource "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name}" \
       --logs '[{"category":"Audit","enabled":true}]'
   ```

## 参考资源

- [Azure CLI 文档](https://docs.microsoft.com/cli/azure/)
- [Azure AI Foundry 文档](https://learn.microsoft.com/azure/ai-services/agents/)
- [Azure OpenAI 服务](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure Key Vault](https://docs.microsoft.com/azure/key-vault/)
- [DefaultAzureCredential](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)

## 支持

如有问题，请：
1. 查阅本文档的故障排查部分
2. 检查 [EXAMPLES.md](EXAMPLES.md) 中的常见问题
3. 在 GitHub Issues 中提问
