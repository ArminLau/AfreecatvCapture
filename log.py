import datetime
import logging
import yaml

log_level = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

with open("application.yml", 'r', encoding="utf-8") as f:
    config = yaml.safe_load(f)
log_config = config['logger']
level = log_config['level']
log_name = log_config['name']
log_format = log_config['format']
# 创建 logger 对象
logger = logging.getLogger(__name__)
logger_level = log_level.get(level)
# 设置 logger 的级别为 DEBUG
logger.setLevel(logger_level)
# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logger_level)
log_filename = datetime.datetime.now().strftime(log_name.encode('unicode-escape').decode()).encode().decode(
    'unicode-escape')
# 创建文件处理器
file_handler = logging.FileHandler(f'./{log_filename}', mode='w', encoding='utf-8')
file_handler.setLevel(logger_level)
# 创建日志格式化器
formatter = logging.Formatter(log_format)
# 将格式化器添加到处理器中
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
# 将处理器添加到 logger 对象中
logger.addHandler(console_handler)
logger.addHandler(file_handler)
