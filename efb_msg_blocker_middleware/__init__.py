# coding: utf-8
import json
import logging
import os
from typing import Any, Dict, Optional, List, Tuple, Callable, Iterator
import re

import yaml
from ehforwarderbot import EFBMiddleware, EFBMsg, MsgType, EFBChat, coordinator
from ehforwarderbot.utils import get_config_path

from . import __version__ as version
from .db import DatabaseManager


# class WeChatChannel(EFBChannel):
class MessageBlockerMiddleware(EFBMiddleware):
    """
    EFB Middleware - MessageBlockerMiddleware
    Add and manage filters to block some messages.
    Author: Catbaron <https://github.com/catbaron0>
    """

    middleware_id = "catbaron.msg_blocker"
    middleware_name = "Message Blocker Middleware"
    __version__ = version.__version__
    logger: logging.Logger = logging.getLogger(
        "plugins.%s.MessageBlockerMiddleware" % middleware_id
        )

    def __init__(self, instance_id=None):
        super().__init__()
        self.types = {
            'image', 'animation', 'audio', 'file', 'link', 'location', 'status',
            'sticker', 'text', 'video', 'unsupported'
            }
        self.db: DatabaseManager = DatabaseManager(self)
        # To avoid reading from db, save filters to self.filters
        # and keep it up to date
        # Not necessary though.
        self.filters: Dict[Tuple, List] = dict()

        self.commands: Dict[str, Callable] = {
                'list': self.cmd_list_filter,
                'add': self.cmd_add_filter,
                'del': self.cmd_del_filter
                }

    def reply_msg(self, message: EFBMsg, text: str) -> EFBMsg:
        msg: EFBMsg = EFBMsg()
        msg.chat = message.chat
        msg.author = message.author
        msg.author.module_id = self.middleware_id
        msg.author.module_name = self.middleware_name
        msg.author.chat_name = 'Message Blocker'
        msg.author.module_id = self.middleware_id
        msg.author.module_name = self.middleware_name
        msg.deliver_to = coordinator.master
        msg.type = MsgType.Text
        msg.uid = message.uid
        msg.text = text
        return msg

    def cmd_list_filter(self, message: EFBMsg, arg: str) -> EFBMsg:
        """
        list filter for current chat.
        Arguments:
            message: [EFBMsg], the message sending this command.
            arg: [str], unused here.
        Return:
            If the message replies to a target message, return filters
            related to the author user of target message. Otherwise
            return all the filters set to current chat.
        """
        self.logger.info("List filters...")

        filters_data: List[str] = list()
        target: EFBMsg = message.target

        # Read filters from self.filters
        filters: List = self.get_filters(message)
        if not target:
            for fi in filters:
                filters_data.append(str(fi.__data__))
        else:
            # List filters related to an user
            uid: str = target.author.chat_uid
            for fi in filters:
                if uid == eval(fi.filter_text).get('user', ''):
                    filters_data.append(str(fi.__data__))

        reply_text: str = '\n'.join(filters_data)
        if not reply_text:
            reply_text = 'No filter was found.'
        msg = self.reply_msg(message, reply_text)
        return msg

    def cmd_add_filter(self, message: EFBMsg, arg: str) -> EFBMsg:
        """
        Add a new filter to database, and update self.filters.
        Arguments:
            message: [EFBMsg], the message sending this command.
                    If there is a target message, add the author
                    of the target message to the added filters.
            arg: [str], content of command arguments.
                 When arg is one of the types, take the added filters
                 as {'type', [arg]}, otherwise the arg should be a
                 json string.
        """

        self.logger.info("Add filters")
        arg: str = arg.lower()
        self.logger.info("filter_text:", arg)
        filters: Dict[str, Any] = dict()
        if arg:
            if arg in self.types:
                # Add type as filters directly
                filters['type'] = [arg]
            else:
                # Add filter according to the arg string
                # The arg string should be json-string
                # Convert the arg to dict object
                self.logger.info("Filters of arg: %s", arg)
                try:
                    filters = eval(arg)
                except Exception:
                    reply_text = f"Failed to add filter. Invalid filter text. "
                    return self.reply_msg(message, reply_text)
        if message.target:
            # Add target author to the filters
            self.logger.info(
                "Filters to user: %s", message.target.author.chat_name
                )
            # message.chat.chat_name = message.target.chat.chat_name
            filters['user'] = str(message.target.author.chat_uid)

        if filters:
            filter_text: str = json.dumps(filters)
            self.logger.info("Add filters: %s", filter_text)
            # Add filters to database
            self.db.add_filter(message, filter_text)
            # Update self.filters from database
            self.update_filters(message)
            reply_text = f"Filter added: {filter_text}"
        else:
            reply_text = f"Failed to add filter. Filter is empty."
        self.logger.info(reply_text)
        # filters.update(filters)
        return self.reply_msg(message, reply_text)

    def cmd_del_filter(
            self, message: EFBMsg, filter_id: Optional[str] = None) -> EFBMsg:
        """
        Delete a filter from database, and update self.filters.
        Arguments:
            message: [EFBMsg], the message sending this command.
                    If there is a target message and the filter_id
                    is None, delete all the filter related the
                    author of the target message.
            filter_id: [str], Id of filter. The filter with the id
                    will be deleted from the database. """

        target: EFBMsg = message.target
        if not filter_id and target:
            # Delete all the filters to the author of target message
            filter_data = []
            for fi in self.select_filters(message):
                filter_dict = eval(fi.filter_text)
                if filter_dict.get('user', '') == target.author.chat_uid:
                    filter_data.append(str(fi.__data__))
                    fi.delete_instance()
            reply_text: str = 'Filter deleted: %s' % '\n'.join(filter_data)
        elif filter_id:
            # Delete the filter based on the filter_id
            self.logger.info('Delete filter')
            filter_id: int = int(filter_id)
            reply_text: str = 'Filter deleted: %s' % \
                self.db.Filter.get(id=filter_id).__data__
            self.db.delete_filter(filter_id=filter_id)
        else:
            reply_text: str = "No filter to delete."
        self.logger.info(reply_text)
        self.update_filters(message)
        return self.reply_msg(message, reply_text)

    def select_filters(self, message: EFBMsg) -> List:
        """
        Select filters from database based on the mesage sending a command.
        Arguments:
            message: [EFBMsg], the message sending this command.
        """

        author_module_id: str = message.chat.module_id
        chat_chat_uid: str = message.chat.chat_uid
        filters: Iterator = self.db.Filter.select().where(
            self.db.Filter.author_module_id == author_module_id,
            self.db.Filter.chat_chat_uid == chat_chat_uid
        )
        return list(filters)

    def update_filters(self, message: EFBMsg) -> List:
        """
        Update self.filters from database
        Arguments:
            message: [EFBMsg], the message sending this command.
        Return:
            List of fitlers
        """
        self.logger.info('Update filter from database')
        author_module_id: str = message.chat.module_id
        chat_chat_uid: str = message.chat.chat_uid
        filters = self.select_filters(message)
        self.filters[(author_module_id, chat_chat_uid)] = filters
        return filters

    def get_filters(self, message: EFBMsg) -> List:
        """
        Get filters added to current chat.
        To avoid selecting from database everytime querying, get
        filters from self.filters. Select from database and update
        self.filters if there is no filters in self.filters.
        Arguments:
            message: [EFBMsg], the message sending this command.
        Return:
            List of fitlers
        """
        key = (message.chat.module_id,  message.chat.chat_uid)
        return self.filters.get(key, self.update_filters(message))

    def load_config(self) -> Dict[str, str]:
        config_path = get_config_path(self.middleware_id)
        if not os.path.exists(config_path):
            self.self.logger.info('The configure file does not exist!')
            return
        with open(config_path, 'r') as f:
            d = yaml.load(f)
            if not d:
                self.self.logger.info('Load configure file failed!')
                return
            return d

    @staticmethod
    def sent_by_master(message: EFBMsg) -> bool:
        author: EFBChat = message.author
        try:
            if author.module_id == 'blueset.telegram':
                return True
            else:
                return False
        except Exception:
            return False

    def match_msg(self, message: EFBMsg, filter_dict: Dict[str, Any]) -> bool:
        """
        Match a message to filters with keys of 'user', 'text' and 'type'.
        The messaged is matched when it matches to all the keys.
        Arguments:
            message: [EFBMsg] Message to match
            filter_dict: [Dict], a filter to match
        Return:
            True if the message is matched to the filter.
            False otherwise.
        """
        if 'user' not in filter_dict \
                and 'text' not in filter_dict \
                and 'type' not in filter_dict:
            return False

        author = message.author
        match_user, match_text, match_type = True, True, True
        if 'user' in filter_dict:
            if filter_dict['user'] != author.chat_uid:
                match_user = False
        if 'text' in filter_dict:
            k = re.compile(str(filter_dict['text']))
            if not re.search(k, message.text):
                match_text = False
        if 'type' in filter_dict:
            types: List[str] = filter_dict['type']
            m_type: MsgType = message.type
            if not('image' in types and m_type == MsgType.Image
                    or 'animation' in types and m_type == MsgType.Animation
                    or 'audio' in types and m_type == MsgType.Audio
                    or 'file' in types and m_type == MsgType.File
                    or 'link' in types and m_type == MsgType.Link
                    or 'location' in types and m_type == MsgType.Location
                    or 'status' in types and m_type == MsgType.Status
                    or 'sticker' in types and m_type == MsgType.Sticker
                    or 'text' in types and m_type == MsgType.Text
                    or 'video' in types and m_type == MsgType.Video
                    or 'unsupported' in types and m_type == MsgType.Unsupported):
                match_type = False
        if match_user:
            # print('user matched')
            self.logger.info('user_id matched')
        if match_type:
            # print('type matched')
            self.logger.info('type matched')
        if match_text:
            # print('text matched')
            self.logger.info('text matched')
        match = match_user and match_text and match_type
        return match

    def process_message(self, message: EFBMsg) -> Optional[EFBMsg]:
        """
        Process a message with middleware

        Args:
            message (:obj:`.EFBMsg`): Message object to process

        Returns:
            Optional[:obj:`.EFBMsg`]: Processed message or None if discarded.
        """
        msg_text: str = message.text.strip()
        if self.sent_by_master(message):
            # import ipdb;ipdb.set_trace()
            if msg_text.startswith('\\'):
                # command message
                cmd_arg = msg_text[1:].split(' ', 1)
                if len(cmd_arg) > 1:
                    cmd, arg = cmd_arg
                else:
                    cmd, arg = cmd_arg[0], ''
                if cmd in self.commands:
                    return self.commands[cmd](message, arg)
                else:
                    return message
            else:
                # normal message, pass it.
                return message

        # Match messages from salves to filters
        matched = False
        for fi in self.get_filters(message):
            filter_dict = eval(fi.filter_text)
            matched = self.match_msg(message, filter_dict)
            if matched:
                break
        if not matched:
            return message
        else:
            # print('Message blocked!')
            self.logger.info('Message blocked: %s', message.__dict__)
            return None
