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

# ============ 赫斯特指数滑动窗口统计配置 ============
# 固定窗口长度（数据条数）
HURST_STATS_WINDOW_SIZE = 100
# 固定K线周期
HURST_STATS_INTERVAL = '1h'
# 滑动步长（每次滑动多少根K线，1=逐条滑动，10=每10条算一次）
HURST_STATS_STEP_SIZE = 10
# "近期"统计取最近多少个窗口
HURST_STATS_RECENT_COUNT = 50
# 近期 vs 历史均值差异阈值
HURST_STATS_RECENT_THRESHOLD = 0.03
# 计算进度打印间隔（每多少个窗口打印一次进度）
HURST_STATS_PROGRESS_INTERVAL = 100

# ============ 赫斯特指数分桶回测配置 ============
# 分桶边界列表（相邻两个值组成一个桶，左闭右开，最后一个桶右闭）
HURST_BUCKET_EDGES = [0.45, 0.55, 0.60, 0.65, 0.70]
# 趋势判断回看K线根数（最近N根return之和 > 0 则做多，否则做空）
HURST_BUCKET_TREND_LOOKBACK = 10
# 未来收益观察期列表（分别统计未来N根的收益、胜率、最大回撤）
HURST_BUCKET_FORWARD_BARS = [5, 10]
# 分桶分析使用的K线周期（与滑动窗口统计保持一致）
HURST_BUCKET_INTERVAL = '1h'
# 分桶分析使用的窗口大小（与滑动窗口统计保持一致）
HURST_BUCKET_WINDOW_SIZE = 100
# 分桶分析使用的滑动步长（与滑动窗口统计保持一致）
HURST_BUCKET_STEP_SIZE = 10
# 分桶分析进度打印间隔
HURST_BUCKET_PROGRESS_INTERVAL = 500
