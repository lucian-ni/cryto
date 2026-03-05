"""
赫斯特指数分桶回测分析启动入口
对滑动窗口赫斯特指数按区间分桶，统计做多/做空的未来收益、胜率和最大回撤
使用方式：python run_hurst_bucket.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.mysql_client import MySQLClient
from src.strategy.hurst_bucket_analysis import HurstBucketAnalyzer
from src.lib_resource import (
    COLOR_CYAN, COLOR_RED, COLOR_RESET, TAG_HURST_BUCKET,
    TITLE_HURST_BUCKET, TITLE_HURST_BUCKET_DONE, MSG_HURST_BUCKET_FATAL
)


def main():
    """赫斯特指数分桶回测分析主函数"""
    print(f"{TAG_HURST_BUCKET} {COLOR_CYAN}{TITLE_HURST_BUCKET}{COLOR_RESET}")

    print(f"{TAG_HURST_BUCKET} 正在初始化数据表...")
    MySQLClient.init_tables()

    analyzer = HurstBucketAnalyzer()
    try:
        analyzer.run()
    except Exception as e:
        print(f"{TAG_HURST_BUCKET} {COLOR_RED}"
              f"{MSG_HURST_BUCKET_FATAL.format(error=str(e))}{COLOR_RESET}")
        sys.exit(1)

    print(f"{TAG_HURST_BUCKET} {COLOR_CYAN}{TITLE_HURST_BUCKET_DONE}{COLOR_RESET}")


if __name__ == '__main__':
    main()
