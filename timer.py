import time
from datetime import datetime
from config import global_config
from logger import logger


class Timer(object):
    def __init__(self, sleep_interval=0.5):
        self.run_time = datetime.strptime(
            global_config["run_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        self.sleep_interval = sleep_interval

    def start(self):
        logger.info("正在等待到达设定时间:%s" % self.run_time)
        now_time = datetime.now
        while True:
            if now_time() >= self.run_time:
                logger.info("时间到达，开始执行")
                break
            else:
                time.sleep(self.sleep_interval)
