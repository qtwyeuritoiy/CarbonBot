#!/usr/bin/env python3

import dice, re, numbers
from carbon2_command_classes import Command

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
        bot.reply("Unsupported dice format:\n{}".format(e.pretty_print()), metadata["message_id"], metadata['from_group'], metadata['_id'])

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

    bot.reply(formatted, metadata["message_id"], metadata['from_group'], metadata['_id'])

    # dice_expression.sides is broken: it gives 1 for fudge dice (-1 through 1), who clearly have 3 sides
    if dice_expression.min_value == dice_expression.max_value:
        bot.send("(seriously tho?)", metadata['from_group'], metadata['_id'])

dice_cmd = Command(r"{ident}dice(?: (?P<dicespec>.+))?", "dice (<dice specification>)", "Roll a dice.", dice_fun)
