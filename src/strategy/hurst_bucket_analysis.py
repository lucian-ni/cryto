"""
赫斯特指数分桶回测分析模块

对滑动窗口计算出的赫斯特指数按区间分桶，结合趋势方向判断（做多/做空），
统计每个桶内未来N根K线的收益均值、胜率和最大回撤。

趋势判断规则：最近 TREND_LOOKBACK 根K线的收益率之和 > 0 则做多，否则做空。
"""
import numpy as np
from collections import defaultdict

from config.settings import (
    DOWNLOAD_SYMBOLS,
    HURST_BUCKET_EDGES, HURST_BUCKET_TREND_LOOKBACK,
    HURST_BUCKET_FORWARD_BARS, HURST_BUCKET_INTERVAL,
    HURST_BUCKET_WINDOW_SIZE, HURST_BUCKET_STEP_SIZE,
    HURST_BUCKET_PROGRESS_INTERVAL
)
from src.lib_resource import (
    COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_CYAN, COLOR_RESET,
    TAG_HURST_BUCKET,
    MSG_HURST_BUCKET_LOAD_DATA, MSG_HURST_BUCKET_DATA_LOADED,
    MSG_HURST_BUCKET_DATA_NOT_ENOUGH, MSG_HURST_BUCKET_CALC_HURST,
    MSG_HURST_BUCKET_CALC_HURST_DONE, MSG_HURST_BUCKET_ANALYZE_START,
    MSG_HURST_BUCKET_PROGRESS, MSG_HURST_BUCKET_WINDOW_SKIP_TREND,
    MSG_HURST_BUCKET_WINDOW_SKIP_FUTURE, MSG_HURST_BUCKET_WINDOW_SKIP_RANGE,
    MSG_HURST_BUCKET_ANALYZE_DONE, MSG_HURST_BUCKET_SAVING,
    MSG_HURST_BUCKET_SAVED, MSG_HURST_BUCKET_ERROR,
    MSG_HURST_BUCKET_ALL_DONE, MSG_HURST_BUCKET_EMPTY,
    DIRECTION_LONG, DIRECTION_SHORT
)
from src.strategy.hurst_exponent import compute_hurst_exponent
from src.db.mysql_client import MySQLClient


QUERY_ALL_CLOSE_PRICE_SQL = """
    SELECT open_time_dt, close_price
    FROM kline_data
    WHERE symbol = %s AND interval_type = %s
    ORDER BY open_time ASC
"""

DELETE_OLD_BUCKET_STATS_SQL = """
    DELETE FROM hurst_bucket_stats
    WHERE symbol = %s AND interval_type = %s AND window_size = %s
"""

INSERT_BUCKET_STATS_SQL = """
    INSERT INTO hurst_bucket_stats
    (symbol, interval_type, window_size, bucket_label, bucket_low, bucket_high,
     sample_count, long_count, short_count,
     avg_return_5, avg_return_10, win_rate_5, win_rate_10,
     avg_max_dd_5, avg_max_dd_10, worst_max_dd_5, worst_max_dd_10)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        sample_count = VALUES(sample_count),
        long_count = VALUES(long_count),
        short_count = VALUES(short_count),
        avg_return_5 = VALUES(avg_return_5),
        avg_return_10 = VALUES(avg_return_10),
        win_rate_5 = VALUES(win_rate_5),
        win_rate_10 = VALUES(win_rate_10),
        avg_max_dd_5 = VALUES(avg_max_dd_5),
        avg_max_dd_10 = VALUES(avg_max_dd_10),
        worst_max_dd_5 = VALUES(worst_max_dd_5),
        worst_max_dd_10 = VALUES(worst_max_dd_10),
        created_at = CURRENT_TIMESTAMP
"""


class HurstBucketAnalyzer:
    """赫斯特指数分桶回测分析器"""

    def __init__(self):
        self.interval = HURST_BUCKET_INTERVAL
        self.window_size = HURST_BUCKET_WINDOW_SIZE
        self.step_size = HURST_BUCKET_STEP_SIZE
        self.bucket_edges = HURST_BUCKET_EDGES
        self.trend_lookback = HURST_BUCKET_TREND_LOOKBACK
        self.forward_bars = HURST_BUCKET_FORWARD_BARS
        self.max_forward = max(self.forward_bars)

    def _build_bucket_labels(self):
        """
        根据分桶边界构建桶标签列表
        :return: [(label, low, high), ...] 的列表
        """
        buckets = []
        for i in range(len(self.bucket_edges) - 1):
            low = self.bucket_edges[i]
            high = self.bucket_edges[i + 1]
            label = f"{low}~{high}"
            buckets.append((label, low, high))
        return buckets

    def _get_bucket_label(self, hurst_value):
        """
        判断赫斯特值落在哪个桶，返回桶标签；不在任何桶内返回 None
        规则：左闭右开 [low, high)，最后一个桶右闭 [low, high]
        """
        num_buckets = len(self.bucket_edges) - 1
        for i in range(num_buckets):
            low = self.bucket_edges[i]
            high = self.bucket_edges[i + 1]
            is_last_bucket = (i == num_buckets - 1)
            if is_last_bucket:
                if low <= hurst_value <= high:
                    return f"{low}~{high}"
            else:
                if low <= hurst_value < high:
                    return f"{low}~{high}"
        return None

    def _load_prices(self, symbol):
        """
        加载指定交易对的全部K线收盘价数据
        :return: (open_time_dt列表, prices numpy数组) 或 (None, None) 数据不足时
        """
        print(f"{TAG_HURST_BUCKET} "
              f"{MSG_HURST_BUCKET_LOAD_DATA.format(symbol=symbol, interval=self.interval)}")

        rows = MySQLClient.execute_query(
            QUERY_ALL_CLOSE_PRICE_SQL, (symbol, self.interval)
        )

        min_required = self.window_size + self.trend_lookback + self.max_forward
        if len(rows) < min_required:
            print(f"{TAG_HURST_BUCKET} {COLOR_YELLOW}"
                  f"{MSG_HURST_BUCKET_DATA_NOT_ENOUGH.format(symbol=symbol, interval=self.interval, need=min_required, actual=len(rows))}"
                  f"{COLOR_RESET}")
            return None, None

        times = [row['open_time_dt'] for row in rows]
        prices = np.array([float(row['close_price']) for row in rows])

        print(f"{TAG_HURST_BUCKET} "
              f"{MSG_HURST_BUCKET_DATA_LOADED.format(count=len(prices), start=times[0], end=times[-1])}")

        return times, prices

    def _compute_hurst_per_window(self, prices):
        """
        滑动窗口计算每个窗口的赫斯特指数
        :return: (window_results列表, total_windows总数)
                 window_results 元素: {'window_index': i, 'end_idx': end_idx, 'hurst_value': float}
        """
        n = len(prices)
        total_windows = (n - self.window_size) // self.step_size + 1

        print(f"{TAG_HURST_BUCKET} "
              f"{MSG_HURST_BUCKET_CALC_HURST.format(window=self.window_size, step=self.step_size, total=total_windows)}")

        window_results = []
        for i in range(total_windows):
            start_idx = i * self.step_size
            end_idx = start_idx + self.window_size
            window_prices = prices[start_idx:end_idx]

            try:
                hurst_value = compute_hurst_exponent(window_prices, verbose=False)
                window_results.append({
                    'window_index': i,
                    'end_idx': end_idx,
                    'hurst_value': hurst_value,
                })
            except ValueError:
                pass

            completed = i + 1
            if completed % HURST_BUCKET_PROGRESS_INTERVAL == 0 or completed == total_windows:
                pct = completed / total_windows * 100
                print(f"{TAG_HURST_BUCKET} 赫斯特计算进度：{completed}/{total_windows} ({pct:.1f}%)")

        print(f"{TAG_HURST_BUCKET} {COLOR_GREEN}"
              f"{MSG_HURST_BUCKET_CALC_HURST_DONE.format(valid=len(window_results), total=total_windows)}"
              f"{COLOR_RESET}")

        return window_results, total_windows

    def _determine_direction(self, prices, end_idx):
        """
        判断趋势方向：最近 trend_lookback 根K线的对数收益率之和
        :param prices: 完整价格数组
        :param end_idx: 窗口结束位置（不含，即 prices[end_idx-1] 是窗口最后一根）
        :return: DIRECTION_LONG 或 DIRECTION_SHORT
        """
        lookback_start = end_idx - self.trend_lookback - 1
        recent_prices = prices[lookback_start:end_idx]
        recent_log_returns = np.diff(np.log(recent_prices))
        total_return = np.sum(recent_log_returns)
        return DIRECTION_LONG if total_return > 0 else DIRECTION_SHORT

    def _compute_forward_metrics(self, prices, end_idx, direction, forward_n):
        """
        计算未来 forward_n 根的方向收益和最大回撤
        :param prices: 完整价格数组
        :param end_idx: 窗口结束位置（prices[end_idx-1] 是当前价格）
        :param direction: DIRECTION_LONG 或 DIRECTION_SHORT
        :param forward_n: 向前看多少根
        :return: (directional_return, max_drawdown) 或 None（数据不足时）
        """
        current_price_idx = end_idx - 1
        future_end_idx = current_price_idx + forward_n + 1

        if future_end_idx > len(prices):
            return None

        current_price = prices[current_price_idx]
        future_prices = prices[current_price_idx:future_end_idx]

        cum_return = future_prices[-1] / current_price - 1

        if direction == DIRECTION_LONG:
            directional_return = cum_return
            equity_curve = future_prices / current_price
        else:
            directional_return = -cum_return
            equity_curve = 2.0 - future_prices / current_price

        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve - running_max) / running_max
        max_drawdown = float(abs(np.min(drawdowns)))

        return directional_return, max_drawdown

    def _analyze_buckets(self, prices, window_results):
        """
        对所有窗口进行分桶回测分析
        :return: bucket_data 字典 {label: {returns_5: [], returns_10: [], max_dd_5: [], max_dd_10: [], long_count, short_count}}
        """
        print(f"{TAG_HURST_BUCKET} "
              f"{MSG_HURST_BUCKET_ANALYZE_START.format(edges=self.bucket_edges)}")

        bucket_data = defaultdict(lambda: {
            'long_count': 0,
            'short_count': 0,
        })
        for fwd in self.forward_bars:
            for suffix in [f'returns_{fwd}', f'max_dd_{fwd}']:
                pass

        for label, _, _ in self._build_bucket_labels():
            bucket_data[label]['long_count'] = 0
            bucket_data[label]['short_count'] = 0
            for fwd in self.forward_bars:
                bucket_data[label][f'returns_{fwd}'] = []
                bucket_data[label][f'max_dd_{fwd}'] = []

        total = len(window_results)
        processed_count = 0
        valid_count = 0

        for idx, wr in enumerate(window_results):
            end_idx = wr['end_idx']
            hurst_value = wr['hurst_value']
            window_index = wr['window_index']

            processed_count += 1

            # 检查趋势回看数据是否充足
            if end_idx - self.trend_lookback - 1 < 0:
                print(f"{TAG_HURST_BUCKET} {COLOR_YELLOW}"
                      f"{MSG_HURST_BUCKET_WINDOW_SKIP_TREND.format(index=window_index)}"
                      f"{COLOR_RESET}")
                continue

            # 检查未来数据是否充足
            current_price_idx = end_idx - 1
            remain = len(prices) - current_price_idx - 1
            if remain < self.max_forward:
                print(f"{TAG_HURST_BUCKET} {COLOR_YELLOW}"
                      f"{MSG_HURST_BUCKET_WINDOW_SKIP_FUTURE.format(index=window_index, need=self.max_forward, remain=remain)}"
                      f"{COLOR_RESET}")
                continue

            # 分桶判断
            bucket_label = self._get_bucket_label(hurst_value)
            if bucket_label is None:
                continue

            # 判断趋势方向
            direction = self._determine_direction(prices, end_idx)

            if direction == DIRECTION_LONG:
                bucket_data[bucket_label]['long_count'] += 1
            else:
                bucket_data[bucket_label]['short_count'] += 1

            # 计算各观察期的收益和最大回撤
            all_forward_ok = True
            for fwd in self.forward_bars:
                result = self._compute_forward_metrics(prices, end_idx, direction, fwd)
                if result is None:
                    all_forward_ok = False
                    break
                dir_return, max_dd = result
                bucket_data[bucket_label][f'returns_{fwd}'].append(dir_return)
                bucket_data[bucket_label][f'max_dd_{fwd}'].append(max_dd)

            if all_forward_ok:
                valid_count += 1

            # 定期打印进度
            if processed_count % HURST_BUCKET_PROGRESS_INTERVAL == 0 or processed_count == total:
                pct = processed_count / total * 100
                print(f"{TAG_HURST_BUCKET} "
                      f"{MSG_HURST_BUCKET_PROGRESS.format(current=processed_count, total=total, pct=pct)}")

        print(f"{TAG_HURST_BUCKET} {COLOR_GREEN}"
              f"{MSG_HURST_BUCKET_ANALYZE_DONE.format(processed=processed_count, valid=valid_count)}"
              f"{COLOR_RESET}")

        return bucket_data

    def _compute_bucket_stats(self, bucket_data):
        """
        汇总每个桶的统计指标
        :return: [{ label, low, high, sample_count, long_count, short_count,
                    avg_return_5, avg_return_10, win_rate_5, win_rate_10,
                    avg_max_dd_5, avg_max_dd_10, worst_max_dd_5, worst_max_dd_10 }, ...]
        """
        results = []
        for label, low, high in self._build_bucket_labels():
            data = bucket_data.get(label)
            if data is None:
                continue

            sample_count = data['long_count'] + data['short_count']
            if sample_count == 0:
                print(f"{TAG_HURST_BUCKET} {COLOR_YELLOW}"
                      f"{MSG_HURST_BUCKET_EMPTY.format(label=label)}{COLOR_RESET}")
                continue

            stats = {
                'label': label,
                'low': low,
                'high': high,
                'sample_count': sample_count,
                'long_count': data['long_count'],
                'short_count': data['short_count'],
            }

            for fwd in self.forward_bars:
                returns = np.array(data[f'returns_{fwd}'])
                max_dds = np.array(data[f'max_dd_{fwd}'])

                if len(returns) > 0:
                    stats[f'avg_return_{fwd}'] = float(np.mean(returns))
                    stats[f'win_rate_{fwd}'] = float(
                        np.sum(returns > 0) / len(returns) * 100
                    )
                else:
                    stats[f'avg_return_{fwd}'] = 0.0
                    stats[f'win_rate_{fwd}'] = 0.0

                if len(max_dds) > 0:
                    stats[f'avg_max_dd_{fwd}'] = float(np.mean(max_dds))
                    stats[f'worst_max_dd_{fwd}'] = float(np.max(max_dds))
                else:
                    stats[f'avg_max_dd_{fwd}'] = 0.0
                    stats[f'worst_max_dd_{fwd}'] = 0.0

            results.append(stats)

        return results

    def _print_report(self, symbol, bucket_stats_list):
        """打印分桶回测报告到控制台"""
        separator = '=' * 70
        line = '-' * 70

        print(f"\n{separator}")
        print(f" {symbol} {self.interval} 赫斯特指数分桶回测报告")
        print(f" 窗口大小：{self.window_size} | 滑动步长：{self.step_size} | "
              f"趋势回看：{self.trend_lookback}根")
        print(separator)

        for stats in bucket_stats_list:
            label = stats['label']
            print(f"\n 【桶: {label}】 样本数: {stats['sample_count']} | "
                  f"{DIRECTION_LONG}: {stats['long_count']} | "
                  f"{DIRECTION_SHORT}: {stats['short_count']}")
            print(line)

            for fwd in self.forward_bars:
                avg_ret = stats[f'avg_return_{fwd}']
                win_rate = stats[f'win_rate_{fwd}']
                avg_dd = stats[f'avg_max_dd_{fwd}']
                worst_dd = stats[f'worst_max_dd_{fwd}']

                print(f"   未来{fwd:>2d}根 | "
                      f"收益均值: {avg_ret:>10.6f} ({avg_ret * 100:>6.3f}%) | "
                      f"胜率: {win_rate:>5.1f}% | "
                      f"平均回撤: {avg_dd:>8.6f} ({avg_dd * 100:>6.3f}%) | "
                      f"最大回撤: {worst_dd:>8.6f} ({worst_dd * 100:>6.3f}%)")

        print(f"\n{separator}\n")

    def _save_bucket_stats(self, symbol, bucket_stats_list):
        """保存分桶统计结果到数据库"""
        print(f"{TAG_HURST_BUCKET} {MSG_HURST_BUCKET_SAVING}")

        MySQLClient.execute_update(
            DELETE_OLD_BUCKET_STATS_SQL,
            (symbol, self.interval, self.window_size)
        )

        for stats in bucket_stats_list:
            MySQLClient.execute_update(INSERT_BUCKET_STATS_SQL, (
                symbol, self.interval, self.window_size,
                stats['label'], stats['low'], stats['high'],
                stats['sample_count'], stats['long_count'], stats['short_count'],
                round(stats['avg_return_5'], 8),
                round(stats['avg_return_10'], 8),
                round(stats['win_rate_5'], 2),
                round(stats['win_rate_10'], 2),
                round(stats['avg_max_dd_5'], 8),
                round(stats['avg_max_dd_10'], 8),
                round(stats['worst_max_dd_5'], 8),
                round(stats['worst_max_dd_10'], 8),
            ))

        print(f"{TAG_HURST_BUCKET} {COLOR_GREEN}{MSG_HURST_BUCKET_SAVED}{COLOR_RESET}")

    def analyze_symbol(self, symbol):
        """
        单个交易对的完整分桶回测流程：
        加载数据 → 滑动窗口计算赫斯特指数 → 分桶回测分析 → 保存结果 → 打印报告
        """
        print(f"\n{TAG_HURST_BUCKET} {COLOR_CYAN}开始分析 {symbol}{COLOR_RESET}")

        # 第一步：加载全部K线数据
        times, prices = self._load_prices(symbol)
        if times is None:
            return

        # 第二步：滑动窗口计算赫斯特指数
        window_results, total_windows = self._compute_hurst_per_window(prices)
        if not window_results:
            print(f"{TAG_HURST_BUCKET} {COLOR_YELLOW}没有有效的赫斯特计算结果，跳过{COLOR_RESET}")
            return

        # 第三步：分桶回测分析
        bucket_data = self._analyze_buckets(prices, window_results)

        # 第四步：汇总统计
        bucket_stats_list = self._compute_bucket_stats(bucket_data)
        if not bucket_stats_list:
            print(f"{TAG_HURST_BUCKET} {COLOR_YELLOW}所有桶均无有效样本，跳过{COLOR_RESET}")
            return

        # 第五步：保存结果到数据库
        self._save_bucket_stats(symbol, bucket_stats_list)

        # 第六步：打印报告
        self._print_report(symbol, bucket_stats_list)

    def run(self):
        """
        主流程：遍历所有配置的交易对进行分桶回测分析
        """
        print(f"{TAG_HURST_BUCKET} {COLOR_CYAN}开始赫斯特指数分桶回测分析{COLOR_RESET}")
        print(f"{TAG_HURST_BUCKET} 交易对列表：{DOWNLOAD_SYMBOLS}")
        print(f"{TAG_HURST_BUCKET} K线周期：{self.interval}")
        print(f"{TAG_HURST_BUCKET} 窗口大小：{self.window_size}，滑动步长：{self.step_size}")
        print(f"{TAG_HURST_BUCKET} 分桶边界：{self.bucket_edges}")
        print(f"{TAG_HURST_BUCKET} 趋势判断回看：{self.trend_lookback}根")
        print(f"{TAG_HURST_BUCKET} 未来观察期：{self.forward_bars}")

        for symbol in DOWNLOAD_SYMBOLS:
            try:
                self.analyze_symbol(symbol)
            except Exception as e:
                print(f"{TAG_HURST_BUCKET} {COLOR_RED}"
                      f"{MSG_HURST_BUCKET_ERROR.format(error=str(e))}{COLOR_RESET}")

        print(f"{TAG_HURST_BUCKET} {COLOR_GREEN}{MSG_HURST_BUCKET_ALL_DONE}{COLOR_RESET}")
