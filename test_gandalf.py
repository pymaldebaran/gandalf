# -*- coding: utf-8 -*-
"""Test file for the gandalf project command line parser."""

# Used to inspect databse content
import sqlite3

# Used to easily analyse columns descriptions
from collections import deque

# Gandalf module to test
from gandalf import createdb


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
    assert len(tables) == 4
    assert "plannings" in tables
    assert "options" in tables
    assert "voters" in tables
    assert "votes" in tables

    # Table columns
    # We use PRAGMA table_info('table_name') to get the column descriptions
    # The returned table has this structure (illustrated by an exemple):
    # cid         name        type        notnull     dflt_value  pk
    # ----------  ----------  ----------  ----------  ----------  ----------
    # 0           id          integer     99                      1
    # 1           name                    0                       0
    cursor.execute("PRAGMA table_info('plannings')")
    plannings_columns = deque(cursor.fetchall())
    assert len(plannings_columns) == 4
    assert ('pl_id', 'INTEGER') == plannings_columns.popleft()[1:3]
    assert ('user_id', 'INTEGER') == plannings_columns.popleft()[1:3]
    assert ('title', 'TEXT') == plannings_columns.popleft()[1:3]
    assert ('status', 'TEXT') == plannings_columns.popleft()[1:3]

    cursor.execute("PRAGMA table_info('options')")
    options_columns = deque(cursor.fetchall())
    assert len(options_columns) == 4
    assert ('opt_id', 'INTEGER') == options_columns.popleft()[1:3]
    assert ('pl_id', 'INTEGER') == options_columns.popleft()[1:3]
    assert ('txt', 'TEXT') == options_columns.popleft()[1:3]
    assert ('num', 'INTEGER') == options_columns.popleft()[1:3]

    cursor.execute("PRAGMA table_info('voters')")
    voters_columns = deque(cursor.fetchall())
    assert len(voters_columns) == 3
    assert ('v_id', 'INTEGER') == voters_columns.popleft()[1:3]
    assert ('first_name', 'TEXT') == voters_columns.popleft()[1:3]
    assert ('last_name', 'TEXT') == voters_columns.popleft()[1:3]

    cursor.execute("PRAGMA table_info('votes')")
    votes_columns = deque(cursor.fetchall())
    assert len(votes_columns) == 2
    assert ('opt_id', 'INTEGER') == votes_columns.popleft()[1:3]
    assert ('v_id', 'INTEGER') == votes_columns.popleft()[1:3]
