"""
币安K线数据下载器
负责从币安API下载K线数据并存储到MySQL
"""
import time
from datetime import datetime, timedelta

import requests

from config.settings import (
    BINANCE_BASE_URL, BINANCE_KLINE_ENDPOINT, BINANCE_KLINE_LIMIT,
    BINANCE_REQUEST_INTERVAL_SEC, DOWNLOAD_SYMBOLS, DOWNLOAD_INTERVALS,
    DOWNLOAD_HISTORY_YEARS, UPDATE_POLL_INTERVAL_SEC
)
from src.lib_resource import (
    COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_CYAN, COLOR_RESET, TAG_DOWNLOADER,
    MSG_DOWNLOAD_START, MSG_DOWNLOAD_SYMBOL_INTERVAL, MSG_DOWNLOAD_BATCH,
    MSG_DOWNLOAD_BATCH_DONE, MSG_DOWNLOAD_SAVE, MSG_DOWNLOAD_SAVE_DONE,
    MSG_DOWNLOAD_SYMBOL_DONE, MSG_DOWNLOAD_ALL_DONE, MSG_DOWNLOAD_UPDATE_START,
    MSG_DOWNLOAD_UPDATE_DONE, MSG_DOWNLOAD_WAIT, MSG_DOWNLOAD_NO_DATA,
    MSG_DOWNLOAD_ERROR, MSG_DOWNLOAD_RETRY, MSG_DOWNLOAD_RESUME,
    MSG_DOWNLOAD_FRESH, MSG_DOWNLOAD_LATEST
)
from src.db.mysql_client import MySQLClient


# 批量插入K线数据的SQL（使用IGNORE避免重复插入）
INSERT_KLINE_SQL = """
    INSERT IGNORE INTO kline_data 
    (symbol, interval_type, open_time, open_time_dt, open_price, high_price, 
     low_price, close_price, volume, close_time, quote_volume, trades_count, 
     taker_buy_volume, taker_buy_quote_volume)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# 查询某交易对某周期最新的开盘时间
QUERY_LATEST_OPEN_TIME_SQL = """
    SELECT MAX(open_time) as latest_open_time 
    FROM kline_data 
    WHERE symbol = %s AND interval_type = %s
"""

# 错误重试最大次数
MAX_RETRY_COUNT = 3
# 错误重试等待时间（秒）
RETRY_WAIT_SEC = 10
# 每年天数（用于计算历史数据起始时间）
DAYS_PER_YEAR = 365
# 毫秒与秒的转换倍数
MS_PER_SEC = 1000
# HTTP请求超时时间（秒）
HTTP_TIMEOUT_SEC = 30


class BinanceDownloader:
    """币安K线数据下载器"""

    def __init__(self):
        """初始化下载器，创建HTTP会话"""
        print(f"{TAG_DOWNLOADER} 初始化HTTP会话...")
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'CrytoDataDownloader/1.0'
        })
        print(f"{TAG_DOWNLOADER} HTTP会话初始化完成")

    def _fetch_klines(self, symbol, interval, start_time, end_time=None):
        """
        从币安API获取K线数据
        :param symbol: 交易对，如BTCUSDT
        :param interval: K线周期，如1h
        :param start_time: 起始时间戳（毫秒）
        :param end_time: 结束时间戳（毫秒），可选
        :return: K线数据列表
        """
        url = f"{BINANCE_BASE_URL}{BINANCE_KLINE_ENDPOINT}"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_time,
            'limit': BINANCE_KLINE_LIMIT
        }
        if end_time is not None:
            params['endTime'] = end_time

        for retry in range(MAX_RETRY_COUNT):
            try:
                print(f"{TAG_DOWNLOADER} 发起API请求：symbol={symbol}, interval={interval}, "
                      f"startTime={start_time}")
                response = self.session.get(url, params=params, timeout=HTTP_TIMEOUT_SEC)
                response.raise_for_status()
                data = response.json()
                print(f"{TAG_DOWNLOADER} API请求成功，返回 {len(data)} 条数据")
                return data
            except Exception as e:
                print(f"{TAG_DOWNLOADER} {COLOR_RED}"
                      f"{MSG_DOWNLOAD_ERROR.format(error=str(e))}{COLOR_RESET}")
                if retry < MAX_RETRY_COUNT - 1:
                    print(f"{TAG_DOWNLOADER} {COLOR_YELLOW}"
                          f"{MSG_DOWNLOAD_RETRY.format(seconds=RETRY_WAIT_SEC)}{COLOR_RESET}")
                    time.sleep(RETRY_WAIT_SEC)
                else:
                    raise

    def _parse_klines(self, symbol, interval, raw_klines):
        """
        解析币安返回的原始K线数据为数据库插入参数
        币安K线返回格式：
        [开盘时间, 开盘价, 最高价, 最低价, 收盘价, 成交量,
         收盘时间, 成交额, 成交笔数, 主动买入成交量, 主动买入成交额, 忽略]
        :param symbol: 交易对
        :param interval: K线周期
        :param raw_klines: 币安原始返回数据
        :return: 参数元组列表
        """
        params_list = []
        for kline in raw_klines:
            open_time = int(kline[0])
            open_time_dt = datetime.utcfromtimestamp(open_time / MS_PER_SEC)
            params_list.append((
                symbol,
                interval,
                open_time,
                open_time_dt,
                kline[1],       # open_price
                kline[2],       # high_price
                kline[3],       # low_price
                kline[4],       # close_price
                kline[5],       # volume
                int(kline[6]),  # close_time
                kline[7],       # quote_volume
                int(kline[8]),  # trades_count
                kline[9],       # taker_buy_volume
                kline[10],      # taker_buy_quote_volume
            ))
        return params_list

    def _save_klines(self, params_list):
        """
        批量保存K线数据到数据库
        :param params_list: 参数元组列表
        :return: 影响行数
        """
        if not params_list:
            return 0
        count = len(params_list)
        print(f"{TAG_DOWNLOADER} {MSG_DOWNLOAD_SAVE.format(count=count)}")
        affected = MySQLClient.execute_many(INSERT_KLINE_SQL, params_list)
        print(f"{TAG_DOWNLOADER} {COLOR_GREEN}{MSG_DOWNLOAD_SAVE_DONE.format(count=affected)}{COLOR_RESET}")
        return affected

    def _get_latest_open_time(self, symbol, interval):
        """
        查询数据库中某交易对某周期最新的开盘时间
        :param symbol: 交易对
        :param interval: K线周期
        :return: 最新开盘时间戳（毫秒），无数据时返回None
        """
        print(f"{TAG_DOWNLOADER} 查询 {symbol} {interval} 数据库中最新数据时间...")
        result = MySQLClient.execute_query(QUERY_LATEST_OPEN_TIME_SQL, (symbol, interval))
        if result and result[0]['latest_open_time'] is not None:
            latest = int(result[0]['latest_open_time'])
            latest_dt = datetime.utcfromtimestamp(latest / MS_PER_SEC)
            print(f"{TAG_DOWNLOADER} {symbol} {interval} 数据库最新数据时间：{latest_dt}")
            return latest
        print(f"{TAG_DOWNLOADER} {symbol} {interval} 数据库中无历史数据")
        return None

    def download_history(self, symbol, interval):
        """
        下载某交易对某周期的历史K线数据（从3年前至今）
        支持断点续传：若数据库已有数据，则从最新记录之后继续下载
        :param symbol: 交易对
        :param interval: K线周期
        :return: 总下载条数
        """
        print(f"{TAG_DOWNLOADER} {COLOR_CYAN}"
              f"{MSG_DOWNLOAD_SYMBOL_INTERVAL.format(symbol=symbol, interval=interval)}{COLOR_RESET}")

        # 检查数据库是否已有数据，有则从最新数据之后继续下载
        latest_open_time = self._get_latest_open_time(symbol, interval)
        if latest_open_time is not None:
            # 从最新记录的下一个时间点开始（+1毫秒）
            start_time = latest_open_time + 1
            resume_dt = datetime.utcfromtimestamp(start_time / MS_PER_SEC)
            print(f"{TAG_DOWNLOADER} {MSG_DOWNLOAD_RESUME.format(time=resume_dt)}")
        else:
            # 从指定年数前开始下载
            start_dt = datetime.utcnow() - timedelta(days=DOWNLOAD_HISTORY_YEARS * DAYS_PER_YEAR)
            start_time = int(start_dt.timestamp() * MS_PER_SEC)
            print(f"{TAG_DOWNLOADER} {MSG_DOWNLOAD_FRESH.format(time=start_dt)}")

        end_time = int(datetime.utcnow().timestamp() * MS_PER_SEC)
        total_count = 0
        batch_num = 0

        while start_time < end_time:
            batch_num += 1
            start_dt_str = datetime.utcfromtimestamp(start_time / MS_PER_SEC).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{TAG_DOWNLOADER} {MSG_DOWNLOAD_BATCH.format(batch=batch_num, start_time=start_dt_str)}")

            # 从币安API获取数据
            raw_klines = self._fetch_klines(symbol, interval, start_time, end_time)

            if not raw_klines:
                print(f"{TAG_DOWNLOADER} {COLOR_YELLOW}"
                      f"{MSG_DOWNLOAD_NO_DATA.format(symbol=symbol, interval=interval)}{COLOR_RESET}")
                break

            print(f"{TAG_DOWNLOADER} {MSG_DOWNLOAD_BATCH_DONE.format(batch=batch_num, count=len(raw_klines))}")

            # 解析并保存数据
            params_list = self._parse_klines(symbol, interval, raw_klines)
            self._save_klines(params_list)
            total_count += len(raw_klines)

            # 更新下一批次的起始时间（最后一条的开盘时间+1毫秒）
            start_time = int(raw_klines[-1][0]) + 1

            # 如果返回数据少于limit，说明已经到最新了
            if len(raw_klines) < BINANCE_KLINE_LIMIT:
                print(f"{TAG_DOWNLOADER} 本批次返回数据量({len(raw_klines)})小于"
                      f"limit({BINANCE_KLINE_LIMIT})，该周期数据已下载完毕")
                break

            # 请求间隔，避免触发频率限制
            print(f"{TAG_DOWNLOADER} 等待 {BINANCE_REQUEST_INTERVAL_SEC} 秒后继续下一批次...")
            time.sleep(BINANCE_REQUEST_INTERVAL_SEC)

        print(f"{TAG_DOWNLOADER} {COLOR_GREEN}"
              f"{MSG_DOWNLOAD_SYMBOL_DONE.format(symbol=symbol, interval=interval, total=total_count)}"
              f"{COLOR_RESET}")
        return total_count

    def download_all_history(self):
        """下载所有交易对所有周期的历史数据"""
        print(f"{TAG_DOWNLOADER} {COLOR_CYAN}{MSG_DOWNLOAD_START}{COLOR_RESET}")
        print(f"{TAG_DOWNLOADER} 交易对列表：{DOWNLOAD_SYMBOLS}")
        print(f"{TAG_DOWNLOADER} K线周期列表：{DOWNLOAD_INTERVALS}")
        print(f"{TAG_DOWNLOADER} 历史数据回溯年数：{DOWNLOAD_HISTORY_YEARS}")

        for symbol in DOWNLOAD_SYMBOLS:
            for interval in DOWNLOAD_INTERVALS:
                self.download_history(symbol, interval)
                # 每对交易对/周期之间稍等一下，避免过于频繁
                time.sleep(BINANCE_REQUEST_INTERVAL_SEC)

        print(f"{TAG_DOWNLOADER} {COLOR_GREEN}{MSG_DOWNLOAD_ALL_DONE}{COLOR_RESET}")

    def incremental_update(self):
        """增量更新所有交易对所有周期的最新数据"""
        print(f"{TAG_DOWNLOADER} {MSG_DOWNLOAD_UPDATE_START}")

        for symbol in DOWNLOAD_SYMBOLS:
            for interval in DOWNLOAD_INTERVALS:
                latest_open_time = self._get_latest_open_time(symbol, interval)

                if latest_open_time is None:
                    # 如果没有历史数据，执行全量下载
                    print(f"{TAG_DOWNLOADER} {symbol} {interval} 无历史数据，执行全量下载")
                    self.download_history(symbol, interval)
                    continue

                # 从最新记录之后开始获取增量数据
                start_time = latest_open_time + 1
                end_time = int(datetime.utcnow().timestamp() * MS_PER_SEC)

                if start_time >= end_time:
                    print(f"{TAG_DOWNLOADER} {COLOR_YELLOW}"
                          f"{MSG_DOWNLOAD_LATEST.format(symbol=symbol, interval=interval)}{COLOR_RESET}")
                    continue

                print(f"{TAG_DOWNLOADER} {symbol} {interval} 开始增量获取数据...")
                raw_klines = self._fetch_klines(symbol, interval, start_time, end_time)
                new_count = 0
                if raw_klines:
                    params_list = self._parse_klines(symbol, interval, raw_klines)
                    self._save_klines(params_list)
                    new_count = len(raw_klines)

                print(f"{TAG_DOWNLOADER} {COLOR_GREEN}"
                      f"{MSG_DOWNLOAD_UPDATE_DONE.format(symbol=symbol, interval=interval, count=new_count)}"
                      f"{COLOR_RESET}")

                # 请求间隔
                time.sleep(BINANCE_REQUEST_INTERVAL_SEC)

    def run_forever(self):
        """
        持续运行模式：
        第一步：下载全量历史数据（支持断点续传）
        第二步：进入增量更新循环，定时获取最新数据
        """
        # 第一步：下载全量历史数据
        print(f"{TAG_DOWNLOADER} ===== 第一步：下载全量历史数据 =====")
        self.download_all_history()

        # 第二步：循环增量更新
        print(f"{TAG_DOWNLOADER} ===== 第二步：进入增量更新循环 =====")
        while True:
            print(f"{TAG_DOWNLOADER} {COLOR_YELLOW}"
                  f"{MSG_DOWNLOAD_WAIT.format(seconds=UPDATE_POLL_INTERVAL_SEC)}{COLOR_RESET}")
            time.sleep(UPDATE_POLL_INTERVAL_SEC)
            try:
                self.incremental_update()
            except Exception as e:
                print(f"{TAG_DOWNLOADER} {COLOR_RED}"
                      f"{MSG_DOWNLOAD_ERROR.format(error=str(e))}{COLOR_RESET}")
                print(f"{TAG_DOWNLOADER} {COLOR_YELLOW}"
                      f"{MSG_DOWNLOAD_RETRY.format(seconds=RETRY_WAIT_SEC)}{COLOR_RESET}")
                time.sleep(RETRY_WAIT_SEC)

