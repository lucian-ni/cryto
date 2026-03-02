"""
颜色定义和中文字符串常量
"""

# ============ 终端颜色定义 ============
COLOR_RESET = '\033[0m'
COLOR_RED = '\033[91m'
COLOR_GREEN = '\033[92m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_CYAN = '\033[96m'

# ============ 模块标识 ============
TAG_DOWNLOADER = '[数据下载器]'
TAG_DB = '[数据库]'
TAG_HURST = '[赫斯特指数]'

# ============ 日志消息 - 下载器 ============
MSG_DOWNLOAD_START = '开始下载币安K线数据...'
MSG_DOWNLOAD_SYMBOL_INTERVAL = '正在下载 {symbol} {interval} 的K线数据'
MSG_DOWNLOAD_BATCH = '正在获取第 {batch} 批数据，起始时间：{start_time}'
MSG_DOWNLOAD_BATCH_DONE = '第 {batch} 批数据获取完成，获取到 {count} 条K线'
MSG_DOWNLOAD_SAVE = '正在保存 {count} 条K线数据到数据库'
MSG_DOWNLOAD_SAVE_DONE = '成功保存 {count} 条K线数据'
MSG_DOWNLOAD_SYMBOL_DONE = '{symbol} {interval} 历史数据下载完成，共 {total} 条'
MSG_DOWNLOAD_ALL_DONE = '所有交易对的历史数据下载完成'
MSG_DOWNLOAD_UPDATE_START = '开始增量更新数据...'
MSG_DOWNLOAD_UPDATE_DONE = '{symbol} {interval} 增量更新完成，新增 {count} 条'
MSG_DOWNLOAD_WAIT = '等待 {seconds} 秒后开始下一轮更新...'
MSG_DOWNLOAD_NO_DATA = '本批次未获取到数据，{symbol} {interval} 下载结束'
MSG_DOWNLOAD_ERROR = '下载出错：{error}'
MSG_DOWNLOAD_RETRY = '将在 {seconds} 秒后重试...'
MSG_DOWNLOAD_RESUME = '检测到已有数据，从 {time} 继续下载'
MSG_DOWNLOAD_FRESH = '从 {time} 开始下载历史数据'
MSG_DOWNLOAD_LATEST = '{symbol} {interval} 数据已是最新，无需更新'
MSG_DOWNLOAD_STOP = '收到停止信号，下载器已退出'
MSG_DOWNLOAD_FATAL = '下载器异常退出：{error}'

# ============ 日志消息 - 数据库 ============
MSG_DB_CONNECT = '正在连接数据库 {host}:{port}/{db}'
MSG_DB_CONNECT_OK = '数据库连接成功'
MSG_DB_INIT_TABLE = '正在初始化数据表...'
MSG_DB_INIT_TABLE_OK = '数据表初始化完成'
MSG_DB_ERROR = '数据库操作出错：{error}'

# ============ 日志消息 - 赫斯特指数 ============
MSG_HURST_START = '开始计算赫斯特指数...'
MSG_HURST_CALC = '正在计算 {symbol} {interval} 窗口={window} 的赫斯特指数'
MSG_HURST_RESULT = '{symbol} {interval} 窗口={window} 赫斯特指数={value:.4f} ({interpretation})'
MSG_HURST_SAVE = '赫斯特指数计算结果已保存到数据库'
MSG_HURST_NO_DATA = '{symbol} {interval} 数据不足（需要 {need} 条，实际 {actual} 条），跳过'
MSG_HURST_ALL_DONE = '所有赫斯特指数计算完成'
MSG_HURST_ERROR = '赫斯特指数计算出错：{error}'
MSG_HURST_FATAL = '计算异常退出：{error}'

# ============ 赫斯特指数解读 ============
HURST_TREND_PERSISTENT = '趋势持续（正相关）'
HURST_RANDOM_WALK = '随机游走'
HURST_MEAN_REVERTING = '均值回归（负相关）'
# 判断阈值
HURST_THRESHOLD_HIGH = 0.55
HURST_THRESHOLD_LOW = 0.45

# ============ 程序标题 ============
TITLE_DOWNLOADER = '========== 币安数据下载器启动 =========='
TITLE_HURST = '========== 赫斯特指数计算程序启动 =========='
TITLE_HURST_DONE = '========== 计算完成 =========='
