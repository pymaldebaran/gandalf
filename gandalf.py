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

DEFAULT_DATABASE_FILE = 'plannings.db'

# Global variable used to give database file name to the threads.
# It is initialized through the program --db argument.
# Only serve() has write access to that variable to initialize it.
DATABASE_FILE = None

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
    'new_cancel_first_answer':
        'Sorry but you already have a planning creation in progress.\n'
        'You can cancel the current creation using the /cancel command or '
        'finish it using the /done command.',
    'description_answer':
        'Creating new planning:\n'
        '*{title}*\n'
        '_{description}_\n\n'
        'Please send me the first option for participant to join. '
        '/cancel to abort creation.',
    'option_answer':
        'Good. Feel free to had more options. '
        '/done to finish creating the planning or /cancel to abort creation.',
    'done_answer':
        '👍 Planning created. You can now publish it to a group or send it '
        'to your friends in a private message. To do this, tap the button '
        'below or start your message in any other chat with @{botusername} '
        'and select one of your polls to send.',
    'done_error_answer':
        'Sorry but you have to create at least one option for this planning.',
    'cancel_answer':
        'Planning creation canceled.',
    'no_current_planning_answer':
        'Sorry but there is no planning currently in edition. To start '
        'creating one use the /new command. Like this:\n\n'
        '/new _My fancy planning title_',
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


class Planning:
    """Represent a user created planning."""

    class Status(str, Enum):
        """Represent the different possible status for a planning."""

        UNDER_CONSTRUCTION = "Under construction"
        OPENED = "Opened"
        CLOSED = "Closed"

    def __init__(self, pl_id, title, status):
        """Create a new Planning."""
        self.pl_id = pl_id
        self.title = title
        self.status = status


    def short_description(self, num):
        """
        Return a short str description of the planning.

        Useful for list view of many plannings."

        Arguments:
            num -- position of the planning in the list

        Returns:
            string describing the planning prefixed by it's provided position.
        """
        return '*{num}*. *{planning.title}* - _{planning.status}_'.format(
            num=num+1,
            planning=self)


    def save_to_db(self, db_conn):
        """
        Save the Planning object to the provided database.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
        """
        # Preconditions
        assert db_conn is not None

        c = db_conn.cursor()
        c.execute("INSERT INTO plannings(title, status) VALUES (?,?)",
            (self.title, self.status))
        db_conn.commit()
        c.close()


    def update_to_db(self, db_conn):
        """
        Update the Planning object status to the provided database.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
        """
        # Preconditions
        assert db_conn is not None

        pprint(self.status)

        # Get a connexion to the database
        c = db_conn.cursor()

        # Update the planning's status in the database
        c.execute("UPDATE plannings SET status=? WHERE pl_id=?",
            (self.status, self.pl_id))

        # Check the results of the planning update consistancy
        assert c.rowcount != 0, "Tried to update planning with id {id} that "\
            "doesn't exist in database.".format(id=self.pl_id)
        assert c.rowcount == 1, "Updated more than one planning with id {id} "\
            "from the database.".format(id=self.pl_id)

        # Once the results are checked we can commit and close cursor
        db_conn.commit()
        c.close()


    def remove_from_db(self, db_conn):
        """
        Remove the Planning object and dependancies from the database.

        Remove the Planning object and all the corresponding Option object
        from the provided database.

        Arguments:
            db_conn -- connexion to the database from where the Planning will
            be removed.

        Exceptions:
            If none or many plannings would have been removed from the
            database the database AssertionError is raised.
        """
        # Preconditions
        assert db_conn is not None
        assert self.pl_id is not None

        # Get a connexion to the database
        c = db_conn.cursor()

        # First try to remove the option if any
        c.execute('DELETE FROM options WHERE pl_id=?', (self.pl_id,))

        # Remove the planning itself from the database
        c.execute('DELETE FROM plannings WHERE pl_id=?',(self.pl_id,))

        # Check the results of the planning delete
        assert c.rowcount != 0, "Tried to remove planning with id {id} that "\
            "doesn't exist in database.".format(id=self.pl_id)
        assert c.rowcount < 2, "Removed more than one planning with id {id} "\
            "from the database.".format(id=self.pl_id)

        # Once the results are checked we can commit and close cursor
        db_conn.commit()
        c.close()


    @staticmethod
    def load_all_from_db(db_conn):
        """
        Load all the instances available in the database.

        Arguments:
            db_conn -- connexion to the database from which to load the
                       plannings.

        Returns:
            A list of Planning instances corresponding to the one present in
            the database. If no instance are available [] is returned.

        """
        # Preconditions
        assert db_conn is not None

        # Retreive all the planning data from the db as tuple
        c = db_conn.cursor()
        c.execute('SELECT pl_id, title, status FROM plannings')
        rows = c.fetchall()
        c.close()

        # Create the Planning instances
        plannings = [Planning(pl_id, title, status)\
            for pl_id, title, status in rows]

        return plannings


    @staticmethod
    def load_under_construction_from_db(db_conn):
        """
        Load the only available under construction planning from the database.

        Arguments:
            db_conn -- connexion to the database from which to load the
                       plannings.

        Returns:
            If a unique planning with the status "under construction" is
            present, a correspinding Planning instance is returned.
            If no planning with the status "under construction" is present in
            the database, None is returned.

        Exceptions:
            If many planning with the status "under construction" are present
            in the database AssertionError is raised.
        """
        # Preconditions
        assert db_conn is not None

        # Retreival from the database
        c = db_conn.cursor()
        c.execute('SELECT pl_id, title, status FROM plannings WHERE status=?',
            (Planning.Status.UNDER_CONSTRUCTION,))
        rows = c.fetchall()
        c.close()

        # If we have many instances... it's an error
        assert len(rows) <= 1, "There should never be more than one "\
            "planning in edition at any given time. "\
            "{nb} have been found in the data base: {pl!r}.".format(
                nb=len(rows),
                pl=rows)

        # Now that we are sure there's not many instances, let's return what
        # we have found
        if rows:
            pl_id, title, status = rows[0]
            p = Planning(pl_id, title, status)

            # Postconditions
            assert p.pl_id is not None, "A Planning instance extracted from the "\
                "database must have an id."

            return p
        else:
            return None


class Option:
    """
    Represent a possible option for a planning.

    This could be a date, an hour, a place... in fact whatevere you what the
    attendees to select/choose in order to orgonise your planning.

    It always refer to one specific and existing planning throught its id but
    this constraint is only check when inserting the option to the database
    because of a FOREIGN KEY constraint.
    """

    def __init__(self, pl_id, txt):
        """
        Create an Option instance providing all necessary information.

        Arguments:
            pl_id -- id of a planning to which the option belong.
            txt -- free form text of the option describing what it is.
        """
        self.pl_id = pl_id
        self.txt = txt


    def save_to_db(self, db_conn):
        """
        Save the Option object to the provided database.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
        """
        # Preconditions
        assert db_conn is not None

        # Insert the new Option to the database
        c = db_conn.cursor()
        c.execute("INSERT INTO options(pl_id, txt) VALUES (?,?)",
            (self.pl_id, self.txt))
        db_conn.commit()
        c.close()


    @staticmethod
    def load_all_from_planning_id_from_db(db_conn, pl_id):
        """
        Get all the Option instance with provided planning id from database.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
            pl_id -- planning id to find

        Returns:
            A list of Option object created from the data retreived from the
            database.
            Empty list if no such object are found.
        """
        # Preconditions
        assert db_conn is not None

        # Retreival from the database
        c = db_conn.cursor()
        c.execute('SELECT pl_id, txt FROM options WHERE pl_id=?', (pl_id,))
        rows = c.fetchall()
        c.close()

        # Let's build objects from those tuples
        return [Option(my_id, my_txt) for my_id, my_txt in rows]


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
        elif is_command(text, '/cancel'):
            self.on_command_cancel()
        elif is_command(text, '/done'):
            self.on_command_done()
        # Not a command or not a recognized one
        else:
            self.on_not_a_command(text)


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
        # Precondition
        assert self._conn is not None

        # First check if there is not a planning uneder construction
        if Planning.load_under_construction_from_db(self._conn) is not None:
            self.sender.sendMessage(CHAT_MSG['new_cancel_first_answer'])
            return

        # Retrieve the title of the planning
        command, _, title = text.lstrip().partition(' ')

        # The user must provide a title
        if title == '':
            self.sender.sendMessage(
                CHAT_MSG['new_error_answer'],
                parse_mode='Markdown')
            return

        # Create a new planning
        planning = Planning(None, title, Planning.Status.UNDER_CONSTRUCTION)

        # Save the new planning to the database
        planning.save_to_db(self._conn)

        # Some feedback in the logs
        print(LOG_MSG['db_new_planning'].format(
            dbfile=DATABASE_FILE,
            title=planning.title))

        # Send the answer
        reply = CHAT_MSG['new_answer'].format(title=title)
        self.sender.sendMessage(reply, parse_mode='Markdown')


    def on_command_plannings(self):
        """Handle the /plannings command by retreiving all plannings."""
        # Preconditions
        assert self._conn is not None

        # Retrieve plannings from database
        plannings = Planning.load_all_from_db(self._conn)

        # Prepare a list of the short desc of each planning
        planning_list = '\n\n'.join(
            [p.short_description(num) for num, p in enumerate(plannings)])

        # Format the reply and send it
        reply = CHAT_MSG['plannings_answer'].format(
            nb_plannings=len(plannings),
            planning_list=planning_list)
        self.sender.sendMessage(reply, parse_mode='Markdown')


    def on_command_cancel(self):
        """
        Handle the /cancel command to cancel the current planning.

        This only works if there is a planning under construction i.e. after a
        /new command and before a /done command.
        """
        # Preconditions
        assert self._conn is not None

        # Retreive the current planning if any
        planning = Planning.load_under_construction_from_db(self._conn)

        # No planning... nothing to do
        if planning is None:
            self.sender.sendMessage(CHAT_MSG['no_current_planning_answer'])
        else:
            # TODO ask a confirmation here using button
            # Remove the planning from the database
            planning.remove_from_db(self._conn)
            self.sender.sendMessage(CHAT_MSG['cancel_answer'])


    def on_command_done(self):
        """
        Handle the /done command to finish the current planning.

        This only works if there is a planning under construction i.e. after a
        /new command and after the creation of at least one option for this
        planning.
        """
        # Preconditions
        assert self._conn is not None

        # Retreive the current planning if any
        planning = Planning.load_under_construction_from_db(self._conn)

        # No planning... nothing to do and return
        if planning is None:
            self.sender.sendMessage(CHAT_MSG['no_current_planning_answer'])
            return

        # Retrievethe corresponding options
        options = Option.load_all_from_planning_id_from_db(
            self._conn, planning.pl_id)

        # No option... ask for one and return
        if len(options) == 0 :
            self.sender.sendMessage(CHAT_MSG['done_error_answer'])
            return

        # Change planning state and update it in the database
        planning.status = Planning.Status.OPENED
        planning.update_to_db(self._conn)

        self.sender.sendMessage(CHAT_MSG['done_answer'])


    def on_not_a_command(self, text):
        """
        Handle any text message that is not a command or not a recognised one.

        If called after a /new command it adds a new option to the current
        planning.
        Any other case trigger a "I don't understand" message.

        Arguments:
        text -- string containing the text of the message recieved.
        """
        # Preconditions
        assert self._conn is not None

        # Retreive the current planning if any
        planning = Planning.load_under_construction_from_db(self._conn)

        if planning is not None:
            # We have a planning in progress... let's add the option to it !
            opt = Option(planning.pl_id, text)

            # and save the option to database
            opt.save_to_db(self._conn)

            self.sender.sendMessage(CHAT_MSG['option_answer'])
        else:
            # We have no planning in progress, we just can't understand the msg
            self.sender.sendMessage(CHAT_MSG['dont_understand'])


def serve(args):
    """
    Start the bot and launch the listenning loop.

    Arguments:
    args -- command line arguments transmited after the "serve" command.
    """
    # We need write access to the global variable database to initialise it
    global DATABASE_FILE
    DATABASE_FILE = args.db

    # Initialise the bot global variable
    delegation_pattern = pave_event_space()(
        per_chat_id(),
        create_open,
        Planner,
        timeout=TIMEOUT)
    bot = telepot.DelegatorBot(args.token, [delegation_pattern])

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
    # Delete the database file if it already exists
    if os.path.exists(args.db):
        os.remove(args.db)
        # Some feed back in the logs
        print(LOG_MSG['db_file_deleted'].format(dbfile=args.db))

    # Connect to the persistence database
    conn = sqlite3.connect(args.db)
    c = conn.cursor()

    # Create tables
    c.execute("""CREATE TABLE plannings (
        pl_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        status TEXT NOT NULL
        )""")
    c.execute("""CREATE TABLE options (
        pl_id INTEGER NOT NULL,
        txt NOT NULL,
        FOREIGN KEY(pl_id) REFERENCES plannings(pl_id)
        )""")

    # Save (commit) the changes
    conn.commit()

    # Close the connexion to the database
    conn.close()

    # Some feed back in the logs
    print(LOG_MSG['db_file_created'].format(dbfile=args.db))


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
    parser_serve.add_argument(
        "--db", help="database file to use", default=DEFAULT_DATABASE_FILE)
    parser_serve.set_defaults(func=serve)

    # create the parser for the "createdb" command
    parser_createdb = subparsers.add_parser(
        'createdb', help="create new database file")
    parser_createdb.add_argument(
        "--db", help="database file to use", default=DEFAULT_DATABASE_FILE)
    parser_createdb.set_defaults(func=createdb)

    # parse the args and call whatever function was selected
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
