import traceback

class Command:
    def __init__(self, regex, title, description, on_exec, raw_match=False,
            display_condition = lambda match, metadata, bot: True,
            exec_condition = lambda match, metadata, bot: True, flags = list()):
        self.regex = regex
        self.title = title
        self.description = description
        self.on_exec = self.run_on_sandbox
        self.func = on_exec
        self.display_condition = display_condition
        self.exec_condition = exec_condition
        self.flags = flags
        self.raw_match = raw_match

    def run_on_sandbox(self, match, metadata, bot):
        try:
            if self.exec_condition(match, metadata, bot):
                self.func(match, metadata, bot)
        except:
            traceback.print_exc()
            e = sys.exc_info()[0]
            bot.send("Oops! Something Went Horribly Wrong! (%s)" % e,
                    metadata['from_group'], metadata['_id'])

class CannedResponseCommand(Command):
    def __init__(self, regex, title, description, canned = "", raw_match=False,
            display_condition = lambda match, metadata, bot: True,
            exec_condition = lambda match, metadata, bot: True, flags = list()):
        super(self.__class__, self).__init__(regex, title, description, self.canned, raw_match, display_condition, exec_condition, flags)
        self.canned_response = canned

    def canned(self, match, metadata, bot):
        bot.send(self.canned_response, metadata['from_group'], metadata['_id'])

about = CannedResponseCommand(r"{ident}about", "about", "Show information about this bot.",
    canned = "Carbon 2.0 alpha\nA Multi-Protocol Bot developed by imsesaok.\nhttps://github.com/qtwyeuritoiy/CarbonBot2")
ping = CannedResponseCommand(r"{ident}ping", "ping", "Test the connection between the user and the bot.", canned = "Pong!")
echo = Command(r"{ident}echo(?: (?P<message>.+))?", "echo <message>", "Echo message.",
    lambda match, metadata, bot: bot.send(match['message'], metadata['from_group'], metadata['_id']))

