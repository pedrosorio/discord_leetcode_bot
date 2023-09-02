import prediction_utils as pu
import discord_utils as du
from query_utils import QueryUtils

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

def update_all_discord_usernames_in_db(qu: QueryUtils):
    for user_id in qu.get_all_discord_user_ids():
        user = du.get_user(user_id)
        username=user['global_name'] if user['global_name'] else user['username']
        qu.insert_or_update_discord_user(
            user_id=user_id,
            username=username
        )

def fetch_and_post_last_contest(send_message=False, redo_if_registered=True):
    contest_name = pu.get_last_contest_names()[0]
    qu = QueryUtils()
    if qu.is_contest_registered(contest_name):
        print("contest already registered")
        if not redo_if_registered:
            return 
    fetch_missing_users_for_contest(contest_name)
    user_predictions = qu.get_contest_performances(contest_name)
    leetcode_user_to_prediction = {
        up.username: up
        for up
        in user_predictions
    }

    # before sending messages, make sure discord usernames are updated (users can change their display names) 
    print("updating discord user names")
    update_all_discord_usernames_in_db(qu)

    for server_id, channel_id in qu.get_discord_servers_and_channels():
        server = du.get_guild(server_id)
        print("processing server:", server['name'])
        ct_users = 0
        up_list = []
        for discord_user_id, leetcode_username, discord_username in qu.get_server_users_with_discord_username(server_id):
            ct_users += 1
            up = leetcode_user_to_prediction.get(leetcode_username)
            if up:
                up.username = discord_username
                up_list.append(up)
        print(f"{len(up_list)} of {ct_users} from this server participated in the contest")
        if up_list:
            msg = pu.format_message_for_users(contest_name, user_predictions)
            print(msg)
            if send_message:
                du.post_message(msg, channel_id=channel_id)
                print("posted message to server")


fetch_and_post_last_contest()