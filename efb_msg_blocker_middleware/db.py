from peewee import Model
from peewee import SqliteDatabase
from peewee import CharField
from ehforwarderbot import Middleware, utils, Message, Chat
from ehforwarderbot.chat import ChatMember
import os
from typing import Optional


class DatabaseManager:
    def __init__(self, middleware: Middleware):
        base_path = utils.get_data_path(middleware.middleware_id)
        self.db = SqliteDatabase(os.path.join(base_path, 'ftdata.db'))
        self.db.connect()

        class BaseModel(Model):
            class Meta:
                database = self.db

        class Filter(BaseModel):
            chat_module_id = CharField()
            chat_id = CharField()
            chat_name = CharField()
            user_name = CharField(null=True)
            user_id = CharField(null=True)
            msg_type = CharField(null=True)

        self.Filter = Filter
        if not self.Filter.table_exists():
            self.Filter.create_table()

    def delete_filter(self, filter_id: int, chat_id: str):
        instance = self.Filter.get_or_none(
                self.Filter.id==filter_id,
                self.Filter.chat_id==chat_id)
        if instance:
            instance.delete_instance()
        else:
            raise KeyError

    def add_filter(self, chat: Chat, user: Optional[ChatMember], msg_type: str):
        user_id = ""
        user_name = ""
        if user:
            user_id = user.uid
            user_name = user.name
        self.Filter.create(
            chat_module_id=chat.module_id,
            chat_id=chat.uid,
            chat_name=chat.name,
            user_name=user_name,
            user_id=user_id,
            msg_type=msg_type)

    def select_filters(
            self, chat: Chat,
            user: Optional[ChatMember] = None,
            msg_type: str = "",
            ):
        """
        Select filters from database
        :param chat: Chat, the chat where the message is sent.
        :param user: ChatMember, activated when a message is replied. 
        :param msg_type: str, message type to be filtered.

        return: Message to reply to the user
        """
        filters = self.Filter.select().where(
            self.Filter.chat_module_id == chat.module_id,
            self.Filter.chat_id == chat.uid,
            self.Filter.chat_name == chat.name,
        )
        if user:
            user_id = user.uid
            user_name = user.name
            filters = filters.where(
                self.Filter.user_id == user_id,
                self.Filter.user_name == user_name,
            )
        if msg_type:
            filters = filters.where(
                self.Filter.msg_type == msg_type
            )
        return list(filters)
