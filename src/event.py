import threading

from single_log.log import Logger


class EventConsole:
    key_close = 'close'
    key_login_success = 'login_success'
    key_logout = 'logout'
    key_login = 'login'
    key_recv_waterball = 'recv_waterball'
    key_send_waterball = 'send_waterball'

    def __init__(self, console_obj):
        self.console = console_obj

        self.logger = Logger('EventConsole', self.console.config.log_level, handler=self.console.config.log_handler)

        self.event_chain = dict()

    def register(self, event_chain_name, func):
        event_chain_name = event_chain_name.lower()
        if event_chain_name not in self.event_chain:
            self.event_chain[event_chain_name] = list()

        self.event_chain[event_chain_name].append(func)

    def _execute_thread(self, event_chain_name, parameter):

        self.logger.show(Logger.INFO, '線程執行 event_chain_name', event_chain_name)
        self.logger.show(Logger.INFO, '線程執行 parameter', parameter)

        for e in self.event_chain[event_chain_name]:
            e(parameter)

    def execute(self, event_chain_name, run_thread: bool = False, parameter: tuple = None):

        if run_thread:
            t = threading.Thread(target=self._execute_thread, args=(event_chain_name, parameter))
            t.start()

        else:

            for e in self.event_chain[event_chain_name]:
                e(parameter)


if __name__ == '__main__':
    ec = EventConsole()

    ec.execute('test', run_thread=True, parameter=(1, 2, '3'))
