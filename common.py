import os
import re
import yaml
import log

config = dict()
config_file = "application.yml"
with open(config_file, 'r', encoding="utf-8") as f:
    config = yaml.safe_load(f)

def delete_target_files(dir_path, logger:log, pattern:re.Pattern=None, filter:list=None):
    if not os.path.exists(dir_path):
        logger.error(f"指定的目录:{dir_path}不存在！")
        return
    count = 0
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            if (pattern is not None and pattern.match(file)) or (filter is not None and (file in filter)):
                logger.warning(f"删除目标文件: {file_path}")
                os.remove(file_path)
                count = count + 1
    logger.warning(f"总共有{count}个目标文件被删除！")