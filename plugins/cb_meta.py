#!/usr/bin/env python3

import time
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
                         if x.display_condition(match[0], metadata, bot) and x.title)
    target_cmd = ""

    args = match.groupdict()
    if args["page"]:
        index = int(args['page'].strip()) - 1
    elif args["command"]:
        target_cmd = args['command']
    else:
        index = 0

    if target_cmd:
        #for command in command_list:
        pass
    else:
        try:
            maximum, list_message = display_paginated(metadata, bot, command_list, index)
            bot.reply("Usage: <identifier><command>\nIdentifier setting for the current adapter: `{}`\n".format(metadata["ident"]),
                      metadata["message_id"], metadata['from_group'], metadata['_id'])

            message = "Commands: " + str(index+1) + " out of " + str(maximum)
            message += list_message
            bot.send_index(message, metadata['from_group'], metadata['_id'])
        except IndexError as e:
            bot.reply(str(e), metadata["message_id"], metadata['from_group'], metadata['_id'])

def register_with(carbon):
    carbon.add_commands(
        # About the bot
        CannedResponseCommand(r"{ident}about",
                              "about",
                              "Show information about this bot.",
                              canned = \
"""Carbon 2.0 alpha
A Multi-Protocol Bot developed by imsesaok with contributions by M1dgard.
https://github.com/qtwyeuritoiy/CarbonBot2"""
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
        Command(r"{ident}help(?: ?(?:(?P<page>\d+)|(?P<command>\s+)))?",
                "help <page>|<command>",
                "Show help text for a page or command.",
                print_help
                ),

        # Uptime
        Command(r"{ident}uptime",
                "uptime",
                "Show how long the bot has been operating.",
                lambda match, metadata, bot: bot.reply(str(timedelta(seconds=time.time() - start_time)),
                                                       metadata["message_id"], metadata['from_group'], metadata['_id'])
                ),
    )
