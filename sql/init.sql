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
