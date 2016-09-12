#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot to help create Doodle like planning.

It's name comes from Friends character Mike "Gandalf" Ganderson seen in
episode "The One Where They're Going To Party". He is supposedly a "party
animal" who gets Ross and Chandler in different crazy situations on nights out.

Usage:

First create a database:
# gandalf.py create

Then launch the server using a Telegram Bot API Token:
# gadalf.py serve 999999999999999999999999

"""

# For clean access to program arguments
import argparse

# For database access snce we need data persistence
import sqlite3

# For path manipulation
import os.path

# For file manipulation
import os

# Used to represent status of a planning
from enum import Enum

# For debugging Telegram message
from pprint import pprint

# Telegram python binding
# c.f. https://telepot.readthedocs.io/en/latest/
import telepot
from telepot.delegate import pave_event_space, per_chat_id, create_open

__version__ = "0.1.0"
__author__ = "Pierre-Yves Martin"
__copyright__ = "Copyright 2016, Pierre-Yves Martin"
__credits__ = []
__license__ = "AGPL-3.0"
__maintainer__ = "Pierre-Yves Martin"
__email__ = "pym.aldebaran@gmail.com"
__status__ = "Prototype"

TIMEOUT = 60*60  # sec

DATABASE_FILE = 'plannings.db'

LOG_MSG = {
    'greetings':
        'My name is {botname} and you can contact me via @{botusername} and '
        'talk to me.',
    'goodbye':
        '\nParty is over ! Time to go to bed.',
    'user_greetings':
        'Hello {userfirstname}... are you doing?',
    'user_goodbye':
        'Goodbye {userfirstname}... it was nice seeing you.',
    'db_file_created':
        'New database file <{dbfile}> created.',
    'db_file_deleted':
        'Database file <{dbfile}> already existed and was deleted.',
    'db_new_planning':
        'Planning "{title}" added to database file <{dbfile}>.'
}
CHAT_MSG = {
    'help_answer':
        'This bot will help you create planings. Use /new to create a '
        'planning here, then publish it to groups or send it to individual '
        'friends.\n\n'
        'You can control me by sending these commands:\n\n'
        '/new - create a new planning\n'
        '/plannings - manage your existing plannings.\n'
        '/help - display this help',
    'dont_understand':
        'Sorry I did not understand... try /help to see how you should talk '
        'to me.',
    'new_answer':
        'You want to create a planning named *{title}*. Send me a description'
        'or a question to ask to the participant. '
        '/cancel to abort creation.',
    'new_error_answer':
        'Sorry to create a planning you have give a title after the /new '
        'command. Like this :\n\n'
        '/new _My fancy planning title_',
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
    'plannings_answer':
        'You have currently {nb_plannings} plannings:\n\n'
        '{planning_list}',
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

# Global variable to store the plannings
plannings = []


class Planning:
    """Represent a user created planning."""

    class Status(str, Enum):
        """Represent the different possible status for a planning."""

        UNDER_CONSTRUCTION = "Under construction"
        OPENED = "Opened"
        CLOSED = "Closed"

    def __init__(self, title):
        """Create a new Planning."""
        self.title = title
        self.status = Planning.Status.UNDER_CONSTRUCTION


def is_command(text, cmd):
    """Analyse a string to determine if it is a peticular command message.

    This function does not check for valid number of parameters in the
    message.

    Arguments:
    text -- a string to analyse.
    cmd -- the command to check for. It must include the leading '/' char.
    """
    # cmd preconditions
    assert cmd.strip() == cmd  # No spaces around
    assert cmd.startswith('/')  # Leading slash included
    assert len(cmd) > 1  # At least one char for command name

    return len(text.strip()) > 0 and text.split()[0] == cmd


class Planner(telepot.helper.ChatHandler):
    """Process messages to create persistent plannings."""

    def __init__(self, *args, **kwargs):
        """
        Create a new Planner.

        This is implicitly called when creating a new thread.
        """
        super(Planner, self).__init__(*args, **kwargs)
        self._from = None  # User that started the chat with the bot
        self._conn = None  # Connexion to the database


    def open(self, initial_msg, seed):
        """Called at the 1st messag of a user."""
        # Preconditions
        assert self._from is None
        assert self._conn is None

        # Initialise the from attribute using the first message
        self._from = initial_msg['from']

        # Connect to the persistence database
        self._conn = sqlite3.connect(DATABASE_FILE)

        # Some feedback for the logs
        print(LOG_MSG['user_greetings'].format(
            userfirstname=self._from['first_name']))

        # Post condition
        assert self._from is not None
        assert self._conn is not None


    def on_close(self, ex):
        """
        Called after timeout.

        Timeout is mandatory to prevent infinity of threads to be created.
        """
        # Preconditions
        assert self._from is not None
        assert self._conn is not None

        # Close the connexion to the database
        self._conn.close()

        # Some feedback for the logs
        print(LOG_MSG['user_goodbye'].format(
            userfirstname=self._from['first_name']))


    def on_chat_message(self, msg):
        """React the the reception of a Telegram message."""
        # We need write access to the plannings global variables
        global plannings

        # Raw printing of the message received
        pprint(msg)

        # Retreive basic information
        content_type, _, chat_id = telepot.glance(msg)

        # We only want text messages
        if content_type != 'text':
            self.sender.sendMessage(CHAT_MSG['dont_understand'])
            return

        # Now we can extract the text...
        text = msg['text']

        # Switching according to witch command is received
        if is_command(text, '/help'):
            self.on_command_help()
        elif is_command(text, '/new'):
            self.on_command_new(text)
        elif is_command(text, '/plannings'):
            self.on_command_plannings()
        # Not a command or not a recognized one
        else:
            self.sender.sendMessage(CHAT_MSG['dont_understand'])


    def on_command_help(self):
        """Handle the /help command by sending an help message."""
        self.sender.sendMessage(CHAT_MSG['help_answer'])


    def on_command_new(self, text):
        """
        Handle the /new command by creating a new planning.

        Arguments:
        text -- string containing the text of the message recieved (including
                the /new command)
        """
        # Retrieve the title of the planning
        command, _, title = text.lstrip().partition(' ')

        # The user must provide a title
        if title == '':
            self.sender.sendMessage(
                CHAT_MSG['new_error_answer'],
                parse_mode='Markdown')
            return

        # TODO remove the planning variable in favor of the database
        # Create a new planning
        planning = Planning(title)
        plannings.append(planning)

        # TODO move this to Planning class
        # Get a cursor to the database
        c = self._conn.cursor()

        # Insert a new row to the database
        c.execute("INSERT INTO plannings VALUES (?,?)",
            (planning.title, planning.status))

        # Save (commit) the changes
        self._conn.commit()

        # Some feedback in the logs
        print(LOG_MSG['db_new_planning'].format(
            dbfile=DATABASE_FILE,
            title=planning.title))

        # Send the answer
        reply = CHAT_MSG['new_answer'].format(title=title)
        self.sender.sendMessage(reply, parse_mode='Markdown')


    def on_command_plannings(self):
        """Handle the /plannings command by retreiving all plannings."""
        # TODO use only 2 string params using the planning.title syntax
        # TODO retrieve the inf from the database
        # TODO put the formating in the Planning class
        # Prepare a list of the short desc of each planning
        planning_list = '\n\n'.join(
            ['*{num}*. *{title}* - _{status}_'.format(
                num=num+1, title=p.title, status=p.status)
            for num, p in enumerate(plannings)])

        # Format the reply and send it
        reply = CHAT_MSG['plannings_answer'].format(
            nb_plannings=len(plannings),
            planning_list=planning_list)
        self.sender.sendMessage(reply, parse_mode='Markdown')


def serve(args):
    """
    Start the bot and launch the listenning loop.

    Arguments:
    args -- command line arguments transmited after the "serve" command.
    """
    TOKEN = args.token

    # Initialise the bot global variable
    delegation_pattern = pave_event_space()(
        per_chat_id(),
        create_open,
        Planner,
        timeout=TIMEOUT)
    bot = telepot.DelegatorBot(TOKEN, [delegation_pattern])

    # Get the bot info
    me = bot.getMe()
    NAME = me["first_name"]
    USERNAME = me["username"]
    print(LOG_MSG['greetings'].format(
        botname=NAME,
        botusername=USERNAME))

    # Receive messages and dispatch them to the Delegates
    try:
        bot.message_loop(run_forever='Listening ...')
    except KeyboardInterrupt:
        print(LOG_MSG['goodbye'])


def createdb(args):
    """
    Create an new database file containing only empty tables.

    Arguments:
    args -- command line arguments transmited after the "serve" command.
    """
    # TODO replace database file name constant by a command line arg
    # Delete the database file if it already exists
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        # Some feed back in the logs
        print(LOG_MSG['db_file_deleted'].format(dbfile=DATABASE_FILE))

    # Connect to the persistence database
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    # Create tables
    c.execute("CREATE TABLE plannings (title TEXT, status TEXT)")

    # Save (commit) the changes
    conn.commit()

    # Close the connexion to the database
    conn.close()

    # Some feed back in the logs
    print(LOG_MSG['db_file_created'].format(dbfile=DATABASE_FILE))


def main():
    """Parse the command line arguments and launch the corresponding func."""
    # create the top-level parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # create the parser for the "serve" command
    parser_serve = subparsers.add_parser(
        'serve', help="listen for chats")
    parser_serve.add_argument(
        "token", help="token used to connect to the Telegram Bot API")
    parser_serve.set_defaults(func=serve)

    # create the parser for the "createdb" command
    parser_createdb = subparsers.add_parser(
        'createdb', help="create new database file")
    parser_createdb.set_defaults(func=createdb)

    # TODO make args a global variable for the threads to access it (read only)
    # parse the args and call whatever function was selected
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
