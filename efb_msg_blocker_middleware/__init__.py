# coding: utf-8
import logging
from typing import Dict, Optional, List, Callable
import time

from ehforwarderbot import Middleware, Message, MsgType
from ehforwarderbot import Chat, coordinator
from ehforwarderbot.types import MessageID, ModuleID, ChatID


from . import __version__ as version
from .db import DatabaseManager as DB


class MessageBlockerMiddleware(Middleware):
    """
    Middleware - MessageBlockerMiddleware
    Add and manage filters to block some messages.
    Author: Catbaron <https://github.com/catbaron0>
    """

    middleware_id = ModuleID("catbaron.msg_blocker")
    middleware_name = "Message Blocker Middleware"
    __version__ = version.__version__
    logger: logging.Logger = logging.getLogger(
        "plugins.%s.MessageBlockerMiddleware" % middleware_id
        )

    def __init__(self, instance_id=None):
        super().__init__()
        self.types = {
            'image', 'animation', 'audio', 'file', 'link', 'location',
            'status', 'sticker', 'text', 'video', 'unsupported'
            }
        self.db: DB = DB(self)
        self.commands: Dict[str, Callable] = {
                'list': self.cmd_list_filter,
                'add': self.cmd_add_filter,
                'del': self.cmd_del_filter
                }

    def gen_reply_msg(self, chat: Chat, text: str) -> Message:
        msg: Message = Message()
        msg.chat = chat
        try:
            msg.author = msg.chat.get_member(
                ChatID(self.middleware_id)
            )
        except KeyError:
            msg.author = msg.chat.add_system_member(
                uid=ChatID(self.middleware_id),
                middleware=self,
                name="Message Blocker"
            )
        # msg.author = SystemChatMember(msg.chat, middleware=self)
        # msg.author.name = 'Message Blocker'
        # msg.author.uid = self.middleware_id
        msg.deliver_to = coordinator.master
        msg.type = MsgType.Text
        uid = self.middleware_id + str(int(time.time() * 1000))
        msg.uid = MessageID(uid)
        msg.text = text
        return msg


    @staticmethod
    def gen_filter_text(f) -> str:
        text: List[str] = list()
        text.append('-----')
        text.append(f'id: {f.id}')
        text.append(f'chat_name: {f.chat_name}')
        text.append(f'user_name: {f.user_name}')
        text.append(f'msg_type: {f.msg_type}')
        return '\n'.join(text)

    def cmd_list_filter(
            self, message: Message,
            msg_type: str = "",
            ) -> Message:
        """
        list filter for current chat.
        :param message: The command message
        :param msg_type: To list filters on this message type

        return: Message to reply to the user
        """
        self.logger.info("List filters...")
        msg_type = msg_type.lower()
        chat = message.chat
        user = None
        if message.target:
            user = message.target.author

        filters = self.db.select_filters(chat, user, msg_type)
        filter_text = [self.gen_filter_text(f) for f in filters]

        reply_text: str = '\n'.join(filter_text)
        if not reply_text:
            reply_text = 'No filter was found.'
        msg = self.gen_reply_msg(chat, reply_text)
        return msg

    def cmd_add_filter( self, message: Message, msg_type: str = "") -> Message:
        """
        Add a new filter to database
        :param message: The command message
        :param msg_type: str, message type to be filtered.

        return: Message to reply to the user
        """
        self.logger.info("Add filters")
        msg_type = msg_type.lower()
        chat = message.chat
        user = None
        if message.target:
            user = message.target.author

        if not user and not msg_type:
            # user and msg_type can't be both Null
            reply_text = "User and message type can't be both null"
            return self.gen_reply_msg(chat, reply_text)
        if msg_type:
            try:
                msg_type = msg_type.capitalize()
                MsgType(msg_type)
            except ValueError:
                reply_text = f"Invalid message type: {msg_type}"
                return self.gen_reply_msg(chat, reply_text)
        try:
            self.db.add_filter(chat, user, msg_type)
            reply_text = f"Filter added."
        except Exception as e:
            reply_text = f"Failed to add filter. {e}"
        self.logger.info(reply_text)
        return self.gen_reply_msg(chat, reply_text)

    def cmd_del_filter(self, message: Message, filter_id: int) -> Message:
        """
        Delete a filter from database
        """
        chat = message.chat
        self.logger.info('Delete filter')
        try:
            self.db.delete_filter(chat_id=chat.uid, filter_id=filter_id)
            reply_text: str = "Filter Deleted"
        except KeyError:
            reply_text = "Can't find the filter in current chat."

        return self.gen_reply_msg(chat, reply_text)

    @staticmethod
    def sent_by_master(message: Message) -> bool:
        return message.deliver_to != coordinator.master

    def match_filter(self, message: Message, f) -> bool:
        if f.user_id and f.user_id != message.author.uid:
            return False
        if f.msg_type:
            msg_type = MsgType(f.msg_type.capitalize())
            if msg_type != message.type:
                return False
        return True

    def filter_message(self, message: Message):
        """
        Match a message to filters of this chat.
        The messaged is matched when it matches to all the keys.
        :pamram message: [Message] Message to match
        Return:
            True if the message is matched to one filter.
            False otherwise.
        """
        filters = self.db.select_filters(message.chat)
        for f in filters:
            if self.match_filter(message, f):
                return f
        return None

    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process a message with middleware

        :param message: Message, message to proces
        :return: Optional[Message], message or None if discarded.
        """
        msg_text: str = message.text.strip()
        if self.sent_by_master(message):
            if msg_text.startswith('\\msg_blocker '):
                # command message
                cmd_arg = msg_text.split(' ', 2)[1:]
                if len(cmd_arg) > 1:
                    cmd, arg = cmd_arg
                else:
                    cmd, arg = cmd_arg[0], ''
                if cmd in self.commands:
                    return self.commands[cmd](message, arg)
                else:
                    return self.gen_reply_msg(
                        message.chat, f"{cmd} is not a msg_blocker command")
            else:
                # normal message, pass it.
                return message

        # Match messages from salves to filters
        f = self.filter_message(message)
        if f:
            reply = self.gen_filter_text(f)
            self.logger.info(
                'Message blocked by: %s',
                reply
            )
            return None
        else:
            return message
