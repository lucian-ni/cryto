-- 币安K线数据表
CREATE TABLE IF NOT EXISTS kline_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT '交易对，如BTCUSDT',
    interval_type VARCHAR(10) NOT NULL COMMENT 'K线周期，如1h,2h,4h,12h,1d',
    open_time BIGINT NOT NULL COMMENT '开盘时间戳(毫秒)',
    open_time_dt DATETIME NOT NULL COMMENT '开盘时间(可读)',
    open_price DECIMAL(20, 8) NOT NULL COMMENT '开盘价',
    high_price DECIMAL(20, 8) NOT NULL COMMENT '最高价',
    low_price DECIMAL(20, 8) NOT NULL COMMENT '最低价',
    close_price DECIMAL(20, 8) NOT NULL COMMENT '收盘价',
    volume DECIMAL(30, 8) NOT NULL COMMENT '成交量',
    close_time BIGINT NOT NULL COMMENT '收盘时间戳(毫秒)',
    quote_volume DECIMAL(30, 8) NOT NULL COMMENT '成交额',
    trades_count INT NOT NULL COMMENT '成交笔数',
    taker_buy_volume DECIMAL(30, 8) NOT NULL COMMENT '主动买入成交量',
    taker_buy_quote_volume DECIMAL(30, 8) NOT NULL COMMENT '主动买入成交额',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_symbol_interval_open_time (symbol, interval_type, open_time),
    INDEX idx_symbol_interval_dt (symbol, interval_type, open_time_dt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='币安K线数据表';

-- 赫斯特指数计算结果表
CREATE TABLE IF NOT EXISTS hurst_exponent_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT '交易对',
    interval_type VARCHAR(10) NOT NULL COMMENT 'K线周期',
    window_size INT NOT NULL COMMENT '计算窗口大小(数据条数)',
    hurst_value DECIMAL(10, 6) NOT NULL COMMENT '赫斯特指数值',
    interpretation VARCHAR(50) NOT NULL COMMENT '解读：趋势持续/随机游走/均值回归',
    calc_start_time DATETIME NOT NULL COMMENT '计算数据起始时间',
    calc_end_time DATETIME NOT NULL COMMENT '计算数据结束时间',
    data_count INT NOT NULL COMMENT '实际使用的数据条数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_symbol_interval_window_end (symbol, interval_type, window_size, calc_end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赫斯特指数计算结果表';

-- 赫斯特指数滑动窗口明细表
CREATE TABLE IF NOT EXISTS hurst_window_detail (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT '交易对',
    interval_type VARCHAR(10) NOT NULL COMMENT 'K线周期',
    window_size INT NOT NULL COMMENT '窗口大小',
    window_index INT NOT NULL COMMENT '窗口序号（从0开始）',
    hurst_value DECIMAL(10, 6) NOT NULL COMMENT '该窗口的赫斯特指数',
    interpretation VARCHAR(50) NOT NULL COMMENT '解读',
    window_start_time DATETIME NOT NULL COMMENT '窗口起始时间',
    window_end_time DATETIME NOT NULL COMMENT '窗口结束时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_symbol_window (symbol, interval_type, window_size, window_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赫斯特指数滑动窗口明细表';

-- 赫斯特指数统计汇总表
CREATE TABLE IF NOT EXISTS hurst_stats_summary (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT '交易对',
    interval_type VARCHAR(10) NOT NULL COMMENT 'K线周期',
    window_size INT NOT NULL COMMENT '窗口大小',
    step_size INT NOT NULL COMMENT '滑动步长',
    total_windows INT NOT NULL COMMENT '总窗口数',
    valid_windows INT NOT NULL COMMENT '有效窗口数',
    data_start_time DATETIME NOT NULL COMMENT '数据起始时间',
    data_end_time DATETIME NOT NULL COMMENT '数据结束时间',
    -- 基础统计
    hurst_mean DECIMAL(10, 6) NOT NULL COMMENT '均值',
    hurst_median DECIMAL(10, 6) NOT NULL COMMENT '中位数',
    hurst_std DECIMAL(10, 6) NOT NULL COMMENT '标准差',
    hurst_min DECIMAL(10, 6) NOT NULL COMMENT '最小值',
    hurst_max DECIMAL(10, 6) NOT NULL COMMENT '最大值',
    hurst_q25 DECIMAL(10, 6) NOT NULL COMMENT '25%分位数',
    hurst_q75 DECIMAL(10, 6) NOT NULL COMMENT '75%分位数',
    hurst_skewness DECIMAL(10, 6) NOT NULL COMMENT '偏度',
    hurst_kurtosis DECIMAL(10, 6) NOT NULL COMMENT '峰度',
    -- 分类占比
    pct_trend DECIMAL(6, 2) NOT NULL COMMENT '趋势持续占比(%)',
    pct_random DECIMAL(6, 2) NOT NULL COMMENT '随机游走占比(%)',
    pct_mean_revert DECIMAL(6, 2) NOT NULL COMMENT '均值回归占比(%)',
    -- 近期对比
    recent_mean DECIMAL(10, 6) NOT NULL COMMENT '近期窗口均值',
    recent_verdict VARCHAR(50) NOT NULL COMMENT '近期趋势判断：偏高/持平/偏低',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_symbol_interval_window_step (symbol, interval_type, window_size, step_size)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赫斯特指数统计汇总表';

-- 赫斯特指数分桶回测统计表
CREATE TABLE IF NOT EXISTS hurst_bucket_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT '交易对',
    interval_type VARCHAR(10) NOT NULL COMMENT 'K线周期',
    window_size INT NOT NULL COMMENT '窗口大小',
    bucket_label VARCHAR(20) NOT NULL COMMENT '桶标签，如 0.45~0.55',
    bucket_low DECIMAL(6, 2) NOT NULL COMMENT '桶下界',
    bucket_high DECIMAL(6, 2) NOT NULL COMMENT '桶上界',
    sample_count INT NOT NULL COMMENT '落入该桶的窗口数',
    long_count INT NOT NULL COMMENT '做多次数',
    short_count INT NOT NULL COMMENT '做空次数',
    avg_return_5 DECIMAL(12, 8) NOT NULL COMMENT '未来5根方向收益均值',
    avg_return_10 DECIMAL(12, 8) NOT NULL COMMENT '未来10根方向收益均值',
    win_rate_5 DECIMAL(6, 2) NOT NULL COMMENT '未来5根胜率(%)',
    win_rate_10 DECIMAL(6, 2) NOT NULL COMMENT '未来10根胜率(%)',
    avg_max_dd_5 DECIMAL(12, 8) NOT NULL COMMENT '未来5根平均最大回撤',
    avg_max_dd_10 DECIMAL(12, 8) NOT NULL COMMENT '未来10根平均最大回撤',
    worst_max_dd_5 DECIMAL(12, 8) NOT NULL COMMENT '未来5根最差最大回撤',
    worst_max_dd_10 DECIMAL(12, 8) NOT NULL COMMENT '未来10根最差最大回撤',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_symbol_bucket (symbol, interval_type, window_size, bucket_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='赫斯特指数分桶回测统计表';
