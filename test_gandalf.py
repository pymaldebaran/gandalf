# -*- coding: utf-8 -*-
"""Test file for the gandalf project command line parser."""

# Used to inspect databse content
import sqlite3

# USed to autoclose database cursors and connections
from contextlib import closing

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
    with closing(sqlite3.connect(db_test)) as conn:
        with closing(conn.cursor()) as cursor:
            # Table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            tables = [e for (e,) in tables]  # just unpacking tuples
            assert len(tables) == 4
            assert "plannings" in tables
            assert "options" in tables
            assert "voters" in tables
            assert "votes" in tables
