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

# ============ 日志消息 - 赫斯特指数统计 ============
TAG_HURST_STATS = '[赫斯特统计]'
MSG_HURST_STATS_LOAD_DATA = '正在加载 {symbol} {interval} 全部K线数据...'
MSG_HURST_STATS_DATA_LOADED = '数据加载完成，共 {count} 条，时间范围：{start} ~ {end}'
MSG_HURST_STATS_DATA_NOT_ENOUGH = '{symbol} {interval} 数据不足（需要至少 {need} 条，实际 {actual} 条），跳过'
MSG_HURST_STATS_CALC_START = '开始滑动窗口计算，窗口={window}，步长={step}，总窗口数={total}'
MSG_HURST_STATS_PROGRESS = '计算进度：{current}/{total} ({pct:.1f}%)'
MSG_HURST_STATS_WINDOW_ERROR = '窗口 {index} 计算失败：{error}'
MSG_HURST_STATS_CALC_DONE = '滑动窗口计算完成，有效结果 {valid}/{total} 个'
MSG_HURST_STATS_SAVING_DETAIL = '正在保存 {count} 条窗口明细到数据库...'
MSG_HURST_STATS_SAVING_SUMMARY = '正在保存统计汇总到数据库...'
MSG_HURST_STATS_SAVED = '结果已保存到数据库'
MSG_HURST_STATS_ERROR = '赫斯特统计计算出错：{error}'
MSG_HURST_STATS_FATAL = '统计分析异常退出：{error}'
MSG_HURST_STATS_ALL_DONE = '所有交易对的赫斯特统计分析完成'

# 近期 vs 历史趋势判断
HURST_STATS_VERDICT_HIGHER = '偏高（近期趋势性增强）'
HURST_STATS_VERDICT_LOWER = '偏低（近期趋势性减弱）'
HURST_STATS_VERDICT_STABLE = '持平'

# ============ 日志消息 - 赫斯特指数分桶回测 ============
TAG_HURST_BUCKET = '[分桶回测]'
MSG_HURST_BUCKET_LOAD_DATA = '正在加载 {symbol} {interval} 全部K线数据...'
MSG_HURST_BUCKET_DATA_LOADED = '数据加载完成，共 {count} 条，时间范围：{start} ~ {end}'
MSG_HURST_BUCKET_DATA_NOT_ENOUGH = '{symbol} {interval} 数据不足（需要至少 {need} 条，实际 {actual} 条），跳过'
MSG_HURST_BUCKET_CALC_HURST = '开始滑动窗口计算赫斯特指数，窗口={window}，步长={step}，总窗口数={total}'
MSG_HURST_BUCKET_CALC_HURST_DONE = '赫斯特指数计算完成，有效结果 {valid}/{total} 个'
MSG_HURST_BUCKET_ANALYZE_START = '开始分桶回测分析，分桶边界：{edges}'
MSG_HURST_BUCKET_PROGRESS = '分桶分析进度：{current}/{total} ({pct:.1f}%)'
MSG_HURST_BUCKET_WINDOW_SKIP_TREND = '窗口 {index} 趋势回看数据不足，跳过'
MSG_HURST_BUCKET_WINDOW_SKIP_FUTURE = '窗口 {index} 未来数据不足（需要 {need} 根，剩余 {remain} 根），跳过'
MSG_HURST_BUCKET_WINDOW_SKIP_RANGE = '窗口 {index} 赫斯特值 {hurst:.4f} 不在分桶范围内，跳过'
MSG_HURST_BUCKET_ANALYZE_DONE = '分桶分析完成，共处理 {processed} 个窗口，有效 {valid} 个'
MSG_HURST_BUCKET_SAVING = '正在保存分桶统计结果到数据库...'
MSG_HURST_BUCKET_SAVED = '分桶统计结果已保存到数据库'
MSG_HURST_BUCKET_ERROR = '分桶回测出错：{error}'
MSG_HURST_BUCKET_FATAL = '分桶回测异常退出：{error}'
MSG_HURST_BUCKET_ALL_DONE = '所有交易对的分桶回测分析完成'
MSG_HURST_BUCKET_EMPTY = '桶 {label} 没有样本数据'

# 方向标签
DIRECTION_LONG = '做多'
DIRECTION_SHORT = '做空'

# ============ 程序标题 ============
TITLE_DOWNLOADER = '========== 币安数据下载器启动 =========='
TITLE_HURST = '========== 赫斯特指数计算程序启动 =========='
TITLE_HURST_DONE = '========== 计算完成 =========='
TITLE_HURST_STATS = '========== 赫斯特指数滑动窗口统计程序启动 =========='
TITLE_HURST_STATS_DONE = '========== 统计分析完成 =========='
TITLE_HURST_BUCKET = '========== 赫斯特指数分桶回测程序启动 =========='
TITLE_HURST_BUCKET_DONE = '========== 分桶回测完成 =========='
