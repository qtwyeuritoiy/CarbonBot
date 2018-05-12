import random, re, sys, time, traceback, numbers
from carbon2_command_classes import CannedResponseCommand, Command
import dice
import hangman

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
        bot.send("Invalid argument: expecting integer.", metadata['from_group'], metadata['_id'])
        return
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


def format_six_faced_die(value):
    return ("⚀", "⚁", "⚂", "⚃", "⚄", "⚅")[value-1]


def format_fudge_die(value):
    return ("⊟", "⊡", "⊞")[value+1]


def format_other_die(value):
    return "[{}]".format(value)


def dice_fun(match, metadata, bot):
    spec = match["dicespec"]

    if not spec:
        spec = "1d6"

    if "," in spec:
        spec = spec.split(",")

        match = match.groupdict()
        for x in spec:
            match["dicespec"] = x
            dice_fun(match, metadata, bot)
        return

    # Some cases we would like to handle that the dice library does not support
    if re.fullmatch(r'\d+', spec):
        spec = "1d" + spec
    elif re.fullmatch(r'\d+d', spec):
        spec = spec + "6"

    # Let the dice library parse the format
    try:
        dice_expression = dice.parse_expression(spec)[0]
    except dice.exceptions.DiceBaseException as e:
        bot.send("Unsupported dice format:\n{}".format(e.pretty_print()), metadata['from_group'], metadata['_id'])
        return

    # Roll the dice
    dice_result = dice_expression.evaluate_cached()

    # Format the result
    try:
        # Format 6-faced dice differently
        if dice_expression.min_value == 1 and dice_expression.max_value == 6:
            formatter = format_six_faced_die
        elif dice_expression.min_value == -1 and dice_expression.max_value == 1:
            formatter = format_fudge_die
        else:
            formatter = format_other_die

        if dice_expression.amount == 1:
            format_string = "{graphic}"
        else:
            format_string = "{total}: {graphic}"

        formatted = format_string.format(graphic=' '.join(map(formatter, dice_result)),
                                         total=sum(dice_result))

    except AttributeError:
        # If the dice_expression doesn't have min_value, it's probably a complex spec that evaluates to just a number.
        # Check this explicitly to avoid leaking information.
        if isinstance(dice_result, numbers.Number):
            formatted = str(dice_result)
        else:
            formatted = "Unable to recognize dice result"
            print("Unable to recognize dice result: {}".format(dice_result))


    bot.send(formatted, metadata['from_group'], metadata['_id'])

    # dice_expression.sides is broken: it gives 1 for fudge dice (-1 through 1), who clearly have 3 sides
    if dice_expression.min_value == 1 and dice_expression.max_value == 1:
        bot.send("(seriously tho?)", metadata['from_group'], metadata['_id'])

dice_cmd = Command(r"{ident}dice(?: (?P<dicespec>.+))?", "dice (<dice specification>)", "Roll a dice.", dice_fun)

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

commands = [help, about, ping, dice_cmd, uptime, echo, add_echo, remove_echo, list_echo, regex_switch, *hangman.commands, ]
