import json

from SingleLog.log import Logger
from backend_util.src import config
from backend_util.src import util


class DictData:
    def __init__(self, console_obj, data_name, save_path=None):

        self.console = console_obj
        self.logger = Logger(f'Data-{data_name}', config.log_level, handler=config.log_handler)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        save_path = util.clean_path(save_path)
        self.save_path = save_path

        self.data_name = data_name
        self.data = dict()

        if self.save_path is not None:
            util.mkdir(self.save_path)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

    def __len__(self):
        return len(self.data)

    def load(self):

        if not self.save_path:
            return False

        data_file = f'{self.save_path}/{self.data_name}.json'

        self.logger.show(Logger.INFO, '載入檔案', '啟動', data_file)
        try:
            with open(data_file, encoding='utf8') as f:
                temp_data = json.load(f)
        except FileNotFoundError:
            self.logger.show(Logger.INFO, '載入檔案', '失敗', '檔案不存在')
            temp_data = None

        if temp_data is not None:
            self.data = temp_data
            self.logger.show(Logger.INFO, '載入檔案', '成功')

        return temp_data is not None

    def save(self):
        # self.logger.show(Logger.INFO, '儲存檔案', '啟動')
        if self.save_path is None or self.data is None:
            self.logger.show(Logger.INFO, '儲存檔案', '失敗')
            return
        with open(f'{self.save_path}/{self.data_name}.json', 'w', encoding='utf8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        # self.logger.show(Logger.INFO, '儲存檔案', '成功')

    def get_value(self, key):

        key = str(key)

        if key not in self.data:
            return None
        return self.data[key]

    def _set_value_func(self, key, value):

        key = str(key)

        value_change = False
        if value is not None:
            if key not in self.data:
                value_change = True
            elif self.data[key] != value:
                value_change = True

            self.data[key] = value
        elif key in self.data:
            # value is None
            if key in self.data:
                value_change = True
            del self.data[key]

        if value_change:
            if key not in self.data:
                self.logger.show(Logger.INFO, '已經清空資料', key)
            else:
                if isinstance(self.data[key], str) or isinstance(self.data[key], int):
                    self.logger.show(Logger.INFO, '已經更新資料', key, self.data[key])
                else:
                    self.logger.show(Logger.INFO, '已經更新資料', key)
        else:
            self.logger.show(Logger.INFO, '資料沒有更動', key, '沒有更動')

        return value_change

    def set_value(self, key, value):

        key = str(key)
        value_change = self._set_value_func(key, value)
        if value_change and self.save_path:
            self.save()
        return value_change


if __name__ == '__main__':
    pass
    # from backend_util.src.console import Console
    # from backend_util.src.config import Config
    #
    # console_obj = Console()
    # console_obj.role = Console.role_client
    #
    # config_obj = Config(console_obj)
    # console_obj.config = config_obj


