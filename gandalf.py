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

# Used to launch autotests of the program
import doctest
import pytest

# Used to list unittests correctly
from glob import glob

# Telegram python binding
# c.f. https://telepot.readthedocs.io/en/latest/
import telepot
from telepot.delegate import pave_event_space, per_chat_id, per_inline_from_id
from telepot.delegate import create_open, intercept_callback_query_origin

# Handlers for the Telegram protocol
from handlers import PlannerChatHandler
from handlers import PlannerInlineHandler

__version__ = "0.1.0"
__author__ = "Pierre-Yves Martin"
__copyright__ = "Copyright 2016, Pierre-Yves Martin"
__credits__ = []
__license__ = "AGPL-3.0"
__maintainer__ = "Pierre-Yves Martin"
__email__ = "pym.aldebaran@gmail.com"
__status__ = "Prototype"

# unexported constants used as pytest.main return codes
# c.f. https://github.com/pytest-dev/pytest/blob/master/_pytest/main.py
PYTEST_EXIT_OK = 0
PYTEST_EXIT_TESTSFAILED = 1
PYTEST_EXIT_INTERRUPTED = 2
PYTEST_EXIT_INTERNALERROR = 3
PYTEST_EXIT_USAGEERROR = 4
PYTEST_EXIT_NOTESTSCOLLECTED = 5

TIMEOUT = 60*60  # sec

DEFAULT_DATABASE_FILE = 'plannings.db'

LOG_MSG = {
    'greetings':
        'My name is {botname} and you can contact me via @{botusername} and '
        'talk to me.',
    'goodbye':
        'Goodbye... it was nice seeing you.',
    'db_file_created':
        'New database file <{dbfile}> created.',
    'db_file_deleted':
        'Database file <{dbfile}> already existed and was deleted.',
}


def serve(token, db, **kwargs):
    """
    Start the bot and launch the listenning loop.

    Arguments:
        token -- Telegram bot API token
        kwargs -- other command line arguments transmited after the "serve"
                  command.
    """
    # Initialise the bot
    delegation_pattern = [
        pave_event_space()(
            per_chat_id(),
            create_open,
            PlannerChatHandler,
            db,  # Param for PlannerChatHandler constructor
            timeout=TIMEOUT),
        intercept_callback_query_origin(pave_event_space())(
            per_inline_from_id(),
            create_open,
            PlannerInlineHandler,
            db,  # Param for PlannerInlineHandler constructor
            timeout=TIMEOUT)
        ]
    bot = telepot.DelegatorBot(token, delegation_pattern)

    # Get the bot info and greet the user
    me = bot.getMe()
    print(LOG_MSG['greetings'].format(
        botname=me["first_name"],
        botusername=me["username"]))

    # Receive messages and dispatch them to the Delegates
    try:
        bot.message_loop(run_forever='Listening ...')
    except KeyboardInterrupt:
        print(LOG_MSG['goodbye'])


def createdb(db, **kwargs):
    """
    Create an new database file containing only empty tables.

    Arguments:
        db -- database file name to use
        kwargs -- other command line arguments transmited after the "createdb"
                  command.
    """
    # Delete the database file if it already exists
    if os.path.exists(db):
        os.remove(db)
        # Some feed back in the logs
        print(LOG_MSG['db_file_deleted'].format(dbfile=db))

    # Connect to the persistence database
    conn = sqlite3.connect(db)
    c = conn.cursor()

    # Create tables
    c.execute("""CREATE TABLE plannings (
        pl_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        title TEXT NOT NULL,
        status TEXT NOT NULL
        )""")
    c.execute("""CREATE TABLE options (
        opt_id INTEGER PRIMARY KEY,
        pl_id INTEGER NOT NULL,
        txt TEXT NOT NULL,
        num INTEGER NOT NULL,
        FOREIGN KEY(pl_id) REFERENCES plannings(pl_id)
        )""")
    c.execute("""CREATE TABLE voters (
        v_id INTEGER NOT NULL UNIQUE,
        first_name TEXT NOT NULL,
        last_name TEXT
        )""")
    c.execute("""CREATE TABLE votes (
        opt_id INTEGER NOT NULL,
        v_id INTEGER NOT NULL,
        FOREIGN KEY(opt_id) REFERENCES options(opt_id),
        FOREIGN KEY(v_id) REFERENCES voters(v_id)
        )""")

    # Save (commit) the changes
    conn.commit()

    # Close the connexion to the database
    conn.close()

    # Some feed back in the logs
    print(LOG_MSG['db_file_created'].format(dbfile=db))


def autotest(*args, **kwargs):
    """
    Execute all the test to check if the program works correctly.

    The tests are:
    *   test from the documentation of the code itself (via :mod:`doctest`
        module). They basically check if the usage of the function has not
        changed. This is the equivalent of doing :command:`python -m doctest -v
        ludocore.py`.
    *   unittest from the `tests` directory. Those test are here to check that
        every function works as expected and that all functionnalities are ok
        even in corner cases. They use :mod:`pytest` module.
    *   functionnal tests that try to replicate actuel usecases. They are
        located in `functional_test.py`. They use :mod:`pytest` module. This is
        the equivalent of doing :command:`py.test --quiet --tb=line
        functional_test.py`
    """
    PYTHON_FILES = sorted(glob('*.py'))
    TEST_FILES = sorted(glob('test_*.py'))
    NON_TEST_FILES = sorted(set(PYTHON_FILES) - set(TEST_FILES))
    FUNCTIONNAL_TEST_FILES = sorted(glob('test_functional*.py'))
    UNIT_TEST_FILES = sorted(set(TEST_FILES) - set(FUNCTIONNAL_TEST_FILES))

    # Doctests
    print("DOCTESTS".center(80, '#'))
    print("Tests examples from the documentation".center(80, '-'))
    for file_with_doctest in NON_TEST_FILES:
        nb_fails, nb_tests = doctest.testmod(
            __import__(file_with_doctest[:-3]),
            verbose=False)
        if nb_tests == 0:
            continue
        nb_oks = nb_tests - nb_fails
        print(file_with_doctest, " : ",
              nb_oks, "/", nb_tests, "tests are OK.")
        if nb_fails > 0:
            print("FAIL")
            print("     To have more details about the errors you should try "
                  "the command: python3 -m doctest -v", file_with_doctest, "\n")
        else:
            print("SUCCESS\n")

    # Unit tests
    if os.path.exists("test_gandalf.py"):
        print("UNIT TESTS".center(80, '#'))
        print("Tests every functionnality in deep".center(80, '-'))
        unit_result = pytest.main([
            "--quiet",
            "--color=no",
            "--tb=line"] + UNIT_TEST_FILES)
        if unit_result not in (PYTEST_EXIT_OK, PYTEST_EXIT_NOTESTSCOLLECTED):
            print("FAIL")
            print("     To have more details about the errors you should try "
                  "the command: py.test", " ".join(UNIT_TEST_FILES))
        else:
            print("SUCCESS")

    # Functional tests
    if os.path.exists("test_functional.py"):
        print("FUNCTIONAL TESTS".center(80, '#'))
        print("Tests actual real life usage and data".center(80, '-'))
        func_result = pytest.main([
            "--quiet",
            "--color=no",
            "--tb=line"] + FUNCTIONNAL_TEST_FILES)
        if func_result not in (PYTEST_EXIT_OK, PYTEST_EXIT_NOTESTSCOLLECTED):
            print("FAIL")
            print("     To have more details about the errors you should try "
                  "the command: py.test", " ".join(FUNCTIONNAL_TEST_FILES))
        else:
            print("SUCCESS")


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

    # Create the parser for the "autotest" command
    parser_autotest = subparsers.add_parser(
        'autotest', help="launch all unittests for Gandalf.")
    parser_autotest.set_defaults(func=autotest)

    # parse the args and call whatever function was selected
    args = parser.parse_args()
    args.func(**vars(args))  # We use `vars` to convert args to a dict


if __name__ == '__main__':
    main()
