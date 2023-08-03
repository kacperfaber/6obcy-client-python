import websocket
import threading
import time
import sys
import os
import datetime

clientlib = __import__("obcy-client")
captcha_verification_request_dialog = __import__("captcha_verification_request_dialog")


class CaptchaVerificationRequest(clientlib.CommandListener):
    def command_received(self, command):
        cmd_text = command.ev_data["tlce"]["cmdText"]
        data = command.ev_data["tlce"]["data"]
        response = captcha_verification_request_dialog.CaptchaVerificationRequestDialog(cmd_text, data).show()
        client.answer_captcha(response)


class MessageReceiver(clientlib.CommandListener):
    def command_received(self, command):
        if command.ev_name == "rmsg":
            message_console_log(command.ev_data["msg"], "STR")


class TypeStateReceiver(clientlib.CommandListener):
    def command_received(self, command):
        if command.ev_name == "styp":
            if command.ev_data:
                print("Stranger's writing...", end='\r')
            else:
                print('', end='\r')
                sys.stdout.flush()


class DisconnectReceiver(clientlib.CommandListener):
    def command_received(self, command):
        if command.ev_name == "sdis":
            global channel
            channel = None
            print("Disconnected.\n\n")


class ConnectedEventReceiver(clientlib.CommandListener):
    def command_received(self, command):
        if command.ev_name == "talk_s":
            print("Connected.\n\n")


sock = websocket.create_connection("wss://server.6obcy.pl:7004/6eio/?EIO=3&transport=websocket")
socket_client = clientlib.SocketClient(sock)
socket_client.register_listener("rmsg", MessageReceiver())
socket_client.register_listener("styp", TypeStateReceiver())
socket_client.register_listener("sdis", DisconnectReceiver())
socket_client.register_listener("talk_s", ConnectedEventReceiver())
socket_client.register_listener("caprecvsas", CaptchaVerificationRequest())
socket_client.transaction.run_receiver()

client = clientlib.ObcyClient(socket_client)
channel = None


def message_console_log(message_text, sender):
    msg = message_text
    if len(msg) < 23:
        msg = msg + " " * (23 - len(msg))
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        print(f'{current_time} {sender}: {msg}')
        sys.stdout.flush()


def setup_console():
    os.system("color")


def read_input_loop():
    while True:
        x = input()
        global channel
        if x == "/connect":
            channel = client.find_stranger()
            continue
        if channel is not None:
            if x == "/disc":
                channel.disconnect()
                continue
            channel.send_text_message(x)
            print('\033[1A' + '\033[K', end='', flush=True)
            message_console_log(x, "YOU")


def ping_loop():
    while True:
        time.sleep(10)
        client.socket_client.ping()


setup_console()

input_thread = threading.Thread(target=read_input_loop)
input_thread.start()

ping_thread = threading.Thread(target=ping_loop)
ping_thread.start()
