## PYIFF 购票程序

### 配置

1. 修改`config.sample.yaml`文件名为`config.yaml`
2. `bark_key`在 Bark App 中找到
3. `run_time`为开始运行抢票程序的时间，在此之前不会请求网站接口。
4. `token`需要在登录[平遥电影节官网](https://www.pyiffestival.com)后，在 RequestHeader 中找到*Authorization*，并拷贝到此配置文件中
5. `movies` 可填写多部电影，在每个电影配置中需要填写以下几个字段
   - name: 电影名称，必填。
   - category: 电影分类，必填。有以下几个可选值: 特别展映|卧虎|藏龙|首映|回顾/致敬|从山西出发
   - date: 电影放映日期，必填
   - count: 需要购买的张数，必填，最多为 5 张
   - area: 影厅的区域，可选。小城之春厅:左下|右下|中后 站台露天:中前|中后|右前|右后|左前|左后|看台右上|看台右下|看台左上|看台左下|
6. `activity_id` 无需改动

### 运行

1. 安装依赖 `pip install -r requirements.txt`
2. 运行程序 `python main.py`

运行结束后，会在`logs`目录下生成`pingyao.txt`文件，记录了抢票过程中的日志。如果抢票成功，会在`pay`目录下生成对应订单的文件，为电影票的二维码。

### 说明

1. 本程序仅供学习交流使用，不得用于商业用途。
