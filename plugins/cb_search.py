#!/usr/bin/env python3

from duckduckpy import secure_query
from carbonbot import Command

def query(match, metadata, bot):
    result = secure_query(match["query"], user_agent=u'CarbonBot 2.0 on duckduckpy 0.2', no_redirect=True, skip_disambig=True)

    abst = result.abstract_text
    ansr = result.answer
    defi = result.definition

    abstl = result.abstract_url
    defil = result.definition_url
    redir = result.redirect

    result_text = abst if abst else defi if defi else ansr
    result_link = abstl if abstl else defil if defil else redir

    if not result_text and not result_link:
        return

    bot.reply("{}{}".format(result_text[:140]+"..." if len(result_text) > 140 else result_text,
                            " "+result_link if result_text else result_link),
             metadata["message_id"], metadata['from_group'], metadata['_id'])


def register_with(carbon):
    carbon.add_commands(
        #Instant Answers
        Command(r"\?(?P<query>.+)", "?<query>", "Search for Instant Answers in DuckDuckGo.", query),
    )
