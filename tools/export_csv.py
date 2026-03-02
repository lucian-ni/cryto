"""
将 MySQL 中的 K 线数据导出为 CSV 文件
每个 (symbol, interval) 导出为一个独立的 CSV 文件
输出目录: 项目根目录下的 exports/
"""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import DOWNLOAD_SYMBOLS, DOWNLOAD_INTERVALS
from src.db.mysql_client import MySQLClient

EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')

QUERY_SQL = """
    SELECT 
        symbol, interval_type, open_time, open_time_dt,
        open_price, high_price, low_price, close_price,
        volume, close_time, quote_volume, trades_count,
        taker_buy_volume, taker_buy_quote_volume
    FROM kline_data
    WHERE symbol = %s AND interval_type = %s
    ORDER BY open_time ASC
"""

CSV_HEADER = [
    'symbol', 'interval_type', 'open_time', 'open_time_dt',
    'open_price', 'high_price', 'low_price', 'close_price',
    'volume', 'close_time', 'quote_volume', 'trades_count',
    'taker_buy_volume', 'taker_buy_quote_volume'
]


def export_to_csv(symbol, interval):
    """导出单个 symbol+interval 的数据到 CSV"""
    rows = MySQLClient.execute_query(QUERY_SQL, (symbol, interval))
    if not rows:
        print(f"[跳过] {symbol} {interval}: 无数据")
        return 0

    filename = f"{symbol}_{interval}.csv"
    filepath = os.path.join(EXPORT_DIR, filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[完成] {symbol} {interval}: {len(rows)} 条 -> {filepath}")
    return len(rows)


def main():
    print("========== 导出 K 线数据为 CSV ==========\n")

    os.makedirs(EXPORT_DIR, exist_ok=True)
    print(f"输出目录: {EXPORT_DIR}\n")

    total = 0
    for symbol in DOWNLOAD_SYMBOLS:
        for interval in DOWNLOAD_INTERVALS:
            total += export_to_csv(symbol, interval)

    print(f"\n导出完成，共计 {total} 条数据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
