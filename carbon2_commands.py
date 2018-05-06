import random, re, sys, time, traceback

class Command:
    def __init__(self, regex, title, description, on_exec, raw_match=False,
            display_condition = lambda message, metadata, bot: True, flags = list()):
        self.regex = regex
        self.title = title
        self.description = description
        self.on_exec = self.run_on_sandbox
        self.func = on_exec
        self.display_condition = display_condition
        self.flags = flags
        self.raw_match = raw_match

    def run_on_sandbox(self, match, metadata, bot):
        try:
            self.func(match, metadata, bot)
        except:
            traceback.print_exc()
            e = sys.exc_info()[0]
            bot.send("Oops! Something Went Horribly Wrong! (%s)" % e,
                    metadata['from_group'], metadata['_id'])

class CannedResponseCommand(Command):
    def __init__(self, regex, title, description, canned = "", raw_match=False,
            display_condition = lambda message, metadata, bot: True):
        super(self.__class__, self).__init__(regex, title, description, self.canned, raw_match, display_condition)
        self.canned_response = canned

    def canned(self, message, metadata, bot):
        bot.send(self.canned_response, metadata['from_group'], metadata['_id'])

def print_help(match, metadata, bot):
    linecount = 4
    string = ""
    command_list = list()
    for command in bot.commands:
        if command.display_condition(match[0], metadata, bot):
            command_list.append(command)

    command_count = len(command_list)
    try:
        index = int(match['page'].strip()) - 1
    except ValueError:
        bot.send("Invalid argument: expecting number.", metadata['from_group'], metadata['_id'])
    except AttributeError:
        index = 0

    start = index * linecount
    end = start + linecount

    maximum = int(-(-command_count // linecount))
    if command_count < end:
        end = command_count
        if end <= start:
            bot.send("Invalid number: use number below " + str(maximum) + ".",
                metadata['from_group'], metadata['_id'])
            return

    bot.send("Usage: <identifier><command>\nIdentifier setting for the current adapter: {}\n".format(metadata["ident"]), metadata['from_group'], metadata['_id'])

    message = "Commands: " + str(index + 1) + " out of " + str(maximum)
    for i in range(start, end):
        command = bot.commands[i]
        message += "\n"+ command.title + ": " + command.description

    bot.send(message, metadata['from_group'], metadata['_id'])

def dice(match, metadata, bot):
    number = 6
    try:
        number = int(match['number'].strip())
    except ValueError:
        bot.send("Invalid argument: expecting number.", metadata['from_group'], metadata['_id'])
        return
    except AttributeError:
        pass

    if number < 1:
        bot.send("Hey, thought I can't do math? Your number is too small!", metadata['from_group'], metadata['_id'])
    elif number is 1:
        bot.send("1!\n(seriously tho?)", metadata['from_group'], metadata['_id'])
    else:
        bot.send(str(random.randrange(1, number+1)) + "!", metadata['from_group'], metadata['_id'])

def echo_exec(message, metadata_lambda, metadata, bot, reply):
    if metadata_lambda['from_group'] == metadata['from_group'] and metadata_lambda["_id"] == metadata["_id"]:
        bot.send(reply, metadata['from_group'], metadata['_id'])

def add_echo_command(match, metadata, bot):
    condition = match['condition'].strip()
    reply = match['reply'].strip()
    echo_reply = Command(condition, "if %s"%condition, "echo %s"%reply,
        lambda message, metadata_lambda, bot: echo_exec(message, metadata_lambda, metadata, bot, reply),
        raw_match=True, display_condition = lambda message, metadata, bot: False, flags=["echo"])

    for command in bot.commands:
        if condition == command.regex and "echo" in command.flags:
            bot.commands.remove(command)
            bot.commands.append(echo_reply)
            bot.send("Rule Already Exists. Overridden.", metadata['from_group'], metadata['_id'])
            return
        elif re.search("^{ident}{command}$".format(ident=metadata["ident"], command=command.regex), condition) and not command.raw_match:
            bot.send("Rule Not Accepted: You cannot override existing commands.", metadata['from_group'], metadata['_id'])
            return

    bot.commands.append(echo_reply)
    bot.send("Rule successfully created.", metadata['from_group'], metadata['_id'])

def remove_echo_command(match, metadata, bot):
    condition = match['condition']

    for command in bot.commands:
        if condition == command.regex and "echo" in command.flags:
            bot.commands.remove(command)
            bot.send("Rule successfully deleted.", metadata['from_group'], metadata['_id'])
            return

    bot.send("Rule does not exist.", metadata['from_group'], metadata['_id'])

from datetime import datetime, date, timedelta
about = CannedResponseCommand(r"about", "about", "Show information about this bot.",
    canned = "Carbon 2.0 alpha\nA Multi-Protocol Bot developed by imsesaok.\nhttps://github.com/qtwyeuritoiy/CarbonBot2")
ping = CannedResponseCommand(r"{ident}ping", "ping", "Test the connection between the user and the bot.", canned = "Pong!")

dice = Command(r"{ident}dice(?: (?P<number>\d+))?", "dice <number>", "Roll a dice.", dice)
help = Command(r"{ident}help(?: ?(?P<page>\d+))?", "help <page>", "Show this text.", print_help)
echo = Command(r"{ident}echo (?P<message>.+)", "echo <message>", "Echo message.",
    lambda match, metadata, bot: bot.send(match['message'], metadata['from_group'], metadata['_id']))
add_echo = Command(r"(?P<ident>{ident})if (?P<condition>.+?) (?P=ident)?echo (?P<reply>.+)", "if <message> echo <message>",
    "Makes the bot reply to certain messages.", add_echo_command)
remove_echo = Command(r"{ident}removeif (?P<condition>.+?)", "removeif <message>",
    "Remove the echo rule.", remove_echo_command)

uptime = Command(r"{ident}uptime", "uptime", "Show how long the bot has been operating.",
    lambda match, metadata, bot: bot.send(str(timedelta(seconds=time.time() - start_time)), metadata['from_group'], metadata['_id']))
start_time = time.time()

commands = [help, about, ping, dice, uptime, echo, add_echo, remove_echo, ]
