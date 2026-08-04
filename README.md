# AI-Kit

> 用 AI 驱动的实用小工具集合，让重复性工作自动化。

## 功能模块

### 01-7x24h 实时财经快讯
- 基于 **PyQt6** 的桌面悬浮窗应用，实时抓取新浪财经 7x24 滚动新闻
- 支持全局热键（`Shift+Space`）呼出/隐藏、系统托盘驻留、迷你模式、新闻搜索与图片预览
- ⚠️ **额外依赖**：`PyQt6`、`Pillow`、`keyboard`（见下方依赖说明）
- ⚠️ **平台限制**：`keyboard` 库在 macOS 上需要辅助功能权限；Windows 上某些安全软件可能拦截全局热键
- 自动去重机制，最大卡片数可配置（默认 1000），抓取间隔可配置（默认 600s，最低 10s）

### 02-Job-Tool 工作评估系统
- **雷达图评估工具** — 基于 Vue 3 + ECharts 5，支持自定义评估维度（福利待遇、通勤、发展、团队氛围等），多份工作多维度对比评分，浏览器直接打开即可使用
- **Coze 审核工作流** — 基于 Coze 工作流的自动化内容审核流水线，内置递归 JSON 解析工具
- **职位评估 Prompt** — 职位评估提示词模板
- **Career Agent** — 基于 Coze Agent 的职业规划助手

### 03-Home-Debt 家债管理系统
- 基于 **Vue 3 + Vue Router** 的家债可视化工具，展示当期与往期家债
- 自动按到期日划分当期/往期，计算出资人当前应收本息
- 移动端友好，支持左右滑动切换标签
- 📁 **源码**：`03-Home-Debt/source/`（完整 Vue 项目源码，含 router、views、data）
- 🌐 **在线访问**：https://splendidzheng1.github.io/AI-Kit/03-Home-Debt/

### 04-Leet-Code LeetCode 题解
- LeetCode 算法题解答归档，共 36 题（35 道 TypeScript + 1 道 C++）
- 涵盖树、链表、数组、字符串、动态规划、贪心、图/BFS 等常见题型
- 文件命名格式：`题号.题目名称.语言后缀`（如 `2.两数相加.ts`、`3275.第-k-近障碍物查询.cpp`）
- 📁 **源码**：`04-Leet-Code/`（原 LeetCode 仓库题解已归档至此）

### 05-WeChat-Auto 微信单删检测 / 按名单清理
- 基于 **uiautomator2** 的安卓微信自动化工具（原项目代号 `B-UiAutomation`）
- 用 ¥0.01 转账探测找出疑似单删好友（不输入支付密码），并可按名单批量删除
- 三种模式：`smoke`（连接自检）、`scan`（转账探测生成名单）、`purge`（按名单删除）、`clear`（清空记录）
- ⚠️ **平台限制**：需 Windows + Python 3.10+ + USB 调试的安卓手机；操作涉及真实微信界面与好友关系，请自担风控与误删风险
- ⚠️ **隐私**：`data/`（单删名单、删除结果等）与 `screenshots/` 含个人数据，已加入 `.gitignore` 绝不入库
- 📁 **源码**：`05-WeChat-Auto/`

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
python 02-Job-Tool/A_coze_workflow.py
```

**封装版财经快讯（桌面悬浮窗）**
```bash
# 需要额外安装 PyQt6、Pillow、keyboard
pip install PyQt6 Pillow keyboard
python 01-7x24h/xinlang_news_fetcher.py
```

**家债管理系统**
```bash
# 在线访问（构建产物已部署到 GitHub Pages）
# https://splendidzheng1.github.io/AI-Kit/03-Home-Debt/

# 本地开发 / 修改源码：
cd 03-Home-Debt/source
npm install
npm run dev      # 启动开发服务器
npm run build    # 构建到 source/dist，再覆盖到 03-Home-Debt/ 根目录
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端/脚本 | Python 3.8+ |
| HTTP 请求 | requests |
| AI 平台 | Coze (cozepy) |
| 前端可视化 | Vue 3, ECharts 5 |
| 桌面 GUI | PyQt6, Pillow |
| 移动端自动化 | uiautomator2, adbutils |
| 算法题解 | TypeScript, C++ |

---

## 项目结构

```
AI-Kit/
├── 01-7x24h/               # 实时财经快讯
│   ├── xinlang_news_fetcher.py
│   ├── XinlangNews.spec     # PyInstaller 打包配置
│   └── dist/                # 构建产物（XinlangNews.exe）
├── 02-Job-Tool/            # 工作评估系统 + AI 审核工作流
│   ├── index.html           # 雷达图评估工具（Vue 3 + ECharts 5）
│   ├── A_coze_workflow.py   # Coze 审核工作流
│   ├── B_prompt_职位评估.md  # 职位评估 Prompt
│   └── C-Agent/             # Career Agent
│       ├── Agent_Career.py
│       └── career_input_template.json
├── 03-Home-Debt/           # 家债管理系统
│   ├── index.html          # 构建产物（Pages 访问入口）
│   ├── favicon.svg
│   ├── assets/             # 构建产物（JS/CSS）
│   └── source/             # 完整 Vue 3 源码
│       ├── src/
│       ├── public/
│       ├── package.json
│       └── vite.config.js
├── 04-Leet-Code/           # LeetCode 题解归档（36 题，TS/C++）
│   ├── *.ts                # TypeScript 题解
│   ├── *.cpp               # C++ 题解
│   └── .gitattributes
├── 05-WeChat-Auto/        # 微信单删检测 / 按名单清理（uiautomator2）
│   ├── main.py            # 入口：smoke / scan / purge / clear 模式
│   ├── detector.py        # 转账探测单删逻辑
│   ├── device.py          # 设备/控件操作封装
│   ├── config.py          # 配置
│   ├── io_util.py         # IO 工具
│   ├── log_util.py        # 日志工具
│   ├── debug_ui.py        # 控件树调试
│   ├── requirements.txt   # uiautomator2 / adbutils
│   ├── tests/             # 测试（占位）
│   ├── data/              # 运行产物（gitignore）
│   └── screenshots/       # 截图（gitignore）
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
