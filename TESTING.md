# 测试指南 - 快速参考

本文档提供端到端测试的快速参考和常用命令。

## 快速开始

### 1. 最快验证方式（Mock 模式）

```bash
# Bash 版本
./scripts/test_e2e.sh mock

# Python 版本
python scripts/test_e2e.py --mode mock
```

**耗时**: 约 10-30 秒  
**要求**: 仅需 Python 3.8+  
**成本**: 免费

### 2. 完整测试（Azure AI 模式）

```bash
# 先配置认证
cp .env.example .env
# 编辑 .env，填入 Azure 信息
az login

# 运行测试
./scripts/test_e2e.sh azure

# 或带详细输出
python scripts/test_e2e.py --mode azure --verbose
```

**耗时**: 约 2-5 分钟  
**要求**: Azure AI Foundry 认证  
**成本**: 消耗 Azure tokens

## 测试脚本功能

两个测试脚本（bash 和 Python）执行相同的 8 个步骤：

1. ✅ 验证 Python 环境
2. ✅ 检查必需文件（config、workflow、tools）
3. ✅ 验证 workflow YAML 语法
4. ✅ 测试工具注册表（确认 4 个工具可用）
5. ✅ 生成可执行 runner
6. ✅ 检查 Azure 认证（仅 azure 模式）
7. ✅ 运行完整工作流
8. ✅ 验证所有输出文件

## 测试输出

成功后会生成：

```
generated/social_insight_output/
├── raw_signals.json          # 15 个模拟信号
├── signals/                  # 按平台分组
│   ├── weibo.json
│   ├── douyin.json
│   └── zhihu.json
├── clusters/
│   └── hotspots.json         # 3 个聚类热点
├── insights/
│   └── insights.json         # 3 个社会洞察
└── report.md                 # 最终策略报告
```

## 查看结果

```bash
# 查看最终报告
cat generated/social_insight_output/report.md

# 查看热点
cat generated/social_insight_output/clusters/hotspots.json

# 查看洞察
cat generated/social_insight_output/insights/insights.json

# 使用 jq 美化 JSON（如果安装了）
cat generated/social_insight_output/raw_signals.json | jq .
```

## 单独测试工具

如果只想测试某个工具：

```bash
# 列出所有工具
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py --tool __list__

# 测试信号采集
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.ingest_signals \
  --args-json '{"hot_api_list_path":"config/hot_api_list.json","output_dir":"test_output","time_window_hours":24}'

# 测试聚类
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py \
  --tool social.cluster_signals_fallback \
  --args-json '{"raw_signals_path":"test_output/raw_signals.json","output_dir":"test_output","top_k":5}'
```

## 常见问题

### Q: 测试失败，如何调试？

A: 按步骤检查：

```bash
# 1. 验证 Python
python3 --version  # 需要 3.8+

# 2. 验证 YAML
python .github/skills/maf-decalarative-yaml/scripts/validate_maf_workflow_yaml.py \
  workflows/social_insight_workflow.yaml

# 3. 验证工具
python .github/skills/maf-shared-tools/scripts/call_shared_tool.py --tool __list__

# 4. 查看详细日志
python scripts/test_e2e.py --mode mock --verbose
```

### Q: Azure 模式认证失败？

A: 查看详细指南：

```bash
# 检查认证状态
az account show

# 重新登录
az logout
az login

# 验证环境变量
cat .env | grep AZURE_AI

# 参考完整指南
cat AZURE_CREDENTIALS.md
```

### Q: 如何清理测试输出？

A: 删除 generated 目录（会自动重新生成）：

```bash
# 清理所有生成的文件
rm -rf generated/social_insight_*

# 重新运行测试
./scripts/test_e2e.sh mock
```

### Q: Mock 模式和 Azure 模式有什么区别？

| 特性 | Mock 模式 | Azure 模式 |
|------|----------|-----------|
| LLM 调用 | 不调用 | 调用 Azure AI |
| 聚类质量 | 基于规则 | AI 智能分析 |
| 洞察质量 | 模板生成 | AI 深度分析 |
| 报告质量 | 通用模板 | 定制化建议 |
| 速度 | 快（10-30秒） | 慢（2-5分钟） |
| 成本 | 免费 | 消耗 tokens |
| 适用场景 | 开发/测试 | 生产/演示 |

### Q: 如何修改测试参数？

A: 编辑工作流 YAML 或工具参数：

```bash
# 修改信号采集的时间窗口
# 编辑 workflows/social_insight_workflow.yaml
# 找到 set_time_window，修改 value: 24 改为其他值

# 修改 API 配置
# 编辑 config/hot_api_list.json
# 添加/删除平台或修改设置
```

## 性能测试

测试不同模式的性能：

```bash
# 测试 mock 模式性能
time ./scripts/test_e2e.sh mock

# 测试 azure 模式性能
time ./scripts/test_e2e.sh azure
```

## 自动化 CI/CD

在 CI/CD 管道中使用：

```yaml
# GitHub Actions 示例
- name: Run E2E Test
  run: |
    python scripts/test_e2e.py --mode mock
  
# 或使用 Azure 认证
- name: Azure Login
  uses: azure/login@v1
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}

- name: Run E2E Test with Azure
  env:
    AZURE_AI_PROJECT_ENDPOINT: ${{ secrets.AZURE_AI_PROJECT_ENDPOINT }}
    AZURE_AI_MODEL_DEPLOYMENT_NAME: ${{ secrets.AZURE_AI_MODEL_DEPLOYMENT_NAME }}
  run: |
    python scripts/test_e2e.py --mode azure
```

## 进一步学习

- **完整架构**: 查看 [README.md](README.md)
- **详细示例**: 查看 [EXAMPLES.md](EXAMPLES.md)
- **认证配置**: 查看 [AZURE_CREDENTIALS.md](AZURE_CREDENTIALS.md)
- **实现细节**: 查看 [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## 问题反馈

如遇到问题：
1. 查看本文档的常见问题
2. 运行 `--verbose` 模式查看详细日志
3. 在 GitHub Issues 中提问
