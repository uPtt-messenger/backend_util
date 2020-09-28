import time
import threading

from SingleLog.log import Logger
from PyPtt import PTT

from backend_util.src.event import EventConsole
from backend_util.src.errorcode import ErrorCode
from backend_util.src.msg import Msg
from backend_util.src.console import Console
from backend_util.src.config import Config
from backend_util.src import util
from tag import Tag


class Command:
    def __init__(self, console_obj, to_server: bool):
        self.login = False
        self.logout = False

        self.push_msg = list()

        self.login_id = None
        self.login_password = None
        self.logout = False
        self.close = False
        self.send_waterball_id = None
        self.send_waterball_content = None
        self.add_friend_id = None
        self.parameter = None
        self.res_msg = None

        self.console = console_obj
        self.to_server = to_server
        self.ptt_bot_lock = threading.Lock()

        self.logger = Logger('Command-' + ('Server' if to_server else 'Client'), self.console.config.log_level,
                             handler=self.console.config.log_handler)

    def check_token(self, msg):
        if msg is None:
            return False
        if Msg.key_token not in msg.data:
            return False

        current_token = msg.data[Msg.key_token]

        return self.console.login_token == current_token

    def _get_token_thread(self):
        for e in self.console.event.event_chain[EventConsole.key_send_token]:
            self.res_msg = e(self.parameter)

    def analyze(self, recv_msg: Msg):

        opt = recv_msg.get(Msg.key_opt)
        if opt == Msg.key_get_token:

            if self.console.role == Console.role_server:

                current_ptt_id = recv_msg.get(Msg.key_ptt_id)
                if current_ptt_id is None:
                    return
                self.logger.show(Logger.INFO, 'ptt_id', current_ptt_id)

                current_token = util.generate_token()
                self.logger.show(Logger.INFO, 'token', current_token)

                ptt_id = self.console.config.get_value(Config.level_SYSTEM, Config.key_ptt_id)
                ptt_pw = self.console.config.get_value(Config.level_SYSTEM, Config.key_ptt_pw)

                self.ptt_bot_lock.acquire()
                try:
                    self.parameter = (ptt_id, ptt_pw, current_ptt_id, current_token)
                    t = threading.Thread(target=self._get_token_thread)
                    t.start()
                    t.join()
                finally:
                    self.ptt_bot_lock.release()

                # Update token
                self.console.token_list.set_value(current_ptt_id.lower(), current_token)
                self.push(self.res_msg)
            else:
                # {"operation": "server_get_token", "code": 0, "msg": "Success"}
                error_code = recv_msg.get(Msg.key_code)
                if error_code == ErrorCode.Success:
                    self.logger.show(Logger.INFO, '伺服器已經送出 token')
                    self.console.event.execute(EventConsole.key_get_token)
                else:
                    # 送訊息到前端
                    self.console.command.push(Msg)

        elif opt == 'echo':
            current_res_msg = Msg(
                operate=opt,
                code=ErrorCode.Success,
                msg=recv_msg.get(Msg.key_msg))
            self.push(current_res_msg)

        elif opt == 'login':
            ptt_id = recv_msg.get(Msg.key_payload)[Msg.key_ptt_id]
            ptt_pass = recv_msg.get(Msg.key_payload)[
                Msg.key_ptt_pass]

            self.logger.show(
                Logger.INFO,
                '執行登入程序')

            res_msg = None

            for e in self.console.event.event_chain[EventConsole.key_login]:
                current_res_msg = e(ptt_id, ptt_pass)
                if current_res_msg is None:
                    continue
                if current_res_msg.get(Msg.key_code) != ErrorCode.Success:
                    self.push(current_res_msg)
                    self.logger.show(
                        Logger.INFO,
                        '登入程序中斷')
                    return
                res_msg = current_res_msg
            self.push(res_msg)

            self.logger.show(
                Logger.INFO,
                '登入程序全數完成')

        elif opt == 'logout':
            self.logger.show(
                Logger.INFO,
                '執行登出程序')
            # for e in self.console.event.logout:
            #     e()
            self.console.event.execute(EventConsole.key_logout)
            self.logger.show(
                Logger.INFO,
                '登出程序全數完成')

        elif opt == 'close':
            self.logger.show(
                Logger.INFO,
                '執行終止程序')
            self.console.event.execute(EventConsole.key_close)
            self.logger.show(
                Logger.INFO,
                '終止程序全數完成')

        elif opt == 'sendwaterball':
            if not self.check_token(recv_msg):
                self.logger.show(
                    Logger.INFO,
                    '權杖不相符')
                res_msg = Msg(
                    operate=opt,
                    code=ErrorCode.TokenNotMatch,
                    msg='Token not match')
                self.push(res_msg)
                return
            waterball_id = recv_msg.get(Msg.key_payload)[Msg.key_ptt_id]
            waterball_content = recv_msg.get(Msg.key_payload)[Msg.key_content]

            self.logger.show(
                Logger.INFO,
                '執行丟水球程序')
            # for e in self.console.event.send_waterball:
            #     e(waterball_id, waterball_content)
            self.console.event.execute(EventConsole.key_send_waterball, parameter=(waterball_id, waterball_content))
            self.logger.show(
                Logger.INFO,
                '丟水球程序全數完成')

        elif opt == 'getwaterballhistory':

            if not self.check_token(recv_msg):
                self.logger.show(
                    Logger.INFO,
                    'Token not match')
                res_msg = Msg(
                    operate=opt,
                    code=ErrorCode.TokenNotMatch,
                    msg='Token not match')
                self.push(res_msg)
                return

            target_id = recv_msg.data[Msg.key_payload][Msg.key_ptt_id]
            count = recv_msg.data[Msg.key_payload][Msg.key_count]

            if Msg.key_index in recv_msg.data[Msg.key_payload]:
                index = recv_msg.data[Msg.key_payload][Msg.key_index]
                history_list = self.console.dialogue.get(target_id, count, index=index)
            else:
                history_list = self.console.dialogue.get(target_id, count)

            current_res_msg = Msg(
                operate=opt,
                code=ErrorCode.Success,
                msg='Get history waterball success')

            payload = Msg()

            tag_name = Tag(self.console).get_tag(target_id)
            if tag_name is None:
                tag_name = ''

            payload.add(Msg.key_tag, tag_name)
            payload.add(Msg.key_list, history_list)
            current_res_msg.add(Msg.key_payload, payload)

            self.push(current_res_msg)
        elif opt == 'addfriend':
            self.add_friend_id = recv_msg.get(Msg.key_payload)[Msg.key_ptt_id]

        else:
            if self.to_server:
                self.logger.show(
                    Logger.INFO,
                    '收到來自伺服器不明訊息',
                    opt)
            else:
                current_res_msg = Msg(
                    operate=opt,
                    code=ErrorCode.Unsupported,
                    msg='Unsupported')
                self.push(current_res_msg)

    def push(self, push_msg):
        self.push_msg.append(push_msg.__str__())
