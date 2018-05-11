import base64, logging, os, re, socket, ssl, threading, time
import carbon2_commands
from datetime import datetime

class Adapter(threading.Thread):
    def __init__(self, identifier="!"):
        self.identifier=identifier

    def register_callback(self, func, _id):
        pass

    def send_to(self, message, to):
        pass

class IRCAdapter(Adapter):
    def __init__(self, server, port, is_ssl, channels, owner, nick="Carbon", codec="UTF-8", is_sasl=False, password=None):
        super(self.__class__, self).__init__()
        self.server = server
        self.port = port
        self.is_ssl = is_ssl
        self.is_sasl = is_sasl
        self.nick = nick
        self.channels = channels
        self.owner = owner
        self.codec = codec
        self.password = password

        threading.Thread.__init__(self)
        self.logger = logging.getLogger("IRCAdapter")
        logging.basicConfig(level=logging.DEBUG)

    def ping(self, msg):
        pong = msg.strip("PING :")
        self.raw_send("PONG :%s\n" %pong)

    def register_callback(self, func, _id):
        self.execute = func
        self._id = _id

    def raw_send(self, message):
        self.sock.send(message.encode(self.codec))
        self.logger.info("Sent: %s" %message)

    def send(self, message, to):
        send_to = to.strip()
        if not message.strip("\r\n").strip():
            return
        for line in message.split("\n"):
            message = line.strip(" ")
            self.raw_send("PRIVMSG " + to + " :" + message + "\n")

    def join_channel(self, ch):
        self.raw_send("JOIN %s\n"%ch)

    def run(self):
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.connect((self.server, self.port))

        if self.is_ssl:
            self.sock = ssl.wrap_socket(raw_socket)
        else:
            self.sock = raw_socket

        if self.is_sasl:
            self.raw_send("CAP REQ :sasl\n")

        self.raw_send("NICK %s\n" % self.nick)
        self.raw_send("USER {0} {0} {0} :Carbon, IRC bot made by imsesaok\n".format(self.nick))

        self.logger.info("logging in...")

        while True:
            msg = self.sock.recv(512).decode(self.codec).strip().replace(self.nick, "")
            if msg is not "":
                self.logger.info(msg)
            if "MODE %s"%self.nick in msg or "MOTD" in msg:
                break

            elif "PING :" in msg:
                self.ping(msg)

            elif "CAP" in msg and "ACK" in msg:
                    self.raw_send("AUTHENTICATE PLAIN\n")

            elif "AUTHENTICATE" in msg:
                auth = ('{sasl_username}\0'
                '{sasl_username}\0'
                '{sasl_password}').format(sasl_username=self.nick,
                sasl_password=self.password)
                auth = base64.encodestring(auth.encode(self.codec))
                auth = auth.decode(self.codec).rstrip('\n')
                self.raw_send("AUTHENTICATE " + auth +"\n")

            elif "903" in msg:
                self.raw_send("CAP END\n")

        for ch in self.channels:
            self.join_channel(ch)

        self.logger.info("Logged in succesfully!")

        while True:
            try:
                msg = self.sock.recv(2048).decode(self.codec).strip()
                if msg is not "":
                    self.logger.info(msg)
                if "PING :" in msg:
                    self.ping(msg)
                elif "PRIVMSG" in msg:
                    ch = msg.split("PRIVMSG")[-1].split(" :")[0]
                    user = msg.split("!")[0].split(":", 1)[1]
                    message = msg.split(":", 2)[2]
                    metadata = {"from_user": user, "from_group": ch, "when": datetime.now(),
                            "_id": self._id, "ident": self.identifier, "type": self.__class__.__name__,
                            "mentioned": self.nick in message, "is_mod": user == self.owner, } #FIXME: Check for other admins in the channel.
                    self.execute(message, metadata)

            except Exception as e:
                self.logger.error("Error while reading socket.", exc_info=True)

class TelegramAdapter(Adapter):
    def __init__(self, token, admin_id):
        super(self.__class__, self).__init__(r"[!/]")
        from telegram.ext import Updater
        self.updater = Updater(token = token)
        self.dispatcher = self.updater.dispatcher
        self.bot = self.updater.bot
        self.bot_id = self.bot.get_me()["username"]
        self.admin_id = admin_id
        threading.Thread.__init__(self)

    def run(self):
        from telegram.ext import MessageHandler, CommandHandler, Filters
        handler = MessageHandler(Filters.text | Filters.command, self.eval)
        self.dispatcher.add_handler(handler)
        self.updater.start_polling()

    def register_callback(self, func, _id):
        self.callback = func
        self._id = _id

    def eval(self, bot, update):
        message = update.message.text.strip().replace("@"+self.bot_id, "")
        from_user = update.message.from_user.name
        from_group = update.message.chat_id
        when = update.message.date
        metadata = {"from_user": from_user, "from_group": from_group, "when": when,
                "_id": self._id, "ident": self.identifier, "type": self.__class__.__name__,
                "mentioned": "@"+self.bot_id in message, "is_mod": from_user == self.admin_id, } #FIXME: Check for other admins in the channel.
        self.callback(message, metadata)

    def send(self, message, to):
        self.bot.send_message(chat_id=to, text=message)

class Carbon:
    def __init__(self, adapters, commands = []):
        self.commands = commands
        self.adapters = adapters
        self.metadata = dict()
        for _id in self.adapters:
            self.adapters[_id].register_callback(self.process, _id)

    def run(self):
        for adapter in self.adapters.values():
            adapter.start()

    def process(self, message, metadata):
        for command in self.commands:
            if command.raw_match:
                match = message if command.regex == message else None
            else:
                regex = command.regex.format(ident=metadata["ident"])
                match = re.search("^{}$".format(regex), message)
            if match is not None:
                command.on_exec(match, {**metadata, **self.metadata}, self)

    def send(self, message, to, _id):
        self.adapters[_id].send(message, to)

    def finalise(self):
        for adapter in self.adapters.values():
            adapter.finalise()

telegram = TelegramAdapter(os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_BOT_OWNER'))
freenode = IRCAdapter(os.environ.get('IRC_SERVER_ADDRESS'), int(os.environ.get('IRC_SERVER_PORT')),
    False if os.environ.get('IRC_SERVER_IS_SSL') is "0" else True, os.environ.get('IRC_CHANNELS').split(","),
    os.environ.get('IRC_OWNER'), nick = os.environ.get('IRC_NICK'), password=os.environ.get('IRC_SASL_PASSWORD'),
    is_sasl = False if os.environ.get('IRC_SERVER_IS_SASL') is "0" else True)

adapters = {"carbon_telegram_bot": telegram, "freenode_carbon_bot": freenode}
Carbon(adapters, carbon2_commands.commands).run()

#Logging code.
#Will clean up later.
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.FileHandler('carbon.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
