import re, time
from carbon2_command_classes import CannedResponseCommand, Command
import hangman, carbon2_dice

about = CannedResponseCommand(r"{ident}about", "about", "Show information about this bot.",
    canned = "Carbon 2.0 alpha\nA Multi-Protocol Bot developed by imsesaok.\nhttps://github.com/qtwyeuritoiy/CarbonBot2")
ping = CannedResponseCommand(r"{ident}ping", "ping", "Test the connection between the user and the bot.", canned = "Pong!")
echo = Command(r"{ident}echo(?: (?P<message>.+))?", "echo <message>", "Echo message.",
    lambda match, metadata, bot: bot.reply(match['message'], metadata["message_id"], metadata['from_group'], metadata['_id']) if match['message'] else None)

from datetime import datetime, date, timedelta
uptime = Command(r"{ident}uptime", "uptime", "Show how long the bot has been operating.",
    lambda match, metadata, bot: bot.reply(str(timedelta(seconds=time.time() - start_time)), metadata["message_id"], metadata['from_group'], metadata['_id']))
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
        bot.reply("Invalid argument: expecting number.", metadata["message_id"], metadata['from_group'], metadata['_id'])
        return
    except AttributeError:
        index = 0

    start = index * linecount
    end = start + linecount

    maximum = int(-(-command_count // linecount))
    if command_count < end:
        end = command_count
        if end <= start:
            bot.reply("Invalid number: use number below " + str(maximum) + ".", metadata["message_id"],
                metadata['from_group'], metadata['_id'])
            return

    bot.reply("Usage: <identifier><command>\nIdentifier setting for the current adapter: {}\n".format(metadata["ident"]),
        metadata["message_id"], metadata['from_group'], metadata['_id'])

    message = "Commands: " + str(index + 1) + " out of " + str(maximum)
    for i in range(start, end):
        command = bot.commands[i]
        message += "\n"+ command.title + ": " + command.description

    bot.send(message, metadata['from_group'], metadata['_id'])

help = Command(r"{ident}help(?: ?(?P<page>\d+))?", "help <page>", "Show this text.", print_help)

def nested_eval(match, metadata, bot, command):
    metadata['nested'] = True
    bot.process(command, metadata)

def add_echo_command(match, metadata, bot):
    try:
        if not match['condition'] or not match['command']: return

        condition = str(match['condition']).strip()
        command_str = str(match['command']).strip()
    except AttributeError:
        return

    group = metadata['from_group']
    adapter_id = metadata["_id"]

    try:
        re.compile(condition)
    except re.error as e:
        bot.reply("Rule Not Accepted: Regular expression is not valid. ({})".format(e), metadata["message_id"], metadata['from_group'], metadata['_id'])
        return

    conditional_cmd = Command(condition, condition, command_str, lambda match, metadata, bot:
        nested_eval(match, metadata, bot, command_str), flags=["echo"],
        display_condition = lambda message, metadata, bot: False,
        exec_condition = lambda message, metadata, bot:
            metadata['from_group'] == group and metadata["_id"] == adapter_id and bot.metadata.get("regexif", True) and not metadata.get("nested", False))

    command_works=False

    for command in bot.commands:
        if command.exec_condition(match, metadata, bot):
            if condition == command.regex and "echo" in command.flags:
                bot.reply("Rule Not Accepted: Rule already exists. ('{}' -> {})\nDelete the command before writing a new one.".format(command.regex, command.description),
                        metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
            elif re.search("^{command}$".format(command=command.regex.format(ident=metadata["ident"])), condition) and not command.raw_match: #The condition matches the regex of the existing command.
                bot.reply("Rule Not Accepted: You cannot override existing commands.", metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
            elif command.exec_condition(match, {**metadata, "nested": True}, bot) and re.search("^{command}$".format(command=command.regex.format(ident=metadata["ident"])), command_str):
                command_works=True

    if not command_works:
        bot.reply("Rule Not Accepted: The command '{}' is not defined or accessible.".format(command_str), metadata["message_id"], metadata['from_group'], metadata['_id'])
        return

    bot.commands.append(conditional_cmd)
    bot.reply("Rule successfully created: '{}' -> {}".format(conditional_cmd.regex, conditional_cmd.description), metadata["message_id"],
            metadata['from_group'], metadata['_id'])

add_echo = Command(r"(?P<ident>{ident})if(?: (?P<condition>.+?) (?P<command>(?P=ident).+?))?", "if <condition> <command>",
    "Excecute certain command when certain message is sent.", add_echo_command, exec_condition = lambda message, metadata, bot: metadata.get("nested", None) is None)

def remove_echo_command(match, metadata, bot):
    try:
        condition = match["condition"]
    except AttributeError:
        return

    for command in bot.commands:
        if "echo" in command.flags and command.exec_condition(match, metadata, bot):
            if condition == command.regex:
                bot.commands.remove(command)
                bot.reply("Rule successfully deleted.", metadata["message_id"], metadata['from_group'], metadata['_id'])
                return

    bot.reply("Rule does not exist.", metadata["message_id"], metadata['from_group'], metadata['_id'])

remove_echo = Command(r"{ident}removeif(?: (?P<condition>.+?))?", "removeif <message>",
    "Remove the echo ruleby providing regex.", remove_echo_command, exec_condition = lambda message, metadata, bot:
        metadata.get("nested", None) is None)

def remove_echo_match(match, metadata, bot):
    try:
        condition = match["condition"]
    except AttributeError:
        return

    del_count = 0
    for command in bot.commands:
        if "echo" in command.flags and command.exec_condition(match, metadata, bot):
            if re.search("^{command}$".format(command=command.regex.format(ident=metadata["ident"])), condition):
                bot.commands.remove(command)
                del_count += 1

    if del_count > 0:
        bot.reply("%d rule(s) has been successfully deleted."%del_count, metadata["message_id"], metadata['from_group'], metadata['_id'])
    else:
        bot.reply("No matching rules exist.", metadata["message_id"], metadata['from_group'], metadata['_id'])

remove_match = Command(r"{ident}removematch(?: (?P<condition>.+?))?", "removematch <message>",
    "Remove the echo rule by matching regex.", remove_echo_match, exec_condition = lambda message, metadata, bot:
        metadata.get("nested", None) is None)

def list_rules(match, metadata, bot):
    try:
        condition = match["condition"]
    except AttributeError:
        condition = None

    if condition:
        for command in bot.commands:
            if condition == command.regex and "echo" in command.flags and command.exec_condition(match, metadata, bot):
                bot.reply("'{}' -> {}".format(command.title, command.description), metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
        bot.reply("Rule with condition '{}' Not Found.".format(condition), metadata["message_id"], metadata['from_group'], metadata['_id'])
    else:
        rules = ""
        for command in bot.commands:
            if "echo" in command.flags and command.exec_condition(match, metadata, bot):
                rules += "'{}' -> {}\n".format(command.title, command.description)
        rules = rules.strip()
        if rules:
            bot.reply(rules, metadata["message_id"], metadata['from_group'], metadata['_id'])
        else:
            bot.reply("No Rules Defined.", metadata["message_id"], metadata['from_group'], metadata['_id'])

list_echo = Command(r"{ident}rule(?: (?P<condition>.+))?", "rule <condition>",
    "Display All Rules or (If Condition Is Given) Display Rule Containing Given Condition.", list_rules)

def switch_regexif(match, metadata, bot):
    try:
        if str(match["bool"]) in "true":
            bot.metadata["regexif"] = True
        elif str(match["bool"]) in "false":
            bot.metadata["regexif"] = False
        bot.reply("regexif = %s"%bot.metadata["regexif"], metadata["message_id"], metadata['from_group'], metadata['_id'])
    except AttributeError:
        pass
    except KeyError:
        bot.reply("regexif = undefined", metadata["message_id"], metadata['from_group'], metadata['_id'])

regex_switch = Command(r"#regexif(?: (?P<bool>true|false))?", "", "", switch_regexif,
    display_condition = lambda message, metadata, bot: False,
    exec_condition = lambda message, metadata, bot: metadata["is_mod"], flags=["mod"])

commands = [help, about, ping, carbon2_dice.dice_cmd, uptime, echo, add_echo, remove_echo, list_echo, regex_switch, *hangman.commands, ]
