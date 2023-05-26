import os
import subprocess
import sys
import log
from log import logger

def merge_multiple_ts(start:int, end:int, ts_path:str, postfix="ts"):
    os.chdir(ts_path)
    files = list()
    output_file = f"{os.path.basename(os.getcwd())}_{start}-{end}.{postfix}"
    for i in range(start, end+1):
        filename = f"seg-{i}.ts"
        if not os.path.exists(os.getcwd() + os.sep + filename):
            log_info = f"缺失vod分片:seg-{i}.ts, 转换失败!"
            logger.exception(log_info)
            raise Exception(log_info)
        else:
            files.append(filename)
    # 调用FFmpeg工具进行合并
    # 生成ffmpeg命令
    command = ['ffmpeg', '-i', f'concat:{"|".join(files)}', '-c', 'copy', output_file]
    # 将输出和错误流重定向到sys.stdout，以便实时打印输出信息
    p = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stdout)
    # 等待进程结束
    p.wait()

def convert_ts_to_mp4(start:int, end:int, ts_path:str, crf=18, audio_bitrate=256):
    os.chdir(ts_path)
    input_files = list()
    output_file = "output.mp4"
    for i in range(start, end+1):
        filename = f"seg-{i}.ts"
        if not os.path.exists(os.getcwd() + os.sep + filename):
            raise Exception(f"缺失vod分片:seg-{i}.ts, 转换失败!")
        else:
            input_files.append(filename)
    # 使用subprocess模块调用FFmpeg工具进行合并
    inputs = " ".join([f"-i {f}" for f in input_files])
    cmd = f"ffmpeg {inputs} -c:v libx264 -preset medium -crf {crf} -c:a aac -b:a {audio_bitrate}k -filter_complex '[0:v] [0:a] "
    for i in range(1, len(input_files)):
        cmd += f"[{i}:v] [{i}:a] "
    cmd += f"concat=n={len(input_files)}:v=1:a=1[outv][outa]' -map '[outv]' -map '[outa]' {output_file}"
    subprocess.call(cmd, shell=True)