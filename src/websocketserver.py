import asyncio
import websockets
import time
import threading
import json

from SingleLog.log import Logger

from backend_util.src.msg import Msg
from backend_util.src.console import Console
from backend_util.src.config import Config
from backend_util.src.event import EventConsole
from backend_util.src.errorcode import ErrorCode
from backend_util.src import util


class WsServer:

    def __init__(self, console_obj, to_server: bool):

        self.logger = Logger(('WsServer' if to_server else 'Client-WsServer'), console_obj.config.log_level,
                             handler=console_obj.config.log_handler)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        self.console = console_obj
        self.to_server = to_server

        self.thread = None
        self.start_error = False
        self.run_session = True
        self.run = True
        self.server_start = False
        self.connect_server_error = False

        self.console.event.register(
            EventConsole.key_close,
            self.stop)

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

        self.run = False
        self.run_session = False

        time.sleep(0.5)

        self.logger.show(
            Logger.INFO,
            '終止程序完成')

    async def consumer_handler(self, ws, path):

        while self.run_session:
            try:
                try:
                    recv_msg_str = await ws.recv()
                except Exception as e:
                    raise ValueError('Connection Close: recv fail')

                # self.logger.show(
                #     Logger.INFO,
                #     '收到字串',
                #     recv_msg_str)

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

                if self.to_server:
                    self.console.server_command.analyze(recv_msg, ws)
                else:
                    self.console.command.analyze(recv_msg, ws)
            except Exception as e:
                # traceback.print_tb(e.__traceback__)
                self.run_session = False
                break

    async def producer_handler(self, ws, path):

        while self.run_session:
            while self.console.command.push_msg:
                push_msg = self.console.command.push_msg.pop(0)

                if self.console.role == Console.role_client:
                    role = 'frontend'
                else:
                    role = 'client'

                self.logger.show(Logger.INFO, f'push to {role}', push_msg)
                try:
                    await ws.send(push_msg)
                except websockets.exceptions.ConnectionClosedOK:
                    self.logger.show(Logger.INFO, f'push to {role}', 'Fail', 'ConnectionClosedOK')
                    break
                except websockets.exceptions.ConnectionClosedError:
                    self.logger.show(Logger.INFO, f'push to {role}', 'Fail', 'ConnectionClosedOK')
                    break
            await asyncio.sleep(0.01)

    async def producer_handler_to_server(self, ws, path):

        while self.run_session:
            while self.console.server_command.push_msg:
                push_msg = self.console.server_command.push_msg.pop(0)

                self.logger.show(Logger.INFO, 'push to server', push_msg)

                try:
                    await ws.send(push_msg)
                except websockets.exceptions.ConnectionClosedOK:
                    self.logger.show(Logger.INFO, 'push to frontend', 'Fail')
                    break
            await asyncio.sleep(0.01)

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

    async def handler_to_server(self, websocket, path=None):
        while self.run_session:
            consumer_task = asyncio.ensure_future(
                self.consumer_handler(websocket, path))

            producer_task = asyncio.ensure_future(
                self.producer_handler_to_server(websocket, path))

            _, pending = await asyncio.wait(
                [consumer_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()

        self.run_session = self.run

    def server_setup(self):

        if self.console.role == Console.role_client:
            bind_ip = '127.0.0.1'
            current_port = self.console.config.port
        else:
            bind_ip = '0.0.0.0'
            current_port = self.console.config.server_port

        self.logger.show(
            Logger.INFO,
            '啟動伺服器',
            f'ws://{bind_ip}:{current_port}')

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        start_server = websockets.serve(
            self.handler,
            bind_ip,
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

    async def connect_server(self):
        async with websockets.connect(self.uri) as ws:
            await self.handler_to_server(ws)

    def connect_thread(self):

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

        self.connect_server_error = False
        try:
            asyncio.get_event_loop().run_until_complete(self.connect_server())
        except ConnectionRefusedError:
            self.logger.show(Logger.INFO, 'Connect to server error')
            self.connect_server_error = True

    def connect_setup(self):

        if self.console.run_mode == Console.run_mode_dev:
            if self.console.server_mode == Console.server_mode_local:
                self.uri = f'ws://127.0.0.1:{self.console.config.server_port}'
            else:
                self.uri = f'ws://{self.console.dynamic_data.online_server}:{self.console.config.server_port}'
        else:
            self.uri = f'ws://{self.console.dynamic_data.online_server}:{self.console.config.server_port}'

        self.logger.show(
            Logger.INFO,
            '啟動連線',
            self.uri)

        t = threading.Thread(target=self.connect_thread)
        t.daemon = True
        t.start()
