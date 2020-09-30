import sys
import os
import json

from SingleLog.log import Logger
from PyPtt import PTT

from .console import Console
from .data import DictData
from backend_util.src import util

log_handler = None
log_level = Logger.INFO


class Config:
    level_USER = 0
    level_SYSTEM = 1

    app_name = 'uPtt'

    config_file_name = 'config.json'
    system_config_file_name = 'system_config.json'
    friend_file_name = 'friend.txt'

    key_version = 'version'
    key_ptt_id = 'ptt_id'
    key_ptt_pw = 'ptt_pw'

    version = '0.0.1'
    quick_response_time = 0.05
    query_cycle = 3.0 + quick_response_time
    update_cycle = 180
    port = 50732

    log_level = Logger.INFO
    log_handler = None

    ptt_log_level = PTT.log.level.INFO
    ptt_log_handler = None

    server_port = 57983
    server_frequency = 60

    system_mail_title = '-----uPtt system-----'

    token_title = 'uPtt token'
    token_start = f'-----BEGIN uPtt token-----'
    token_end = f'-----END uPtt token-----'

    key_title = '-----uPtt key-----'

    key_private_key = 'PRIVATE KEY'
    key_private_start = f'-----BEGIN PRIVATE KEY-----'
    key_private_end = f'-----END PRIVATE KEY-----'

    admin_list = [
        '6fbc54708c7fcf16ef15511919f203186bfb22bb53b6ad631796d0373a86f400',
        '7d3850c0f2cdac6cf799a8a5b5f80c803ee250a5cf7f947337e11463661d3999',
        '6e44bf549ce0fb7c67d9e96d6237f14f19860061393f468c78e7da245cda555a'
    ]

    def __init__(self, console_obj):

        # 不想給使用者改的設定值就寫在這兒
        # 想給使用者改的就透過 setValue
        # 因為會被存起來

        self.console = console_obj

        self.config_path = None

        self.logger = Logger('Config', log_level, handler=log_handler)
        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        if self.console.role == Console.role_client:
            # client
            if os.name == 'nt':
                self.logger.show(
                    Logger.INFO,
                    '作業系統',
                    'Windows')

                # C:\ProgramData
                self.config_path = f"{os.environ['ALLUSERSPROFILE']}/{self.app_name}"

            self.system_config_path = None
            self.user_config_path = None

            util.mkdir(self.config_path)

            self.user_data = None
            self.id = None

        else:
            # server
            self.config_path = '.'
            self.system_config_path = '.'

            self.system_data = DictData(
                self.console,
                self.system_config_path,
                'SystemConfig')

            load_default = False
            if not self.system_data.load():
                # 載入系統預設資料
                load_default = True

            if not load_default:

                current_value = self.system_data.get_value(self.key_ptt_id)
                if not current_value:
                    self.logger.show(Logger.INFO, f'系統設定檔值', self.key_ptt_id, '不存在')
                    load_default = True
                elif len(current_value) == 0:
                    self.logger.show(Logger.INFO, f'系統設定檔值', self.key_ptt_id, '無實際數值')
                    load_default = True

                current_value = self.system_data.get_value(self.key_ptt_pw)
                if not current_value:
                    self.logger.show(Logger.INFO, f'系統設定檔值', self.key_ptt_pw, '不存在')
                    load_default = True
                elif len(current_value) == 0:
                    self.logger.show(Logger.INFO, f'系統設定檔值', self.key_ptt_pw, '無實際數值')
                    load_default = True

            if load_default:
                self.logger.show(Logger.INFO, '系統設定檔初始化', '啟動')
                self.system_data.set_value(self.key_ptt_id, '')
                self.system_data.set_value(self.key_ptt_pw, '')
                self.logger.show(Logger.INFO, '系統設定檔初始化', '完成')
                self.logger.show(Logger.INFO, '請修改設定檔內容再執行')
                sys.exit()

            else:
                self.logger.show(Logger.INFO, '系統設定檔', '設定檢查', '成功')

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

    def init_user(self, ptt_id):
        self.logger.show(
            Logger.INFO,
            '使用者設定值初始化',
            ptt_id)
        self.id = ptt_id
        self.user_config_path = f'{self.config_path}/{ptt_id}'

        self.system_data = DictData(
            self.console,
            self.user_config_path,
            'system_config')
        if not self.system_data.load():
            # 載入系統預設資料
            pass

        self.user_data = DictData(
            self.console,
            self.user_config_path,
            'config')
        if not self.user_data.load():
            # init user config
            self.user_data.set_value(self.key_ptt_id, self.id)

    def check_value(self, level, key, value, default_value):
        if value is None:
            self.set_value(level, key, default_value)
            return False
        return True

    def get_value(self, level, key):

        if level == self.level_SYSTEM:
            return self.system_data.get_value(key)
        elif level == self.level_USER:
            return self.user_data.get_value(key)
        else:
            raise ValueError()

    def set_value(self, level, key, value):

        if level == self.level_SYSTEM:
            self.system_data.set_value(key, value)
        elif level == self.level_USER:
            self.user_data.set_value(key, value)
        else:
            raise ValueError()
