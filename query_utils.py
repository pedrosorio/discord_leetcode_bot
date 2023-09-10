import logging
import os
import sqlite3
import time
from typing import *
import prediction_utils as pu

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
            conn.row_factory = sqlite3.Row
            self.close_at_del = True
        self.conn = conn

    def __del__(self):
        if self.close_at_del:
            self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def get_discord_servers_and_channels(self):
        res = self.conn.execute("SELECT server_id, channel_id FROM server_to_channel")
        return [list(tup) for tup in res]
    
    def get_all_discord_user_ids(self):
        res = self.conn.execute("SELECT discord_user_id from discord_users")
        return [tup[0] for tup in res]

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

    def delete_discord_user(self, user_id):
        self.conn.execute("DELETE FROM discord_users WHERE discord_user_id = :user_id", {'user_id': user_id})

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

    def delete_server_user(self, server_id, discord_user_id):
        params = {
            'server_id': server_id,
            'discord_user_id': discord_user_id
        }
        self.conn.execute("""
            DELETE FROM
                server_users
            WHERE
                server_id = :server_id
                AND discord_user_id = :discord_user_id
        """, params)

    def count_user_servers(self, discord_user_id):
        params = {
            'discord_user_id': discord_user_id
        }
        res = self.conn.execute("SELECT server_id FROM server_users WHERE discord_user_id = :discord_user_id", params)
        return len([tup for tup in res]) 

    def get_server_users_with_discord_username(self, server_id):
        params = {
            'server_id': server_id
        }
        return self.conn.execute("""
            SELECT
                su.discord_user_id,
                su.leetcode_username,
                du.discord_username
            FROM discord_users du
            JOIN server_users su
            ON (su.server_id = :server_id AND su.discord_user_id = du.discord_user_id)
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
    
    def get_leecode_user_set(self) -> Set[str]:
        res = self.conn.execute("SELECT DISTINCT leetcode_username FROM server_users")
        return set([tup[0] for tup in res])
    
    def register_contest(self, contest_name):
        timestamp = int(time.time())
        params = {'timestamp': timestamp, 'contest_name': contest_name}
        self.conn.execute("INSERT OR IGNORE into contests VALUES (:contest_name, :timestamp)", params)
    
    def is_contest_registered(self, contest_name):
        res = self.conn.execute("SELECT * FROM contests WHERE contest_name = :contest_name", {'contest_name': contest_name})
        return len(res.fetchall()) > 0
    
    def insert_contest_performances(self, contest_name: str, users_predictions: List[pu.FullUserPrediction]):
        values = [
            (
                contest_name,
                up.username,
                up.rank,
                up.new_rating,
                up.delta_rating,
                up.country_code
            )
            for up in users_predictions
        ]
        self.conn.executemany("INSERT OR IGNORE INTO contest_performances VALUES (?, ?, ?, ?, ?, ?)", values)
    
    def get_contest_performances(self, contest_name: str, skip_null_rank: bool = True) -> List[pu.FullUserPrediction]:
        params = {'contest_name': contest_name}
        res = self.conn.execute("""
            SELECT 
                leetcode_username as username,
                rank,
                new_rating,
                delta_rating,
                country_code
            FROM
                contest_performances
            WHERE
                contest_name = :contest_name
        """ + ("AND rank IS NOT NULL" if skip_null_rank else ""), params)
        lst = [dict(row) for row in res.fetchall()]
        print(lst)
        return [pu.FullUserPrediction(**dc) for dc in lst]

