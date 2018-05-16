#!/usr/bin/env python3

import re
from carbonbot import Command


def nested_eval(match, metadata, bot, command):
    metadata['nested'] = True
    bot.process(command, metadata)


def add(match, metadata, bot):
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


def show(match, metadata, bot):
    try:
        condition = match["condition"]
    except AttributeError:
        condition = None

    if condition:
        for command in bot.commands:
            if condition == command.regex and "echo" in command.flags and command.exec_condition(match, metadata, bot):
                bot.reply("'{}' -> {}".format(command.title, command.description), metadata["message_id"], metadata['from_group'], metadata['_id'])
                return
        bot.reply("Rule with condition '{}' not found.".format(condition), metadata["message_id"], metadata['from_group'], metadata['_id'])
    else:
        rules = ""
        for command in bot.commands:
            if "echo" in command.flags and command.exec_condition(match, metadata, bot):
                rules += "'{}' -> {}\n".format(command.title, command.description)
        rules = rules.strip()
        if rules:
            bot.reply(rules, metadata["message_id"], metadata['from_group'], metadata['_id'])
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
        Command(r"{ident}rule(?: (?P<condition>.+))?",
                "rule <condition>",
                "Display all rules or (if condition is given) display rules matching given condition.",
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
