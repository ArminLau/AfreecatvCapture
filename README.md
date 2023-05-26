### 一个用于截取afreecatv视频片段的脚本工具
#### 使用条件
* Python版本3.8版本及以上
* 获取afreecatv的vod_id，获取来源: https://vod.afreecatv.com/player/{vod_id}
* 安装脚本运行必须的依赖: 
```commandline
pip install -r requirements.txt
```
* 需要安装ffmpeg以使用视频分片合并功能，如果希望在没有ffmpeg的条件下使用，需要修改配置文件application.yml将download.auto-merge置为false

#### 使用步骤
* 根据需要修改application.yml配置文件
* 执行以下命令启动脚本
```commandline
python main.py
```
* 选择控制台支持的任务编号
```commandline
请选择需要执行的任务编号(1:下载vod视频 2:合并视频分片): 1
```
* 输入VOD ID
```commandline
请输入VOD的ID: xxxxxxxx
```
* 输入需要截取的时间片段
```commandline
#假如需要截取视频的第10分钟到第15分钟的内容
请输入需要截取的时间片段(格式%H:%M:%S-%H:%M:%S):00:10:00-00:15:00
```
* 等待脚本执行完毕即可