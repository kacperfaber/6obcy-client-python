import json
import threading
import time


class Command:
    def __init__(self, ev_name, ev_data, opcode):
        self.ev_name = ev_name
        self.ev_data = ev_data
        self.opcode = opcode


class CommandListener(object):
    def command_received(self, command: Command):
        pass


class AddedCommandListener(object):
    def __init__(self, ev_name, command_listener):
        self.ev_name = ev_name
        self.command_listener = command_listener


class IdOffset():
    def __init__(self, id, offset):
        self.id = id
        self.offset = offset


class Transaction(object):
    def __init__(self, socket_client):
        self.socket_client = socket_client
        self.commands = []
        self.id_objects = []
        pass

    def run_receiver(self):
        self.receiver_thread = threading.Thread(target=self.receiver_thread)
        self.receiver_thread.start()

    def receiver_thread(self):
        while True:
            r = self.socket_client.socket.recv()
            if r == "3" or r.startswith("0"):
                continue
            cmd = self.socket_client.parse_command_string(r)
            self.commands.append(cmd)
            log = open("log.txt", "a+")
            log.write(cmd.ev_name + "\n")
            log.close()
            matched_listeners = self.socket_client.get_registered_listeners_by_name(cmd.ev_name)
            for matched_listener in matched_listeners:
                matched_listener.command_received(cmd)

    def read_command(self, offset) -> Command | None:
        try:
            return self.commands[offset]
        except:
            return None

    def get_offset_for_id(self, id):
        for obj in self.id_objects:
            if obj.id == id:
                return obj.offset

    def is_id_exists(self, id):
        for obj in self.id_objects:
            if obj.id == id:
                return True
        return False

    def make_id(self, id, offset=0):
        self.id_objects.append(IdOffset(id, offset))

    def increase_offset_for_id(self, id):
        for obj in self.id_objects:
            if obj.id == id:
                obj.offset = obj.offset + 1

    def read_command_for_id(self, id):
        if self.is_id_exists(id) == False:
            self.make_id(id)
        try:
            cmd = self.read_command(self.get_offset_for_id(id))
            self.increase_offset_for_id(id)
            return cmd
        except:
            time.sleep(1)
            cmd = self.read_command(self.get_offset_for_id(id))
            self.increase_offset_for_id(id)
            return cmd


class SocketClient:
    def __init__(self, ws_client):
        self.transaction = Transaction(self)
        self.socket = ws_client
        self.ceid = 1
        self.listeners = []

    def wait_for_messages(self, *args):
        offset = len(self.transaction.commands)
        while True:
            cmd = self.transaction.read_command(offset)
            if cmd is None:
                time.sleep(1)
                continue
            offset = offset + 1
            if cmd.ev_name is not None:
                if cmd.ev_name in args:
                    return cmd

    def wait_for_message(self, ev_name):
        offset = len(self.transaction.commands)
        while True:
            cmd = self.transaction.read_command(offset)
            if cmd == None:
                time.sleep(1)
                continue
            offset = offset + 1
            if cmd.ev_name is not None:
                if cmd.ev_name == ev_name:
                    return cmd

    def get_registered_listeners_by_name(self, ev_name):
        ret = []
        for listener in self.listeners:
            if listener.ev_name == ev_name:
                ret.append(listener.command_listener)
        return ret

    def read_data_loop(self):
        pass

    def ping(self):
        self.socket.send('2')

    def cmd(self, ev_name, ev_data, with_ceid=False):
        d = dict(ev_name=ev_name, ev_data=ev_data)
        if with_ceid:
            d['ceid'] = self.ceid
        self.socket.send('4' + json.dumps(d))
        pass

    def parse_command_string(self, command_string):
        if command_string.startswith("0"):
            return None
        if command_string.startswith("4"):
            d = json.loads(command_string[1:])
            return Command(d["ev_name"], d["ev_data"], 4)
        if command_string == "3":
            return None
        return None

    def get_cmd(self, message):
        if isinstance(message, Command):
            return message
        return Command(message["ev_name"], message["ev_data"], 0)

    def register_listener(self, ev_name, command_listener: CommandListener):
        self.listeners.append(AddedCommandListener(ev_name, command_listener))


class ChannelClient:
    def __init__(self, socket_client, ckey, cid):
        self.socket_client = socket_client
        self.ckey = ckey
        self.cid = cid
        self.idn = 0
        self.disconnected = False

    def increment_idn(self):
        self.idn = self.idn + 1

    def send_text_message(self, text):
        self.socket_client.cmd("_pmsg", dict(ckey=self.ckey, idn=self.idn, msg=text), with_ceid=True)
        self.increment_idn()
        pass

    def read_text_message(self):
        cmd = self.socket_client.get_cmd(self.socket_client.wait_for_message("rmsg"))
        return cmd.ev_data["msg"]

    def disconnect(self):
        self.socket_client.cmd("_distalk", dict(ckey=self.ckey), with_ceid=True)
        self.disconnected = True


class ObcyClient:
    def __init__(self, socket_client):
        self.socket_client = socket_client

    def ping(self):
        self.socket_client.send("2")

    def ping_loop(self, offset):
        while True:
            time.sleep(offset)
            self.ping()

    def run_ping_thread(self, offset=15):
        ping_thread = threading.Thread(target=self.ping_loop, args=[offset])
        ping_thread.start()

    def find_stranger(self) -> ChannelClient | None:
        self.socket_client.cmd("_sas",
                               dict(channel="main", myself=dict(sex=0, loc=16), preferences=dict(sex=0, loc=16)),
                               with_ceid=False)
        talk_or_captcha_message = self.socket_client.wait_for_messages("talk_s", "caprecvsas")
        talk_or_captcha_cmd = self.socket_client.get_cmd(talk_or_captcha_message)

        # When I'm 'find_stranger'. I think, when captcha is sent the thread is broke because we're still waiting for stranger. TODO

        if talk_or_captcha_cmd.ev_name == "talk_s":
            return ChannelClient(self.socket_client, talk_or_captcha_cmd.ev_data['ckey'],
                                 talk_or_captcha_cmd.ev_data["cid"])

        return None

    def answer_captcha(self, answer):
        self.socket_client.cmd("_capsol", dict(solution=answer), with_ceid=False)
