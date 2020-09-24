import asyncio
import websockets
import traceback
import time
import threading
import json

from SingleLog.log import Logger

from .msg import Msg
from .console import Console


class WsServer:

    def __init__(self, console_obj):

        self.logger = Logger('WsServer', console_obj.config.log_level, handler=console_obj.config.log_handler)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        self.console = console_obj

        self.thread = None
        self.start_error = False
        self.run_session = True
        self.run = True
        self.server_start = False

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

    def start(self):
        self.thread = threading.Thread(
            target=self.server_setup,
            daemon=True)
        self.thread.start()
        time.sleep(2)
        if not self.start_error:
            self.logger.show(
                Logger.INFO,
                '啟動成功')

    def stop(self, p):

        self.logger.show(
            Logger.INFO,
            '執行終止程序')

        while not self.server_start and not self.start_error:
            time.sleep(0.1)

        self.run_session = False
        self.run = False

        self.logger.show(
            Logger.INFO,
            '終止程序完成')

    async def consumer_handler(self, ws, path):

        while self.run_session:
            try:
                try:
                    recv_msg_str = await ws.recv()
                except Exception as e:
                    print('Connection Close: recv fail')
                    recv_msg_str = None
                    # raise ValueError('Connection Close: recv fail')

                self.logger.show(
                    Logger.INFO,
                    '收到字串',
                    recv_msg_str)
                self.logger.show(
                    Logger.INFO,
                    '路徑',
                    path)

                try:
                    recv_msg = Msg(strobj=recv_msg_str)
                except json.JSONDecodeError:
                    self.logger.show(
                        Logger.INFO,
                        'Json 解析失敗，丟棄訊息',
                        recv_msg_str)
                    self.run_session = False
                    break

                if self.console.role == Console.role_client:
                    if path is not None and 'token=' in path:
                        token = path[path.find('token=') + len('token='):]
                        if '&' in token:
                            token = token[:token.find('&')]
                        self.logger.show(
                            Logger.INFO,
                            '收到權杖',
                            token)
                        recv_msg.add(Msg.key_token, token)

                # print(str(recv_msg))
                self.console.command.analyze(recv_msg)
                # await ws.send(recv_msg)
                # print(f'echo complete')
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                print(e)
                print('Connection Close')
                self.run_session = False
                break

    async def producer_handler(self, ws, path):

        while self.run_session:
            while self.console.command.push_msg:
                push_msg = self.console.command.push_msg.pop()

                print(f'push [{push_msg}]')
                try:
                    await ws.send(push_msg)
                except websockets.exceptions.ConnectionClosedOK:
                    print(f'push fail')
                    break
            await asyncio.sleep(0.1)

    async def handler(self, websocket, path=None):
        while self.run_session:
            consumer_task = asyncio.ensure_future(
                self.consumer_handler(websocket, path))

            producer_task = asyncio.ensure_future(
                self.producer_handler(websocket, path))

            _, pending = await asyncio.wait(
                [consumer_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()

        self.run_session = self.run

    def server_setup(self):

        if self.console.role == Console.role_client:
            current_port = self.console.config.port
        else:
            current_port = self.console.config.server_port

        self.logger.show(
            Logger.INFO,
            '啟動伺服器',
            f'ws://127.0.0.1:{current_port}')

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        start_server = websockets.serve(
            self.handler,
            "localhost",
            current_port)

        try:
            asyncio.get_event_loop().run_until_complete(start_server)
        except OSError:
            self.start_error = True

        if self.start_error:
            self.logger.show(Logger.INFO, '啟動伺服器失敗')
        else:

            self.server_start = True

            asyncio.get_event_loop().run_forever()

    def connect_server(self):

        if self.console.run_mode == Console.run_mode_dev:
            self.uri = f'ws://127.0.0.1:{self.console.config.server_port}'
        else:
            self.uri = f'ws://{self.console.dynamic_data.online_server}:{self.console.config.server_port}'

        self.logger.show(
            Logger.INFO,
            'uri',
            self.uri)

        return websockets.connect(self.uri)

    def connect_thread(self):

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        self.logger.show(
            Logger.INFO,
            'uri',
            '=============================')

        self._websocket = self.connect_server()

        asyncio.get_event_loop().run_until_complete(self.handler(self._websocket))

    def connect_setup(self):

        self.logger.show(
            Logger.INFO,
            '啟動連線',
            f'{self.console.dynamic_data.online_server}')

        t = threading.Thread(target=self.connect_thread)
        t.daemon = True
        t.start()
