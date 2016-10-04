# -*- coding: utf-8 -*-
"""Test file for the gandalf poject."""

# Gandalf module to test
from gandalf import createdb, PlannerChatHandler
from planning import Planning
from handlers import is_command

# Unit test utils
import pytest
from unittest.mock import MagicMock, call

# Used to inspect databse content
import sqlite3

# Used to mimic answers of the bot through Mock object calls
from telepot.namedtuple import InlineKeyboardMarkup
from telepot.namedtuple import InlineKeyboardButton

# Used to easily contruct fake messages
from telepot.namedtuple import Message, User, Chat
import time


def test_is_command():
    """Test all interesting cases for the is_command() function."""
    # Positive cases
    assert is_command("/foo", "/foo"), "Commands are matched when alone."
    assert is_command("/bar", "/bar"), "Commands other than /foo are matched."
    assert is_command(" /foo", "/foo"),\
        "Commands preceded by spaces are matched."
    assert is_command("/foo blah", "/foo"),\
        "Commands followed by one word are matched."
    assert is_command("/foo blah blah", "/foo"),\
        "Commands followed by any text are matched."
    assert is_command("/foo /blah", "/foo"),\
        "Commands followed by other commands are matched."

    # Negative cases
    assert not is_command("blah", "/foo"),\
        "Random text does not match command."
    assert not is_command("/bar", "/foo"),\
        "Random command does not match another command."
    assert not is_command("", "/foo"),\
        "Empty text does not match command."
    assert not is_command("a/foo", "/foo"),\
        "Commands can not be preceded by a char."
    assert not is_command("blah /foo", "/foo"),\
        "Commands can not be preceded by text."
    assert not is_command("/fooooooo", "/foo"),\
        "Commands with extra char does not match."


def test_createdb(tmpdir):
    """Test the creation of an empty database."""
    # A temp file to store the database
    db_test = str(tmpdir.join('test'))

    # Let's create the database
    createdb(db=db_test)

    # Test the database

    # We need connexion and cursor
    conn = sqlite3.connect(db_test)
    cursor = conn.cursor()

    # Table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    tables = [e for (e,) in tables]  # just unpacking tuples
    assert len(tables) == 2
    assert "plannings" in tables
    assert "options" in tables

    # Table columns
    # We use PRAGMA table_info('table_name') to get the column descriptions
    # The returned table has this structure (illustrated by an exemple):
    # cid         name        type        notnull     dflt_value  pk
    # ----------  ----------  ----------  ----------  ----------  ----------
    # 0           id          integer     99                      1
    # 1           name                    0                       0
    cursor.execute("PRAGMA table_info('plannings')")
    plannings_columns = cursor.fetchall()
    assert len(plannings_columns) == 4
    assert ('pl_id', 'INTEGER') == plannings_columns[0][1:3]
    assert ('user_id', 'INTEGER') == plannings_columns[1][1:3]
    assert ('title', 'TEXT') == plannings_columns[2][1:3]
    assert ('status', 'TEXT') == plannings_columns[3][1:3]

    cursor.execute("PRAGMA table_info('options')")
    plannings_columns = cursor.fetchall()
    assert len(plannings_columns) == 3
    assert ('pl_id', 'INTEGER') == plannings_columns[0][1:3]
    assert ('txt', 'TEXT') == plannings_columns[1][1:3]
    assert ('num', 'INTEGER') == plannings_columns[2][1:3]


class PlannerChatHandlerTester:
    """
    Helper class that makes the tests of PlannerChatHandler scenario easier.

    Once initialized this object allows you to just call send_message() method
    many times to simulate a discussion with the bot.
    """

    def __init__(self, db):
        """Create a ready-to-use PlannerChatHandlerTester instance."""
        self.db = db
        self._users_planner = {}  # user_id -> PlannerChatHandler

    def _create_test_planner(self):
        """Create a new PlannerChatHandler object configured for testing."""
        # Dummy parameters
        seed = MagicMock(), MagicMock(), MagicMock()
        event_space = MagicMock()
        timeout = 1

        # Create the planner itself
        planner = PlannerChatHandler(
            seed_tuple=seed,
            db_file=self.db,
            event_space=event_space,
            timeout=timeout)

        # We replace the sendMessage() func by a mock to be able to query
        # the number and argument of the sendMessage() calls
        planner.sender.sendMessage = MagicMock()

        # We force the planner's bot to have the good name
        planner.bot.getMe = MagicMock(
            return_value={"username": "gandalf_planner_bot"})

        return planner

    def get_planner(self, user):
        """Retreive the planner associated to the provided user."""
        assert user is not None
        assert 'id' in user

        return self._users_planner[user['id']]

    def send_message(self, user, txt):
        """
        Encapsulate sending of message for easy test writing.

        Arguments:
            user -- dict describing the user sending the message.
                    It must mimics a Telegram User description.
            txt -- text content of the wannabe message.
        """
        # Preconditions
        assert user is not None
        assert 'id' in user

        user_id = user['id']
        msg = fake_msg(user, txt)

        # If the user does not have a planner yet let's create it
        if user_id not in self._users_planner:
            # Put the planner in the dict
            self._users_planner[user_id] = self._create_test_planner()

        # We have a user we can send the message
        planner = self._users_planner.get(user_id, self._create_test_planner())
        planner.on_chat_message(msg)


def FakeMessage(**kwargs):
    """
    Helper pseudo type to create fake Telegram messages.

    Returns:
        A dict compatible with Telegram definition of a message.
    """
    # Preconditions
    assert all([key in Message._fields for key in kwargs])
    assert 'from_' in kwargs

    # Work around the fact from is a reserved word and can't be used as
    # parameter name
    kwargs['from'] = kwargs['from_']
    del kwargs['from_']

    return kwargs


def FakeUser(**kwargs):
    """
    Helper pseudo type to create fake Telegram user.

    Returns:
        A dict compatible with Telegram definition of a message.
    """
    # Preconditions
    assert all([key in User._fields for key in kwargs])
    assert 'first_name' in kwargs
    assert 'id' not in kwargs

    kwargs['id'] = hash(kwargs['first_name'])

    return kwargs


def FakeChat(**kwargs):
    """
    Helper pseudo type to create fake Telegram chat.

    Returns:
        A dict compatible with Telegram definition of a message.
    """
    # Preconditions
    assert all([key in Chat._fields for key in kwargs])
    assert 'id' not in kwargs

    # KISS way to have a unique id for each chat
    kwargs['id'] = hash(time.time())

    return kwargs


def fake_msg(user, txt):
    """
    Helper function to create fake messages for test purpose.

    Arguments:
        user -- dict describing the user sending the message.
                It must mimics a Telegram User description.
        txt -- text content of the wannabe message.

    Returns:
        a dict object that looks enough like an real telegram message.
    """
    return FakeMessage(
        chat=FakeChat(type='text'),
        from_=user,
        text=txt)


@pytest.fixture()
def init_planner_tester(tmpdir):
    """Setup and Teardown for all tests about the PlannerChatHandler class."""
    # Create a database for the test
    db_test = str(tmpdir.join('test.db'))
    createdb(db=db_test)
    conn = sqlite3.connect(db_test)
    cursor = conn.cursor()

    # Create easy to use planner tester
    planner_tester = PlannerChatHandlerTester(db_test)

    yield db_test, cursor, planner_tester

    # Close the database and cursor
    cursor.close()
    conn.close()


@pytest.fixture()
def users():
    """Setup that gives some users for sending messages."""
    joey = FakeUser(
        first_name='Joey',
        last_name='Tribbiani',
        username='@friendsjoey')

    chandler = FakeUser(
        first_name='Chandler',
        last_name='Bing',
        username='@friendschandler')

    return joey, chandler


def test_say_anything(init_planner_tester, users):
    """Test what happens when we send whatever message to the bot."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    planner_tester.send_message(user, "Hello handsome ;)")

    # Test answer
    planner = planner_tester.get_planner(user)
    assert planner.sender.sendMessage.call_count == 1
    planner.sender.sendMessage.assert_called_once_with(
        'Sorry I did not understand... try /help to see how you should talk '
        'to me.')

    # Test the database content

    # Plannings table
    cursor.execute("SELECT * FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No planning should have been created."

    # Options table
    cursor.execute("SELECT * FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."


def test_help_command(init_planner_tester, users):
    """Test what happens when using the /help command."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    planner_tester.send_message(user, "/help")

    # Test answer
    planner = planner_tester.get_planner(user)
    assert planner.sender.sendMessage.call_count == 1
    planner.sender.sendMessage.assert_called_once_with(
        'This bot will help you create planings. Use /new to create a '
        'planning here, then publish it to groups or send it to individual '
        'friends.\n\n'
        'You can control me by sending these commands:\n\n'
        '/new - create a new planning\n'
        '/plannings - manage your existing plannings.\n'
        '/help - display this help')


def test_new_command_starts_creation_of_a_planning(init_planner_tester, users):
    """Test what happens when using the /new command."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    planner_tester.send_message(user, "/new Fancy diner")

    # Test answer
    planner = planner_tester.get_planner(user)
    assert planner.sender.sendMessage.call_count == 1
    planner.sender.sendMessage.assert_called_once_with(
        'You want to create a planning named *Fancy diner*. Send me a '
        'description or a question to ask to the participant. '
        '/cancel to abort creation.',
        parse_mode='Markdown')

    # Test the database content

    # Plannings table
    cursor.execute("SELECT * FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 1, "Only one planning should be created."
    _, user_id, title, status = rows[0]
    assert user['id'] == user_id,\
        "User id of the sender should be set correctly."
    assert "Fancy diner" == title,\
        "Title should be set correctly."
    assert Planning.Status.UNDER_CONSTRUCTION == status,\
        "Status should be set correctly."

    # Options table
    cursor.execute("SELECT * FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."


def test_new_command_without_title(init_planner_tester, users):
    """Test what happens when /new command is used without a title."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    planner_tester.send_message(user, "/new")

    # Test answer
    planner = planner_tester.get_planner(user)
    assert planner.sender.sendMessage.call_count == 1
    planner.sender.sendMessage.assert_called_once_with(
        'Sorry to create a planning you have give a title after the /new '
        'command. Like this :\n\n'
        '/new _My fancy planning title_',
        parse_mode='Markdown')

    # Test the database content

    # Plannings table
    cursor.execute("SELECT * FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No planning should be created."
    # Options table
    cursor.execute("SELECT * FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."


def test_done_command_show_a_planning_recap(init_planner_tester, users):
    """Test what is sent by the bot after a valid /done command."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    # Planning some stuff
    planner_tester.send_message(user, "/new Fancy diner")
    planner_tester.send_message(user, "1 Monday evening")
    planner_tester.send_message(user, "2 Tuesday evening")
    planner_tester.send_message(user, "3 Thursday evening")
    planner_tester.send_message(user, "4 Saturday evening")

    # We reset call count to test only next call
    planner = planner_tester.get_planner(user)
    planner.sender.sendMessage.reset_mock()

    # And we are done with this planning
    planner_tester.send_message(user, "/done")

    # Test answer
    assert planner.sender.sendMessage.call_count == 2
    planner.sender.sendMessage.assert_has_calls(
        [
            call('*Fancy diner*\n\n'
                 '1 Monday evening - 👥 0\n'
                 '2 Tuesday evening - 👥 0\n'
                 '3 Thursday evening - 👥 0\n'
                 '4 Saturday evening - 👥 0\n\n'
                 '👥 0 people participated so far. _Planning Opened_.',
                 parse_mode='Markdown'),
            call('👍 Planning created. You can now publish it to a group or '
                 'send it to your friends in a private message. To do this, '
                 'tap the button below or start your message in any other '
                 'chat with @gandalf_planner_bot and select one of your polls '
                 'to send.',
                 reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text='Publish planning',
                            switch_inline_query='planning_1'
                        )]]
                    )
                 )
        ])


def test_plannings_command_without_planning(init_planner_tester, users):
    """Test what happens when /new command is used without a title."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    planner_tester.send_message(user, "/plannings")

    # Test answer
    planner = planner_tester.get_planner(user)
    assert planner.sender.sendMessage.call_count == 1
    planner.sender.sendMessage.assert_called_once_with(
        'You have currently 0 plannings:\n\n',
        parse_mode='Markdown')


def test_plannings_command_with_some_planning(init_planner_tester, users):
    """Test what happens when /new command is used without a title."""
    db_test, cursor, planner_tester = init_planner_tester
    joey, chandler = users

    # First Joey is planning some stuff
    planner_tester.send_message(joey, "/new Fancy diner")
    planner_tester.send_message(joey, "1 Monday evening")
    planner_tester.send_message(joey, "/done")
    planner_tester.send_message(joey, "/new Crappy lunch")
    # Then Chandler too
    planner_tester.send_message(chandler, "/new Lousy breakfast")

    # We reset call count to test only next call
    planner_joey = planner_tester.get_planner(joey)
    planner_joey.sender.sendMessage.reset_mock()

    # What is Joey viewing ? ###############
    planner_tester.send_message(joey, "/plannings")

    # Test answer
    assert planner_joey.sender.sendMessage.call_count == 1
    planner_joey.sender.sendMessage.assert_called_once_with(
        'You have currently 2 plannings:\n\n'
        '*1*. *Fancy diner* - _Opened_\n\n'
        '*2*. *Crappy lunch* - _Under construction_',
        parse_mode='Markdown')

    # We reset call count to test only this call
    planner_chandler = planner_tester.get_planner(chandler)
    planner_chandler.sender.sendMessage.reset_mock()

    # What is Chandler viewing ? ###########
    planner_tester.send_message(chandler, "/plannings")

    # Test answer
    assert planner_chandler.sender.sendMessage.call_count == 1
    planner_chandler.sender.sendMessage.assert_called_once_with(
        'You have currently 1 plannings:\n\n'
        '*1*. *Lousy breakfast* - _Under construction_',
        parse_mode='Markdown')


def test_can_create_a_planning(init_planner_tester, users):
    """Simplest planning creation scenario."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    # The scenario
    planner_tester.send_message(user, "/new Fancy diner")
    planner_tester.send_message(user, "1 Monday evening")
    planner_tester.send_message(user, "2 Tuesday evening")
    planner_tester.send_message(user, "3 Thursday evening")
    planner_tester.send_message(user, "4 Saturday evening")
    planner_tester.send_message(user, "/done")

    # Test answers
    # (one response for each message sent but the response to /done is made of
    # two answers)
    assert planner_tester.get_planner(user).sender.sendMessage.call_count == 7

    # Test the database content

    # Plannings table
    cursor.execute("SELECT * FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 1, "Only one planning should be created."
    _, user_id, title, status = rows[0]
    assert user['id'] == user_id,\
        "User id of the sender should be set correctly."
    assert "Fancy diner" == title,\
        "Title should be set correctly."
    assert Planning.Status.OPENED == status,\
        "Status should be set correctly."

    # Options table
    cursor.execute("SELECT txt FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 4, "4 options should be created."
    assert ("1 Monday evening",) == rows[0],\
        "Option text should be set correctly."
    assert ("2 Tuesday evening",) == rows[1],\
        "Option text should be set correctly."
    assert ("3 Thursday evening",) == rows[2],\
        "Option text should be set correctly."
    assert ("4 Saturday evening",) == rows[3],\
        "Option text should be set correctly."


def test_can_cancel_a_planning(init_planner_tester, users):
    """Scenario where we start creating a planning but then cancel it."""
    db_test, cursor, planner_tester = init_planner_tester
    user, _ = users

    # The scenario
    planner_tester.send_message(user, "/new Fancy diner")
    planner_tester.send_message(user, "1 Monday evening")
    planner_tester.send_message(user, "2 Tuesday evening")
    planner_tester.send_message(user, "3 Thursday evening")
    planner_tester.send_message(user, "4 Saturday evening")
    planner_tester.send_message(user, "/cancel")

    # Test answers
    assert planner_tester.get_planner(user).sender.sendMessage.call_count == 6

    # Test the database content

    # Plannings table
    cursor.execute("SELECT * FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No planning should have been created."

    # Options table
    cursor.execute("SELECT * FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."
