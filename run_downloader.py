"""
币安数据下载器启动入口
持续运行，先下载历史数据，然后不断增量更新
使用方式：python run_downloader.py
"""
import sys
import os

# 将项目根目录加入系统路径，确保模块可正确导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.mysql_client import MySQLClient
from src.downloader.binance_downloader import BinanceDownloader
from src.lib_resource import (
    COLOR_CYAN, COLOR_RED, COLOR_RESET, TAG_DOWNLOADER,
    TITLE_DOWNLOADER, MSG_DOWNLOAD_STOP, MSG_DOWNLOAD_FATAL
)


def main():
    """下载器主函数"""
    print(f"{TAG_DOWNLOADER} {COLOR_CYAN}{TITLE_DOWNLOADER}{COLOR_RESET}")

    # 第一步：初始化数据表
    print(f"{TAG_DOWNLOADER} 正在初始化数据表...")
    MySQLClient.init_tables()

    # 第二步：启动下载器（持续运行）
    downloader = BinanceDownloader()
    print(f"{TAG_DOWNLOADER} 开始执行数据下载任务（Ctrl+C 可停止）...")
    try:
        downloader.run_forever()
    except KeyboardInterrupt:
        print(f"\n{TAG_DOWNLOADER} {COLOR_CYAN}{MSG_DOWNLOAD_STOP}{COLOR_RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{TAG_DOWNLOADER} {COLOR_RED}{MSG_DOWNLOAD_FATAL.format(error=str(e))}{COLOR_RESET}")
        sys.exit(1)


if __name__ == '__main__':
    main()

