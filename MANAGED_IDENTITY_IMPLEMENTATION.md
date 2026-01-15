# Azure Managed Identity 实现说明

## 需求

> "this project must use azure ai foundry agent service with managed identity."

## 实现概述

本项目现已完全支持 Azure Managed Identity 作为**首选认证方式**，适用于生产环境部署到 Azure。

## 核心改动

### 1. 认证优先级（新）

```
1. Managed Identity (系统分配或用户分配)
   ↓ (如果不可用)
2. DefaultAzureCredential (Azure CLI, 环境变量等)
   ↓ (如果不可用)
3. 失败并报错
```

### 2. 自动检测 Azure 环境

代码会自动检测以下环境变量来判断是否在 Azure 中运行：

- `IDENTITY_ENDPOINT` - Azure App Service/Functions
- `IMDS_ENDPOINT` - Azure VM/VMSS
- `MSI_ENDPOINT` - 传统 Azure 服务

如果检测到这些环境变量，会优先使用 Managed Identity。

### 3. 配置选项

#### 强制使用 Managed Identity

```bash
USE_MANAGED_IDENTITY=true
```

#### 用户分配的 Managed Identity

```bash
AZURE_CLIENT_ID=your-user-assigned-identity-client-id
```

#### 必需的配置（无论哪种认证方式）

```bash
AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

## 代码实现

### 关键函数

#### `_create_azure_credential(exclude_interactive: bool = True)`

创建同步 Azure 凭据，优先使用 Managed Identity：

```python
def _create_azure_credential(exclude_interactive: bool = True):
    """
    创建 Azure 凭据，优先使用 Managed Identity
    
    优先级：
    1. Managed Identity (如果在 Azure 环境中)
    2. DefaultAzureCredential 链
    """
    # 检测 Azure 环境
    in_azure_env = any([
        os.getenv("IDENTITY_ENDPOINT"),
        os.getenv("IMDS_ENDPOINT"),
        os.getenv("MSI_ENDPOINT"),
    ])
    
    if in_azure_env:
        # 尝试 Managed Identity
        managed_identity = ManagedIdentityCredential(
            client_id=os.getenv("AZURE_CLIENT_ID")  # 可选：用户分配
        )
        default_credential = DefaultAzureCredential(...)
        return ChainedTokenCredential(managed_identity, default_credential)
    
    # 本地开发等场景
    return DefaultAzureCredential(...)
```

#### `_create_async_azure_credential(exclude_interactive: bool = True)`

异步版本，用于 async/await 操作。

### 修改的文件

1. **`.github/skills/maf-workflow-gen/scripts/run_template.py`**
   - 添加 `_create_azure_credential()` 和 `_create_async_azure_credential()`
   - 更新 `AzureAIFoundryAgentInvoker` 使用新的凭据函数

2. **`.github/skills/maf-agent-create/scripts/create_agents_from_workflow.py`**
   - 添加 `_create_azure_credential()`
   - 更新 `_create_foundry_agents()` 使用新的凭据函数

3. **`.env.example`**
   - 添加 Managed Identity 配置部分（置顶）
   - 详细文档和示例

4. **`AZURE_CREDENTIALS.md`**
   - 添加 Managed Identity 作为方法 1（首选）
   - 完整的设置指南：
     - Azure VM
     - Azure Container Instances
     - Azure App Service
   - 权限分配示例
   - 故障排查

5. **`README.md`**
   - 更新认证部分，推荐 Managed Identity
   - 添加快速配置示例

6. **`E2E_TEST_AND_CREDENTIALS.md`**
   - 更新为 4 种认证方法（之前是 3 种）
   - Managed Identity 作为方法 1

7. **`.github/copilot-instructions.md`**
   - 更新最佳实践，优先使用 Managed Identity

## 使用场景

### 场景 1: Azure VM

```bash
# 1. 启用 Managed Identity
az vm identity assign --name "my-vm" --resource-group "my-rg"

# 2. 获取 Principal ID 并授权
PRINCIPAL_ID=$(az vm show --name "my-vm" --resource-group "my-rg" \
    --query identity.principalId -o tsv)

az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Cognitive Services User" \
    --scope "/subscriptions/{sub}/resourceGroups/{rg}"

# 3. 在 VM 中设置环境变量
export AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
export AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4

# 4. 运行应用 - 自动使用 Managed Identity
./scripts/test_e2e.sh azure
```

### 场景 2: Azure Container Instances

```bash
# 创建容器时启用 Managed Identity
az container create \
    --name "social-insight-app" \
    --resource-group "my-rg" \
    --image "myregistry.azurecr.io/social-insight:latest" \
    --assign-identity \
    --environment-variables \
        AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms \
        AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

### 场景 3: Azure App Service

```bash
# 启用 Managed Identity
az webapp identity assign \
    --name "social-insight-webapp" \
    --resource-group "my-rg"

# 配置应用设置
az webapp config appsettings set \
    --name "social-insight-webapp" \
    --resource-group "my-rg" \
    --settings \
        AZURE_AI_PROJECT_ENDPOINT=https://your-project.api.azureml.ms \
        AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

### 场景 4: 本地开发（回退到 Azure CLI）

```bash
# 仍然支持本地开发
az login
cp .env.example .env
# 编辑 .env
./scripts/test_e2e.sh azure
```

## 优势

### 安全性

- ✅ **无密钥存储** - 不需要在代码或配置中存储敏感信息
- ✅ **自动轮换** - Azure 自动管理凭据生命周期
- ✅ **最小权限** - 可以精确控制权限范围
- ✅ **审计跟踪** - 所有访问通过 Azure AD 记录

### 运维

- ✅ **零配置** - 在 Azure 中自动检测和使用
- ✅ **向后兼容** - 不影响现有的认证方法
- ✅ **灵活性** - 支持系统分配和用户分配的标识

### 合规

- ✅ 符合企业安全标准
- ✅ 满足 SOC 2、ISO 27001 等合规要求
- ✅ 无需手动密钥轮换审计

## 验证

### 检查 Managed Identity 是否可用

在 Azure 资源中运行：

```bash
curl -H "Metadata:true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://cognitiveservices.azure.com/"
```

如果返回访问令牌，说明 Managed Identity 已正确配置。

### 测试应用

```bash
# 在 Azure 资源中运行测试
./scripts/test_e2e.sh azure

# 应该看到成功消息，无需 az login
```

## 故障排查

### 问题: "ManagedIdentityCredential authentication failed"

**原因**: Managed Identity 未启用或权限不足

**解决**:
1. 检查是否已启用 Managed Identity
2. 验证角色分配是否正确
3. 确认资源在正确的订阅/资源组中

### 问题: "AZURE_AI_PROJECT_ENDPOINT not set"

**原因**: 环境变量未配置

**解决**: 在 Azure 资源的应用设置中添加必需的环境变量

## 后续工作

当前实现已满足需求，可选的增强功能：

- [ ] 添加 Managed Identity 健康检查端点
- [ ] 添加详细的认证方法日志记录
- [ ] 创建 Terraform/Bicep 模板自动配置 Managed Identity
- [ ] 添加 CI/CD 管道示例

## 参考资源

- [Azure Managed Identities 文档](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [DefaultAzureCredential 文档](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)
- [Azure AI Foundry 身份验证](https://learn.microsoft.com/azure/ai-services/agents/how-to/authenticate)
