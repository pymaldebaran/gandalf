# -*- coding: utf-8 -*-
"""Test file for planning classes of the gandalf project."""

# For database access snce we need data persistence
import sqlite3

# USed to autoclose database cursors and connections
from contextlib import closing

# Used to easily analyse columns descriptions
from collections import deque

# Planning module elements to test
from planning import Planning, Option, Voter


def test_planning_create_tables_in_db():
    """Test the effect of Planning.create_tables_in_db() on the database."""
    with closing(sqlite3.connect(':memory:')) as conn:

        # Let's create the tables
        Planning.create_tables_in_db(conn)

        # Let's test the database
        with closing(conn.cursor()) as cursor:
            # Table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            assert len(tables) == 1

            # Table columns
            # We use PRAGMA table_info('table_name') to get the column
            # descriptions. The returned table has this structure (illustrated
            # by an exemple):
            # cid         name        type        notnull     dflt_value  pk
            # ----------  ----------  ----------  ----------  ----------  -----
            # 0           id          integer     99                      1
            # 1           name                    0                       0
            cursor.execute("PRAGMA table_info('plannings')")
            cols = deque(cursor.fetchall())
            assert len(cols) == 4
            assert ('pl_id', 'INTEGER') == cols.popleft()[1:3]
            assert ('user_id', 'INTEGER') == cols.popleft()[1:3]
            assert ('title', 'TEXT') == cols.popleft()[1:3]
            assert ('status', 'TEXT') == cols.popleft()[1:3]


def test_option_create_tables_in_db():
    """Test the effect of Option.create_tables_in_db() on the database."""
    with closing(sqlite3.connect(':memory:')) as conn:

        # Let's create the tables
        Option.create_tables_in_db(conn)

        # Let's test the database
        with closing(conn.cursor()) as cursor:
            # Table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            assert len(tables) == 1

            # Table columns
            # We use PRAGMA table_info('table_name') to get the column
            # descriptions. The returned table has this structure (illustrated
            # by an exemple):
            # cid         name        type        notnull     dflt_value  pk
            # ----------  ----------  ----------  ----------  ----------  -----
            # 0           id          integer     99                      1
            # 1           name                    0                       0
            cursor.execute("PRAGMA table_info('options')")
            cols = deque(cursor.fetchall())
            assert len(cols) == 4
            assert ('opt_id', 'INTEGER') == cols.popleft()[1:3]
            assert ('pl_id', 'INTEGER') == cols.popleft()[1:3]
            assert ('txt', 'TEXT') == cols.popleft()[1:3]
            assert ('num', 'INTEGER') == cols.popleft()[1:3]


def test_voter_create_tables_in_db():
    """Test the effect of Voter.create_tables_in_db() on the database."""
    with closing(sqlite3.connect(':memory:')) as conn:

        # Let's create the tables
        Voter.create_tables_in_db(conn)

        # Let's test the database
        with closing(conn.cursor()) as cursor:
            # Table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            assert len(tables) == 2

            # Table columns
            # We use PRAGMA table_info('table_name') to get the column
            # descriptions. The returned table has this structure (illustrated
            # by an exemple):
            # cid         name        type        notnull     dflt_value  pk
            # ----------  ----------  ----------  ----------  ----------  -----
            # 0           id          integer     99                      1
            # 1           name                    0                       0
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
