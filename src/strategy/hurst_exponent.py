"""
赫斯特指数（Hurst Exponent）计算模块
使用R/S（重标极差）分析法计算赫斯特指数

赫斯特指数含义：
  H > 0.5: 趋势持续（序列具有正自相关性，适合趋势跟踪策略）
  H = 0.5: 随机游走（序列无记忆性）
  H < 0.5: 均值回归（序列具有负自相关性，适合均值回归策略）
"""
import numpy as np

from config.settings import (
    DOWNLOAD_SYMBOLS, DOWNLOAD_INTERVALS,
    HURST_WINDOW_SIZES, HURST_MIN_SUBSERIES_LEN
)
from src.lib_resource import (
    COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_CYAN, COLOR_RESET, TAG_HURST,
    MSG_HURST_START, MSG_HURST_CALC, MSG_HURST_RESULT, MSG_HURST_SAVE,
    MSG_HURST_NO_DATA, MSG_HURST_ALL_DONE, MSG_HURST_ERROR,
    HURST_TREND_PERSISTENT, HURST_RANDOM_WALK, HURST_MEAN_REVERTING,
    HURST_THRESHOLD_HIGH, HURST_THRESHOLD_LOW
)
from src.db.mysql_client import MySQLClient


# 查询K线收盘价数据（按时间倒序取最近N条）
QUERY_CLOSE_PRICE_SQL = """
    SELECT open_time_dt, close_price 
    FROM kline_data 
    WHERE symbol = %s AND interval_type = %s 
    ORDER BY open_time DESC 
    LIMIT %s
"""

# 插入赫斯特指数结果（重复时更新）
INSERT_HURST_SQL = """
    INSERT INTO hurst_exponent_result 
    (symbol, interval_type, window_size, hurst_value, interpretation,
     calc_start_time, calc_end_time, data_count)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE 
        hurst_value = VALUES(hurst_value),
        interpretation = VALUES(interpretation),
        calc_start_time = VALUES(calc_start_time),
        data_count = VALUES(data_count),
        created_at = CURRENT_TIMESTAMP
"""

# 计算R/S时要求的最少有效分组数
MIN_VALID_RS_GROUPS = 2


def compute_hurst_exponent(prices, verbose=True):
    """
    使用R/S分析法（重标极差分析法）计算赫斯特指数

    算法步骤：
    1. 计算对数收益率序列
    2. 对不同子序列长度n（取2的幂次），将序列分成多个子序列
    3. 对每个子序列计算：均值偏差的累积和的极差R，标准差S
    4. 计算R/S的均值
    5. 对 log(n) 和 log(R/S) 做线性回归，斜率即为赫斯特指数H

    :param prices: 价格序列（numpy数组）
    :param verbose: 是否打印R/S分析及拟合的详细日志，批量计算时建议False
    :return: 赫斯特指数值
    """
    min_data_points = HURST_MIN_SUBSERIES_LEN * 2
    if len(prices) < min_data_points:
        raise ValueError(f"价格序列长度不足，至少需要 {min_data_points} 个数据点")

    # 第一步：计算对数收益率
    if verbose:
        print(f"{TAG_HURST} 计算对数收益率序列，价格序列长度：{len(prices)}")
    log_returns = np.diff(np.log(prices))
    n = len(log_returns)

    # 第二步：确定不同的子序列长度（取2的幂次，从最小子序列长度到n//2）
    max_k = int(np.floor(np.log2(n)))
    min_k = int(np.ceil(np.log2(HURST_MIN_SUBSERIES_LEN)))
    sizes = [2 ** i for i in range(min_k, max_k + 1) if 2 ** i <= n // 2]
    if verbose:
        print(f"{TAG_HURST} R/S分析子序列长度列表：{sizes}")

    if len(sizes) < MIN_VALID_RS_GROUPS:
        raise ValueError("数据长度不足以进行R/S分析，无法生成足够的分组")

    # 第三步：对每个子序列长度计算R/S值
    rs_values = []
    for size in sizes:
        num_subseries = n // size
        rs_list = []
        for j in range(num_subseries):
            subseries = log_returns[j * size: (j + 1) * size]
            mean = np.mean(subseries)
            # 累积偏差序列
            cumulative_dev = np.cumsum(subseries - mean)
            # 极差 R = max(累积偏差) - min(累积偏差)
            r = np.max(cumulative_dev) - np.min(cumulative_dev)
            # 标准差 S（使用无偏估计，ddof=1）
            s = np.std(subseries, ddof=1)
            if s > 0:
                rs_list.append(r / s)

        if rs_list:
            avg_rs = np.mean(rs_list)
            rs_values.append((size, avg_rs))
            if verbose:
                print(f"{TAG_HURST} 子序列长度={size}, 分组数={num_subseries}, "
                      f"平均R/S={avg_rs:.4f}")

    if len(rs_values) < MIN_VALID_RS_GROUPS:
        raise ValueError("有效R/S值不足，无法进行线性拟合")

    # 第四步：对 log(size) 和 log(R/S) 做线性回归
    log_sizes = np.log([v[0] for v in rs_values])
    log_rs = np.log([v[1] for v in rs_values])

    # 最小二乘拟合，斜率即为赫斯特指数
    hurst, intercept = np.polyfit(log_sizes, log_rs, 1)
    if verbose:
        print(f"{TAG_HURST} 线性拟合完成：H={hurst:.6f}, 截距={intercept:.6f}")

    return hurst


def interpret_hurst(hurst_value):
    """
    解读赫斯特指数
    :param hurst_value: 赫斯特指数值
    :return: 中文解读字符串
    """
    if hurst_value > HURST_THRESHOLD_HIGH:
        return HURST_TREND_PERSISTENT
    elif hurst_value < HURST_THRESHOLD_LOW:
        return HURST_MEAN_REVERTING
    else:
        return HURST_RANDOM_WALK


class HurstCalculator:
    """赫斯特指数计算器"""

    def calculate_and_save(self, symbol, interval, window_size):
        """
        计算并保存单个交易对/周期/窗口的赫斯特指数
        :param symbol: 交易对
        :param interval: K线周期
        :param window_size: 窗口大小（数据条数）
        :return: 赫斯特指数值，计算失败返回None
        """
        print(f"{TAG_HURST} {MSG_HURST_CALC.format(symbol=symbol, interval=interval, window=window_size)}")

        # 从数据库读取收盘价（按时间倒序取最近window_size条）
        print(f"{TAG_HURST} 从数据库读取 {symbol} {interval} 最近 {window_size} 条收盘价...")
        rows = MySQLClient.execute_query(QUERY_CLOSE_PRICE_SQL, (symbol, interval, window_size))

        if len(rows) < window_size:
            print(f"{TAG_HURST} {COLOR_YELLOW}"
                  f"{MSG_HURST_NO_DATA.format(symbol=symbol, interval=interval, need=window_size, actual=len(rows))}"
                  f"{COLOR_RESET}")
            return None

        # 按时间正序排列（查询是DESC，需要反转）
        rows = list(reversed(rows))
        prices = np.array([float(row['close_price']) for row in rows])
        calc_start_time = rows[0]['open_time_dt']
        calc_end_time = rows[-1]['open_time_dt']
        data_count = len(prices)

        print(f"{TAG_HURST} 数据时间范围：{calc_start_time} 至 {calc_end_time}，共 {data_count} 条")

        try:
            # 计算赫斯特指数
            hurst_value = compute_hurst_exponent(prices)
            interpretation = interpret_hurst(hurst_value)

            print(f"{TAG_HURST} {COLOR_GREEN}"
                  f"{MSG_HURST_RESULT.format(symbol=symbol, interval=interval, window=window_size, value=hurst_value, interpretation=interpretation)}"
                  f"{COLOR_RESET}")

            # 保存结果到数据库
            print(f"{TAG_HURST} 正在保存计算结果到数据库...")
            MySQLClient.execute_update(INSERT_HURST_SQL, (
                symbol, interval, window_size, round(hurst_value, 6),
                interpretation, calc_start_time, calc_end_time, data_count
            ))
            print(f"{TAG_HURST} {MSG_HURST_SAVE}")

            return hurst_value
        except ValueError as e:
            print(f"{TAG_HURST} {COLOR_RED}{MSG_HURST_ERROR.format(error=str(e))}{COLOR_RESET}")
            return None

    def run(self):
        """
        对所有配置的交易对、周期、窗口大小计算赫斯特指数
        遍历顺序：交易对 → K线周期 → 窗口大小
        """
        print(f"{TAG_HURST} {COLOR_CYAN}{MSG_HURST_START}{COLOR_RESET}")
        print(f"{TAG_HURST} 交易对列表：{DOWNLOAD_SYMBOLS}")
        print(f"{TAG_HURST} K线周期列表：{DOWNLOAD_INTERVALS}")
        print(f"{TAG_HURST} 窗口大小列表：{HURST_WINDOW_SIZES}")

        for symbol in DOWNLOAD_SYMBOLS:
            for interval in DOWNLOAD_INTERVALS:
                for window_size in HURST_WINDOW_SIZES:
                    try:
                        self.calculate_and_save(symbol, interval, window_size)
                    except Exception as e:
                        print(f"{TAG_HURST} {COLOR_RED}"
                              f"{MSG_HURST_ERROR.format(error=str(e))}{COLOR_RESET}")

        print(f"{TAG_HURST} {COLOR_GREEN}{MSG_HURST_ALL_DONE}{COLOR_RESET}")

