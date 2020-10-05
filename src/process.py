import threading
import time

from SingleLog.log import Logger

from backend_util.src.msg import Msg
from backend_util.src.event import EventConsole


class Process:
    def __init__(self, console_obj):
        self.console = console_obj

        self.logger = Logger(
            'Process',
            self.console.config.log_level,
            handler=self.console.config.log_handler)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        # login process
        self.break_login_process = False

        self.login_ptt_login_complete = False
        self.login_find_token_complete = False
        self.login_find_key_complete = False

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

    def run_login(self):

        self.break_login_process = False

        self.login_ptt_login_complete = False
        self.login_find_token_complete = False
        self.login_find_key_complete = False

        t = threading.Thread(target=self.login)
        t.start()

    def login(self):

        self.logger.show(
            Logger.INFO,
            '登入流程',
            '啟動')

        push_msg = Msg(
            operate=Msg.key_notify,
            msg='PTT 登入流程啟動')
        self.console.command.push(push_msg)

        while not self.login_ptt_login_complete and not self.break_login_process:
            time.sleep(0.5)
        if self.break_login_process:
            return

        push_msg = Msg(
            operate=Msg.key_notify,
            msg='PTT 登入流程成功')
        self.console.command.push(push_msg)

        push_msg = Msg(
            operate=Msg.key_notify,
            msg='取得 uPtt 權杖流程啟動')
        self.console.command.push(push_msg)

        while not self.login_find_token_complete and not self.break_login_process:
            time.sleep(0.5)
        if self.break_login_process:
            self.console.event.execute(EventConsole.key_logout)
            return

        push_msg = Msg(
            operate=Msg.key_notify,
            msg='取得 uPtt 權杖流程成功')
        self.console.command.push(push_msg)

        push_msg = Msg(
            operate=Msg.key_notify,
            msg='加密流程啟動')
        self.console.command.push(push_msg)

        while not self.login_find_key_complete and not self.break_login_process:
            time.sleep(0.5)
        if self.break_login_process:
            self.console.event.execute(EventConsole.key_logout)
            return

        push_msg = Msg(
            operate=Msg.key_notify,
            msg='加密流程成功')
        self.console.command.push(push_msg)

        self.console.event.execute(EventConsole.key_login_success)

        self.logger.show(
            Logger.INFO,
            '登入流程',
            '完成')
