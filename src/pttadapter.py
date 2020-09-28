import datetime
import threading
import time

from PyPtt import PTT

from SingleLog.log import Logger
from dialogue import Dialogue
from backend_util.src.errorcode import ErrorCode
from backend_util.src.msg import Msg
from backend_util.src import util
from backend_util.src.event import EventConsole


class PTTAdapter:
    def __init__(self, console_obj):

        self.logger = Logger('PTTAdapter', console_obj.config.log_level, handler=console_obj.config.log_handler)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        self.console = console_obj

        self.console.event.register(EventConsole.key_login, self.event_login)
        self.console.event.register(EventConsole.key_logout, self.event_logout)
        self.console.event.register(EventConsole.key_close, self.event_logout)
        self.console.event.register(EventConsole.key_close, self.event_close)
        self.console.event.register(EventConsole.key_send_waterball, self.event_send_waterball)

        # server
        self.console.event.register(EventConsole.key_send_token, self.event_send_token)

        self.dialogue = None

        self.bot = None
        self.ptt_id = None
        self.ptt_pw = None

        self.recv_logout = False

        self.run_server = True
        self.login = False

        self.has_new_mail = False
        self.res_msg = None

        self.send_waterball_list = []
        self.send_waterball_complete = True
        self.send_waterball = False

        self.init_bot()

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

        self.thread = threading.Thread(
            target=self.run,
            daemon=True)
        self.thread.start()
        time.sleep(0.5)

    def init_bot(self):
        self.ptt_id = None
        self.ptt_pw = None

        self.recv_logout = False

        self.login = False

        self.send_waterball_list = []

        self.has_new_mail = False

    def event_logout(self, p):
        self.recv_logout = True

    def event_close(self, p):
        self.logger.show(
            Logger.INFO,
            '執行終止程序')
        # self.logout()
        self.run_server = False
        self.thread.join()
        self.logger.show(
            Logger.INFO,
            '終止程序完成')

    def event_login(self, ptt_id, ptt_pw):

        self.ptt_id = ptt_id
        self.ptt_pw = ptt_pw

        while self.ptt_id is not None:
            time.sleep(self.console.config.quick_response_time)

        return self.res_msg

    def event_send_waterball(self, parameter):

        waterball_id, waterball_content = parameter

        self.send_waterball_complete = False

        self.send_waterball_list.append(
            (waterball_id, waterball_content))

        self.send_waterball = True

        while not self.send_waterball_complete:
            time.sleep(self.console.config.quick_response_time)

    def event_send_token(self, parameter):
        ptt_id, ptt_pw, target_id, token = parameter

        content = list()
        content.append('------- uPtt token start -------')
        content.append(token)
        content.append('------- uPtt token end -------')
        content.append('請勿刪除此信 by uPtt')
        content = '\r'.join(content)

        max_try = 3
        self.bot = PTT.API()
        for try_count in range(max_try):
            try:
                self.bot.login(ptt_id, ptt_pw, kick_other_login=True)
                break
            except PTT.exceptions.LoginError:
                self.logger.show(Logger.INFO, '登入失敗')
                return Msg(
                    operate=Msg.key_get_token,
                    code=ErrorCode.UnknownError,
                    msg='Unknown Error')
            except PTT.exceptions.WrongIDorPassword:
                self.logger.show(Logger.INFO, '帳號密碼錯誤')
                return Msg(
                    operate=Msg.key_get_token,
                    code=ErrorCode.WrongIDPW,
                    msg='Wrong PTT ID PW')
            except PTT.exceptions.LoginTooOften:
                if try_count != max_try - 1:
                    self.logger.show(Logger.INFO, '請稍等一下再登入')
                    time.sleep(5)
                else:
                    return Msg(
                        operate=Msg.key_get_token,
                        code=ErrorCode.TryLater,
                        msg='Try Later')

        res_msg = None
        try:
            self.bot.mail(
                target_id,
                'uPtt token',
                content,
                0)
        except PTT.exceptions.NoSuchUser:
            res_msg = Msg(
                operate=Msg.key_get_token,
                code=ErrorCode.NoSuchUser,
                msg='NoSuchUser')
        finally:
            self.bot.logout()

        if res_msg is not None:
            return res_msg

        return Msg(
            operate=Msg.key_get_token,
            code=ErrorCode.Success,
            msg='Success')

    def event_get_token(self):
        self.logger.show(
            Logger.INFO,
            '搜尋 Token')

        mail_index = self.bot.get_newest_index(PTT.data_type.index_type.MAIL)
        self.logger.show(
            Logger.INFO,
            '最新信件編號',
            mail_index)

        token_index = 0
        key_index = 0
        for i in reversed(range(1, mail_index + 1)):
            self.logger.show(
                Logger.INFO,
                '檢查信件編號',
                i)

            mail_info = self.bot.get_mail(i)
            if mail_info.title is None:
                continue

            if 'uPtt token' in mail_info.title:
                token_index = i
                print(mail_info.content)

        if token_index == 0 or True:
            push_msg = Msg(operate=Msg.key_get_token)
            push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
            self.console.server_command.push(push_msg)

        elif key_index == 0:
            pass
    def run(self):

        self.logger.show(
            Logger.INFO,
            'PTT 溝通核心初始化',
            '啟動')

        self.bot = PTT.API(
            log_handler=self.console.config.ptt_log_handler,
            # log_level=self.console.config.ptt_log_level
            log_level=Logger.SILENT)

        self.logger.show(
            Logger.INFO,
            'PTT 溝通核心初始化',
            '完成')
        while self.run_server:
            # 快速反應區
            start_time = end_time = time.time()
            while end_time - start_time < self.console.config.query_cycle:

                if not self.run_server:
                    break

                if (self.ptt_id, self.ptt_pw) != (None, None):
                    self.logger.show(
                        Logger.INFO,
                        '執行登入')
                    try:
                        self.bot.login(
                            self.ptt_id,
                            self.ptt_pw,
                            kick_other_login=True)

                        self.console.ptt_id = self.ptt_id
                        self.console.ptt_pw = self.ptt_pw

                        self.console.config.init_user(self.ptt_id)
                        # self.dialogue = Dialogue(self.console)
                        # self.console.dialogue = self.dialogue

                        self.login = True
                        self.bot.set_call_status(PTT.data_type.call_status.OFF)
                        self.bot.get_waterball(PTT.data_type.waterball_operate_type.CLEAR)

                        self.res_msg = Msg(
                            operate=Msg.key_login,
                            code=ErrorCode.Success,
                            msg='Login success')

                        if self.console.run_mode == 'dev':
                            hash_id = util.sha256(self.ptt_id)
                            if hash_id == 'c2c10daa1a61f1757019e995223ad346284e13462c62ee9dccac433445248899':
                                token = util.sha256(f'{self.ptt_id} fixed token')
                            else:
                                token = util.generate_token()
                        else:
                            token = util.generate_token()

                        self.console.login_token = token

                        payload = Msg()
                        payload.add(Msg.key_token, token)

                        self.res_msg.add(Msg.key_payload, payload)

                        self.console.event.execute(EventConsole.key_login_success)

                    except PTT.exceptions.LoginError:
                        self.res_msg = Msg(
                            operate=Msg.key_login,
                            code=ErrorCode.LoginFail,
                            msg='Login fail')
                    except PTT.exceptions.WrongIDorPassword:
                        self.res_msg = Msg(
                            operate=Msg.key_login,
                            code=ErrorCode.LoginFail,
                            msg='ID or PW error')
                    except PTT.exceptions.LoginTooOften:
                        self.res_msg = Msg(
                            operate=Msg.key_login,
                            code=ErrorCode.LoginFail,
                            msg='Please wait a moment before login')
                    self.ptt_id = None
                    self.ptt_pw = None

                    ddddd

                if self.login:

                    if self.recv_logout:
                        self.logger.show(
                            Logger.INFO,
                            '執行登出')

                        self.bot.logout()

                        res_msg = Msg(
                            operate=Msg.key_logout,
                            code=ErrorCode.Success,
                            msg='Logout success')

                        self.console.command.push(res_msg)

                        self.init_bot()

                    if self.send_waterball:

                        while self.send_waterball_list:
                            waterball_id, waterball_content = self.send_waterball_list.pop()

                            try:
                                self.logger.show(
                                    Logger.INFO,
                                    '準備丟水球')
                                self.bot.throw_waterball(waterball_id, waterball_content)
                                self.logger.show(
                                    Logger.INFO,
                                    '丟水球完畢，準備儲存')

                                current_dialogue_msg = Msg()
                                current_dialogue_msg.add(Msg.key_ptt_id, waterball_id)
                                current_dialogue_msg.add(Msg.key_content, waterball_content)
                                current_dialogue_msg.add(Msg.key_msg_type, 'send')

                                timestamp = int(datetime.datetime.now().timestamp())
                                current_dialogue_msg.add(Msg.key_timestamp, timestamp)

                                # self.dialogue.save(current_dialogue_msg)

                                res_msg = Msg(
                                    operate=Msg.key_sendwaterball,
                                    code=ErrorCode.Success,
                                    msg='send waterball success')
                            except PTT.exceptions.NoSuchUser:
                                self.logger.show(Logger.INFO, '無此使用者')
                                res_msg = Msg(
                                    operate=Msg.key_sendwaterball,
                                    code=ErrorCode.NoSuchUser,
                                    msg='No this user')
                            except PTT.exceptions.UserOffline:
                                self.logger.show(Logger.INFO, '使用者離線')
                                res_msg = Msg(
                                    operate=Msg.key_sendwaterball,
                                    code=ErrorCode.UserOffLine,
                                    msg='User offline')
                            self.console.command.push(res_msg)

                        self.send_waterball_complete = True
                        self.send_waterball = False

                    # addfriend_id = self.command.addfriend()
                    # if addfriend_id is not None:
                    #     try:
                    #         user = self.bot.getUser(addfriend_id)
                    #
                    #         res_msg = Msg(
                    #             ErrorCode.Success,
                    #             '新增成功'
                    #         )
                    #
                    #     except PTT.exceptions.NoSuchUser:
                    #         print('無此使用者')

                time.sleep(self.console.config.quick_response_time)
                end_time = time.time()

            if not self.login:
                continue

            # 慢速輪詢區
            self.logger.show(
                Logger.DEBUG,
                '慢速輪詢')

            try:
                waterball_list = self.bot.get_waterball(PTT.data_type.waterball_operate_type.CLEAR)
            except:
                self.ptt_id = self.console.ptt_id
                self.ptt_pw = self.console.ptt_pw
                continue

            self.logger.show(
                Logger.DEBUG,
                '取得水球')

            if waterball_list is not None:
                for waterball in waterball_list:
                    if not waterball.type == PTT.data_type.waterball_type.CATCH:
                        continue

                    waterball_id = waterball.target
                    waterball_content = waterball.content
                    waterball_date = waterball.date

                    self.logger.show(
                        Logger.INFO,
                        f'收到來自 {waterball_id} 的水球',
                        f'[{waterball_content}][{waterball_date}]')

                    # 01/07/2020 10:46:51
                    # 02/24/2020 15:40:34
                    date_part1 = waterball_date.split(' ')[0]
                    date_part2 = waterball_date.split(' ')[1]

                    year = int(date_part1.split('/')[2])
                    month = int(date_part1.split('/')[0])
                    day = int(date_part1.split('/')[1])

                    hour = int(date_part2.split(':')[0])
                    minute = int(date_part2.split(':')[1])
                    sec = int(date_part2.split(':')[2])

                    # print(f'waterball_date {waterball_date}')
                    # print(f'year {year}')
                    # print(f'month {month}')
                    # print(f'day {day}')
                    # print(f'hour {hour}')
                    # print(f'minute {minute}')
                    # print(f'sec {sec}')

                    waterball_timestamp = int(datetime.datetime(year, month, day, hour, minute, sec).timestamp())
                    # print(f'waterball_timestamp {waterball_timestamp}')

                    payload = Msg()
                    payload.add(Msg.key_ptt_id, waterball_id)
                    payload.add(Msg.key_content, waterball_content)
                    payload.add(Msg.key_timestamp, waterball_timestamp)

                    push_msg = Msg(operate=Msg.key_recvwaterball)
                    push_msg.add(Msg.key_payload, payload)

                    current_dialogue_msg = Msg()
                    current_dialogue_msg.add(Msg.key_ptt_id, waterball_id)
                    current_dialogue_msg.add(Msg.key_content, waterball_content)
                    current_dialogue_msg.add(Msg.key_msg_type, 'receive')
                    current_dialogue_msg.add(Msg.key_timestamp, waterball_timestamp)

                    # self.dialogue.save(current_dialogue_msg)

                    # self.dialog.recv(waterball_target, waterball_content, waterball_date)

                    p = (waterball_id, waterball_content, waterball_timestamp)
                    self.console.event.execute(EventConsole.key_recv_waterball, parameter=p)

                    self.console.command.push(push_msg)

            try:
                new_mail = self.bot.has_new_mail()
            except:
                self.ptt_id = self.console.ptt_id
                self.ptt_pw = self.console.ptt_pw
                continue
            self.logger.show(
                Logger.DEBUG,
                '取得新信')

            if new_mail > 0 and not self.has_new_mail:
                self.has_new_mail = True
                push_msg = Msg(
                    operate=Msg.key_notify)
                push_msg.add(Msg.key_msg, f'You have {new_mail} mails')

                self.console.command.push(push_msg)
            else:
                self.has_new_mail = False

        self.logger.show(
            Logger.INFO,
            '關閉成功')
