#!/usr/bin/env python3

import time, re
from datetime import timedelta
from carbonbot import Command, CannedResponseCommand


start_time = time.time()


def display_paginated(metadata, bot, _list, index):
    linecount = 4
    list_length = len(_list)
    start_index = index * linecount
    end_index = start_index + linecount

    if index < 0:
        raise IndexError("Invalid number: use a number above or equal to 1.")

    maximum = int(-(-list_length // linecount))
    if list_length < end_index:
        end_index = list_length
        if end_index <= start_index:
            raise IndexError("Invalid number: use a number below or equal to " + str(maximum) + ".")

    message = ""
    for i in range(start_index, end_index):
        command = _list[i]
        message += "\n"+ command.title + ": " + command.description

    return (maximum, message)

def print_help(match, metadata, bot):
    command_list = tuple(x for x in bot.commands
                         if x.display_condition(match, metadata, bot) and x.title)
    target_cmd = ""

    args = match.groupdict()
    if args["page"]:
        index = int(args['page'].strip()) - 1
    elif args["command"]:
        target_cmd = args['command']
    else:
        index = 0

    if target_cmd:
        for command in list(command_list):
            if re.search("^{}$".format(command.regex.format(ident=metadata["ident"])), target_cmd) or target_cmd in command.title:
                bot.reply(command.title + ": " + command.description, metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
        bot.reply("Command '{}' does not exist or is not available.".format(target_cmd), metadata["message_id"], metadata['from_group'], metadata['_id'])
    else:
        try:
            maximum, list_message = display_paginated(metadata, bot, command_list, index)
            bot.reply("Usage: <identifier><command>\nIdentifier setting for the current adapter: `{}`\n".format(metadata["ident"]),
                      metadata["message_id"], metadata['from_group'], metadata['_id'])

            command_count = len(command_list)
            message = "Commands: {current} out of {maximum}\n".format(current=index+1, maximum=maximum)
            message += "Total of {total} command{s} {are} available.".format(total=command_count,
                                                                             s="s" if command_count > 1 else "",
                                                                             are="are" if command_count > 1 else "is")
            message += list_message
            bot.send(message, metadata['from_group'], metadata['_id'])
        except IndexError as e:
            bot.reply(str(e), metadata["message_id"], metadata['from_group'], metadata['_id'])

def print_owner(match, metadata, bot):
    bot.reply("{} is!".format(bot.adapters[metadata["_id"]].owner),
              metadata["message_id"], metadata['from_group'], metadata['_id'])


def register_with(carbon):
    carbon.add_commands(
        # About the bot
        CannedResponseCommand(r"{ident}about",
                              "about",
                              "Show information about this bot.",
                              canned = \
"""Carbon 2.0 alpha
A Multi-Protocol Bot developed by imsesaok with contributions by M1dgard.
Source code: {}""".format(carbon.SOURCE_URL)
                              ),

        # Ping to test connection
        CannedResponseCommand(r"{ident}ping",
                              "ping",
                              "Test the connection between the user and the bot.",
                              canned = "Pong!"
                              ),

        # Echo a message
        Command(r"{ident}echo(?: (?P<message>.+))?",
                "echo <message>",
                "Echo message.",
                lambda match, metadata, bot: bot.reply(match['message'], metadata["message_id"], metadata['from_group'],
                                                       metadata['_id']) if match['message'] else None
                ),

        # Help
        Command(r"{ident}help(?: ?(?:(?P<page>\d+)|(?P<command>.+)))?",
                "help <page>|<command>",
                "Show help text for a page or command.",
                print_help
                ),

        # Print owner
        Command(r"{ident}who(?:'|’)s your owner\?",
                "who's your owner?",
                "Show the owner of the bot",
                print_owner
                ),

        # Uptime
        Command(r"{ident}uptime",
                "uptime",
                "Show how long the bot has been operating.",
                lambda match, metadata, bot: bot.reply(str(timedelta(seconds=time.time() - start_time)),
                                                       metadata["message_id"], metadata['from_group'], metadata['_id'])
                ),
    )
