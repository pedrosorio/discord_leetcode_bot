import prediction_utils as pu
import discord_utils as du
from query_utils import QueryUtils
import time

def fetch_missing_users_for_contest(contest_name) -> None:
    print("fetching user results for contest", contest_name)
    qu = QueryUtils()
    leetcode_user_set = qu.get_leecode_user_set()
    print("set of leetcode users in DB", leetcode_user_set)
    inserted_user_set = set([up.username for up in qu.get_contest_performances(contest_name, skip_null_rank=False)])
    print("set of leetcode users already fetched", inserted_user_set)

    user_predictions = []
    for user in leetcode_user_set - inserted_user_set:
        print(user)
        up = pu.fetch_user_prediction(contest_name, user)
        user_predictions.append(up)
    print(user_predictions)
    if user_predictions:
        qu.insert_contest_performances(contest_name, user_predictions)
        qu.register_contest(contest_name)
        qu.commit()

def fetch_and_post_last_contest(send_message=True, redo_if_registered=False):
    contest_name = pu.get_last_contest_names()[0]
    qu = QueryUtils()
    if qu.is_contest_registered(contest_name):
        print("contest already registered")
        if not redo_if_registered:
            return False
    fetch_missing_users_for_contest(contest_name)
    all_user_predictions = qu.get_contest_performances(contest_name)
    leetcode_user_to_prediction = {
        up.username: up
        for up
        in all_user_predictions
    }

    for server_id, channel_id in qu.get_discord_servers_and_channels():
        server = du.get_guild(server_id)
        print("processing server:", server['name'])
        ct_users = 0
        server_list = []
        for discord_user_id, leetcode_username, discord_username in qu.get_server_users_with_discord_username(server_id):
            ct_users += 1
            print(discord_user_id, leetcode_username, discord_username)
            up = leetcode_user_to_prediction.get(leetcode_username)
            if up:
                server_list.append(pu.DiscordUserPrediction(discord_user_id=discord_user_id, **vars(up)))
        print(f"{len(server_list)} of {ct_users} from this server participated in the contest")
        if server_list:
            msg = pu.format_message_for_users(contest_name, server_list)
            print(msg)
            if send_message:
                du.post_message(msg, channel_id=channel_id)
                print("posted message to server")
    return True

while not fetch_and_post_last_contest():
    time.sleep(30)