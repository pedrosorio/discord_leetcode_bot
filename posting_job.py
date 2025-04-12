import prediction_utils as pu
import discord_utils as du
from query_utils import QueryUtils
import time
import sys

def fetch_missing_users_for_contest(contest_name) -> None:
    print("fetching user results for contest", contest_name)
    qu = QueryUtils()
    leetcode_user_set = qu.get_leecode_user_set()
    print("set of leetcode users in DB", leetcode_user_set)
    inserted_user_set = set([up.username for up in qu.get_contest_performances(contest_name, skip_null_rank=False)])
    print("set of leetcode users already fetched", inserted_user_set)

    user_predictions = []
    set_to_fetch = leetcode_user_set - inserted_user_set
    for i, user in enumerate(set_to_fetch):
        print(user, f"{i+1}/{len(set_to_fetch)}")
        up = pu.fetch_user_prediction(contest_name, user)
        user_predictions.append(up)
        sys.stdout.flush()
    print(user_predictions)
    if user_predictions:
        qu.insert_contest_performances(contest_name, user_predictions)
        qu.register_contest(contest_name)
        qu.commit()

DEFAULT_SUFFIX_MSG = "If you would like to join, type /register_leetcode_user in any channel on this discord server to add yourself to the list" 

def fetch_and_post_last_contest(send_message=True, redo_if_registered=False, fetch_missing_users=True) -> bool:
    print("send_message", send_message)
    print("redo_if_registered", redo_if_registered)
    print("fetch_missing_users", fetch_missing_users)
    try:
        contest_name = pu.get_last_contest_names()[0]
    except Exception as ex:
        print("failed to get latest contest", str(ex))
    qu = QueryUtils()
    if qu.is_contest_registered(contest_name):
        print("contest already registered")
        if not redo_if_registered:
            return False
    if fetch_missing_users:
        fetch_missing_users_for_contest(contest_name)
    all_user_predictions = qu.get_contest_performances(contest_name)
    leetcode_user_to_prediction = {
        up.username: up
        for up
        in all_user_predictions
    }

    for server_id, channel_id, custom_message in qu.get_discord_server_msg_config():
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
            msgs = pu.format_message_for_users(contest_name, server_list)
            msgs.append(custom_message or DEFAULT_SUFFIX_MSG)
            for msg in msgs:
                print(msg)
                if send_message:
                    du.post_message(msg, channel_id=channel_id)
                    print("posted message to server")
    return True

send_message = True 
redo_if_registered = False
fetch_missing_users = True
max_tries = 240 
if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) > 1:
        if sys.argv[1] == 'backfill':
            send_message = False
            redo_if_registered = True
        if sys.argv[1] == 'backfill_send':
            send_message = True
            redo_if_registered = True
        if sys.argv[1] == 'dry_run_no_fetch':
            send_message = False
            redo_if_registered = True 
            fetch_missing_users = False
    tries = 0
    while tries < max_tries and not fetch_and_post_last_contest(redo_if_registered=redo_if_registered, send_message=send_message, fetch_missing_users=fetch_missing_users):
        print(time.time())
        sys.stdout.flush()
        tries += 1
        time.sleep(30)
