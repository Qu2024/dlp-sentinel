import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv 未安装时也允许本地演示运行；此时只读取系统环境变量。
    pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# AHP 一级权重
L1_WEIGHTS = {"C2": 0.1931, "C3": 0.0746, "C4": 0.4388, "C5": 0.2935}

# AHP 二级局部权重
L2_WEIGHTS = {
    "C2": {"B1": 0.4387, "B2": 0.2194, "B3": 0.2428, "B4": 0.0991},
    "C3": {"A1": 0.2935, "A2": 0.4388, "A3": 0.1931, "A4": 0.0746},
    "C4": {"S1": 0.3525, "S2": 0.1336, "S3": 0.2195, "S4": 0.0749, "S5": 0.2195},
    "C5": {"L1": 0.2516, "L2": 0.3765, "L3": 0.1907, "L4": 0.1258, "L5": 0.0555},
}

# 风险等级阈值
RISK_THRESHOLDS = [(75, "极高风险"), (55, "高风险"), (30, "中风险"), (0, "低风险")]
