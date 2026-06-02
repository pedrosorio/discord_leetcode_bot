import logging
import sys

logging.basicConfig(
    format="%(asctime)s %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level=logging.INFO,
    stream=sys.stdout,
)

import prediction_utils as pu
import discord_utils as du
from query_utils import QueryUtils
import time

log = logging.getLogger(__name__)


def fetch_missing_users_for_contest(contest_name) -> None:
    log.info("fetching user results for contest %s", contest_name)
    qu = QueryUtils()
    leetcode_user_set = qu.get_leecode_user_set()
    log.info("set of leetcode users in DB %s", leetcode_user_set)
    inserted_user_set = set([up.username for up in qu.get_contest_performances(contest_name, skip_null_rank=False)])
    log.info("set of leetcode users already fetched %s", inserted_user_set)

    set_to_fetch = leetcode_user_set - inserted_user_set
    if not set_to_fetch:
        return
    log.info("fetching predictions for %d users: %s", len(set_to_fetch), set_to_fetch)
    user_predictions = list(pu.fetch_users_for_contest(contest_name, set_to_fetch).values())
    sys.stdout.flush()
    log.info("%s", user_predictions)
    if user_predictions:
        qu.insert_contest_performances(contest_name, user_predictions)
        qu.register_contest(contest_name)
        qu.commit()

DEFAULT_SUFFIX_MSG = "If you would like to join, type /register_leetcode_user in any channel on this discord server to add yourself to the list"

def fetch_and_post_last_contest(send_message=True, redo_if_registered=False, fetch_missing_users=True) -> bool:
    log.info("send_message %s", send_message)
    log.info("redo_if_registered %s", redo_if_registered)
    log.info("fetch_missing_users %s", fetch_missing_users)
    try:
        contest_name = pu.get_last_contest_names()[0]
    except Exception as ex:
        log.info("failed to get latest contest %s", str(ex))
        return False
    qu = QueryUtils()
    if qu.is_contest_registered(contest_name):
        log.info("contest already registered")
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
        if 'name' not in server:
            log.info("skipping server %s: guild lookup failed %s", server_id, server)
            continue
        log.info("processing server: %s", server['name'])
        ct_users = 0
        server_list = []
        for discord_user_id, leetcode_username, discord_username in qu.get_server_users_with_discord_username(server_id):
            ct_users += 1
            log.info("%s %s %s", discord_user_id, leetcode_username, discord_username)
            up = leetcode_user_to_prediction.get(leetcode_username)
            if up and up.new_rating is not None and up.delta_rating is not None:
                server_list.append(pu.DiscordUserPrediction(discord_user_id=discord_user_id, **vars(up)))
        log.info("%d of %d from this server participated in the contest", len(server_list), ct_users)
        if server_list:
            msgs = pu.format_message_for_users(contest_name, server_list)
            msgs.append(custom_message or DEFAULT_SUFFIX_MSG)
            for msg in msgs:
                log.info("%s", msg)
                if send_message:
                    du.post_message(msg, channel_id=channel_id)
                    log.info("posted message to server")
    return True

send_message = True
redo_if_registered = False
fetch_missing_users = True
max_tries = 240
if __name__ == "__main__":
    log.info("%s", sys.argv)
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
        log.info("%s", time.time())
        sys.stdout.flush()
        tries += 1
        time.sleep(30)
