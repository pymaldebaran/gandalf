#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test file for the gandalf poject."""

# Gandalf module to test
from gandalf import is_command

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
