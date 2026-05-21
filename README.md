# AI-Kit

> 用 AI 驱动的实用小工具集合，让重复性工作自动化。

## 功能模块

### 01-7x24h 实时财经快讯
- **华尔街见闻快讯抓取** — 支持宏观、A股、美股、区块链、外汇、商品等多频道实时监控
- **新浪 7x24 财经快讯** — 实时抓取新浪财经滚动新闻，支持分页与去重
- 自动去重机制，持续轮询模式，按 `Ctrl+C` 优雅退出

### 02-Job-Tool 工作评估系统
- 基于 **Vue 3 + ECharts 5** 的雷达图可视化工具
- 支持自定义评估维度（福利待遇、通勤、发展、团队氛围等）
- 多份工作多维度对比评分，浏览器直接打开即可使用，零依赖后端

### 03-Ai-Censor-Job AI 审核工作流
- 基于 **Coze 工作流** 的自动化内容审核流水线
- 内置递归 JSON 解析工具，解决 API 多层嵌套字符串问题

### 00-Prompt AI 提示词库
- SQL 语句生成、XPath 语句生成、VBA 程序生成等实用 Prompt
- 职位评估 Prompt 模板

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/splendidzheng1/AI-Kit.git
cd AI-Kit
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行工具

**财经快讯监控**
```bash
python 01-7x24h/wallstreet_news_fetcher.py
python 01-7x24h/xinlang_news_fetcher.py
```

**工作评估系统**
```bash
# 直接在浏览器中打开
open 02-Job-Tool/index.html
```

**Coze 审核工作流**
```bash
# 先设置环境变量
export COZE_API_TOKEN="your_coze_api_token"
python 03-Ai-Censor-Job/A_coze_workflow.py
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端/脚本 | Python 3.8+ |
| HTTP 请求 | requests |
| AI 平台 | Coze (cozepy) |
| 前端可视化 | Vue 3, ECharts 5 |

---

## 项目结构

```
AI-Kit/
├── 00-Prompt/              # AI 提示词库
│   ├── 生成SQL语句.txt
│   ├── 生成XPath语句.txt
│   ├── 生成vba程序.txt
│   └── 职位评估.md
├── 01-7x24h/               # 实时财经快讯
│   ├── wallstreet_news_fetcher.py
│   ├── xinlang_news_fetcher.py
│   └── Encapsulation/      # 封装版本
├── 02-Job-Tool/            # 工作评估系统
│   └── index.html
├── 03-Ai-Censor-Job/       # AI 审核工作流
│   └── A_coze_workflow.py
├── requirements.txt
└── README.md
```

---

## 注意事项

- `COZE_API_TOKEN` 请通过环境变量传入，**切勿将 Token 硬编码到代码中**
- 财经快讯脚本仅供个人学习与研究使用，请遵守相关平台的服务条款

---

## License

[MIT](LICENSE)
