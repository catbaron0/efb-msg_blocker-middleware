# MessageBLocker: A middleware for EFB 

## Notice

**Middleware ID**: `catbaron.message_blocker`

**MessageBLocker** is a middleware for [EFB](https://ehforwarderbot.readthedocs.io), to manage filters and block some specific messages. 

**Note:** I rewrite most parts of this middleware in the last update. Please read the `usage` section to check the change. Because the structer of database is changed, you may need to delete the database file in order to make it work (usually it's at `~/.ehforwarderbot/profiles/default/catbaron.msg_blocker/ftdata.db`). 

**Note:** If you are looking for a way to block all messages from so called `Official Accounts(公众号)`, this plugin is not what you need. Here are some advices:
* Don't subscribe any official accounts. They don't worth it.
* Link all official accounts to one chat, and block the chat. Refer to [wiki of EWS](https://github.com/blueset/efb-wechat-slave/wiki/EWS-&-ETM%EF%BC%9A%E6%89%B9%E9%87%8F%E7%BB%91%E5%AE%9A%EF%BC%88%E5%85%AC%E4%BC%97%E5%8F%B7%E7%AD%89%EF%BC%89).

## Dependense

* Python >= 3.6
* EFB >= 2.0.0b28
* ETM >= 2.0.0b45.dev1 (if you are using it)
* EWS >= 2.0.0a41.dev2 (if you are using it)
* peewee
* PyYaml

## Install

* Install
    ```
    pip install efb-msg_blocker-middleware
    ```
* Register to EFB
Following [this document](https://ehforwarderbot.readthedocs.io/en/latest/getting-started.html) to edit the config file. The config file by default is `~/.ehforwarderbot/profiles/default`. It should look like:
    ```
    master_channel: foo.demo_master
    slave_channels:
    - foo.demo_slave
    - bar.dummy
    middlewares:
    - foo.other_middlewares
    - catbaron.msg_blocker
    ```

    Usually you just need to add the last line to your config file.

* Restart EFB.

## Usage
Three commands are supported by this middleware, namely `list`, `add` and `del`. To avoid conflict to other channels' command, all the commands MUST follow `\msg_blocer` and a space, as shown below.

* `\msg_blocker list`: List all the filters you have added to one chat. You can reply this command to a message, then only filters applied to the author of the target message will be listed. You will see `id`, `chat_name`, `user_name` and `msg_type` for each filter.
    * `id` is the unique ID for this filter. You need it to delete a filter
    * `chat_name` should be the name of current chat where you send the command.
    * `user_name` is the user whose message will be filtered
    * `msg_type` is type of messages to filter out. 
* `\msg_blocker del {id}`: Delete a filter with filter `id`.
* `\msg_blocker add {msg_type}`: Add filters. There are some ways to add filters.
    * `msg_type` is one of any `type` supported by **EFB** (including `Unsupported` type), so that all the messages in the specific type will be blocked. Check all of the supported types [here](https://ehforwarderbot.readthedocs.io/en/latest/API/constants.html#ehforwarderbot.constants.MsgType). For example `\msg_blocker add image` adds a filter to block all the image messages.
    * You cloud reply `\msg_blocker add image` to a message. **MessageBLocker** will get the author of the replied message, and only block image message from the author.
    * If you reply to a message with `\msg_blocker add`, without the `msg_type` argument, all the message from the author will be blocked.

