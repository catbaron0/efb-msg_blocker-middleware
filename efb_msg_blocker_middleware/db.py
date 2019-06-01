from peewee import Model
from peewee import SqliteDatabase
from peewee import IntegerField, CharField
from ehforwarderbot import EFBMiddleware, utils, EFBMsg
import os

class DatabaseManager:
    def __init__(self, middleware: EFBMiddleware):
        base_path = utils.get_data_path(middleware.middleware_id)
        # self.db = SqliteDatabase(str(base_path / 'ftdata.db'))
        self.db = SqliteDatabase(os.path.join(base_path, 'ftdata.db'))
        self.db.connect()

        class BaseModel(Model):
            class Meta:
                database = self.db

        class Filter(BaseModel):
            author_module_id = CharField()
            author_module_name = CharField()
            author_chat_name = CharField()
            author_chat_alias = CharField()

            chat_chat_uid = CharField()
            chat_chat_name = CharField()
            chat_chat_alias = CharField()

            filter_text = CharField()

        self.Filter = Filter
        if not self.Filter.table_exists():
            self.Filter.create_table()

    def delete_filter(self, filter_id):
        filter_instance = self.Filter.get(id=filter_id)
        filter_instance.delete_instance()

    def add_filter(self, message: EFBMsg, filter_text: str):
        chat = message.chat
        self.Filter.create(
                author_module_id = str(chat.module_id),
                author_module_name = str(chat.module_name),
                author_chat_name = str(chat.chat_name),
                author_chat_alias = str(chat.chat_alias),
                chat_chat_uid = str(chat.chat_uid),
                chat_chat_name = str(chat.chat_name),
                chat_chat_alias = str(chat.chat_alias),
                filter_text = filter_text
                )


