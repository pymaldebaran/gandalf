# -*- coding: utf-8 -*-
"""
Gandalf bot planning entities.

All classes needed to encapsultale the underlying database tables needed by
the bot.
"""

# Used to represent status of a planning
from enum import Enum

# Used to represent users obtained from Telegram messages
import telepot


class Planning:
    """Represent a user created planning."""

    # Formating string for Planning str representation
    DESC_SHORT = '*{num}*. *{planning.title}* - _{planning.status}_'
    DESC_FULL = '*{title}*\n\n'\
        '{options}\n\n'\
        '👥 {nb_participants} people participated so far. '\
        '_Planning {planning_status}_.'
    # TODO use planning recap+ instead of planning recap
    DESC_FULL_PLUS = '*{title}*\n'\
        '_{description}_\n\n'\
        '{options}\n\n'\
        '👥 {nb_participants} people participated so far. '\
        '_Planning {planning_status}_.'

    # Prefix used when generating inline query id
    INLINE_QUERY_PREFIX = "planning_"

    class Status(str, Enum):
        """Represent the different possible status for a planning."""

        UNDER_CONSTRUCTION = "Under construction"
        OPENED = "Opened"
        CLOSED = "Closed"

    def __init__(self, pl_id, user_id, title, status, db_conn):
        """
        Create a new Planning.

        Arguments:
            pl_id -- id of the object in plannings table of the database.
            user_id -- id of the user that created the planning. It comes from
                       plannings table of the database.
            title -- title of the planning.
            status -- Planning.Status enum describing the current status of the
                      planning object.
            db_conn -- connexion to the database where the Planning will be
                       saved.
        """
        # Preconditions
        assert db_conn is not None

        self.pl_id = pl_id
        self.user_id = user_id
        self.title = title
        self.status = status
        self._db_conn = db_conn

    @property
    def options(self):
        """
        Return options associated to the planning.

        Returns:
            List of Option object associated to the planning extracted from the
            database sorted by num field.
        """
        return Option.load_all_from_planning_id_from_db(
            self._db_conn, self.pl_id)

    @property
    def voters(self):
        """
        Return voters that voted for at least one of the planning's option.

        Returns:
            List of Voters object associated to the planning extracted from the
            database sorted by first name.
        """
        return Voter.load_all_from_planning_id_from_db(
            self._db_conn, self.pl_id)

    def short_description(self, num):
        """
        Return a short str description of the planning.

        Useful for list view of many plannings."

        Arguments:
            num -- position of the planning in the list

        Returns:
            string describing the planning prefixed by it's provided position.
        """
        return Planning.DESC_SHORT.format(
            num=num+1,
            planning=self)

    def full_description(self):
        """
        Return a full str description of the planning including its options.

        Returns:
            string describing the planning with detailed options and
            contributors.
        """
        options_msg = '\n'.join(
            [opt.short_description() for opt in self.options])

        desc_msg = Planning.DESC_FULL.format(
            title=self.title,
            options=options_msg,
            nb_participants=len(self.voters),
            planning_status=self.status)

        return desc_msg

    def inline_query_id(self):
        """
        Return a unique str representation of the planning for query.

        This string can be used to create Telegram inline query to reference
        this peticular planning.
        """
        return '{prefix}{pl_id}'.format(
            prefix=Planning.INLINE_QUERY_PREFIX,
            pl_id=self.pl_id)

    def is_in_db(self):
        """
        Check if the Option instance is already in database.

        Returns:
            False if the planning has a self.pl_id is None or if there is no
            row in plannings table in the database with pl_id == self.pl_id.
            True else.
        """
        # No id means not yet saved
        if self.pl_id is None:
            return False

        # Search in database
        c = self._db_conn.cursor()
        c.execute(
            """SELECT * FROM plannings WHERE pl_id=?""",
            (self.pl_id))
        rows = c.fetchall()
        c.close()

        # Is it present ?
        if len(rows) > 0:
            return True
        else:
            return False

    def save_to_db(self):
        """
        Save the Planning object to the provided database.

        If the planning had no pl_id before, it is set (since only the database
        can give a valid id to the planning).

        Exceptions:
            If the planning is already in the database AssertionError is
            raised.
        """
        # Preconditions
        assert not self.is_in_db(), "planning can be saved in database only "\
            "once."

        # Save to database
        c = self._db_conn.cursor()
        c.execute(
            """INSERT INTO plannings(user_id, title, status)
                VALUES (?,?,?)""",
            (self.user_id, self.title, self.status))
        # Retreive the new id
        new_pl_id = c.lastrowid
        self._db_conn.commit()
        c.close()

        # Set the id in the instance
        self.pl_id = new_pl_id

    def update_to_db(self):
        """Update the Planning object status to the provided database."""
        # Get a connexion to the database
        c = self._db_conn.cursor()

        # Update the planning's status in the database
        c.execute("UPDATE plannings SET status=? WHERE pl_id=?",
                  (self.status, self.pl_id))

        # Check the results of the planning update consistancy
        assert c.rowcount != 0, "Tried to update planning with id {id} that "\
            "doesn't exist in database.".format(id=self.pl_id)
        assert c.rowcount == 1, "Updated more than one planning with id {id} "\
            "from the database.".format(id=self.pl_id)

        # Once the results are checked we can commit and close cursor
        self._db_conn.commit()
        c.close()

    def remove_from_db(self):
        """
        Remove the Planning object and dependancies from the database.

        Remove the Planning object and all the corresponding Option object
        from the database.

        Exceptions:
            If none or many plannings would have been removed from the
            database AssertionError is raised.
        """
        # Preconditions
        assert self.pl_id is not None

        # Get a connexion to the database
        c = self._db_conn.cursor()

        # First try to remove the option if any
        c.execute('DELETE FROM options WHERE pl_id=?', (self.pl_id,))

        # Remove the planning itself from the database
        c.execute('DELETE FROM plannings WHERE pl_id=?', (self.pl_id,))

        # Check the results of the planning delete
        assert c.rowcount != 0, "Tried to remove planning with id {id} that "\
            "doesn't exist in database.".format(id=self.pl_id)
        assert c.rowcount < 2, "Removed more than one planning with id {id} "\
            "from the database.".format(id=self.pl_id)

        # Once the results are checked we can commit and close cursor
        self._db_conn.commit()
        c.close()

    # TODO add an remove_vote_to_db and check if a vote already exists
    # TODO add a toggle_vote_to_db that use add/remove_vote_to_db
    @staticmethod
    def add_vote_to_db(pl_id, opt_num, voter, db_conn):
        """
        Register a user vote for an option of the planning to the database.

        Arguments:
            pl_id -- planning id in the database.
            opt_num -- voted option number in the database for this planning.
            voter -- telebot namedtuple User corresponding to the voter.
            db_conn -- connexion to the database to which update the plannings.
        """
        # Preconditions
        assert type(pl_id) is int
        assert type(opt_num) is int
        assert type(voter) is telepot.namedtuple.User
        assert db_conn is not None

        # Retreive the option from database
        opt = Option.load_from_db(
            db_conn=db_conn,
            pl_id=pl_id,
            opt_num=opt_num)
        assert opt is not None, "It's not possible to vote for an inexistant "\
            "option. In planning <{pl_id}> trying to vote for option number "\
            "{opt_num}.".format(pl_id=pl_id, opt_num=opt_num)

        # Register the voter in the vote table
        opt.add_vote_to_db(voter)

    @staticmethod
    def load_all_from_db(user_id, db_conn):
        """
        Load all the planning belonging to the user in the database.

        Arguments:
            user_id -- Telegram user id to look for in the database via the
                       user_id column.
            db_conn -- connexion to the database from which to load the
                       plannings.

        Returns:
            A list of Planning instances corresponding to the one present in
            the database with user_id corresponding to the one provided. If no
            instance are available [] is returned.

        """
        # Preconditions
        assert db_conn is not None
        assert user_id is not None

        # Retreive all the planning data from the db as tuple
        c = db_conn.cursor()
        c.execute('SELECT * FROM plannings WHERE user_id=?', (user_id,))
        rows = c.fetchall()
        c.close()

        # Create the Planning instances
        plannings = [Planning(pl_id, user_id, title, status, db_conn)
                     for pl_id, user_id, title, status in rows]

        return plannings

    @staticmethod
    def load_under_construction_from_db(user_id, db_conn):
        """
        Load the only available under construction planning from the database.

        Arguments:
            user_id -- unique id of the user to which the planning should
                       belong.
            db_conn -- connexion to the database from which to load the
                       plannings.

        Returns:
            If a unique planning with the status "under construction" is
            present for the given user, a correspinding Planning instance is
            returned.
            If no planning with the status "under construction" is present in
            the database, None is returned.

        Exceptions:
            If many planning with the status "under construction" are present
            in the database AssertionError is raised.
        """
        # Preconditions
        assert user_id is not None
        assert db_conn is not None

        # Retreival from the database
        c = db_conn.cursor()
        c.execute('SELECT * FROM plannings WHERE status=? AND user_id=?',
                  (Planning.Status.UNDER_CONSTRUCTION, user_id))
        rows = c.fetchall()
        c.close()

        # If we have many instances... it's an error
        assert len(rows) <= 1, "There should never be more than one "\
            "planning in edition at any given time. "\
            "{nb} have been found in the data base: {pl!r}.".format(
                nb=len(rows),
                pl=rows)

        # Now that we are sure there's not many instances, let's return what
        # we have found
        if rows:
            pl_id, user_id, title, status = rows[0]
            p = Planning(pl_id, user_id, title, status, db_conn)

            # Postconditions
            assert p.pl_id is not None, "A Planning instance extracted from "\
                "the database must have an id."

            return p
        else:
            return None

    @staticmethod
    def load_opened_from_db(pl_id, db_conn):
        """
        Load the only opened planning with specified id from the database.

        Arguments:
            pl_id -- unique id of the desired planning.
            db_conn -- connexion to the database from which to load the
                       plannings.

        Returns:
            The Planning istance if it exists in the database.
            None if not.

        Exceptions:
            If many planning fitting the request are present in the database
            (which should never happen!) AssertionError is raised.
        """
        # Preconditions
        assert db_conn is not None

        # Retreival from the database
        c = db_conn.cursor()
        c.execute('SELECT * FROM plannings WHERE status=? AND pl_id=?',
                  (Planning.Status.OPENED, pl_id))
        rows = c.fetchall()
        c.close()

        # If we have many instances... it's an error
        assert len(rows) <= 1, "There should never be more than one "\
            "planning with a given pl_id. "\
            "{nb} have been found in the data base: {pl!r}.".format(
                nb=len(rows),
                pl=rows)

        # Now that we are sure there's not many instances, let's return what
        # we have found
        if rows:
            pl_id, user_id, title, status = rows[0]
            p = Planning(pl_id, user_id, title, status, db_conn)

            # Postconditions
            assert p.pl_id is not None, "A Planning instance extracted from "\
                "the database must have an id."

            return p
        else:
            return None


class Option:
    """
    Represent a possible option for a planning.

    This could be a date, an hour, a place... in fact whatevere you what the
    attendees to select/choose in order to orgonise your planning.

    It always refer to one specific and existing planning throught its id but
    this constraint is only check when inserting the option to the database
    because of a FOREIGN KEY constraint.
    """

    # Formating strings for Option str representation
    DESC_SHORT = '{description} - 👥 {nb_participant}'

    DESC_FULL = '{description} - 👥 {nb_participant}\n'\
                '{participants}'

    def __init__(self, opt_id, pl_id, txt, num, db_conn):
        """
        Create an Option instance providing all necessary information.

        Arguments:
            opt_id -- unique id of the option in the database
            pl_id -- id of a planning to which the option belong.
            txt -- free form text of the option describing what it is.
            num -- number of the option in its planning
            db_conn -- connexion to the database where the Planning will be
                       saved.
        """
        # Preconditions
        assert db_conn is not None

        self.opt_id = opt_id
        self.pl_id = pl_id
        self.txt = txt
        self.num = num
        self._db_conn = db_conn

    @property
    def voters(self):
        """
        Return voters that voted for this option.

        Returns:
            List of Voters object extracted from the database sorted by first
            name.
        """
        return Voter.load_all_from_option_id_from_db(
            self._db_conn, self.opt_id)

    def is_in_db(self):
        """
        Check if the Option instance is already in database.

        Returns:
            False if the option has a self.opt_id is None or if there is no
            row in options table in the database with opt_id == self.opt_id.
            True else.
        """
        # No id means not yet saved
        if self.opt_id is None:
            return False

        # Search in database
        c = self._db_conn.cursor()
        c.execute(
            """SELECT * FROM options WHERE opt_id=?""",
            (self.opt_id))
        rows = c.fetchall()
        c.close()

        # Is it present ?
        if len(rows) > 0:
            return True
        else:
            return False

    def save_to_db(self):
        """
        Save the Option object to the database.

        If the option had no opt_id before, it is set (since only the database
        can give a valid id to the option).

        Exceptions:
            If the option is already in the database AssertionError is
            raised.
        """
        # Preconditions
        assert not self.is_in_db(), "Option can be saved in database only "\
            "once."

        # Insert the new Option to the database
        c = self._db_conn.cursor()
        c.execute("INSERT INTO options(pl_id, txt, num) VALUES (?,?,?)",
                  (self.pl_id, self.txt, self.num))
        # Retreive the id of the option in the database
        new_opt_id = c.lastrowid
        self._db_conn.commit()
        c.close()

        # Set the id in the instance
        self.opt_id = new_opt_id

    def short_description(self):
        """Return a short description of the option.

        Returns:
            String describing the option with text and number of contributors.
        """
        return Option.DESC_SHORT.format(
                    description=self.txt,
                    nb_participant=len(self.voters))

    def add_vote_to_db(self, user):
        """
        Register the vote to this option from a user to the database.

        Arguments:
            user -- telebot namedtuple User corresponding to the voter.
        """
        # Preconditions
        assert type(user) is telepot.namedtuple.User
        assert self._db_conn is not None

        # Insert the user to the database if not present else update its info
        voter = Voter.create_or_update_to_db(
            v_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            db_conn=self._db_conn)

        # TODO check if we already have a vote for this option from this user

        # Register the voter in the vote table
        c = self._db_conn.cursor()
        c.execute(
            """INSERT INTO votes(opt_id, v_id) VALUES (?,?)""",
            (self.opt_id, voter.v_id))
        self._db_conn.commit()
        c.close()

    @staticmethod
    def load_from_db(db_conn, pl_id, opt_num):
        """
        Get the Option instance with provided planning id and number from db.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
            pl_id -- planning id to find.
            opt_num -- option number in the planning.

        Returns:
            An Option object created from the data retreived from the
            database corresponding to the provided parameters.
            None if no such object exists in database.
        """
        # Preconditions
        assert db_conn is not None
        assert type(pl_id) is int
        assert type(opt_num) is int

        # Retreival from the database
        c = db_conn.cursor()
        c.execute('SELECT * FROM options WHERE pl_id=? AND num=?',
                  (pl_id, opt_num))
        rows = c.fetchall()
        c.close()

        assert len(rows) <= 1, "Only one option should exist in the base for "\
            "a given planning id <{pl_id}> and a given option number "\
            "<{opt_num}>.".format(pl_id=pl_id, opt_num=opt_num)

        # No corresponding option found in database
        if not rows:
            return None

        # Let's build our object from retreived data
        opt_id, pl_id_db, opt_txt, opt_num = rows[0]
        assert pl_id_db == pl_id
        return Option(opt_id, pl_id, opt_txt, opt_num, db_conn)

    @staticmethod
    def load_all_from_planning_id_from_db(db_conn, pl_id):
        """
        Get all the Option instance with provided planning id from database.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
            pl_id -- planning id to find

        Returns:
            A list of Option object created from the data retreived from the
            database and sorted by num field.
            Empty list if no such object are found.
        """
        # Preconditions
        assert db_conn is not None

        # Retreival from the database
        c = db_conn.cursor()
        c.execute('SELECT * FROM options WHERE pl_id=? ORDER BY num', (pl_id,))
        rows = c.fetchall()
        c.close()

        # Let's build objects from those tuples
        return [Option(opt_id, pl_id, opt_txt, opt_num, db_conn)
                for opt_id, _, opt_txt, opt_num in rows]


class Voter:
    """
    Represent a user that has participated to a vote.

    Its unique id is provided by Telegram (the user id in the Telegram API)
    and not by the automatic PRIMARY KEY feature of the database.
    """

    def __init__(self, v_id, first_name, last_name, db_conn):
        """
        Create a Voter instance providing all necessary information.

        It is roughly based on the description of a user in Telegram:
        https://core.telegram.org/bots/api#user

        Arguments:
            v_id -- unique id of the option in the database it is in fact the
                    user id provided by Telegram. It can not be None.
            first_name -- first name of the user it is in fact the first_name
                          provided by Telegram for this user. It can not be
                          None.
            last_name -- last name of the user it is in fact the last_name
                         provided by Telegram for this user. It can be None.
            db_conn -- connexion to the database where the Planning will be
                       saved.
        """
        # Preconditions
        assert type(v_id) is int, "You must provide an integer id for the "\
            "voter."
        assert type(first_name) is str, "You must provide a string first "\
            "name for the voter."
        assert db_conn is not None

        self.v_id = v_id
        self.first_name = first_name
        self.last_name = last_name
        self._db_conn = db_conn

    def is_in_db(self):
        """
        Check if the Voter instance is already in database.

        Returns:
            False if there is no row in options table in the database with
            v_id == self.v_id.
            True else.
        """
        # Search in database
        c = self._db_conn.cursor()
        c.execute(
            """SELECT * FROM voters WHERE v_id=?""",
            (self.v_id,))
        rows = c.fetchall()
        c.close()

        # Is it present ?
        if len(rows) > 0:
            return True
        else:
            return False

    # TODO check if this actualy works with last_name = None
    def save_to_db(self):
        """Save the Voter object to the database."""
        # Preconditions
        assert not self.is_in_db(), "Voter can be saved in database only "\
            "once."

        # Insert the new Option to the database
        c = self._db_conn.cursor()
        c.execute("INSERT INTO voters(v_id, first_name, last_name) "
                  "VALUES (?,?,?)",
                  (self.v_id, self.first_name, self.last_name))
        self._db_conn.commit()
        c.close()

    def update_to_db(self):
        """
        Update the Voter object's columns in the database.

        The v_id is never altered but all other property are updated from
        instance values to database.
        """
        # Preconditions
        assert self.is_in_db(), "Voter can be saved in database only "\
            "once."

        # Insert the new Option to the database
        c = self._db_conn.cursor()
        c.execute("UPDATE voters SET first_name=?, last_name=? "
                  "WHERE v_id=?",
                  (self.first_name, self.last_name, self.v_id))
        self._db_conn.commit()
        c.close()

    @staticmethod
    def create_or_update_to_db(v_id, first_name, last_name, db_conn):
        """
        Create a voter in database or update it's data if it already exist.

        Returns:
            Voter object built from the database.
        """
        # Preconditions
        assert db_conn is not None

        # Let's create a Voter instance
        voter = Voter(v_id, first_name, last_name, db_conn)

        # Retreive the voter if it already exist in the database
        c = db_conn.cursor()
        c.execute('SELECT * FROM voters WHERE v_id=?', (v_id,))
        rows = c.fetchall()
        c.close()

        if rows:
            # Voter exist let's update it's info (since user can change them)
            assert len(rows) == 1, "Voter id should be unique (they are "\
                "Telegram user id."
            voter.update_to_db()
        else:
            # Voter doesn't exist yet let's add it to database
            voter.save_to_db()

        return voter

    @staticmethod
    def load_all_from_planning_id_from_db(db_conn, pl_id):
        """
        Get all the Voter instances regitered in planing's option from db.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
            pl_id -- planning id to find

        Returns:
            A list of Voter objects created from the data retreived from the
            database and sorted by first name field.
            Empty list if no such object are found.
        """
        # Retreival from the database
        c = db_conn.cursor()
        c.execute("""SELECT DISTINCT v_id, first_name, last_name
                     FROM voters
                     NATURAL JOIN votes
                     NATURAL JOIN options
                     WHERE pl_id=?
                     ORDER BY first_name""", (pl_id,))
        rows = c.fetchall()
        c.close()

        # Let's build objects from those tuples
        return [Voter(v_id, first_name, last_name, db_conn)
                for v_id, first_name, last_name in rows]

    @staticmethod
    def load_all_from_option_id_from_db(db_conn, opt_id):
        """
        Get all the Voter instances regitered in povided option from db.

        Arguments:
            db_conn -- connexion to the database where the Planning will be
                       saved.
            opt_id -- option id to find

        Returns:
            A list of Voter objects created from the data retreived from the
            database and sorted by first name field.
            Empty list if no such object are found.
        """
        # Retreival from the database
        c = db_conn.cursor()
        c.execute("""SELECT DISTINCT v_id, first_name, last_name
                     FROM voters
                     NATURAL JOIN votes
                     NATURAL JOIN options
                     WHERE opt_id=?
                     ORDER BY first_name""", (opt_id,))
        rows = c.fetchall()
        c.close()

        # Let's build objects from those tuples
        return [Voter(v_id, first_name, last_name, db_conn)
                for v_id, first_name, last_name in rows]
