"""
检查 K 线数据下载是否完整
对每个 (symbol, interval) 统计条数、时间范围，并与预期（约 3 年）对比
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import DOWNLOAD_SYMBOLS, DOWNLOAD_INTERVALS, DOWNLOAD_HISTORY_YEARS
from src.db.mysql_client import MySQLClient

# 每个周期在 3 年内大约应有的 K 线数量（近似）
EXPECTED_BARS = {
    '1h': 24 * 365 * DOWNLOAD_HISTORY_YEARS,   # 26280
    '2h': 12 * 365 * DOWNLOAD_HISTORY_YEARS,   # 13140
    '4h': 6 * 365 * DOWNLOAD_HISTORY_YEARS,    # 6570
    '12h': 2 * 365 * DOWNLOAD_HISTORY_YEARS,   # 2190
    '1d': 365 * DOWNLOAD_HISTORY_YEARS,        # 1095
}

SQL = """
    SELECT 
        COUNT(*) AS cnt,
        MIN(open_time_dt) AS min_dt,
        MAX(open_time_dt) AS max_dt
    FROM kline_data
    WHERE symbol = %s AND interval_type = %s
"""


def main():
    print("========== K 线数据下载完整性检查 ==========\n")
    print(f"配置: 交易对={DOWNLOAD_SYMBOLS}, 周期={DOWNLOAD_INTERVALS}, 回溯年数={DOWNLOAD_HISTORY_YEARS}\n")

    MySQLClient.init_tables()
    now_utc = datetime.utcnow()
    # 认为「已更新到最近」的阈值：最新 K 线距今不超过 2 个周期（按最大周期 1d 算 2 天）
    lag_ok = timedelta(days=2)
    all_ok = True

    for symbol in DOWNLOAD_SYMBOLS:
        for interval in DOWNLOAD_INTERVALS:
            row = MySQLClient.execute_query(SQL, (symbol, interval))
            if not row or row[0]['cnt'] == 0:
                print(f"[缺失] {symbol} {interval}: 无数据")
                all_ok = False
                continue

            r = row[0]
            cnt = r['cnt']
            min_dt = r['min_dt']
            max_dt = r['max_dt']
            # 处理 datetime 可能带 tzinfo 的情况
            if hasattr(max_dt, 'replace') and max_dt.tzinfo is not None:
                max_dt_naive = max_dt.replace(tzinfo=None)
            else:
                max_dt_naive = max_dt
            lag = now_utc - max_dt_naive
            expected = EXPECTED_BARS.get(interval, 0)
            pct = (cnt / expected * 100) if expected else 0
            status = "完整" if cnt >= expected * 0.95 and lag <= lag_ok else "不完整"
            if status != "完整":
                all_ok = False

            print(f"[{status}] {symbol} {interval}")
            print(f"    条数: {cnt} (预期约 {expected}, {pct:.1f}%)")
            print(f"    范围: {min_dt} ~ {max_dt}")
            print(f"    最新距现在: {lag}")
            print()

    if all_ok:
        print("总体: 所有配置的 K 线数据已完整且更新到最近。")
    else:
        print("总体: 存在缺失或未更新到最近，请继续运行 run_downloader.py。")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
