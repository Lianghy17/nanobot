"""测试日志输出"""
import sys
import logging
from pathlib import Path

# 配置日志
def setup_logger():
    """配置logging日志系统"""
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 配置根日志记录器 - INFO级别
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 移除所有现有的handler
    root_logger.handlers.clear()

    # 创建控制台输出handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setStream(sys.stdout)  # 确保使用 stdout
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 测试输出
    print("\n" + "="*80)
    print("[PRINT测试] 日志系统已配置")
    print("="*80 + "\n")

    logging.info("logging.info 测试")
    root_logger.info("root_logger.info 测试")

    # 测试子 logger
    test_logger = logging.getLogger("test.module")
    test_logger.info("test_logger.info 测试")

    print("\n" + "="*80)
    print("[PRINT测试] 测试完成")
    print("="*80 + "\n")

if __name__ == "__main__":
    setup_logger()
