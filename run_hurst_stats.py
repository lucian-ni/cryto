"""
赫斯特指数滑动窗口统计分析启动入口
固定窗口=100，周期=1h，对每个时间窗口计算赫斯特指数并输出统计报告
使用方式：python run_hurst_stats.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.mysql_client import MySQLClient
from src.strategy.hurst_stats import HurstStatsCalculator
from src.lib_resource import (
    COLOR_CYAN, COLOR_RED, COLOR_RESET, TAG_HURST_STATS,
    TITLE_HURST_STATS, TITLE_HURST_STATS_DONE, MSG_HURST_STATS_FATAL
)


def main():
    """赫斯特指数滑动窗口统计分析主函数"""
    print(f"{TAG_HURST_STATS} {COLOR_CYAN}{TITLE_HURST_STATS}{COLOR_RESET}")

    # 第一步：初始化数据表（确保新增的表存在）
    print(f"{TAG_HURST_STATS} 正在初始化数据表...")
    MySQLClient.init_tables()

    # 第二步：执行滑动窗口统计分析
    calculator = HurstStatsCalculator()
    try:
        calculator.run()
    except Exception as e:
        print(f"{TAG_HURST_STATS} {COLOR_RED}"
              f"{MSG_HURST_STATS_FATAL.format(error=str(e))}{COLOR_RESET}")
        sys.exit(1)

    print(f"{TAG_HURST_STATS} {COLOR_CYAN}{TITLE_HURST_STATS_DONE}{COLOR_RESET}")


if __name__ == '__main__':
    main()
