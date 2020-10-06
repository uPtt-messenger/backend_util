import json
import threading
import time
import urllib.request

from SingleLog.log import Logger
from .console import Console
from .config import Config
from .event import EventConsole


class DynamicData:
    def __init__(self, console_obj):

        self.logger = Logger('DynamicData', console_obj.config.log_level, handler=console_obj.config.log_handler)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        self.console = console_obj
        self.console.event.register(EventConsole.key_close, self.event_close)

        self.run_update = True
        self.update_state = False
        self.update_thread = None

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

        self.update()

    def event_close(self, p):

        self.logger.show(
            Logger.INFO,
            '執行終止程序')

        self.run_update = False
        if self.update_thread is not None:
            self.update_thread.join()

        self.logger.show(
            Logger.INFO,
            '終止程序完成')

    def run(self):

        while self.run_update:
            start_time = end_time = time.time()
            while end_time - start_time < self.console.config.update_cycle:
                time.sleep(self.console.config.quick_response_time)
                end_time = time.time()
                if not self.run_update:
                    break
            if not self.run_update:
                break
            self.update()

    def update(self):
        self.logger.show(
            Logger.INFO,
            '開始更新資料')

        if self.console.run_mode == Console.run_mode_dev:
            update_url = 'https://raw.githubusercontent.com/PttCodingMan/uPtt/develop/data/open_data.json'
        elif self.console.run_mode == Console.run_mode_release:
            update_url = 'https://raw.githubusercontent.com/PttCodingMan/uPtt/main/data/open_data.json'
        try:
            with urllib.request.urlopen(update_url) as url:
                data_temp = json.loads(url.read().decode())
        except urllib.error.URLError:
            self.logger.show(
                Logger.INFO,
                '更新資料失敗')
            self.update_state = False
            return

        self.update_state = True
        self.logger.show(
            Logger.INFO,
            '更新資料完成')
        self.data = data_temp

        self.version = self.data['version']
        self.tag_list = self.data['tag']
        self.black_list = self.data['black_list']
        self.announce = self.data['announce']
        self.online_server = self.data['online_server']

        self.logger.show(
            Logger.INFO,
            '發布版本',
            self.version)

        del_key_list = []
        for _, (hash_value, tag) in enumerate(self.tag_list.items()):
            if hash_value.startswith('//'):
                del_key_list.append(hash_value)
                continue
            if len(hash_value) != 64:
                del_key_list.append(hash_value)
                continue

        for del_key in del_key_list:
            del self.tag_list[del_key]

        for _, (hash_value, tag) in enumerate(self.tag_list.items()):
            self.logger.show(
                Logger.DEBUG,
                'tag',
                tag)

        if self.black_list:
            for block_user in self.black_list:
                self.logger.show(
                    Logger.INFO,
                    'block_user',
                    block_user)
        else:
            self.logger.show(
                Logger.INFO,
                '無黑名單')

        self.logger.show(
            Logger.INFO,
            'online_server',
            self.online_server)
