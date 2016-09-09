#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram Bot to help create Doodle like planning.

It's name comes from Friends character Mike "Gandalf" Ganderson seen in
episode "The One Where They're Going To Party". He is supposedly a "party
animal" who gets Ross and Chandler in different crazy situations on nights out.
"""

# For debugging Telegram message
import argparse

# Used to wait
import time

# For debugging Telegram message
from pprint import pprint

# Telegram python binding
# c.f. https://telepot.readthedocs.io/en/latest/
import telepot

__version__ = "0.1.0"
__author__ = "Pierre-Yves Martin"
__copyright__ = "Copyright 2016, Pierre-Yves Martin"
__credits__ = []
__license__ = "AGPL-3.0"
__maintainer__ = "Pierre-Yves Martin"
__email__ = "pym.aldebaran@gmail.com"
__status__ = "Prototype"

LOG_MSG = {
    'greetings':
        'My name is {botname} and you can contact me via @{botusername} and '
        'talk to me.'
}
CHAT_MSG = {
    'help_answer':
        'This bot will help you create planings. Use /new to create a '
        'planning here, then publish it to groups or send it to individual '
        'friends.\n\n'
        'Send /plannings to manage your existing plannings.',
    'new_answer':
        'You want to create a planning named *{title}*. Send me a description'
        'or a question to ask to the participant. '
        '/cancel to abort creation.',
    'description_answer':
        'Creating new planning:\n'
        '*{title}*\n'
        '_{description}_\n\n'
        'Please send me the first option for participant to join. '
        '\cancel to abort creation.',
    'option_answer':
        'Good. Feel free to had more options. '
        '/done to finish creating the planning or \cancel to abort creation.',
    'done_answer':
        '👍 Planning created. You can now publish it to a group or send it '
        'to your friends in a private message. To do this, tap the button '
        'below or start your message in any other chat with @{botusername} '
        'and select one of your polls to send.',
    'planning_recap':
        '*{title}*\n'
        '_{description}_\n\n'
        '{options}\n'
        '👥 {nb_participants} people participated so far. '
        '_Planning {planning_status}_.'
}
OPTION_FULL = '{description} - 👥 {nb_participant}\n'\
              '{participants}'
OPTION_SHORT = '{description} - 👥 {nb_participant}'


def handle_message(msg):
    """React the the reception of a Telegram message."""
    pprint(msg)


def main():
    """Launch the bot."""
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "token",
        help="token used to connect to the Telegram Bot API")
    args = parser.parse_args()
    TOKEN = args.token

    bot = telepot.Bot(TOKEN)

    # Get the bot info
    me = bot.getMe()
    NAME = me["first_name"]
    USERNAME = me["username"]
    print(LOG_MSG['greetings'].format(
        botname=NAME,
        botusername=USERNAME))

    # Receive messages
    bot.message_loop(handle_message)
    print('Listening ...')

    # Keep the program running.
    while 1:
        time.sleep(10)


if __name__ == '__main__':
    main()
