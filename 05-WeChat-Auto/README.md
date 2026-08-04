# B-UiAutomation — 微信单删检测 / 按名单清理

基于 **uiautomator2** 的安卓微信自动化工具：用 ¥0.01 转账探测找出疑似单删好友，并可按名单批量删除。

> 仅供个人学习与自用。操作涉及真实微信界面与好友关系，请自行承担风控与误删风险。

---

## 功能概览

| 模式 | 作用 |
|------|------|
| `smoke` | 连接自检（不操作微信） |
| `scan` | 遍历通讯录，转账探测，写入疑似单删名单 |
| `purge` | 按 `deleted.txt` 名单删除好友 |
| `clear` | 清空运行记录与截图 |

**探测原理**：对好友发起 0.01 元转账 → **不会输入支付密码**。出现「不是收款方好友」等文案判为疑似单删；进入付款页则视为仍是好友。

**删除方式**：打开资料页 → 右上角 ⋯ → 删除 → 确认。

---

## 环境要求

- Windows + Python 3.10+
- 安卓手机（本项目在 vivo 双开微信场景下验证过）
- USB 调试已开启，`adb devices` 显示为 `device`
- 电脑已安装 [ADB](https://developer.android.com/tools/adb)（或 Android Platform Tools）

### 安装依赖

```powershell
cd <项目目录>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uiautomator2 init
```

`init` 会向手机推送 atx-agent，完成后再次确认：

```powershell
adb devices
```

---

## 使用前准备

1. 手机亮屏、解锁，调长自动锁屏时间  
2. 打开微信，停在**主界面**（底栏：微信 / 通讯录 / 发现 / 我）  
3. 建议用 [scrcpy](#附注scrcpy-安装与使用) 把画面投到电脑，方便盯进度  
4. **控件必须可读**：若 dump 不到「通讯录」等文字，脚本无法点击  

### 分身微信 / 控件读不到时

部分机型（如 vivo 双开「Ⅱ·微信」）默认控件树为空。可按顺序试：

1. 设置 → 无障碍 → 打开「选中朗读 / Speak selection」或 **TalkBack**，再回微信主界面  
2. 或安装 Hamibot，开启其无障碍并保持后台  
3. 跑调试：

```powershell
python debug_ui.py
```

看到 `has 通讯录: True` / `STATUS: OK` 后再 `scan`。

主微信或分身均可，**只要控件可读**。

---

## 常用命令

先激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

### 1. 连接自检

```powershell
python main.py smoke
```

### 2. 转账探测（生成名单）

```powershell
# 从第 0 个好友起测 20 人
python main.py scan --offset 0 --count 20

# 下一批从第 20 个接着测
python main.py scan --offset 20 --count 20
```

- `--offset`：跳过前 N 个好友（从 0 开始）  
- `--count`：本批检测人数  
- 已在 `deleted.txt` 中的名字会跳过复检  
- 每人约 4.5～6 秒；200 人大约 **15～25 分钟**（视机子与命中数而定）  
- `Ctrl+C` 可中止；已完成的人会即时写入文件  

### 3. 按名单删除

```powershell
# 演练：只报告命中，不真删
python main.py purge --offset 0 --count 20 --dry-run

# 真实删除本批 20 人中命中名单的
python main.py purge --offset 0 --count 20

# 从偏移起一直扫到通讯录结束
python main.py purge --offset 0 --count 0
```

### 4. 清空记录

```powershell
python main.py clear          # 只预览
python main.py clear --yes    # 确认清空
```

会删除：`data/result.csv`、`data/deleted.txt`、`data/remove_result.csv`、`data/purge_summary.txt`，以及 `screenshots/` 下全部截图。

### 多设备

```powershell
python main.py smoke --serial 设备序列号
python main.py scan --serial 设备序列号 --offset 0 --count 10
```

---

## 输出文件

| 路径 | 说明 |
|------|------|
| `data/result.csv` | scan 明细（每人一行，即时追加） |
| `data/deleted.txt` | 疑似单删名单（purge 的输入） |
| `data/remove_result.csv` | purge 明细 |
| `data/purge_summary.txt` | 成功删除的逐条记录（时间 + 昵称） |
| `screenshots/` | 仅疑似单删时截图 |

节奏与关键词可在 `config.py` 调整（金额、等待间隔、跳过名单、判定文案等）。

---

## 项目结构

```text
B-UiAutomation/
  main.py          # CLI 入口
  detector.py      # 通讯录遍历、转账探测、删除流程
  device.py        # 连接与控件可读性检查
  io_util.py       # 结果增量写入
  config.py        # 运行参数
  debug_ui.py      # 调试控件树是否可读
  requirements.txt
  data/            # 运行产物
  screenshots/     # 截图
```

---

## 注意事项

- **不会自动输入支付密码**；正常好友停在付款页后会返回  
- 删除不可恢复，建议先 `--dry-run`  
- 微信改版可能导致按钮文案/布局变化，点不准时需改 `detector.py` / `config.py`  
- 批量操作有账号风控风险，请控制频率（`MIN_DELAY` / `MAX_DELAY`）  
- 运行期间尽量不要手动抢操作；息屏/锁屏会导致失败  

---

## 附注：scrcpy 安装与使用

[scrcpy](https://github.com/Genymobile/scrcpy) 通过 adb 把手机画面镜像到电脑，延迟低，可用鼠标在窗口里点按、滑动，方便盯脚本跑进度。

### 安装（Windows 任选一种）

**方式 A：winget**

```powershell
winget install Genymobile.scrcpy
```

**方式 B：scoop**

```powershell
scoop install scrcpy
```

**方式 C：手动下载**

1. 打开 [scrcpy Releases](https://github.com/Genymobile/scrcpy/releases)  
2. 下载 Windows 版压缩包并解压  
3. 把解压目录加入 PATH，或在该目录下打开终端运行  

### 使用

先确保设备已授权：

```powershell
adb devices
```

状态为 `device` 后：

```powershell
scrcpy
```

会弹出手机镜像窗口。常用参数：

```powershell
# 插电保持唤醒；电脑上看画面时关掉手机屏省电
scrcpy --stay-awake --turn-screen-off

# 指定设备
scrcpy -s 设备序列号

# 限制码率 / 分辨率（卡顿时）
scrcpy -m 1024 -b 4M
```

| 参数 | 含义 |
|------|------|
| `--stay-awake` | USB 供电时保持唤醒 |
| `--turn-screen-off` | 关掉手机物理屏（镜像仍可见）；若自动化点不准则去掉此参数 |
| `-s <serial>` | 多设备时指定序列号 |
| `-m 1024` | 最大边限制为 1024 |
| `-b 4M` | 视频码率约 4Mbps |

### 与本脚本配合

1. 先开 `scrcpy`，确认能看到桌面  
2. 在镜像窗口里打开微信，停在主界面  
3. 再跑 `smoke` / `scan` / `purge`  
4. 可在窗口里观察脚本是否点错；紧急时 `Ctrl+C` 停脚本  

说明：scrcpy 只是投屏/遥控，**真正的自动化仍由本仓库的 Python + uiautomator2 完成**。
