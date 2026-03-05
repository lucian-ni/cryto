"""
赫斯特指数滑动窗口统计分析模块

固定窗口大小和K线周期，对全部历史数据做滑动窗口计算，
收集每个窗口的赫斯特指数值，最终输出统计报告。
"""
import numpy as np
from scipy import stats as scipy_stats

from config.settings import (
    DOWNLOAD_SYMBOLS,
    HURST_STATS_WINDOW_SIZE, HURST_STATS_INTERVAL,
    HURST_STATS_STEP_SIZE, HURST_STATS_RECENT_COUNT,
    HURST_STATS_RECENT_THRESHOLD, HURST_STATS_PROGRESS_INTERVAL
)
from src.lib_resource import (
    COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_CYAN, COLOR_RESET,
    TAG_HURST_STATS,
    MSG_HURST_STATS_LOAD_DATA, MSG_HURST_STATS_DATA_LOADED,
    MSG_HURST_STATS_DATA_NOT_ENOUGH, MSG_HURST_STATS_CALC_START,
    MSG_HURST_STATS_PROGRESS, MSG_HURST_STATS_WINDOW_ERROR,
    MSG_HURST_STATS_CALC_DONE, MSG_HURST_STATS_SAVING_DETAIL,
    MSG_HURST_STATS_SAVING_SUMMARY, MSG_HURST_STATS_SAVED,
    MSG_HURST_STATS_ERROR, MSG_HURST_STATS_ALL_DONE,
    HURST_STATS_VERDICT_HIGHER, HURST_STATS_VERDICT_LOWER,
    HURST_STATS_VERDICT_STABLE,
    HURST_THRESHOLD_HIGH, HURST_THRESHOLD_LOW,
    HURST_TREND_PERSISTENT, HURST_RANDOM_WALK, HURST_MEAN_REVERTING
)
from src.strategy.hurst_exponent import compute_hurst_exponent, interpret_hurst
from src.db.mysql_client import MySQLClient


# 查询全部K线收盘价（按时间正序）
QUERY_ALL_CLOSE_PRICE_SQL = """
    SELECT open_time_dt, close_price
    FROM kline_data
    WHERE symbol = %s AND interval_type = %s
    ORDER BY open_time ASC
"""

# 批量插入窗口明细（重复时更新）
INSERT_WINDOW_DETAIL_SQL = """
    INSERT INTO hurst_window_detail
    (symbol, interval_type, window_size, window_index, hurst_value,
     interpretation, window_start_time, window_end_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        hurst_value = VALUES(hurst_value),
        interpretation = VALUES(interpretation),
        window_start_time = VALUES(window_start_time),
        window_end_time = VALUES(window_end_time),
        created_at = CURRENT_TIMESTAMP
"""

# 插入/更新统计汇总
INSERT_STATS_SUMMARY_SQL = """
    INSERT INTO hurst_stats_summary
    (symbol, interval_type, window_size, step_size, total_windows, valid_windows,
     data_start_time, data_end_time,
     hurst_mean, hurst_median, hurst_std, hurst_min, hurst_max,
     hurst_q25, hurst_q75, hurst_skewness, hurst_kurtosis,
     pct_trend, pct_random, pct_mean_revert,
     recent_mean, recent_verdict)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        total_windows = VALUES(total_windows),
        valid_windows = VALUES(valid_windows),
        data_start_time = VALUES(data_start_time),
        data_end_time = VALUES(data_end_time),
        hurst_mean = VALUES(hurst_mean),
        hurst_median = VALUES(hurst_median),
        hurst_std = VALUES(hurst_std),
        hurst_min = VALUES(hurst_min),
        hurst_max = VALUES(hurst_max),
        hurst_q25 = VALUES(hurst_q25),
        hurst_q75 = VALUES(hurst_q75),
        hurst_skewness = VALUES(hurst_skewness),
        hurst_kurtosis = VALUES(hurst_kurtosis),
        pct_trend = VALUES(pct_trend),
        pct_random = VALUES(pct_random),
        pct_mean_revert = VALUES(pct_mean_revert),
        recent_mean = VALUES(recent_mean),
        recent_verdict = VALUES(recent_verdict),
        created_at = CURRENT_TIMESTAMP
"""

# 在保存明细前，先清除该 symbol 的旧明细（避免步长变化后残留旧数据）
DELETE_OLD_DETAIL_SQL = """
    DELETE FROM hurst_window_detail
    WHERE symbol = %s AND interval_type = %s AND window_size = %s
"""


class HurstStatsCalculator:
    """赫斯特指数滑动窗口统计计算器"""

    def __init__(self):
        self.window_size = HURST_STATS_WINDOW_SIZE
        self.interval = HURST_STATS_INTERVAL
        self.step_size = HURST_STATS_STEP_SIZE

    def _load_prices(self, symbol):
        """
        加载指定交易对的全部K线收盘价数据
        :return: (open_time_dt列表, prices numpy数组) 或 (None, None) 数据不足时
        """
        print(f"{TAG_HURST_STATS} "
              f"{MSG_HURST_STATS_LOAD_DATA.format(symbol=symbol, interval=self.interval)}")

        rows = MySQLClient.execute_query(
            QUERY_ALL_CLOSE_PRICE_SQL, (symbol, self.interval)
        )

        if len(rows) < self.window_size:
            print(f"{TAG_HURST_STATS} {COLOR_YELLOW}"
                  f"{MSG_HURST_STATS_DATA_NOT_ENOUGH.format(symbol=symbol, interval=self.interval, need=self.window_size, actual=len(rows))}"
                  f"{COLOR_RESET}")
            return None, None

        times = [row['open_time_dt'] for row in rows]
        prices = np.array([float(row['close_price']) for row in rows])

        print(f"{TAG_HURST_STATS} "
              f"{MSG_HURST_STATS_DATA_LOADED.format(count=len(prices), start=times[0], end=times[-1])}")

        return times, prices

    def _sliding_window_calculate(self, symbol, times, prices):
        """
        滑动窗口计算所有赫斯特指数
        :return: (window_results列表, total_windows总窗口数)
        """
        n = len(prices)
        total_windows = (n - self.window_size) // self.step_size + 1

        print(f"{TAG_HURST_STATS} "
              f"{MSG_HURST_STATS_CALC_START.format(window=self.window_size, step=self.step_size, total=total_windows)}")

        window_results = []
        for i in range(total_windows):
            start_idx = i * self.step_size
            end_idx = start_idx + self.window_size
            window_prices = prices[start_idx:end_idx]
            window_start_time = times[start_idx]
            window_end_time = times[end_idx - 1]

            try:
                hurst_value = compute_hurst_exponent(window_prices, verbose=False)
                interpretation = interpret_hurst(hurst_value)
                window_results.append({
                    'window_index': i,
                    'hurst_value': hurst_value,
                    'interpretation': interpretation,
                    'window_start_time': window_start_time,
                    'window_end_time': window_end_time,
                })
            except ValueError as e:
                print(f"{TAG_HURST_STATS} {COLOR_YELLOW}"
                      f"{MSG_HURST_STATS_WINDOW_ERROR.format(index=i, error=str(e))}"
                      f"{COLOR_RESET}")

            # 定期打印进度
            completed = i + 1
            if completed % HURST_STATS_PROGRESS_INTERVAL == 0 or completed == total_windows:
                pct = completed / total_windows * 100
                print(f"{TAG_HURST_STATS} "
                      f"{MSG_HURST_STATS_PROGRESS.format(current=completed, total=total_windows, pct=pct)}")

        print(f"{TAG_HURST_STATS} {COLOR_GREEN}"
              f"{MSG_HURST_STATS_CALC_DONE.format(valid=len(window_results), total=total_windows)}"
              f"{COLOR_RESET}")

        return window_results, total_windows

    def _compute_statistics(self, hurst_values):
        """
        对赫斯特指数数组计算统计量
        :param hurst_values: numpy数组
        :return: 统计结果字典
        """
        stats = {
            'mean': float(np.mean(hurst_values)),
            'median': float(np.median(hurst_values)),
            'std': float(np.std(hurst_values, ddof=1)),
            'min': float(np.min(hurst_values)),
            'max': float(np.max(hurst_values)),
            'q25': float(np.percentile(hurst_values, 25)),
            'q75': float(np.percentile(hurst_values, 75)),
            'skewness': float(scipy_stats.skew(hurst_values)),
            'kurtosis': float(scipy_stats.kurtosis(hurst_values)),
        }

        total = len(hurst_values)
        count_trend = int(np.sum(hurst_values > HURST_THRESHOLD_HIGH))
        count_random = int(np.sum(
            (hurst_values >= HURST_THRESHOLD_LOW) & (hurst_values <= HURST_THRESHOLD_HIGH)
        ))
        count_mean_revert = int(np.sum(hurst_values < HURST_THRESHOLD_LOW))

        stats['pct_trend'] = round(count_trend / total * 100, 2)
        stats['pct_random'] = round(count_random / total * 100, 2)
        stats['pct_mean_revert'] = round(count_mean_revert / total * 100, 2)
        stats['count_trend'] = count_trend
        stats['count_random'] = count_random
        stats['count_mean_revert'] = count_mean_revert

        # 近期 vs 历史
        recent_count = min(HURST_STATS_RECENT_COUNT, total)
        recent_values = hurst_values[-recent_count:]
        stats['recent_mean'] = float(np.mean(recent_values))

        diff = stats['recent_mean'] - stats['mean']
        if diff > HURST_STATS_RECENT_THRESHOLD:
            stats['recent_verdict'] = HURST_STATS_VERDICT_HIGHER
        elif diff < -HURST_STATS_RECENT_THRESHOLD:
            stats['recent_verdict'] = HURST_STATS_VERDICT_LOWER
        else:
            stats['recent_verdict'] = HURST_STATS_VERDICT_STABLE

        return stats

    def _print_report(self, symbol, total_windows, valid_count,
                      data_start, data_end, stats):
        """打印统计报告到控制台"""
        separator = '=' * 60
        line = '-' * 60

        print(f"\n{separator}")
        print(f" {symbol} {self.interval} 赫斯特指数滑动窗口统计报告")
        print(f" 数据范围：{data_start} ~ {data_end}")
        print(f" 窗口大小：{self.window_size} | 滑动步长：{self.step_size} | "
              f"总窗口数：{total_windows} | 有效：{valid_count}")
        print(separator)

        print(f" 【基础统计】")
        print(f"   均值:    {stats['mean']:.4f}   中位数: {stats['median']:.4f}")
        print(f"   标准差:  {stats['std']:.4f}   "
              f"最小值: {stats['min']:.4f}   最大值: {stats['max']:.4f}")
        print(f"   Q25:     {stats['q25']:.4f}   Q75:    {stats['q75']:.4f}")
        print(f"   偏度:    {stats['skewness']:.4f}   峰度:   {stats['kurtosis']:.4f}")
        print(line)

        print(f" 【状态分布】")
        print(f"   趋势持续(H>{HURST_THRESHOLD_HIGH}):   "
              f"{stats['pct_trend']:5.1f}%  ({stats['count_trend']}个窗口)")
        print(f"   随机游走({HURST_THRESHOLD_LOW}~{HURST_THRESHOLD_HIGH}): "
              f"{stats['pct_random']:5.1f}%  ({stats['count_random']}个窗口)")
        print(f"   均值回归(H<{HURST_THRESHOLD_LOW}):   "
              f"{stats['pct_mean_revert']:5.1f}%  ({stats['count_mean_revert']}个窗口)")
        print(line)

        recent_count = min(HURST_STATS_RECENT_COUNT, valid_count)
        print(f" 【近期 vs 历史】")
        print(f"   历史均值: {stats['mean']:.4f}   "
              f"近期均值(最近{recent_count}个窗口): {stats['recent_mean']:.4f}")
        print(f"   判断: {stats['recent_verdict']}")
        print(f"{separator}\n")

    def _save_detail(self, symbol, window_results):
        """保存窗口明细到数据库"""
        count = len(window_results)
        print(f"{TAG_HURST_STATS} "
              f"{MSG_HURST_STATS_SAVING_DETAIL.format(count=count)}")

        # 先清除旧数据
        MySQLClient.execute_update(
            DELETE_OLD_DETAIL_SQL, (symbol, self.interval, self.window_size)
        )

        params_list = [
            (symbol, self.interval, self.window_size,
             r['window_index'], round(r['hurst_value'], 6),
             r['interpretation'], r['window_start_time'], r['window_end_time'])
            for r in window_results
        ]
        MySQLClient.execute_many(INSERT_WINDOW_DETAIL_SQL, params_list)

    def _save_summary(self, symbol, total_windows, valid_count,
                      data_start, data_end, stats):
        """保存统计汇总到数据库"""
        print(f"{TAG_HURST_STATS} {MSG_HURST_STATS_SAVING_SUMMARY}")

        MySQLClient.execute_update(INSERT_STATS_SUMMARY_SQL, (
            symbol, self.interval, self.window_size, self.step_size,
            total_windows, valid_count, data_start, data_end,
            round(stats['mean'], 6), round(stats['median'], 6),
            round(stats['std'], 6), round(stats['min'], 6),
            round(stats['max'], 6), round(stats['q25'], 6),
            round(stats['q75'], 6), round(stats['skewness'], 6),
            round(stats['kurtosis'], 6),
            stats['pct_trend'], stats['pct_random'], stats['pct_mean_revert'],
            round(stats['recent_mean'], 6), stats['recent_verdict']
        ))

        print(f"{TAG_HURST_STATS} {COLOR_GREEN}{MSG_HURST_STATS_SAVED}{COLOR_RESET}")

    def analyze_symbol(self, symbol):
        """
        单个交易对的完整分析流程：
        加载数据 → 滑动窗口计算 → 统计分析 → 保存结果 → 打印报告
        """
        print(f"\n{TAG_HURST_STATS} {COLOR_CYAN}开始分析 {symbol}{COLOR_RESET}")

        # 第一步：加载全部K线数据
        times, prices = self._load_prices(symbol)
        if times is None:
            return

        # 第二步：滑动窗口计算
        window_results, total_windows = self._sliding_window_calculate(
            symbol, times, prices
        )

        if not window_results:
            print(f"{TAG_HURST_STATS} {COLOR_YELLOW}没有有效的计算结果，跳过{COLOR_RESET}")
            return

        # 第三步：统计分析
        hurst_values = np.array([r['hurst_value'] for r in window_results])
        stats = self._compute_statistics(hurst_values)

        data_start = times[0]
        data_end = times[-1]
        valid_count = len(window_results)

        # 第四步：保存明细和汇总
        self._save_detail(symbol, window_results)
        self._save_summary(symbol, total_windows, valid_count,
                           data_start, data_end, stats)

        # 第五步：打印统计报告
        self._print_report(symbol, total_windows, valid_count,
                           data_start, data_end, stats)

    def run(self):
        """
        主流程：遍历所有配置的交易对进行统计分析
        """
        print(f"{TAG_HURST_STATS} {COLOR_CYAN}开始赫斯特指数滑动窗口统计分析{COLOR_RESET}")
        print(f"{TAG_HURST_STATS} 交易对列表：{DOWNLOAD_SYMBOLS}")
        print(f"{TAG_HURST_STATS} K线周期：{self.interval}")
        print(f"{TAG_HURST_STATS} 窗口大小：{self.window_size}，滑动步长：{self.step_size}")

        for symbol in DOWNLOAD_SYMBOLS:
            try:
                self.analyze_symbol(symbol)
            except Exception as e:
                print(f"{TAG_HURST_STATS} {COLOR_RED}"
                      f"{MSG_HURST_STATS_ERROR.format(error=str(e))}{COLOR_RESET}")

        print(f"{TAG_HURST_STATS} {COLOR_GREEN}{MSG_HURST_STATS_ALL_DONE}{COLOR_RESET}")
