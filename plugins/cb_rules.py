#!/usr/bin/env python3

import re
from carbonbot import Command


def nested_eval(match, metadata, bot, command):
    metadata['nested'] = True
    bot.process(command, metadata)


def add(match, metadata, bot):
    if not metadata.get("regexif", True):
        bot.reply("This feature is currently disabled.", metadata["message_id"], metadata['from_group'], metadata['_id'])
        return

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
        bot.reply("Rule not accepted: regular expression is not valid. ({})".format(e),
                  metadata["message_id"], metadata['from_group'], metadata['_id'])
        return

    conditional_cmd = Command(condition, condition, command_str,
                              lambda match, metadata, bot: nested_eval(match, metadata, bot, command_str), flags=["echo"],
                              display_condition = lambda message, metadata, bot: False,
                              exec_condition = lambda message, metadata, bot: metadata['from_group'] == group \
                                                                              and metadata["_id"] == adapter_id \
                                                                              and metadata.get("regexif", True) \
                                                                              and not metadata.get("nested", False))

    command_works=False

    for command in bot.commands:
        if command.exec_condition(match, metadata, bot):
            if condition == command.regex and "echo" in command.flags:
                bot.reply("Rule not accepted: rule already exists. ('{}' -> {})\n"\
                          "Delete the command before writing a new one.".format(command.regex, command.description),
                          metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
            elif re.search("^{command}$".format(command=command.regex.format(ident=metadata["ident"])), condition) and not command.raw_match: #The condition matches the regex of the existing command.
                bot.reply("Rule not accepted: you cannot override existing commands.", metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
            elif command.exec_condition(match, {**metadata, "nested": True}, bot) and re.search("^{command}$".format(command=command.regex.format(ident=metadata["ident"])), command_str):
                command_works=True

    if not command_works:
        bot.reply("rule not accepted: the command '{}' is not defined or accessible.".format(command_str), metadata["message_id"], metadata['from_group'], metadata['_id'])
        return

    bot.commands.append(conditional_cmd)
    bot.reply("Rule successfully created: '{}' -> {}".format(conditional_cmd.regex, conditional_cmd.description), metadata["message_id"],
            metadata['from_group'], metadata['_id'])


def remove(match, metadata, bot):
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


def remove_matching(match, metadata, bot):
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
        bot.reply("{} rule{} ha{} been successfully deleted.".format(del_count,
                                                                     "s" if del_count != 1 else "",
                                                                     "ve" if del_count != 1 else "s"
                                                                     ),
                  metadata["message_id"], metadata['from_group'], metadata['_id']
                  )
    else:
        bot.reply("No matching rules exist.", metadata["message_id"], metadata['from_group'], metadata['_id'])

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
        message += "'{}' -> {}\n".format(command.title, command.description)

    return (maximum, message.strip())

def show(match, metadata, bot):
    if not metadata.get("regexif", True):
        bot.reply("The feature is currently disabled.", metadata["message_id"], metadata['from_group'], metadata['_id'])
        return

    rule_list = tuple(x for x in bot.commands
                         if "echo" in x.flags and x.exec_condition(match, metadata, bot))

    args = match.groupdict()
    condition = ""
    if args["page"]:
        index = int(args['page'].strip()) - 1
    elif args["condition"]:
        condition = args['condition']
    else:
        index = 0

    if condition:
        for command in rule_list:
            if condition == command.regex and "echo" in command.flags and command.exec_condition(match, metadata, bot):
                bot.reply("'{}' -> {}".format(command.title, command.description), metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
        bot.reply("Rule with condition '{}' not found.".format(condition), metadata["message_id"], metadata['from_group'], metadata['_id'])

    else:
        rule_count = len(rule_list)
        if rule_count > 0:
            try:
                maximum, list_message = display_paginated(metadata, bot, rule_list, index)

                message = "Rules: {current} out of {maximum}\n".format(current=index+1, maximum=maximum)
                message += "Total of {total} rule{s} {are} available.\n".format(total=rule_count,
                                                                                 s="s" if rule_count > 1 else "",
                                                                                 are="are" if rule_count > 1 else "is")
                message += list_message
                bot.reply(message, metadata["message_id"], metadata['from_group'], metadata['_id'])
            except IndexError as e:
                bot.reply(str(e), metadata["message_id"], metadata['from_group'], metadata['_id'])
        else:
            bot.reply("No rules defined.", metadata["message_id"], metadata['from_group'], metadata['_id'])


def set_regexif(match, metadata, bot):
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


def register_with(carbon):
    carbon.add_commands(
        # Add rule
        Command(r"(?P<ident>{ident})if(?: (?P<condition>.+?) (?P<command>(?P=ident).+?))?",
                "if <condition> <command>",
                "Excecute certain command when a message matching the condition is sent.",
                add,
                exec_condition = lambda message, metadata, bot: metadata.get("nested", None) is None
                ),

        # Show rules
        Command(r"{ident}rule(?: ?(?:(?P<page>\d+)|(?P<condition>.+)))?",
                "rule <condition>|<page>",
                "Display all rules by page (if page is given) or (if condition is given) display rules matching given condition.",
                show
                ),

        # Remove rule
        Command(r"{ident}removeif(?: (?P<condition>.+?))?",
                "removeif <condition>",
                "Remove a rule by providing its condition literally.",
                remove,
                exec_condition = lambda message, metadata, bot: metadata.get("nested", None) is None
                ),

        # Remove rule by matching
        Command(r"{ident}removematch(?: (?P<condition>.+?))?",
                "removematch <message>",
                "Remove rules that would match on given text.",
                remove_matching,
                exec_condition = lambda message, metadata, bot: metadata.get("nested", None) is None
                ),

        # Regexif
        Command(r"#regexif(?: (?P<bool>true|false))?",
                "#regexif [true|false]",
                "Enable or disable the execution of rules.",
                set_regexif,
                display_condition = lambda message, metadata, bot: False,
                exec_condition = lambda message, metadata, bot: metadata["is_mod"],
                flags=["mod"]
                ),
    )
