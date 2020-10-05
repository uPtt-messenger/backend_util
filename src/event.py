import threading

from SingleLog.log import Logger

from backend_util.src.errorcode import ErrorCode
from backend_util.src.msg import Msg
from backend_util.src import util


class Event:
    def __init__(self, console_obj):
        self.console = console_obj

        self.logger = Logger('Event', self.console.config.log_level, handler=self.console.config.log_handler)

        self.console.event.register(EventConsole.key_login_success, self.event_login_success)

    def event_login_success(self, _):

        push_msg = Msg(
            operate=Msg.key_login,
            code=ErrorCode.Success,
            msg='Login success')

        if self.console.run_mode == 'dev':
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

        push_msg = Msg(operate=Msg.key_login_success)
        push_msg.add(Msg.key_ptt_id, self.console.ptt_id)
        self.console.server_command.push(push_msg)


class EventConsole:
    # client
    key_close = 'close'
    key_login_success = 'login_success'
    key_logout = 'logout'
    key_login = 'login'
    key_recv_waterball = 'recv_waterball'
    key_send_waterball = 'send_waterball'

    # server
    key_send_token = 'send_token'
    key_get_token = 'get_token'

    def __init__(self, console_obj):
        self.console = console_obj

        self.logger = Logger('EventConsole', self.console.config.log_level, handler=self.console.config.log_handler)

        self.is_thread_running = False
        self.event_chain = dict()

    def register(self, event_chain_name, func):
        event_chain_name = event_chain_name.lower()
        if event_chain_name not in self.event_chain:
            self.event_chain[event_chain_name] = list()

        self.event_chain[event_chain_name].append(func)

    def _execute_thread(self, event_chain_name, parameter):

        self.logger.show(Logger.INFO, f'線程事件通知鏈 {event_chain_name}', '啟動')

        self.logger.show(Logger.DEBUG, '線程執行 event_chain_name', event_chain_name)
        self.logger.show(Logger.DEBUG, '線程執行 parameter', parameter)

        for e in self.event_chain[event_chain_name]:
            e(parameter)

        self.logger.show(Logger.INFO, f'線程事件通知鏈 {event_chain_name}', '完成')

        self.is_thread_running = False

    def execute(self, event_chain_name, run_thread: bool = False, parameter: tuple = None):

        if run_thread:
            t = threading.Thread(target=self._execute_thread, args=(event_chain_name, parameter))
            self.is_thread_running = True
            t.start()
        else:

            if event_chain_name not in self.event_chain:
                self.logger.show(Logger.INFO, f'事件通知鏈 {event_chain_name}', '無事件')
            else:
                self.logger.show(Logger.INFO, f'事件通知鏈 {event_chain_name}', '啟動')
                for e in self.event_chain[event_chain_name]:
                    e(parameter)

            self.logger.show(Logger.INFO, f'事件通知鏈 {event_chain_name}', '完成')


if __name__ == '__main__':
    ec = EventConsole()

    ec.execute('test', run_thread=True, parameter=(1, 2, '3'))
