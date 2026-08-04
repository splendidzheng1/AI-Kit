"""运行参数：按自己的节奏和微信版本微调。"""

# 转账探测金额（不会自动输入支付密码，到付款页即判定为正常）
TRANSFER_AMOUNT = "0.01"

# 人与人之间随机等待（秒）
MIN_DELAY = 1.0
MAX_DELAY = 2.0

# 单步 UI 等待（压到单人约 3~4 秒；过短可能导致点不准）
UI_SHORT = 0.12
UI_STEP = 0.22
UI_PAGE = 0.35
BACK_WAIT = 0.18

# 点转账确认后，等弹窗/付款页出现
AFTER_TRANSFER_WAIT = 0.45

# 命中单删后截图前再等一会，等弹窗动画画完（无障碍节点往往比画面先出现）
SCREENSHOT_SETTLE = 0.8

# 控件查找超时（秒）
EXISTS_FAST = 0.35
EXISTS_NORMAL = 0.7

# 仅对疑似单删截图（加速；正常好友不截）
SCREENSHOT_ONLY_HIT = True

# 通讯录里需要跳过的入口/系统号（不是普通好友）
SKIP_NAMES = frozenset(
    {
        "新的朋友",
        "仅聊天的朋友",
        "群聊",
        "标签",
        "公众号",
        "服务号",
        "企业微信联系人",
        "我的企业/社区/学校",
        "我的企业及企业联系人",
        "我的企业",
        "微信团队",
        "微信支付",
        "文件传输助手",
        "朋友推荐",
        "通讯录管理",
        "关闭悬浮提示",
        "选中后点按两次退出",
    }
)

# 单字母索引（A-Z、#）也跳过
SKIP_INDEX_CHARS = frozenset(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ#"))

# 仅在「已点进转账相关流程后」用来判定单删
DELETED_KEYWORDS = (
    "你不是收款方好友",
    "不是收款方好友",
    "对方添加你为好友后才能发起转账",
    "对方开启了朋友验证",
    "你还不是他（她）朋友",
    "你还不是他朋友",
    "你还不是她朋友",
    "对方账号异常",
    "无法向对方转账",
    "无法转账给对方",
    "转账失败",
    "被对方拉黑",
)

# 仅关闭转账失败提示；不要把「取消/确定」放进来，避免误点其它弹窗
DISMISS_BUTTONS = (
    "我知道了",
    "知道了",
)

NORMAL_KEYWORDS = (
    "请输入支付密码",
    "指纹支付",
    "面容支付",
    "付款方式",
    "更改",
)

RESULT_CSV = "data/result.csv"
DELETED_TXT = "data/deleted.txt"
REMOVE_CSV = "data/remove_result.csv"
PURGE_SUMMARY_TXT = "data/purge_summary.txt"
SCREENSHOT_DIR = "screenshots"
