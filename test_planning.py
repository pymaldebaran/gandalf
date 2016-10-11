# -*- coding: utf-8 -*-
"""Test file for planning classes of the gandalf project."""

# For test utilities
import pytest
from unittest.mock import MagicMock, call

# For database access snce we need data persistence
import sqlite3

# USed to autoclose database cursors and connections
from contextlib import closing

# Used to easily analyse columns descriptions
from collections import deque

# Used to create fake users for tests
from telepot.namedtuple import User

# Planning module elements to test
from planning import Planning, Option, Voter
from planning import LogicError


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


def test_can_not_modify_planning_options():
    """Ensure that it's not possible to modify the planning's options."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # First populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)

        # Create a planning with some options
        pl = Planning(
            pl_id=None,
            user_id=123,
            title="Crappy breakfast",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl.save_to_db()
        pl.add_option("Saturday 6AM")
        pl.add_option("Saturday 7AM")
        pl.add_option("Sunday 8AM")

        # Test a modification of the options
        with pytest.raises(TypeError) as excinfo:
            # trying to set the first option
            pl.options[0] = Option(None, pl.pl_id, "never", 0, conn)
        assert "object does not support item assignment" in str(excinfo.value)


# TODO use FakeUSer
def test_can_not_modify_planning_voters():
    """Ensure that it's not possible to modify the planning's voters."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # First populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)
        Voter.create_tables_in_db(conn)

        # Create a planning with some options
        pl = Planning(
            pl_id=None,
            user_id=123,
            title="Crappy breakfast",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl.save_to_db()
        pl.add_option("Saturday 6AM")
        pl.add_option("Saturday 7AM")
        pl.add_option("Sunday 8AM")
        pl.open()

        # Let's vote !
        pl.options[0].add_vote_to_db(User(id=123456, first_name="Monica"))
        pl.options[0].add_vote_to_db(User(id=456789, first_name="Rachel"))
        pl.options[2].add_vote_to_db(User(id=987654, first_name="Phoebe"))

        # Test a modification of the voters
        with pytest.raises(TypeError) as excinfo:
            # trying to set the first option
            pl.voters[2] = Voter(111111, "Ursula", "Bouffay", conn)
        assert "object does not support item assignment" in str(excinfo.value)


# TODO use FakeUSer
def test_planning_open_allow_votes():
    """Ensure we can not vote before planning opening but can after."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # First populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)
        Voter.create_tables_in_db(conn)

        # Create a first planning with some options
        pl = Planning(
            pl_id=None,
            user_id=123,
            title="Who wants to prevent Monica's wedding?",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl.save_to_db()
        only_option = pl.add_option("Stop this wedding!")

        # Try to vote before openning
        with pytest.raises(LogicError) as excinfo:
            only_option.add_vote_to_db(User(id=666666, first_name="Janice"))
        assert "Planning not opened: impossible to vote" in str(excinfo.value)

        pl.open()

        # Try to vote after opening
        only_option.add_vote_to_db(User(id=999999, first_name="Richard"))


# TODO use FakeUSer
def test_planning_close_forbid_votes():
    """Ensure we can not vote after planning closing."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # First populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)
        Voter.create_tables_in_db(conn)

        # Create a first planning with some options
        pl = Planning(
            pl_id=None,
            user_id=123,
            title="Which gorgeous girl have you met today?",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl.save_to_db()
        only_option = pl.add_option("Kathy, you know, the actress")
        pl.open()

        # Try to vote before closing
        only_option.add_vote_to_db(User(id=135790, first_name="Joey"))

        pl.close()

        # Try to vote after closing
        with pytest.raises(LogicError) as excinfo:
            only_option.add_vote_to_db(User(id=246800, first_name="Chandler"))
        assert "Planning not opened: impossible to vote." in str(excinfo.value)


# TODO use FakeUSer
def test_planning_add_option_to_db_returns_option():
    """Test if add_option_to_db() method returns the correct option."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # First populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)
        Voter.create_tables_in_db(conn)

        # Create a first planning with some options
        pl = Planning(
            pl_id=None,
            user_id=123,
            title="Do you prefer jam or women?",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl.save_to_db()
        jam = pl.add_option("Jam")
        women = pl.add_option("Women")

        # Tests the users
        assert jam is not None
        assert women is not None

        assert jam.is_in_db()
        assert women.is_in_db()

        assert len(pl.options) == 2
        assert jam in pl.options
        assert women in pl.options


# TODO use FakeUSer
def test_planning_add_vote_to_db_returns_voter():
    """Test if add_vote_to_db() method returns the correct voter."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # First populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)
        Voter.create_tables_in_db(conn)

        # Create a first planning with some options
        pl = Planning(
            pl_id=None,
            user_id=123,
            title="Who wants the rooster out?",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl.save_to_db()
        only_option = pl.add_option("I want!")
        pl.open()
        # And now we vote
        monica = only_option.add_vote_to_db(
            User(id=123456, first_name="Monica"))
        rachel = only_option.add_vote_to_db(
            User(id=456789, first_name="Rachel"))

        # Tests the users
        assert monica is not None
        assert rachel is not None

        assert monica.is_in_db()
        assert rachel.is_in_db()

        assert len(pl.voters) == 2
        assert monica in pl.voters
        assert rachel in pl.voters


# TODO add test test_planning_is_vote_in_db_works
# TODO use FakeUSer
@pytest.mark.skip
def test_planning_remove_from_db_erase_all_related_rows():
    """Ensure that all the options, voters and votes are removed from db."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # First populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)
        Voter.create_tables_in_db(conn)

        # Create a first planning with some options
        pl_girl = Planning(
            pl_id=None,
            user_id=123,
            title="Funky lunch",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl_girl.save_to_db()
        pl_girl.add_option("Monday noon")
        pl_girl.add_option("Monday 1PM")
        pl_girl.add_option("Tuesday 1AM")
        pl_girl.open()
        monica = pl_girl.options[0].add_vote_to_db(
            User(id=123456, first_name="Monica"))
        rachel = pl_girl.options[0].add_vote_to_db(
            User(id=456789, first_name="Rachel"))
        phoebe = pl_girl.options[2].add_vote_to_db(
            User(id=987654, first_name="Phoebe"))
        ben = pl_girl.options[1].add_vote_to_db(
            User(id=111111, first_name="Ben"))
        # Register the options for later tests
        opt_girl = pl_girl.options
        assert opt_girl  # To be sure we have options

        # Create a second planning...
        pl_dude = Planning(
            pl_id=None,
            user_id=123,
            title="Crappy lunch",
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=conn)
        pl_dude.save_to_db()
        pl_dude.add_option("Monday 1PM")
        pl_dude.add_option("Monday 2PM")
        pl_dude.add_option("Tuesday 2PM")
        pl_dude.open()
        joey = pl_dude.options[0].add_vote_to_db(
            User(id=135790, first_name="Joey"))
        chandler = pl_dude.options[0].add_vote_to_db(
            User(id=246800, first_name="Chandler"))
        ross = pl_dude.options[2].add_vote_to_db(
            User(id=214365, first_name="Ross"))
        _ = pl_girl.options[1].add_vote_to_db(
            User(id=111111, first_name="Ben"))  # We already have voter Ben
        # Register the options for later tests
        opt_dude = pl_dude.options
        assert opt_girl  # To be sure we have options

        # And we delete a planning
        pl_dude.remove_from_db()

        # Tests the effects on the database
        with closing(conn.cursor()) as cursor:
            # Did we remove the good planning ?
            assert pl_girl.is_in_db()
            assert not pl_dude.is_in_db()

            # Did we remove the good options ?
            assert opt_girl[0].is_in_db()
            assert opt_girl[1].is_in_db()
            assert opt_girl[2].is_in_db()
            assert not opt_dude[0].is_in_db()
            assert not opt_dude[1].is_in_db()
            assert not opt_dude[2].is_in_db()

            # Did we remove the good voters ?
            assert monica.is_in_db()
            assert rachel.is_in_db()
            assert phoebe.is_in_db()
            assert ben.is_in_db()
            assert not joey.is_in_db()
            assert not chandler.is_in_db()
            assert not ross.is_in_db()

            # TODO use is_vote_in_db() method instead of direct db requests
            # Did we remove the good votes from database ?
            cursor.execute("SELECT * FROM votes WHERE opt_id IN (?,?,?)",
                           (opt_girl[0].opt_id,
                            opt_girl[1].opt_id,
                            opt_girl[2].opt_id))
            girl_opt_votes_from_opt = cursor.fetchall()
            assert len(girl_opt_votes_from_opt) == 4

            cursor.execute("SELECT * FROM votes WHERE v_id IN (?,?,?,?)",
                           (monica.v_id,
                            rachel.v_id,
                            phoebe.v_id,
                            ben.v_id))
            girl_opt_votes_from_voter = cursor.fetchall()
            assert len(girl_opt_votes_from_voter) == 4

            cursor.execute("SELECT * FROM votes WHERE opt_id IN (?,?,?)",
                           (opt_dude[0].opt_id,
                            opt_dude[1].opt_id,
                            opt_dude[2].opt_id))
            dude_opt_votes_from_opt = cursor.fetchall()
            assert len(dude_opt_votes_from_opt) == 0

            cursor.execute("SELECT * FROM votes WHERE v_id IN (?,?,?)",
                           (joey.v_id,
                            chandler.v_id,
                            ross.v_id))
            girl_opt_votes_from_voter = cursor.fetchall()
            assert len(girl_opt_votes_from_voter) == 0


def test_option_equality():
    """Test condition of equality between Option instancies."""
    # Option are equal if they have all their value equal
    opt1A = Option(opt_id=123, pl_id=111, txt="aaa", num=1, db_conn=MagicMock)
    opt1B = Option(opt_id=123, pl_id=111, txt="aaa", num=1, db_conn=MagicMock)

    assert opt1A == opt1B

    # Options are different in all other case
    assert opt1A != Option(789, 111, "aaa", 1, MagicMock)
    assert opt1A != Option(123, 222, "aaa", 1, MagicMock)
    assert opt1A != Option(123, 111, "zzz", 1, MagicMock)
    assert opt1A != Option(123, 111, "aaa", 2, MagicMock)


def test_option_belong_to_sequence():
    """Test condition for an Option instance to belong to sequence."""
    # Some options
    opt1 = Option(123, 111, "option1", 1, MagicMock)
    opt2 = Option(456, 111, "option2", 1, MagicMock)
    opt3 = Option(789, 111, "option3", 1, MagicMock)

    # Test belonging
    assert opt1 not in []
    assert opt1 not in [opt2, opt3]
    assert opt1 in [opt1]
    assert opt1 in [opt1, opt2, opt3]
    assert opt1 in [opt3, opt2, opt1]  # order doesn't matter


def test_voter_equality():
    """Test condition of equality between Voter instancies."""
    # Option are equal if they have all their value equal
    v1A = Voter(v_id=123, first_name="aaa", last_name="bbb", db_conn=MagicMock)
    v1B = Voter(v_id=123, first_name="aaa", last_name="bbb", db_conn=MagicMock)

    assert v1A == v1B

    # Options are different in all other case
    assert v1A != Voter(789, "aaa", "bbb", MagicMock)
    assert v1A != Voter(123, "ccc", "bbb", MagicMock)
    assert v1A != Voter(123, "aaa", "ccc", MagicMock)


def test_voter_belong_to_sequence():
    """Test condition for an Voter instance to belong to sequence."""
    # Some options
    v1 = Voter(123, "aaa", "aaa", MagicMock)
    v2 = Voter(456, "bbb", "bbb", MagicMock)
    v3 = Voter(789, "ccc", "ccc", MagicMock)

    # Test belonging
    assert v1 not in []
    assert v1 not in [v2, v2]
    assert v1 in [v1]
    assert v1 in [v1, v2, v3]
    assert v1 in [v3, v2, v1]  # order doesn't matter
