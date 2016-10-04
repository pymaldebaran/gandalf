# -*- coding: utf-8 -*-
"""
Gandalf bot planning entities.

All classes needed to encapsultale the underlying database tables needed by
the bot.
"""

# Used to represent status of a planning
from enum import Enum


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
            List of Option object assciated to the planning extracted from the
            database sorted by num field.
        """
        return Option.load_all_from_planning_id_from_db(
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
            nb_participants=0,  # TODO replace with a number reteived from db
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

    def save_to_db(self):
        """Save the Planning object to the provided database."""
        c = self._db_conn.cursor()
        c.execute(
            """INSERT INTO plannings(user_id, title, status)
                VALUES (?,?,?)""",
            (self.user_id, self.title, self.status))
        self._db_conn.commit()
        c.close()

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

    @staticmethod
    def load_all_from_db(user_id, db_conn):
        """
        Load all the instances belonging to the user in the database.

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

    def __init__(self, pl_id, txt, num, db_conn):
        """
        Create an Option instance providing all necessary information.

        Arguments:
            pl_id -- id of a planning to which the option belong.
            txt -- free form text of the option describing what it is.
            num -- number of the option in its planning
            db_conn -- connexion to the database where the Planning will be
                       saved.
        """
        # Preconditions
        assert db_conn is not None

        self.pl_id = pl_id
        self.txt = txt
        self.num = num
        self._db_conn = db_conn

    def save_to_db(self):
        """Save the Option object to the provided database."""
        # Insert the new Option to the database
        c = self._db_conn.cursor()
        c.execute("INSERT INTO options(pl_id, txt, num) VALUES (?,?,?)",
                  (self.pl_id, self.txt, self.num))
        self._db_conn.commit()
        c.close()

    def short_description(self):
        """Return a short description of the option.

        Returns:
            String describing the option with text and number of contributors.
        """
        return Option.DESC_SHORT.format(
                    description=self.txt,
                    nb_participant=0)

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
        return [Option(my_id, my_txt, num, db_conn)
                for my_id, my_txt, num in rows]
