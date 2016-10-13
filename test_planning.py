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
from planning import LogicError, MultipleVoteError
from planning import is_vote_in_db


# Tests helpers ###############################################################
def FakeUser(first_name):
    """Helper to easily build Telegram User."""
    return User(
        id=hash(first_name),  # KISS way to have a unique id
        first_name=first_name)


@pytest.fixture()
def init_planning_db():
    """Setup and Teardown for all tests needing a planning & co tables."""
    with closing(sqlite3.connect(":memory:")) as conn:
        # Populate the database
        Planning.create_tables_in_db(conn)
        Option.create_tables_in_db(conn)
        Voter.create_tables_in_db(conn)

        yield conn


# Database management tests ###################################################
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


# Planning class tests ########################################################
def test_can_not_modify_planning_options(init_planning_db):
    """Ensure that it's not possible to modify the planning's options."""
    conn = init_planning_db

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


def test_can_not_modify_planning_voters(init_planning_db):
    """Ensure that it's not possible to modify the planning's voters."""
    conn = init_planning_db

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
    pl.options[0].add_vote_to_db(FakeUser("Monica"))
    pl.options[0].add_vote_to_db(FakeUser("Rachel"))
    pl.options[2].add_vote_to_db(FakeUser("Phoebe"))

    # Test a modification of the voters
    with pytest.raises(TypeError) as excinfo:
        # trying to set the first option
        pl.voters[2] = Voter(111111, "Ursula", "Bouffay", conn)
    assert "object does not support item assignment" in str(excinfo.value)


def test_planning_open_allow_votes(init_planning_db):
    """Ensure we can not vote before planning opening but can after."""
    conn = init_planning_db

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
        only_option.add_vote_to_db(FakeUser("Janice"))
    assert "Planning not opened: impossible to vote" in str(excinfo.value)

    pl.open()

    # Try to vote after opening
    only_option.add_vote_to_db(FakeUser("Richard"))


def test_planning_close_forbid_votes(init_planning_db):
    """Ensure we can not vote after planning closing."""
    conn = init_planning_db

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
    only_option.add_vote_to_db(FakeUser("Joey"))

    pl.close()

    # Try to vote after closing
    with pytest.raises(LogicError) as excinfo:
        only_option.add_vote_to_db(User(id=246800, first_name="Chandler"))
    assert "Planning not opened: impossible to vote." in str(excinfo.value)


def test_planning_add_option_to_db_returns_option(init_planning_db):
    """Test if add_option_to_db() method returns the correct option."""
    conn = init_planning_db

    # Create a planning with some options
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


def test_planning_remove_from_db_erase_all_related_rows(init_planning_db):
    """Ensure that all the options, voters and votes are removed from db."""
    conn = init_planning_db

    # Create a first planning with some options
    pl_girl = Planning(
        pl_id=None,
        user_id=123,
        title="Funky lunch",
        status=Planning.Status.UNDER_CONSTRUCTION,
        db_conn=conn)
    pl_girl.save_to_db()
    monday = pl_girl.add_option("Monday")
    tuesday = pl_girl.add_option("Tuesday")
    wednesday = pl_girl.add_option("Wednesday")
    pl_girl.open()
    # Let's vote
    monica = monday.add_vote_to_db(FakeUser("Monica"))
    rachel = monday.add_vote_to_db(FakeUser("Rachel"))
    phoebe = wednesday.add_vote_to_db(FakeUser("Phoebe"))
    ben = tuesday.add_vote_to_db(FakeUser("Ben"))

    # Create a second planning...
    pl_dude = Planning(
        pl_id=None,
        user_id=123,
        title="Crappy lunch",
        status=Planning.Status.UNDER_CONSTRUCTION,
        db_conn=conn)
    pl_dude.save_to_db()
    friday = pl_dude.add_option("Friday")
    saturday = pl_dude.add_option("Saturday")
    sunday = pl_dude.add_option("Sunday")
    pl_dude.open()
    # Let's vote
    joey = friday.add_vote_to_db(FakeUser("Joey"))
    chandler = friday.add_vote_to_db(FakeUser("Chandler"))
    ross = sunday.add_vote_to_db(FakeUser("Ross"))
    _ = saturday.add_vote_to_db(FakeUser("Ben"))  # Ben already voted

    # And we delete a planning
    pl_dude.remove_from_db()

    # Tests the effects on the database
    with closing(conn.cursor()) as cursor:
        # Did we remove the good planning ?
        assert pl_girl.is_in_db()
        assert not pl_dude.is_in_db()

        # Did we remove the good options ?
        assert monday.is_in_db()
        assert tuesday.is_in_db()
        assert wednesday.is_in_db()
        assert not friday.is_in_db()
        assert not saturday.is_in_db()
        assert not sunday.is_in_db()

        # Did we remove the good voters ?
        assert monica.is_in_db()
        assert rachel.is_in_db()
        assert phoebe.is_in_db()
        assert ben.is_in_db()
        assert not joey.is_in_db()
        assert not chandler.is_in_db()
        assert not ross.is_in_db()

        # Did we remove the good votes from database ?
        assert is_vote_in_db(monica, monday, conn)
        assert is_vote_in_db(rachel, monday, conn)
        assert is_vote_in_db(phoebe, wednesday, conn)
        assert is_vote_in_db(ben, tuesday, conn)

        assert not is_vote_in_db(joey, friday, conn)
        assert not is_vote_in_db(chandler, friday, conn)
        assert not is_vote_in_db(ross, sunday, conn)
        assert not is_vote_in_db(ben, saturday, conn)


# Option class tests ##########################################################
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


def test_option_add_vote_to_db_returns_voter(init_planning_db):
    """Test if add_vote_to_db() method returns the correct voter."""
    conn = init_planning_db

    # Create a planning with some options
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
    monica = only_option.add_vote_to_db(FakeUser("Monica"))
    rachel = only_option.add_vote_to_db(FakeUser("Rachel"))

    # Tests the users
    assert monica is not None
    assert rachel is not None

    assert monica.is_in_db()
    assert rachel.is_in_db()

    assert len(pl.voters) == 2
    assert monica in pl.voters
    assert rachel in pl.voters


def test_add_and_remove_to_db_works(init_planning_db):
    """Ensure that Planning.is_vote_in_db() works correctly."""
    conn = init_planning_db

    # Create a first planning with some options
    pl = Planning(None, 123, "Who wants the rooster out?",
                  Planning.Status.UNDER_CONSTRUCTION,
                  db_conn=conn)
    pl.save_to_db()
    want = pl.add_option("I want!")
    pl.open()
    # And now we vote
    monica = want.add_vote_to_db(FakeUser("Monica"))
    rachel = want.add_vote_to_db(FakeUser("Rachel"))

    # Create a second planning with some options
    pl = Planning(
        pl_id=None,
        user_id=123,
        title="Do you prefer jam or women?",
        status=Planning.Status.UNDER_CONSTRUCTION,
        db_conn=conn)
    pl.save_to_db()
    jam = pl.add_option("Jam")
    women = pl.add_option("Women")
    pl.open()
    # And now we vote
    joey = jam.add_vote_to_db(FakeUser("Joey"))
    joey = women.add_vote_to_db(FakeUser("Joey"))

    # Test the presence of votes
    assert is_vote_in_db(monica, want, conn)
    assert is_vote_in_db(rachel, want, conn)
    assert is_vote_in_db(joey, jam, conn)
    assert is_vote_in_db(joey, women, conn)
    assert not is_vote_in_db(joey, want, conn)
    assert not is_vote_in_db(monica, jam, conn)
    assert not is_vote_in_db(rachel, jam, conn)

    # Lets's change our mind !
    jam.remove_vote_to_db(joey)
    assert not is_vote_in_db(joey, jam, conn)
    assert is_vote_in_db(joey, women, conn)


def test_can_not_vote_twice_for_the_same_option(init_planning_db):
    """Ensure that a voter can not vote twice for the same option."""
    conn = init_planning_db

    # Create a first planning with some options
    pl = Planning(None, 123, "What is the most anoying character ever?",
                  Planning.Status.UNDER_CONSTRUCTION,
                  db_conn=conn)
    pl.save_to_db()
    awful_laugh = pl.add_option("Janice")
    pl.open()

    # And now we vote
    joey = awful_laugh.add_vote_to_db(FakeUser("Joey"))

    # And try to vote again
    with pytest.raises(MultipleVoteError):
        _ = awful_laugh.add_vote_to_db(joey)


# Voter class tests ###########################################################
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


def test_voters_are_equal_as_long_as_they_have_the_same_id():
    """Test condition of equality between Voter instancies."""
    # Unique id for Chandler
    CHANDLER_ID = 123456789

    # Original
    chandler_bing = Voter(CHANDLER_ID, "Chandler", "Bing", MagicMock)
    # Dark secret
    muriel_bing = Voter(CHANDLER_ID, "Muriel", "Bing", MagicMock)
    # After wedding
    chandler_geller = Voter(CHANDLER_ID, "Chandler", "Geller", MagicMock)
    # When he decided to change name
    mark_johnson = Voter(CHANDLER_ID, "Mark", "Johnson", MagicMock)

    assert chandler_bing == muriel_bing
    assert chandler_bing == chandler_geller
    assert chandler_bing == mark_johnson

    # Unique id for monica and the fake
    MONICA_ID = 111111111
    NOT_MONICA_ID = 666666666
    monica_geller = Voter(MONICA_ID, "Monica", "Geller", MagicMock)
    fake_monica = Voter(NOT_MONICA_ID, "Monica", "Geller", MagicMock)

    assert monica_geller != fake_monica
