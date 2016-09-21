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


@pytest.yield_fixture()
def init_database(tmpdir):
    # Create a database for the test
    db_test = str(tmpdir.join('test'))
    createdb(db=db_test)
    conn = sqlite3.connect(db_test)
    cursor = conn.cursor()

    yield db_test, cursor

    # Close the database and cursor
    cursor.close()
    conn.close()


@pytest.fixture
def init_planner():
    # Create a planner object to receive messages
    seed = MagicMock(), MagicMock(), MagicMock()
    event_space = MagicMock()
    timeout = 1
    planner = Planner(
        seed_tuple=seed,
        event_space=event_space,
        timeout=timeout)

    return seed, planner


def test_can_create_a_planning(init_database, init_planner):
    """
    Test the simplest planning creation scenario.

    Here we do not test the Telegram/Telepot specific code we directly call
    the Planner.on_chat_message() method just as it would happen via the
    serve() function.
    """
    db_test, cursor = init_database
    seed, planner = init_planner

    # The scenario
    planner.open(
        initial_msg=fake_msg("/new Fancy diner"),
        seed=seed,
        db=db_test)
    planner.on_chat_message(fake_msg("/new Fancy diner"))
    planner.on_chat_message(fake_msg("1 Monday evening"))
    planner.on_chat_message(fake_msg("2 Tuesday evening"))
    planner.on_chat_message(fake_msg("3 Thursday evening"))
    planner.on_chat_message(fake_msg("4 Saturday evening"))
    planner.on_chat_message(fake_msg("/done"))

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


def test_can_cancel_a_planning(init_database, init_planner):
    """
    Test the a scenario where we start creating a planning but then cancel it.

    Here we do not test the Telegram/Telepot specific code we directly call
    the Planner.on_chat_message() method just as it would happen via the
    serve() function.
    """
    db_test, cursor = init_database
    seed, planner = init_planner

    # The scenario
    planner.open(
        initial_msg=fake_msg("/new Fancy diner"),
        seed=seed,
        db=db_test)
    planner.on_chat_message(fake_msg("/new Fancy diner"))
    planner.on_chat_message(fake_msg("1 Monday evening"))
    planner.on_chat_message(fake_msg("2 Tuesday evening"))
    planner.on_chat_message(fake_msg("3 Thursday evening"))
    planner.on_chat_message(fake_msg("4 Saturday evening"))
    planner.on_chat_message(fake_msg("/cancel"))

    # Test the database content
    conn = sqlite3.connect(db_test)
    c = conn.cursor()

    # Plannings table
    cursor.execute("SELECT title, status FROM plannings")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No planning should have been created."

    # Options table
    cursor.execute("SELECT txt FROM options ORDER BY txt")
    rows = cursor.fetchall()
    assert len(rows) == 0, "No option should have been created."

