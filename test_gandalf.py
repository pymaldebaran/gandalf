#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test file for the gandalf poject."""

# Gandalf module to test
from gandalf import is_command, createdb, Planner, Planning

# Unit test utils
import pytest
from unittest.mock import MagicMock

# Used to inspect databse content
import sqlite3

def test_is_command():
    """Test all interesting cases for the is_command() function."""
    # Positive cases
    assert is_command("/foo", "/foo"), "Commands are matched when alone."
    assert is_command("/bar", "/bar"), "Commands other than /foo are matched."
    assert is_command(" /foo", "/foo"), "Commands preceded by spaces are matched."
    assert is_command("/foo blah", "/foo"), "Commands followed by one word are matched."
    assert is_command("/foo blah blah", "/foo"), "Commands followed by any text are matched."
    assert is_command("/foo /blah", "/foo"), "Commands followed by other commands are matched."

    # Negative cases
    assert not is_command("blah", "/foo"), "Random text does not match command."
    assert not is_command("/bar", "/foo"), "Random command does not match another command."
    assert not is_command("", "/foo"), "Empty text does not match command."
    assert not is_command("a/foo", "/foo"), "Commands can not be preceded by a char."
    assert not is_command("blah /foo", "/foo"), "Commands can not be preceded by text."
    assert not is_command("/fooooooo", "/foo"), "Commands with extra char does not match."


class PlannerTester:
    """
    Helper class that makes the tests of Planner scenario easier.

    Once initialized this object allows you to just call send_message() method
    many times to simulate a discussion with the bot.
    """

    def __init__(self, planner, seed, db):
        """Create a ready-to-use PlannerTester instance."""
        self.planner = planner
        self.seed = seed
        self.db = db
        self.openned = False


    def send_message(self, txt):
        """Encapsulate sending of message for easy test writing."""
        if not self.openned:
            self.planner.open(
                initial_msg=fake_msg(txt),
                seed=self.seed,
                db=self.db)
            self.openned = True

        self.planner.on_chat_message(fake_msg(txt))


def fake_msg(txt):
    """
    Helper function to create fake messages for test purpose.

    Arguments:
        txt -- text content of the wannabe message.

    Returns:
        a dict object that looks enough like an real telegram message.
    """
    return {
        'chat':{
            'id':1,
            'type':'text'
        },
        'from':{
            'first_name':'Joey'
        },
        'text':txt
    }


@pytest.fixture()
def init_planner_tester(tmpdir):
    """Setup and Teardown for all tests about the Planner class."""
    # Create a database for the test
    db_test = str(tmpdir.join('test'))
    createdb(db=db_test)
    conn = sqlite3.connect(db_test)
    cursor = conn.cursor()

    # Create a planner object to receive messages
    seed = MagicMock(), MagicMock(), MagicMock()
    event_space = MagicMock()
    timeout = 1
    planner = Planner(
        seed_tuple=seed,
        event_space=event_space,
        timeout=timeout)

    # We need to check if the bot answers...
    planner.sender.sendMessage = MagicMock()

    # Create easy to use planner tester
    planner_tester = PlannerTester(planner, seed, db_test)

    yield db_test, cursor, planner_tester

    # Close the database and cursor
    cursor.close()
    conn.close()


def test_say_anything(init_planner_tester):
    """Test what happens when we send whatever message to the bot."""
    db_test, cursor, planner_tester = init_planner_tester

    planner_tester.send_message("Hello handsome ;)")

    # Test answer
    planner_tester.planner.sender.sendMessage.call_count == 1
    planner_tester.planner.sender.sendMessage.assert_called_with(
        'Sorry I did not understand... try /help to see how you should talk '
        'to me.')

    # Test the database content

    # Plannings table
    cursor.execute("SELECT title, status FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No planning should have been created."

    # Options table
    cursor.execute("SELECT txt FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."


def test_send_new_command_starts_creation_of_a_planning(init_planner_tester):
    """Test what happens when using the /new command."""
    db_test, cursor, planner_tester = init_planner_tester

    planner_tester.send_message("/new Fancy diner")

    # Test answer
    planner_tester.planner.sender.sendMessage.call_count == 1
    planner_tester.planner.sender.sendMessage.assert_called_with(
        'You want to create a planning named *Fancy diner*. Send me a description'
        'or a question to ask to the participant. '
        '/cancel to abort creation.',
        parse_mode='Markdown')

    # Test the database content

    # Plannings table
    cursor.execute("SELECT title, status FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 1, "Only one planning should be created."
    assert ("Fancy diner", Planning.Status.UNDER_CONSTRUCTION) == rows[0],\
        "Title and status should be set correctly."

    # Options table
    cursor.execute("SELECT txt FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."


def test_send_new_command_without_title(init_planner_tester):
    """Test what happens when /new command is used without a title."""
    db_test, cursor, planner_tester = init_planner_tester

    planner_tester.send_message("/new")

    # Test answer
    planner_tester.planner.sender.sendMessage.call_count == 1
    planner_tester.planner.sender.sendMessage.assert_called_with(
        'Sorry to create a planning you have give a title after the /new '
        'command. Like this :\n\n'
        '/new _My fancy planning title_',
        parse_mode='Markdown')

    # Test the database content

    # Plannings table
    cursor.execute("SELECT title, status FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No planning should be created."
    # Options table
    cursor.execute("SELECT txt FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."


def test_send_plannings_command_without_planning(init_planner_tester):
    """Test what happens when /new command is used without a title."""
    db_test, cursor, planner_tester = init_planner_tester

    planner_tester.send_message("/plannings")

    # Test answer
    planner_tester.planner.sender.sendMessage.call_count == 1
    planner_tester.planner.sender.sendMessage.assert_called_with(
        'You have currently 0 plannings:\n\n',
        parse_mode='Markdown')


def test_send_plannings_command_without_planning(init_planner_tester):
    """Test what happens when /new command is used without a title."""
    db_test, cursor, planner_tester = init_planner_tester

    planner_tester.send_message("/new Fancy diner")
    planner_tester.send_message("1 Monday evening")
    planner_tester.send_message("/done")
    planner_tester.send_message("/new Crappy lunch")
    # We reset call count to test only this call
    planner_tester.planner.sender.sendMessage.reset_mock()
    planner_tester.send_message("/plannings")

    # Test answer
    planner_tester.planner.sender.sendMessage.call_count == 1
    planner_tester.planner.sender.sendMessage.assert_called_with(
        'You have currently 2 plannings:\n\n'
        '*1*. *Fancy diner* - _Opened_\n\n'
        '*2*. *Crappy lunch* - _Under construction_',
        parse_mode='Markdown')


def test_can_create_a_planning(init_planner_tester):
    """Simplest planning creation scenario."""
    db_test, cursor, planner_tester = init_planner_tester

    # The scenario
    planner_tester.send_message("/new Fancy diner")
    planner_tester.send_message("1 Monday evening")
    planner_tester.send_message("2 Tuesday evening")
    planner_tester.send_message("3 Thursday evening")
    planner_tester.send_message("4 Saturday evening")
    planner_tester.send_message("/done")

    # Test answers
    planner_tester.planner.sender.sendMessage.call_count == 6

    # Test the database content

    # Plannings table
    cursor.execute("SELECT title, status FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 1, "Only one planning should be created."
    assert ("Fancy diner", Planning.Status.OPENED) == rows[0],\
        "Title and status should be set correctly."

    # Options table
    cursor.execute("SELECT txt FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 4, "4 options should be created."
    assert ("1 Monday evening",) == rows[0], "Text should be set correctly."
    assert ("2 Tuesday evening",) == rows[1], "Text should be set correctly."
    assert ("3 Thursday evening",) == rows[2], "Text should be set correctly."
    assert ("4 Saturday evening",) == rows[3], "Text should be set correctly."


def test_can_cancel_a_planning(init_planner_tester):
    """Scenario where we start creating a planning but then cancel it."""
    db_test, cursor, planner_tester = init_planner_tester

    # The scenario
    planner_tester.send_message("/new Fancy diner")
    planner_tester.send_message("1 Monday evening")
    planner_tester.send_message("2 Tuesday evening")
    planner_tester.send_message("3 Thursday evening")
    planner_tester.send_message("4 Saturday evening")
    planner_tester.send_message("/cancel")

    # Test answers
    planner_tester.planner.sender.sendMessage.call_count == 6

    # Test the database content

    # Plannings table
    cursor.execute("SELECT title, status FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No planning should have been created."

    # Options table
    cursor.execute("SELECT txt FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."

