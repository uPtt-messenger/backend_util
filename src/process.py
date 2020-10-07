import threading
import time

from SingleLog.log import Logger

from backend_util.src.console import Console
from backend_util.src.config import Config
from backend_util.src.event import EventConsole
from backend_util.src.errorcode import ErrorCode
from backend_util.src.msg import Msg
from backend_util.src import util


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

        # logout process
        self.console.event.register(EventConsole.key_logout, self.logout)
        self.console.event.register(EventConsole.key_close, self.logout)
        
        if self.console.role == Console.role_server:
            t = threading.Thread(target=self.check_online)
            t.daemon = True
            t.start()

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

    def logout(self, _):

        self.break_login_process = False

        self.login_ptt_login_complete = False
        self.login_find_token_complete = False
        self.login_find_key_complete = False

        current_time = int(time.time())

        hash_result = util.get_verify_hash(current_time, self.console.token, Msg.key_logout)

        push_msg = Msg(operate=Msg.key_logout_success)
        push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
        push_msg.add(Msg.key_timestamp, current_time)
        push_msg.add(Msg.key_hash, hash_result)
        self.console.server_command.push(push_msg)

    def run_login(self):

        t = threading.Thread(target=self.login)
        t.start()

    def login(self):

        self.logger.show(
            Logger.INFO,
            '登入流程',
            '啟動')

        push_msg = Msg(
            operate=Msg.key_notify,
            code=ErrorCode.Success,
            msg='uPtt 登入流程啟動')
        self.console.command.push(push_msg)

        while not self.login_ptt_login_complete and not self.break_login_process:
            time.sleep(0.1)
        if self.break_login_process:
            return

        push_msg = Msg(
            operate=Msg.key_notify,
            code=ErrorCode.Success,
            msg='PTT 登入流程成功')
        self.console.command.push(push_msg)

        push_msg = Msg(
            operate=Msg.key_notify,
            code=ErrorCode.Success,
            msg='取得 uPtt 權杖流程啟動')
        self.console.command.push(push_msg)

        while not self.login_find_token_complete and not self.break_login_process:
            time.sleep(0.1)
        if self.break_login_process:
            self.console.event.execute(EventConsole.key_logout)
            return

        push_msg = Msg(
            operate=Msg.key_notify,
            code=ErrorCode.Success,
            msg='取得 uPtt 權杖流程成功')
        self.console.command.push(push_msg)

        push_msg = Msg(
            operate=Msg.key_notify,
            code=ErrorCode.Success,
            msg='加密流程啟動')
        self.console.command.push(push_msg)

        while not self.login_find_key_complete and not self.break_login_process:
            time.sleep(0.1)
        if self.break_login_process:
            self.console.event.execute(EventConsole.key_logout)
            return

        push_msg = Msg(
            operate=Msg.key_notify,
            code=ErrorCode.Success,
            msg='加密流程成功')
        self.console.command.push(push_msg)

        push_msg = Msg(
            operate=Msg.key_login,
            code=ErrorCode.Success,
            msg='Login success')

        if self.console.run_mode == Console.run_mode_dev:
            hash_id = util.sha256(self.console.ptt_id)
            if hash_id == 'c2c10daa1a61f1757019e995223ad346284e13462c62ee9dccac433445248899':
                token = util.sha256(f'{self.console.ptt_id} fixed token')
            else:
                token = util.generate_token()
        else:
            token = util.generate_token()

        self.console.login_token = token

        payload = Msg()
        payload.add(Msg.key_token, token)
        push_msg.add(Msg.key_payload, payload)

        self.console.command.push(push_msg)

        # 為了 log 呈現上時序不會亂掉 sleep 一下
        time.sleep(0.01)

        current_time = int(time.time())

        hash_result = util.get_verify_hash(current_time, self.console.token, Msg.key_login_success)

        push_msg = Msg(operate=Msg.key_login_success)
        push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
        push_msg.add(Msg.key_timestamp, current_time)
        push_msg.add(Msg.key_hash, hash_result)
        self.console.server_command.push(push_msg)

        self.console.login_complete = True

        t = threading.Thread(target=self.heartbeat)
        t.daemon = True
        t.start()

        self.logger.show(
            Logger.INFO,
            '登入流程',
            '完成')

    def heartbeat(self):

        self.logger.show(Logger.INFO, '心跳核心', '初始化', '啟動')
        self.logger.show(Logger.INFO, '心跳核心', '傳送間隔時間', Config.heartbeat_time)
        self.logger.show(Logger.INFO, '心跳核心', '初始化', '完成')

        while self.console.login_complete:

            time.sleep(Config.heartbeat_time)

            current_time = int(time.time())

            hash_result = util.get_verify_hash(current_time, self.console.token, Msg.key_heartbeat)

            push_msg = Msg(operate=Msg.key_heartbeat)
            push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
            push_msg.add(Msg.key_timestamp, current_time)
            push_msg.add(Msg.key_hash, hash_result)
            self.console.server_command.push(push_msg)


    def check_online(self):

        self.logger.show(Logger.INFO, '修正線上人數核心', '初始化', '啟動')
        check_time = int(Config.heartbeat_time * 1.1)
        self.logger.show(Logger.INFO, '修正線上人數核心', '修正間隔時間', check_time)
        self.logger.show(Logger.INFO, '修正線上人數核心', '初始化', '完成')

        while True:
            time.sleep(check_time)

            current_time = int(time.time())

            self.logger.show(Logger.INFO, '修正線上人數', '啟動')

            self.console.command.max_online_lock.acquire()

            remove_list = list()

            for ptt_id in self.console.connect_time.data:
                connect_time = self.console.connect_time.get_value(ptt_id)
                if abs(current_time - connect_time) > check_time:
                    remove_list.append(ptt_id)

            for ptt_id in remove_list:
                self.logger.show(Logger.INFO, '剔除使用者', ptt_id, '啟動')
                self.console.connect_list.set_value(ptt_id, None)
                self.console.connect_time.set_value(ptt_id, None)
                self.logger.show(Logger.INFO, '剔除使用者', ptt_id, '完成')

            self.console.command.max_online_lock.release()

            self.logger.show(Logger.INFO, '修正線上人數', '完成')


if __name__ == '__main__':
    qq = {
        '1': 'time1',
        '2': 'time2'
    }

    for id in qq:
        print(id)
        print(qq[id])
