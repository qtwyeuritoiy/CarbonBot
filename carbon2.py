import logging, os, re, socket, ssl, threading, time
import carbon2_commands
from datetime import datetime

class Adapter(threading.Thread):
    def register_callback(self, func, _id):
        pass
    
    def send_to(self, message, to):
        pass

class IRCAdapter(Adapter):
    def __init__(self, server, port, is_ssl, channels, owner, nick="Carbon", codec="UTF-8"):
        self.server = server
        self.port = port
        self.is_ssl = is_ssl
        self.nick = nick
        self.channels = channels
        self.owner = owner
        self.codec = codec
        
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
            
    def join(self, ch):
        self.raw_send("JOIN %s\n"%ch)
    
    def run(self):
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.connect((self.server, self.port))

        if self.is_ssl:
            self.sock = ssl.wrap_socket(raw_socket)
        else:
            self.sock = raw_socket
        
        self.raw_send("USER {0} {0} {0} :Carbon, IRC bot by imsesaok\n".format(self.nick))
        self.raw_send("NICK %s\n" % self.nick)

        self.logger.info("logging in...")

        while True:
            msg = self.sock.recv(512).decode(self.codec).strip("\r\n")
            self.logger.info(msg)
            if "MODE" in msg or "MOTD" in msg:
                break
            
            if "PING :" in msg:
                self.ping(msg)
            
        for ch in self.channels:
            self.join(ch)
        
        self.logger.info("Logged in succesfully!")
        
        while True:
            try:
                msg = self.sock.recv(2048).decode(self.codec).strip("\r\n")
                self.logger.info(msg)
                if "PING :" in msg:
                    self.ping(msg)
                elif "PRIVMSG" in msg:
                    ch = msg.split("PRIVMSG")[-1].split(" :")[0]
                    user = msg.split("!")[0].split(":", 1)[1]
                    message = msg.split(":", 2)[2]
                    metadata = {"from_user": user, "from_group": ch, "when": datetime.now(), "_id": self._id, }
                    self.execute(message, metadata)
                    
            except Exception as e:
                self.logger.error("Error while reading socket.", exc_info=True)

class TelegramAdapter(Adapter):
    def __init__(self, token, admin_id):
        from telegram.ext import Updater
        self.updater = Updater(token = token)
        self.dispatcher = self.updater.dispatcher
        self.bot = self.updater.bot
        self.admin_id = admin_id
        threading.Thread.__init__(self)
    
    def run(self):
        from telegram.ext import MessageHandler, CommandHandler, Filters
        
        handler = MessageHandler(Filters.text, self.eval)
        start_handler = CommandHandler('start', self.eval)
        help_handler = CommandHandler('help', self.eval)
        
        self.dispatcher.add_handler(handler)
        self.dispatcher.add_handler(start_handler)
        self.dispatcher.add_handler(help_handler)
        self.updater.start_polling()
    
    def register_callback(self, func, _id):
        self.callback = func
        self._id = _id
    
    def eval(self, bot, update):
        message = update.message.text.strip()
        from_user = update.message.from_user.name
        from_group = update.message.chat_id
        when = update.message.date
        metadata = {"from_user": from_user, "from_group": from_group, "when": when, "_id": self._id, }
        self.callback(message, metadata)
    
    def send(self, message, to):
        self.bot.send_message(chat_id=to, text=message)

class Carbon:
    def __init__(self, adapters = {"adapter":Adapter()}, commands = []):
        self.commands = commands
        self.adapters= adapters
        for _id in self.adapters:
            self.adapters[_id].register_callback(self.process, _id)
    
    def run(self):
        for adapter in self.adapters.values():
            adapter.start()
    
    def process(self, message, metadata):
        for command in self.commands:
            match = re.search("^%s$"%command.regex, message)
            if match is not None:
                command.on_exec(match, metadata, self)
    
    def send(self, message, to, _id):
        self.adapters[_id].send(message, to)
    
    def finalise(self):
        for adapter in self.adapters.values():
            adapter.finalise()

telegram = TelegramAdapter(os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_BOT_OWNER'))
freenode = IRCAdapter(os.environ.get('IRC_SERVER_ADDRESS'), int(os.environ.get('IRC_SERVER_PORT')),
    False if os.environ.get('IRC_SERVER_IS_SSL') is "0" else True, os.environ.get('IRC_CHANNELS').split(","),
    os.environ.get('IRC_OWNER'), nick = os.environ.get('IRC_NICK'))

adapters = {"carbon_telegram_bot": telegram, "freenode_carbon_bot": freenode}
Carbon(adapters, carbon2_commands.commands).run()

#Logging code.
#Will clean up later.
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.FileHandler('carbon.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
