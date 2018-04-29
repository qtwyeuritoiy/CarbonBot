import random, re, sys, time, traceback

class Command:
    def __init__(self, regex, title, description, on_exec = None, canned = "", criteria = lambda message, metadata, bot: True):
        self.regex = regex
        self.title = title
        self.description = description
        if on_exec is not None:
            self.on_exec = self.run_on_sandbox
            self.func = on_exec
        else:
            self.on_exec = self.canned
        self.canned_response = canned
        self.criteria = criteria
    
    def canned(self, message, metadata, bot):
        bot.send(self.canned_response, metadata['from_group'], metadata['_id'])
    
    def run_on_sandbox(self, match, metadata, bot):
        try:
            self.func(match, metadata, bot)
        except:
            traceback.print_exc()
            e = sys.exc_info()[0]
            bot.send("Oops! Something Went Horribly Wrong! (%s)" % e, metadata['from_group'])

def print_help(match, metadata, bot):
    linecount = 4
    string = ""
    command_list = list()
    for command in bot.commands:
        if command.criteria(match[0], metadata, bot):
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
            bot.send("Invalid number: use number below " + str(maximum) + ".", metadata['from_group'], metadata['_id'])
            return
    
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

def add_echo_command(match, metadata, bot):
    condition = match['condition']
    reply = match['reply']
    echo_reply = Command(condition, "!if %s"%condition, "!echo %s"%reply,
        lambda message, metadata_lambda, bot: [bot.send(reply, metadata['from_group'], metadata['_id'])
            if metadata_lambda['from_group'] == metadata['from_group'] else None],
        criteria = lambda message, metadata: False)
    for command in bot.commands:
        if command.title == "!if " + condition:
            bot.commands.remove(command)
            bot.commands.append(echo_reply)
            bot.send("Rule Already Exists. Overridden.", metadata['from_group'], metadata['_id'])
            return
    
    bot.commands.append(echo_reply)
    bot.send("Rule Created.", metadata['from_group'], metadata['_id'])

from datetime import datetime, date, timedelta
about = Command(r"!about", "!about", "Show information about this bot.",
    canned = "Carbon 2.0 alpha\nA Multi-Protocol Bot run by imsesaok.")
ping = Command(r"!ping", "!ping", "Test the connection between the user and the bot.", canned = "Pong!")

dice = Command(r"!dice(?: (?P<number>\d+))?", "!dice <number>", "Roll a dice.", dice)
help = Command(r"(?:/|!)help(?: ?(?P<page>\d+))?|/start", "!help <page>", "Show this text.", print_help)
echo = Command(r"!echo (?P<message>.+)", "echo <message>", "Echo message.",
    lambda match, metadata, bot: bot.send(match['message'], metadata['from_group'], metadata['_id']))
add_echo = Command(r"!if (?P<condition>.+?) !?echo (?P<reply>.+)", "!if <message> (!)echo <message>",
    "Makes the bot reply to certain messages.", add_echo_command)


uptime = Command(r"!uptime", "!uptime", "Show how long the bot has been operating.",
    lambda match, metadata, bot: bot.send(str(timedelta(seconds=time.time() - start_time)), metadata['from_group'], metadata['_id']))
start_time = time.time()

commands = [help, about, dice, ping, uptime, echo, add_echo, ]
