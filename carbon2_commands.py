import random, re, sys, time, traceback

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

from datetime import datetime, date, timedelta
uptime = Command(r"{ident}uptime", "uptime", "Show how long the bot has been operating.",
    lambda match, metadata, bot: bot.send(str(timedelta(seconds=time.time() - start_time)), metadata['from_group'], metadata['_id']))
start_time = time.time()

def print_help(match, metadata, bot):
    linecount = 4
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

help = Command(r"{ident}help(?: ?(?P<page>\d+))?", "help <page>", "Show this text.", print_help)

def dice(match, metadata, bot):
    try:
        number = int(match['number'].strip())
    except ValueError:
        bot.send("Invalid argument: expecting number.", metadata['from_group'], metadata['_id'])
        return
    except AttributeError:
        number = 6

    if number < 1:
        bot.send("Hey, thought I can't do math? Your number is too small!", metadata['from_group'], metadata['_id'])
    elif number is 1:
        bot.send("1!\n(seriously tho?)", metadata['from_group'], metadata['_id'])
    else:
        bot.send(str(random.randrange(1, number+1)) + "!", metadata['from_group'], metadata['_id'])

dice = Command(r"{ident}dice(?: (?P<number>\d+))?", "dice (<number>)", "Roll a dice.", dice)

def nested_eval(match, metadata, bot, command):
    metadata['nested'] = True
    bot.process(command, metadata)

def add_echo_command(match, metadata, bot):
    condition = str(match['condition']).strip()
    command_str = str(match['command']).strip()
    group = metadata['from_group']
    adapter_id = metadata["_id"]

    conditional_cmd = Command(condition, condition, command_str, lambda match, metadata, bot: nested_eval(match, metadata, bot, command_str), flags=["echo"],
        display_condition = lambda message, metadata, bot: False,
        exec_condition = lambda message, metadata, bot:
            metadata['from_group'] == group and metadata["_id"] == adapter_id and bot.metadata.get("regexif", True) and not metadata.get("nested", False))

    for command in bot.commands:
        if command.exec_condition(match, metadata, bot):
            if condition == command.regex and "echo" in command.flags:
                bot.commands.remove(command)
                bot.commands.append(conditional_cmd)
                bot.send("Rule Already Exists. Overridden.", metadata['from_group'], metadata['_id'])
                return
            elif re.search("^{command}$".format(command=command.regex.format(ident=metadata["ident"])), condition) and not command.raw_match:
                bot.send("Rule Not Accepted: You cannot override existing commands.", metadata['from_group'], metadata['_id'])
                return

    bot.commands.append(conditional_cmd)
    bot.send("Rule successfully created: '{}' -> {}".format(conditional_cmd.regex, conditional_cmd.description), metadata['from_group'], metadata['_id'])

add_echo = Command(r"(?P<ident>{ident})if(?: (?P<condition>.+?) (?P<command>(?P=ident).+?))?", "if <condition> <command>",
    "Excecute certain command when certain message is sent.", add_echo_command, exec_condition = lambda message, metadata, bot: metadata.get("nested", None) is None)

def remove_echo_command(match, metadata, bot):
    condition = match["condition"]

    for command in bot.commands:
        if "echo" in command.flags and command.exec_condition(match, metadata, bot):
            if condition == command.regex or re.search("^{command}$".format(command=command.regex.format(ident=metadata["ident"])), condition):
                bot.commands.remove(command)
                bot.send("Rule successfully deleted.", metadata['from_group'], metadata['_id'])
                return

    bot.send("Rule does not exist.", metadata['from_group'], metadata['_id'])

remove_echo = Command(r"{ident}removeif(?: (?P<condition>.+?))?", "removeif <message>",
    "Remove the echo rule.", remove_echo_command, exec_condition = lambda message, metadata, bot:
        metadata.get("nested", None) is None)

def list_rules(match, metadata, bot):
    try:
        condition = match["condition"]
    except AttributeError:
        condition = None

    if condition:
        for command in bot.commands:
            if condition == command.regex and "echo" in command.flags and command.exec_condition(match, metadata, bot):
                bot.send("'{}' -> {}".format(command.title, command.description), metadata['from_group'], metadata['_id'])
                return
        bot.send("Rule with condition '{}' Not Found.".format(condition), metadata['from_group'], metadata['_id'])
    else:
        rules = ""
        for command in bot.commands:
            if "echo" in command.flags and command.exec_condition(match, metadata, bot):
                rules += "'{}' -> {}\n".format(command.title, command.description)
        rules = rules.strip()
        if rules:
            bot.send(rules, metadata['from_group'], metadata['_id'])
        else:
            bot.send("No Rules Defined.", metadata['from_group'], metadata['_id'])

list_echo = Command(r"{ident}rule(?: (?P<condition>.+))?", "rule <condition>",
    "Display All Rules or (If Condition Is Given) Display Rule Containing Given Condition.", list_rules)

def switch_regexif(match, metadata, bot):
    try:
        if str(match["bool"]) in "true":
            bot.metadata["regexif"] = True
        elif str(match["bool"]) in "false":
            bot.metadata["regexif"] = False
        bot.send("regexif = %s"%bot.metadata["regexif"], metadata['from_group'], metadata['_id'])
    except AttributeError:
        pass
    except KeyError:
        bot.send("regexif = undefined", metadata['from_group'], metadata['_id'])


regex_switch = Command(r"#regexif(?: (?P<bool>true|false))?", "", "", switch_regexif,
    display_condition = lambda message, metadata, bot: False,
    exec_condition = lambda message, metadata, bot: metadata["is_mod"], flags=["mod"])

commands = [help, about, ping, dice, uptime, echo, add_echo, remove_echo, list_echo, regex_switch, ]
