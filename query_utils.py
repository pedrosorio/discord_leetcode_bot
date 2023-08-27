import logging
import os
import sqlite3
import time
from typing import *

logging.basicConfig(filename='leetcode_discord_bot_flask.log', level=logging.INFO, format="%(asctime)s:%(message)s")

DEFAULT_DB_FILE = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 
    "instance", 
    "discord_leetcode_bot.sqlite")
print(DEFAULT_DB_FILE)

class QueryUtils:
    def __init__(self, conn=None):
        self.close_at_del = False
        if conn is None:
            conn = sqlite3.connect(DEFAULT_DB_FILE)
            self.close_at_del = True
        self.conn = conn

    def __del__(self):
        if self.close_at_del:
            self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def insert_or_update_discord_user(self, user_id, username):
        params = {
            'user_id': user_id,
            'username': username
        }
        self.conn.execute("""
            INSERT INTO 
                discord_users 
            VALUES(:user_id, :username)
            ON CONFLICT(discord_user_id) 
            DO UPDATE SET discord_username = :username
        """, params)

    def insert_or_update_server_user(self, server_id, discord_user_id, leetcode_username):
        params = {
            'server_id': server_id,
            'discord_user_id': discord_user_id,
            'leetcode_username': leetcode_username
        }
        self.conn.execute("""
            INSERT INTO 
                server_users 
            VALUES(:server_id, :discord_user_id, :leetcode_username)
            ON CONFLICT(server_id, discord_user_id)
            DO UPDATE SET leetcode_username = :leetcode_username
        """, params)

    def get_discord_username(self, user_id):
        params = {
            'user_id': user_id
        }
        res = self.conn.execute("SELECT discord_username FROM discord_users WHERE discord_user_id = :user_id", params)
        return [tup[0] for tup in res]
    
    def get_leetcode_username(self, server_id, user_id):
        params = {
            'server_id': server_id,
            'user_id': user_id
        }
        res = self.conn.execute("SELECT leetcode_username FROM server_users WHERE server_id = :server_id AND discord_user_id = :user_id", params)
        return [tup[0] for tup in res]
