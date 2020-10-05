import datetime
import threading
import time

from PyPtt import PTT
from SingleLog.log import Logger

from backend_util.src.console import Console
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

        if self.console.role == Console.role_client:
            self.console.event.register(EventConsole.key_login, self.event_login)
            self.console.event.register(EventConsole.key_logout, self.event_logout)
            self.console.event.register(EventConsole.key_close, self.event_logout)
            self.console.event.register(EventConsole.key_close, self.event_close)
            self.console.event.register(EventConsole.key_send_waterball, self.event_send_waterball)
            self.console.event.register(EventConsole.key_get_token, self.event_get_token)
        else:
            self.console.event.register(EventConsole.key_send_token, self.event_send_token)

        self.dialogue = None

        self.bot = None
        self.ptt_id = None
        self.ptt_pw = None

        self.recv_logout = False

        self.run_server = True

        self.last_new_mail = 0
        self.res_msg = None

        self.send_waterball_list = []
        self.send_waterball_complete = True
        self.send_waterball = False
        self.run_find_token_process = False

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

        self.send_waterball_list = []

        self.last_new_mail = 0

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

        self.console.process.run_login()

        self.ptt_id = ptt_id
        self.ptt_pw = ptt_pw

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
        content.append(self.console.config.token_start)
        content.append(token)
        content.append(self.console.config.token_end)
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
                self.console.config.system_mail_title,
                content,
                0,
                backup=False)
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

    def event_get_token(self, _):
        self.run_find_token_process = True

        while self.run_find_token_process:
            time.sleep(0.1)

    def _check_system_mail(self, mail_info, check_self):
        author = mail_info.author
        author = author[:author.find('(')].strip()

        malicious_mail = False
        if check_self:
            if self.console.ptt_id != author:
                malicious_mail = True
        else:
            if util.sha256(author) not in self.console.config.admin_list:
                malicious_mail = True

        if malicious_mail:
            # 偽造的信
            self.logger.show(Logger.INFO, '偽造信件', '作者', mail_info.author)
            self.logger.show(Logger.INFO, '偽造信件', '內容', mail_info.content)
            return False

        return True

    def _event_get_token(self, _):
        self.logger.show(
            Logger.INFO,
            '搜尋 Token and key')

        try:
            mail_index = self.bot.get_newest_index(
                PTT.data_type.index_type.MAIL,
                # search_type=PTT.data_type.mail_search_type.KEYWORD,
                # search_condition=self.console.config.system_mail_key
            )
        except PTT.exceptions.NoSearchResult:
            self.logger.show(
                Logger.INFO,
                '無搜尋結果，準備請求 token')

            push_msg = Msg(operate=Msg.key_get_token)
            push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
            self.console.server_command.push(push_msg)
            return

        self.logger.show(
            Logger.INFO,
            '最新信件編號',
            mail_index)

        find_token = False
        find_key = False
        for i in reversed(range(1, mail_index + 1)):
            self.logger.show(
                Logger.INFO,
                '檢查信件編號',
                i)

            mail_info = self.bot.get_mail(
                i,
                # search_type=PTT.data_type.mail_search_type.KEYWORD,
                # search_condition=self.console.config.system_mail_key
            )
            if mail_info.title is None:
                continue
            if mail_info.author is None:
                continue
            if mail_info.content is None:
                continue

            if self.console.config.system_mail_title != mail_info.title:
                continue

            if self.console.token is None:
                if self.console.config.token_start in mail_info.content and \
                        self.console.config.token_end in mail_info.content:

                    if not self._check_system_mail(mail_info, False):
                        continue

                    find_token = True
                    self.logger.show(Logger.INFO, 'mail content', mail_info.content)

                    token = util.get_substring(
                        mail_info.content,
                        self.console.config.token_start,
                        self.console.config.token_end)

                    self.logger.show(Logger.INFO, 'token', token)
                    self.console.token = token

                    self.console.process.login_find_token_complete = True
            else:
                self.console.process.login_find_token_complete = True
                find_token = True

            if self.console.public_key is None or self.console.private_key is None:
                if self.console.config.key_private_start in mail_info.content and \
                        self.console.config.key_private_end in mail_info.content:

                    if not self._check_system_mail(mail_info, True):
                        continue

                    find_key = True
                    self.logger.show(Logger.INFO, 'mail content', mail_info.content)

                    private_key = util.get_substring(
                        mail_info.content,
                        self.console.config.key_private_start,
                        self.console.config.key_private_end)

                    self.logger.show(
                        Logger.INFO,
                        'private_key',
                        private_key)
                    self.console.process.login_find_key_complete = True
            else:
                find_key = True
                self.console.process.login_find_key_complete = True

        if not find_token:

            self.logger.show(
                Logger.INFO,
                '準備請求 token')

            push_msg = Msg(operate=Msg.key_get_token)
            push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
            self.console.server_command.push(push_msg)

        elif not find_key:
            self.logger.show(
                Logger.INFO,
                '產生金鑰')

            self.console.crypto.generate_key()
            public_key, private_key = self.console.crypto.export_key()

            content = list()
            content.append(private_key)
            content.append('請勿刪除此信 by uPtt')
            content = '\r'.join(content)
            content = content.replace('\n', '\r')

            self.logger.show(
                Logger.INFO,
                '備份金鑰')

            self.bot.mail(
                self.console.ptt_id,
                self.console.config.system_mail_title,
                content,
                0,
                backup=False)

            current_time = int(time.time())

            hash_result = util.get_verify_hash(current_time, self.console.token, public_key)

            push_msg = Msg(operate=Msg.key_update_public_key)
            push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
            push_msg.add(Msg.key_timestamp, current_time)
            push_msg.add(Msg.key_hash, hash_result)
            push_msg.add(Msg.key_public_key, public_key)

            self.console.server_command.push(push_msg)

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
                    self.logger.show(
                        Logger.INFO,
                        '登入帳號',
                        self.ptt_id)
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

                        self.bot.set_call_status(PTT.data_type.call_status.OFF)
                        self.bot.get_waterball(PTT.data_type.waterball_operate_type.CLEAR)

                        self.ptt_id = None
                        self.ptt_pw = None

                        self.console.process.login_ptt_login_complete = True

                    except PTT.exceptions.LoginError:
                        self.logger.show(
                            Logger.INFO,
                            'PTT.exceptions.LoginError')
                        push_msg = Msg(
                            operate=Msg.key_login,
                            code=ErrorCode.LoginFail,
                            msg='Login fail')
                        self.console.command.push(push_msg)

                        self.console.process.break_login_process = True
                        self.ptt_id = None
                        self.ptt_pw = None
                        continue
                    except PTT.exceptions.WrongIDorPassword:
                        self.logger.show(
                            Logger.INFO,
                            'PTT.exceptions.WrongIDorPassword')
                        push_msg = Msg(
                            operate=Msg.key_login,
                            code=ErrorCode.LoginFail,
                            msg='ID or PW error')
                        self.console.command.push(push_msg)

                        self.console.process.break_login_process = True
                        self.ptt_id = None
                        self.ptt_pw = None
                        continue
                    except PTT.exceptions.LoginTooOften:
                        self.logger.show(
                            Logger.INFO,
                            'PTT.exceptions.LoginTooOften')
                        push_msg = Msg(
                            operate=Msg.key_login,
                            code=ErrorCode.LoginFail,
                            msg='Please wait a moment before login')
                        self.console.command.push(push_msg)

                        self.console.process.break_login_process = True
                        self.ptt_id = None
                        self.ptt_pw = None
                        continue

                    if self.console.token is None:
                        self._event_get_token(None)

                if self.run_find_token_process:
                    self._event_get_token(None)
                    self.run_find_token_process = False

                if self.console.login_complete:

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

            if not self.console.login_complete:
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

            if new_mail > 0 and new_mail != self.last_new_mail:
                self.last_new_mail = new_mail
                push_msg = Msg(
                    operate=Msg.key_notify)
                push_msg.add(Msg.key_msg, f'You have {new_mail} mails')

                self.console.command.push(push_msg)

        self.logger.show(
            Logger.INFO,
            '關閉成功')
