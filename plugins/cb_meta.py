#!/usr/bin/env python3

import time
from datetime import timedelta
from carbonbot import Command, CannedResponseCommand


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
        bot.reply("Invalid argument: expecting integer.", metadata["message_id"], metadata['from_group'], metadata['_id'])
        return
    except AttributeError:
        index = 0

    start = index * linecount
    end = start + linecount

    maximum = int(-(-command_count // linecount))
    if command_count < end:
        end = command_count
        if end <= start:
            bot.reply("Invalid number: use a number below " + str(maximum) + ".", metadata["message_id"],
                metadata['from_group'], metadata['_id'])
            return

    bot.reply("Usage: <identifier><command>\nIdentifier setting for the current adapter: `{}`\n".format(metadata["ident"]),
        metadata["message_id"], metadata['from_group'], metadata['_id'])

    message = "Commands: " + str(index + 1) + " out of " + str(maximum)
    for i in range(start, end):
        command = bot.commands[i]
        message += "\n"+ command.title + ": " + command.description

    bot.send(message, metadata['from_group'], metadata['_id'])


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
                lambda match, metadata, bot: bot.reply(match['message'], metadata["message_id"], metadata['from_group'], metadata['_id']) if match['message'] else None
                ),

        # Help
        Command(r"{ident}help(?: ?(?P<page>\d+))?",
                "help <page>",
                "Show this text.",
                print_help
                ),

        # Uptime
        Command(r"{ident}uptime",
                "uptime",
                "Show how long the bot has been operating.",
                lambda match, metadata, bot: bot.reply(str(timedelta(seconds=time.time() - start_time)), metadata["message_id"], metadata['from_group'], metadata['_id'])
                ),
    )
