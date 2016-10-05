# -*- coding: utf-8 -*-
"""Gandalf bot Telegram protocol handlers."""

# For database access snce we need data persistence
import sqlite3

# For debugging Telegram message
from pprint import pprint

# Telegram python binding
# c.f. https://telepot.readthedocs.io/en/latest/
import telepot
from telepot.namedtuple import Message
from telepot.namedtuple import InlineKeyboardMarkup
from telepot.namedtuple import InlineKeyboardButton
from telepot.namedtuple import InlineQueryResultArticle
from telepot.namedtuple import InputTextMessageContent
from telepot.namedtuple import CallbackQuery

# Planning entities
from planning import Planning, Option

_LOG_MSG = {
    'opening':
        '{handler} opening.',
    'closing':
        '{handler} closing.',
    'db_new_planning':
        'Planning "{title}" added to database file <{dbfile}>.',
    'planning_already_in_progress':
        'Impossible to create a new planning, there is already a planning '
        'in progress.',
    'inline_received':
        'Inline message received.',
    'callback_received':
        'Callback query received with query data: <{data}>.'
}

_CHAT_MSG = {
    'help_answer':
        'This bot will help you create planings. Use /new to create a '
        'planning here, then publish it to groups or send it to individual '
        'friends.\n\n'
        'You can control me by sending these commands:\n\n'
        '/new - create a new planning\n'
        '/plannings - manage your existing plannings.\n'
        '/help - display this help',
    'dont_understand':
        'Sorry I did not understand... try /help to see how you should talk '
        'to me.',
    'new_answer':
        'You want to create a planning named *{title}*. Send me a description '
        'or a question to ask to the participant. '
        '/cancel to abort creation.',
    'new_error_answer':
        'Sorry to create a planning you have give a title after the /new '
        'command. Like this :\n\n'
        '/new _My fancy planning title_',
    'new_already_in_progress':
        'Sorry but you already have a planning creation in progress.\n'
        'You can cancel the current creation using the /cancel command or '
        'finish it using the /done command.',
    'description_answer':
        'Creating new planning:\n'
        '*{title}*\n'
        '_{description}_\n\n'
        'Please send me the first option for participant to join. '
        '/cancel to abort creation.',
    'option_answer':
        'Good. Feel free to had more options. '
        '/done to finish creating the planning or /cancel to abort creation.',
    'done_answer':
        '👍 Planning created. You can now publish it to a group or send it '
        'to your friends in a private message. To do this, tap the button '
        'below or start your message in any other chat with @{botusername} '
        'and select one of your polls to send.',
    'done_error_answer':
        'Sorry but you have to create at least one option for this planning.',
    'cancel_answer':
        'Planning creation canceled.',
    'no_current_planning_answer':
        'Sorry but there is no planning currently in edition. To start '
        'creating one use the /new command. Like this:\n\n'
        '/new _My fancy planning title_',
    'plannings_answer':
        'You have currently {nb_plannings} plannings:\n\n'
        '{planning_list}'
}

_UI_MSG = {
    'publish_btn':
        'Publish planning',
    'click_notification':
        '👍 Your availability has been registered'
}


def is_command(text, cmd):
    """Analyse a string to determine if it is a peticular command message.

    This function does not check for valid number of parameters in the
    message.

    Arguments:
        text -- a string to analyse.
        cmd -- the command to check for. It must include the leading '/' char.

    Returns:
        True if text starts with the cmd provided command.
        False in all other cases
    """
    # cmd preconditions
    assert cmd.strip() == cmd  # No spaces around
    assert cmd.startswith('/')  # Leading slash included
    assert len(cmd) > 1  # At least one char for command name

    return len(text.strip()) > 0 and text.split()[0] == cmd


class PlannerChatHandler(telepot.helper.ChatHandler):
    """Process chat messages to create persistent plannings."""

    def __init__(self, seed_tuple, db_file, **kwargs):
        """
        Create a new PlannerChatHandler.

        This is implicitly called when creating a new thread.

        Arguments:
            seed_tuple -- seed of the delegator.
            db_file -- database file to use.
        """
        super(PlannerChatHandler, self).__init__(seed_tuple, **kwargs)

        # Database file name (for log & debug)
        self._db_file = db_file

        # Connexion to the database
        self._conn = sqlite3.connect(
            db_file,
            check_same_thread=False)  # TODO remove once switched to asyncio

        # Some feedback for the logs
        print(_LOG_MSG['opening'].format(handler=PlannerChatHandler.__name__))

        # Post condition
        assert self._conn is not None

    def on_close(self, ex):
        """
        Called after timeout.

        Timeout is mandatory to prevent infinity of threads to be created.

        Part of the telepot.helper.ChatHandler API.
        """
        # Close the connexion to the database
        self._conn.close()

        # Some feedback for the logs
        print(_LOG_MSG['closing'].format(handler=PlannerChatHandler.__name__))

    def on_chat_message(self, msg):
        """
        React the the reception of a Telegram message.

        Part of the telepot.helper.ChatHandler API.
        """
        # Raw printing of the message received
        pprint(msg)

        # Retreive basic information
        content_type, _, chat_id = telepot.glance(msg)

        # We only want text messages
        if content_type != 'text':
            self.sender.sendMessage(_CHAT_MSG['dont_understand'])
            return

        # Convert message to a convenient namedtuple
        msg = Message(**msg)

        # Now we can extract the text...
        text = msg.text
        from_user = msg.from_

        # Switching according to witch command is received
        if is_command(text, '/help'):
            self.on_command_help(from_user)
        elif is_command(text, '/new'):
            self.on_command_new(from_user, text)
        elif is_command(text, '/plannings'):
            self.on_command_plannings(from_user)
        elif is_command(text, '/cancel'):
            self.on_command_cancel(from_user)
        elif is_command(text, '/done'):
            self.on_command_done(from_user)
        # Not a command or not a recognized one
        else:
            self.on_not_a_command(from_user, text)

    def on_command_help(self, from_user):
        """
        Handle the /help command by sending an help message.

        Arguments:
            from_user -- User namedtuple representing the user thant sent the
                         command
        """
        self.sender.sendMessage(_CHAT_MSG['help_answer'])

    def on_command_new(self, from_user, text):
        """
        Handle the /new command by creating a new planning.

        Arguments:
            from_user -- User namedtuple representing the user thant sent the
                         command
            text -- string containing the text of the message recieved
                (including the /new command)
        """
        # First check if there is not a planning under construction
        under_construction = Planning.load_under_construction_from_db(
            from_user.id,
            self._conn)
        if under_construction is not None:
            # Tell the user
            self.sender.sendMessage(_CHAT_MSG['new_already_in_progress'])
            # Log some info for easy debugging
            print(_LOG_MSG['planning_already_in_progress'])
            return

        # Retrieve the title of the planning
        command, _, title = text.lstrip().partition(' ')

        # The user must provide a title
        if title == '':
            self.sender.sendMessage(
                _CHAT_MSG['new_error_answer'],
                parse_mode='Markdown')
            return

        # Create a new planning
        planning = Planning(
            pl_id=None,
            user_id=from_user.id,
            title=title,
            status=Planning.Status.UNDER_CONSTRUCTION,
            db_conn=self._conn)

        # Save the new planning to the database
        planning.save_to_db()

        # Some feedback in the logs
        print(_LOG_MSG['db_new_planning'].format(
            dbfile=self._db_file,
            title=planning.title))

        # Send the answer
        reply = _CHAT_MSG['new_answer'].format(title=title)
        self.sender.sendMessage(reply, parse_mode='Markdown')

    def on_command_plannings(self, from_user):
        """
        Handle the /plannings command by retreiving all plannings.

        Arguments:
            from_user -- User namedtuple representing the user thant sent the
                         command
        """
        # Retrieve plannings from database for current user
        plannings = Planning.load_all_from_db(from_user.id, self._conn)

        # Prepare a list of the short desc of each planning
        planning_list = '\n\n'.join(
            [p.short_description(num) for num, p in enumerate(plannings)])

        # Format the reply and send it
        reply = _CHAT_MSG['plannings_answer'].format(
            nb_plannings=len(plannings),
            planning_list=planning_list)
        self.sender.sendMessage(reply, parse_mode='Markdown')

    def on_command_cancel(self, from_user):
        """
        Handle the /cancel command to cancel the current planning.

        This only works if there is a planning under construction i.e. after a
        /new command and before a /done command.

        Arguments:
            from_user -- User namedtuple representing the user thant sent the
                         command
        """
        # Retreive the current planning if any
        planning = Planning.load_under_construction_from_db(
            from_user.id,
            self._conn)

        # No planning... nothing to do
        if planning is None:
            self.sender.sendMessage(_CHAT_MSG['no_current_planning_answer'])
        else:
            # TODO ask a confirmation here using button
            # Remove the planning from the database
            planning.remove_from_db()
            self.sender.sendMessage(_CHAT_MSG['cancel_answer'])

    def on_command_done(self, from_user):
        """
        Handle the /done command to finish the current planning.

        This only works if there is a planning under construction i.e. after a
        /new command and after the creation of at least one option for this
        planning.

        Arguments:
            from_user -- User namedtuple representing the user thant sent the
                         command
        """
        # Retreive the current planning if any
        planning = Planning.load_under_construction_from_db(
            from_user.id,
            self._conn)

        # No planning... nothing to do and return
        if planning is None:
            self.sender.sendMessage(_CHAT_MSG['no_current_planning_answer'])
            return

        # No option... ask for one and return
        if len(planning.options) == 0:
            self.sender.sendMessage(_CHAT_MSG['done_error_answer'])
            return

        # Change planning state and update it in the database
        planning.status = Planning.Status.OPENED
        planning.update_to_db()

        # First we must send a recap of the opened planning...
        self.sender.sendMessage(
            planning.full_description(),
            parse_mode='Markdown')

        # ...then we send a confirmation message
        self.sender.sendMessage(
            _CHAT_MSG['done_answer'].format(
                botusername=self.bot.getMe()['username']),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text=_UI_MSG['publish_btn'],
                        switch_inline_query=planning.inline_query_id()
                    )]]
                )
            )

    def on_not_a_command(self, from_user, text):
        """
        Handle any text message that is not a command or not a recognised one.

        If called after a /new command it adds a new option to the current
        planning.
        Any other case trigger a "I don't understand" message.

        Arguments:
            from_user -- User namedtuple representing the user thant sent the
                         command
            text -- string containing the text of the message recieved.
        """
        # Retreive the current planning if any
        planning = Planning.load_under_construction_from_db(
            from_user.id,
            self._conn)

        if planning is not None:
            # We have a planning in progress... let's add the option to it !
            opt = Option(
                opt_id=None,
                pl_id=planning.pl_id,
                txt=text,
                num=len(planning.options),
                db_conn=self._conn)

            # and save the option to database
            opt.save_to_db()

            self.sender.sendMessage(_CHAT_MSG['option_answer'])
        else:
            # We have no planning in progress, we just can't understand the msg
            self.sender.sendMessage(_CHAT_MSG['dont_understand'])


class PlannerInlineHandler(
        telepot.helper.InlineUserHandler,  # Handles inline query/response
        telepot.helper.AnswererMixin,  # Integrate Answerer object
        telepot.helper.InterceptCallbackQueryMixin):  # Handles callback query
    """Process inline messages to show plannings in chats."""

    def __init__(self, seed_tuple, db_file, **kwargs):
        """
        Create a new PlannerInlineHandler.

        This is implicitly called when creating a new thread.

        Arguments:
            seed_tuple -- seed of the delegator.
            db_file -- database file to use.
        """
        super(PlannerInlineHandler, self).__init__(seed_tuple, **kwargs)

        # Database file name (for log & debug)
        self._db_file = db_file

        # Connexion to the database
        self._conn = sqlite3.connect(
            db_file,
            check_same_thread=False)  # TODO remove once switched to asyncio

        # Some feedback for the logs
        print(_LOG_MSG['opening'].format(handler=PlannerChatHandler.__name__))

        # Post condition
        assert self._conn is not None

    def on_close(self, ex):
        """
        Called after timeout.

        Timeout is mandatory to prevent infinity of threads to be created.

        Part of the telepot.helper.ChatHandler API.
        """
        # Close the connexion to the database
        self._conn.close()

        # Some feedback for the logs
        print(_LOG_MSG['closing'].format(handler=PlannerChatHandler.__name__))

    def on_inline_query(self, msg):
        """
        React to the reception of a Telegram inline query.

        Part of the telepot.helper.InlineUserHandler API.
        """
        def compute_answer():
            """
            Helper function to compute the result for the Answerer.

            https://telepot.readthedocs.io/en/latest/#inline-handler-per-user
            """
            # Raw printing of the message received
            pprint(msg)

            # Retreive the major info from the message
            query_id, from_id, query_string = telepot.glance(
                msg=msg,
                flavor='inline_query')
            print('Inline Query:', query_id, from_id, query_string)

            # Trivial case: the query does look like a planning inline query id
            if not query_string.startswith(Planning.INLINE_QUERY_PREFIX):
                # We return an empty answer
                return []

            # Retreive the id of the desired planning if possible
            try:
                pl_id = int(query_string[len(Planning.INLINE_QUERY_PREFIX):])
            except ValueError:
                return []

            # Retreive the corresponding planning from database
            planning = Planning.load_opened_from_db(
                pl_id=pl_id,
                db_conn=self._conn)
            if planning is None:
                return []

            # Build the reply inline keyboard markup
            inline_kbm = [[
                InlineKeyboardButton(
                    text=opt.short_description(),
                    callback_data='{pl_id} {opt_num}'.format(
                        pl_id=planning.pl_id,
                        opt_num=opt.num)
                    )]
                for opt in planning.options]

            # Search for a corresponding planning
            articles = [
                InlineQueryResultArticle(
                    type='article',
                    id=str(planning.pl_id),
                    title=planning.title,
                    description='',  # TODO add a description here
                    input_message_content=InputTextMessageContent(
                        message_text=planning.full_description(),
                        parse_mode='Markdown'),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=inline_kbm)
                   )
                ]

            return articles

        # Use the Answerer to handle the message and reply to them
        self.answerer.answer(msg, compute_answer)

    def on_chosen_inline_result(self, msg):
        """
        React to the selection of a peticular inline result.

        Part of the telepot.helper.InlineUserHandler API.
        """
        print(_LOG_MSG['inline_received'])
        pprint(msg)
        # We do nothing in particular... but the fnction need to be present

    def on_callback_query(self, query):
        """
        React to the click on a callback button.

        Part of the telepot.helper.InlineUserHandler API.
        """
        # Get the basic infos from the message
        query_id, from_id, query_data = telepot.glance(
            query, flavor='callback_query')

        # Some logging
        print(_LOG_MSG['callback_received'].format(data=query_data))
        pprint(query)

        # Extract info from the query data
        pl_id, opt_num = query_data.split()
        pl_id = int(pl_id)
        opt_num = int(opt_num)

        # Convert the message to a convenient namedtuple
        query = CallbackQuery(**query)

        # Register the vote
        # TODO use toggle_vote_to_db instead
        Planning.add_vote_to_db(
            pl_id=pl_id,
            opt_num=opt_num,
            voter=query.from_,
            db_conn=self._conn)

        # Edit the planning post
        # TODO put some actual code here

        # Show confirmation
        self.bot.answerCallbackQuery(
            query_id, text=_UI_MSG['click_notification'])
