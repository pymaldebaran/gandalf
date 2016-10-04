# -*- coding: utf-8 -*-
"""Test file for the gandalf project command line parser."""

# Used to inspect databse content
import sqlite3

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
