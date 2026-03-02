"""
赫斯特指数（Hurst Exponent）策略计算启动入口
独立运行，计算完成后退出
使用方式：python run_hurst.py
"""
import sys
import os

# 将项目根目录加入系统路径，确保模块可正确导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.mysql_client import MySQLClient
from src.strategy.hurst_exponent import HurstCalculator
from src.lib_resource import (
    COLOR_CYAN, COLOR_RED, COLOR_RESET, TAG_HURST,
    TITLE_HURST, TITLE_HURST_DONE, MSG_HURST_FATAL
)


def main():
    """赫斯特指数计算主函数"""
    print(f"{TAG_HURST} {COLOR_CYAN}{TITLE_HURST}{COLOR_RESET}")

    # 第一步：初始化数据表（确保表存在）
    print(f"{TAG_HURST} 正在初始化数据表...")
    MySQLClient.init_tables()

    # 第二步：执行赫斯特指数计算
    calculator = HurstCalculator()
    try:
        calculator.run()
    except Exception as e:
        print(f"{TAG_HURST} {COLOR_RED}{MSG_HURST_FATAL.format(error=str(e))}{COLOR_RESET}")
        sys.exit(1)

    print(f"{TAG_HURST} {COLOR_CYAN}{TITLE_HURST_DONE}{COLOR_RESET}")


if __name__ == '__main__':
    main()

