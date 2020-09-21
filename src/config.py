import json
import os

from single_log.log import Logger
from PyPtt import PTT

log_handler = None
log_level = Logger.INFO


def get_value_func(data, key):
    if key not in data:
        return None
    return data[key]


def set_value_func(data, key, value):
    value_change = False
    if value is not None:
        if key not in data:
            value_change = True
        elif data[key] != value:
            value_change = True

        data[key] = value
    elif key in data:
        # value is None
        if key in data:
            value_change = True
        del data[key]

    return value_change


def write_config(path, data):
    if path is None or data is None:
        return
    with open(path, 'w', encoding='utf8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


class Config:
    level_USER = 0
    level_SYSTEM = 1

    app_name = 'uPtt'

    key_aes_key = 'aes_key'
    key_version = 'version'

    version = '0.0.1'
    quick_response_time = 0.05
    query_cycle = 3.0 + quick_response_time
    update_cycle = 180
    port = 50732

    log_level = Logger.INFO
    log_handler = None

    ptt_log_level = PTT.log.level.INFO
    ptt_log_handler = None

    feedback_port = 57983
    feedback_frequency = 60

    def __init__(self):

        # 不想給使用者改的設定值就寫在這兒
        # 想給使用者改的就透過 setValue
        # 因為會被存起來

        self.config_file_name = 'config.json'
        self.system_config_file_name = 'system_config.json'
        self.friend_file_name = 'friend.txt'

        self.config_path = None

        self.logger = Logger('Config', log_level, handler=log_handler)
        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        if os.name == 'nt':
            self.logger.show(
                Logger.INFO,
                '作業系統',
                'Windows')

            # C:\ProgramData
            self.config_path = f"{os.environ['ALLUSERSPROFILE']}/{self.app_name}"

        self.system_config_path = f'{self.config_path}/{self.system_config_file_name}'
        self.user_config_path = None

        if not os.path.exists(self.config_path):
            os.makedirs(self.config_path)

        try:
            with open(self.system_config_path, encoding='utf8') as f:
                self.system_data = json.load(f)
        except FileNotFoundError:
            self.system_data = dict()
            self.set_value(self.level_SYSTEM, self.key_version, self.version)

        self.user_data = dict()
        self.id = None

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

    def init_user(self, ptt_id):
        self.logger.show(
            Logger.INFO,
            '使用者空間初始化',
            ptt_id)
        self.id = ptt_id
        self.user_config_path = f'{self.config_path}/{ptt_id}/{self.config_file_name}'
        if not os.path.exists(f'{self.config_path}/{ptt_id}'):
            os.makedirs(f'{self.config_path}/{ptt_id}')

            # init user config here

        self.logger.show(
            Logger.INFO,
            '使用者設定初始化',
            ptt_id)

        try:
            with open(self.user_config_path, encoding='utf8') as File:
                self.user_data = json.load(File)
        except FileNotFoundError:
            pass

    def get_value(self, level, key):

        if level == self.level_SYSTEM:
            return get_value_func(self.system_data, key)
        elif level == self.level_USER:
            return get_value_func(self.user_data, key)
        else:
            raise ValueError()

    def set_value(self, level, key, value):

        if level == self.level_SYSTEM:
            value_change = set_value_func(self.system_data, key, value)
            if value_change:
                write_config(self.system_config_path, self.system_data)

        elif level == self.level_USER:
            value_change = set_value_func(self.user_data, key, value)
            if value_change:
                write_config(self.user_config_path, self.user_data)
        else:
            raise ValueError()
