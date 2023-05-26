import datetime
import math
import os

import wget
import requests
import re
import logging
import threading
import yaml
from log import logger
from ffmpeg_tool import merge_multiple_ts
from common import delete_target_files,config

vod_config = config['vod']
fragmentation_divide = vod_config['fragmentation-divide']
timeline_offset_second = vod_config['timeline-offset-second']
dir_format = vod_config['folder-format']

download_config = config['download']
fail_retry_time = download_config['fail-retry-time']
threads_count = download_config['threads']
auto_merge = download_config['auto-merge']
auto_del_tmp = download_config['auto-del-tmp']
del_fragmentation_after_merge = download_config['del-fragmentation-after-merge']

ffmpeg_config = config['ffmpeg']
merge_postfix = ffmpeg_config['merge-postfix']

proxy_config = config['proxy']
proxy_enable = proxy_config['enable']
proxy_protocol = proxy_config['protocol']
proxy_url = proxy_config['url']

default_date_format = "%Y-%m-%d %H:%M:%S"
base_path = os.getcwd()
fail_vod_nums = list()
modes = {"1": "下载vod视频", "2": "手动合并视频分片"}

# fragmentation_divide = 3
# timeline_offset_second = 30
# dir_format = "%Y-%m-%d_%title"
# threads_count = 10
# auto_merge = False
# auto_del_tmp = True
# del_fragmentation_after_merge = False
# merge_postfix = "ts"
# fail_retry_time = 1
# proxy_enable = True
# proxy_protocol = "https"
# proxy_url = "127.0.0.1:10809"

class Vod:
    def __init__(self, title:str, date:datetime.datetime, link:str, duration:int, host:str):
        self.title = title
        self.date = date
        self.link = link
        self.duration = duration
        self.host = host

    def __str__(self):
        return f"Vod(title={self.title}, date={self.date}, link={self.link}, duration={self.duration})"

def format_time(format:str, date:datetime.datetime):
    return date.strftime(format.encode('unicode-escape').decode()).encode().decode('unicode-escape')

def parse_dir_pattern(title:str, date:datetime.datetime, host:str):
    pattern = dir_format
    if title is not None:
        pattern = pattern.replace("%title", title)
    if host is not None:
        pattern = pattern.replace("%host", host)
    return format_time(pattern, date)

def validate_path(path:str):
    if len(path) == 0:
        return os.getcwd()
    while not os.path.exists(path):
        path = input("指定的路径或文件不存在，请重新指定: ")
    return path

def validate_mode(mode:str):
    while mode not in modes.keys():
        mode = input(f"输入错误，请选择可选择的模式编号({' '.join([key+':'+value for key,value in modes.items()])}): ")
    return mode

def validate_timeline(date:str):
    while len(date) == 0 or (len(date) != 0 and (re.search(r"\d{2}:\d{2}:\d{2}-\d{2}:\d{2}:\d{2}", date) is None or len(re.search(r"\d{2}:\d{2}:\d{2}-\d{2}:\d{2}:\d{2}", date).group()) != len(date))):
        date = input("输入格式错误，请按格式%H:%M:%S-%H:%M:%S的格式输入: ")
    return date

def validate_fragmentation_range(range:str):
    while len(range) == 0 or (len(range) != 0 and (re.search(r"\d+-\d+", range) is None or len(re.search(r"\d+-\d+", range).group()) != len(range))):
        range = input("输入格式错误，请输入正确的格式(分片起始数-分片终止数): ")
    return range

def get_time_seconds(time:str):
    hour,min,sec = time.split(":")
    return 3600*int(hour)+60*int(min)+int(sec)

def get_target_fragmentations(duration_timeline:str, duration_second:int):
    before, after = duration_timeline.split("-")
    before = get_time_seconds(before) - timeline_offset_second
    after = get_time_seconds(after) + timeline_offset_second
    before = 0 if before < 0 else before
    after = duration_second if after > duration_second else after
    return math.ceil(before/3),math.ceil(after/3)

def get_fragmentation_num(duration:int):
    return math.ceil(duration/1000/fragmentation_divide)

def get_vod_fragmentation_url(num:int, vod_link:str):
    url = vod_link[0:vod_link.find('video')] + "hls/vod" + vod_link[(vod_link.find('smil:vod')+8):(vod_link.find('playlist'))] + f"original/both/seg-{num}.ts"
    return url

def get_vod_info(vod_id:str):
    url = "https://api.m.afreecatv.com/station/video/a/view"
    proxies = {proxy_protocol: proxy_url}
    headers = {
        'authority': 'api.m.afreecatv.com',
        'method': 'POST',
        'path': '/station/video/a/view',
        'scheme': 'https',
        'accept': 'application/json, text/plain, */*'
    }
    payload = {
        'nTitleNo': f'{vod_id}',
        'nApiLevel': '10',
        'nPlaylistIdx': '0'
    }
    if not proxy_enable:
        proxies = None
    response = requests.post(url=url, proxies=proxies, headers=headers, data=payload)
    vod_info = response.json().get('data')
    # vod日期
    date = datetime.datetime.strptime(vod_info.get('broad_start'), default_date_format)
    # vod标题
    title = vod_info.get('full_title')
    file_info = vod_info.get('files')[0]
    # vod链接
    vod_link = file_info.get('file')
    # vod时长(毫秒)
    vod_duration = int(file_info.get('duration'))
    # vod主播昵称
    vod_host = vod_info.get('writer_nick')
    return Vod(title=title, date=date, link=vod_link, duration=vod_duration, host=vod_host)

def multithreading_download_vods(vod_nums:list, vod_info:Vod):
    dir_name = parse_dir_pattern(title=vod_info.title, date=vod_info.date, host=vod_info.host)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
    os.chdir(dir_name)
    # 将数组拆分成成差不多相等的块
    chunk_size = len(vod_nums) // threads_count
    if chunk_size <= 0:
        chunk_size = 1
    chunks = [vod_nums[i:i + chunk_size] for i in range(0, len(vod_nums), chunk_size)]

    threads = []
    # 为每个资源文件块下载创建一个线程程
    for i in range(len(chunks)):
        t = threading.Thread(target=download_vods, args=(chunks[i],vod_info.link))
        threads.append(t)
        t.start()
    # 等待所有线程完成
    for t in threads:
        t.join()

def download_vods(nums:list, url:str):
    for num in nums:
        vod_url = get_vod_fragmentation_url(num=num, vod_link=url)
        filename = f"seg-{num}.ts"
        if not os.path.exists(os.getcwd() + os.sep + filename):
            try:
                logger.info(f"正在下载资源:{vod_url}")
                wget.download(url=vod_url)
                logger.info(f"成功下载资源:{vod_url}到{os.getcwd()}")
            except Exception as e:
                logging.exception("An exception occurred: %s", str(e))
                logger.error(f"下载以下资源失败:{vod_url}，将其加入下载失败队列")
                fail_vod_nums.append(num)
        else:
            logger.warning(f"资源:{filename} 已存在，略过")

def handle_vod_fragmentation_download():
    vod_id = input("请输入VOD的ID: ")
    base_path = validate_path(input("请输入文件存放的目录(直接回车使用当前脚本所在的目录): "))
    os.chdir(base_path)
    duration_timeline = validate_timeline(input("请输入需要截取的时间片段(格式%H:%M:%S-%H:%M:%S):"))
    vod_info = get_vod_info(vod_id)
    before, after = get_target_fragmentations(duration_timeline=duration_timeline,
                                              duration_second=math.ceil(vod_info.duration / 1000))
    logger.info(f"共计{after - before + 1}个ts分片文件将被下载！")
    vod_nums = [num for num in range(before, after + 1)]
    multithreading_download_vods(vod_nums=vod_nums, vod_info=vod_info)
    for i in range(0, fail_retry_time):
        if len(fail_vod_nums) > 0:
            retry_vod_nums = fail_vod_nums
            fail_vod_nums.clear()
            logger.warning(f"尝试重新下载之前下载失败的资源: {len(retry_vod_nums)}")
            multithreading_download_vods(vod_nums=retry_vod_nums, vod_info=vod_info)
    if auto_del_tmp:
        logger.warning("开始删除ts下载产生的临时文件")
        delete_target_files(dir_path=os.getcwd(), pattern=re.compile(r'.*\.tmp$'), logger=logger)
    if auto_merge:
        logger.info(f"开始自动合并个{after-before+1}ts分片文件")
        merge_multiple_ts(start=before, end=after, ts_path=os.getcwd(), postfix=merge_postfix, del_ts_after_merge=del_fragmentation_after_merge)

if __name__ == '__main__':
    mode = int(validate_mode(input(f"请选择需要执行的任务编号({' '.join([key+':'+value for key,value in modes.items()])}): ")))
    if mode == 1:
        handle_vod_fragmentation_download()
    elif mode == 2:
        start,end = validate_fragmentation_range(input(f"请输入分片起始数和分片终止数并以-分隔(例如: 100-200):")).split("-")
        path = validate_path(input("请输入视频分片文件存放的目录: "))
        merge_multiple_ts(start=int(start), end=int(end), ts_path=path, postfix=merge_postfix, del_ts_after_merge=del_fragmentation_after_merge)

