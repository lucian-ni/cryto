"""
项目全局配置文件
"""

# ============ 数据库配置 ============
DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = 'a653142V#V'
DB_NAME = 'stock_db'
DB_CHARSET = 'utf8mb4'
# 连接池最小缓存连接数
DB_POOL_MIN_CACHED = 2
# 连接池最大缓存连接数
DB_POOL_MAX_CACHED = 5
# 连接池最大共享连接数
DB_POOL_MAX_SHARED = 5
# 连接池最大连接数
DB_POOL_MAX_CONNECTIONS = 10
# 数据库连接超时时间（秒）
DB_CONNECT_TIMEOUT = 10

# ============ 币安API配置 ============
BINANCE_BASE_URL = 'https://api.binance.com'
BINANCE_KLINE_ENDPOINT = '/api/v3/klines'
# 每次请求最大K线数量（币安限制最大1000）
BINANCE_KLINE_LIMIT = 1000
# 请求间隔（秒），避免触发频率限制
BINANCE_REQUEST_INTERVAL_SEC = 0.5

# ============ 下载配置 ============
# 需要下载的交易对
DOWNLOAD_SYMBOLS = ['BTCUSDT', 'ETHUSDT']
# 需要下载的K线周期
DOWNLOAD_INTERVALS = ['1h', '2h', '4h', '12h', '1d']
# 历史数据回溯年数
DOWNLOAD_HISTORY_YEARS = 3
# 增量更新轮询间隔（秒），每轮更新完后等待的时间
UPDATE_POLL_INTERVAL_SEC = 60

# ============ 赫斯特指数配置 ============
# 计算窗口大小列表（数据条数）
HURST_WINDOW_SIZES = [100, 200, 500]
# R/S分析中最小子序列长度
HURST_MIN_SUBSERIES_LEN = 8
