# LLM配置说明

## 快速开始

1. 复制此文件为 `.env` 文件
2. 填写你的API密钥和配置
3. 重启后端服务

## 配置示例

```bash
# OpenAI配置
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4

# 或者使用其他兼容OpenAI API的服务
# LLM_PROVIDER=custom
# LLM_API_KEY=your-api-key
# LLM_BASE_URL=https://your-custom-endpoint.com/v1
# LLM_MODEL=your-model-name

# 超时设置（秒）
LLM_TIMEOUT=60

# 最大token数
LLM_MAX_TOKENS=2000

# 温度参数（0-1）
LLM_TEMPERATURE=0.7
```

## 支持的提供商

- `openai` - OpenAI官方API
- `azure` - Azure OpenAI服务
- `anthropic` - Anthropic Claude API
- `custom` - 任何兼容OpenAI API格式的服务

## 注意事项

- 请妥善保管你的API密钥，不要提交到版本控制系统
- `.env` 文件已添加到 `.gitignore`
