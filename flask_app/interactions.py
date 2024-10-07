from flask import (
    Blueprint, request
)
from flask_app.db import get_db
from discord_utils import get_user, EPHEMERAL_MSG_FLAG
from query_utils import QueryUtils
import json
import logging 

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# found in the application page in the Developer Portal
PUBLIC_KEY = json.loads(open('SECRETS.txt').read())['PUBLIC_KEY']

VERIFY_KEY = VerifyKey(bytes.fromhex(PUBLIC_KEY))

# from flask_app.db import get_db

bp = Blueprint('interactions', __name__)

def handle_register_user(request_json):
    qu = QueryUtils(get_db())
    user_id=request_json['member']['user']['id']
    user_in_db = qu.get_discord_username(user_id)
    if user_in_db:
        username = user_in_db[0]
    else:
        user = get_user(user_id)
        username=user['global_name'] if user['global_name'] else user['username']
        qu.insert_or_update_discord_user(
            user_id=user_id,
            username=username
        )
    server_id = request_json['guild_id']
    leetcode_in_db = qu.get_leetcode_username(server_id, user_id)
    new_leetcode_username = request_json['data']['options'][0]['value']
    logging.info([server_id, username, new_leetcode_username])
    discord_user_id = qu.get_discord_user_in_server_with_leetcode_username(server_id, new_leetcode_username)
    if discord_user_id and int(discord_user_id[0]) != int(user_id):
        msg = 'Another discord user has registered that leetcode username already. If the other discord account belongs to you, you can use command /unregister_leetcode_user to remove that association before linking it with this account. If you do not have access to that account you can reach out to owner of this discord server to ask them to remove the association.'
    else:
        qu.insert_or_update_server_user(
            server_id=server_id,
            discord_user_id=user_id,
            leetcode_username=new_leetcode_username
        )
        qu.commit()
        msg = "new user registered"
        if user_in_db:
            if leetcode_in_db:
                if new_leetcode_username == leetcode_in_db[0]:
                    msg = "this is your leetcode username on this discord server already"
                else:
                    msg = "leetcode username updated for this discord server" 
            else:
                msg = "user already in db for different discord server, assigned leetcode username for this discord server"
    logging.info(msg)
    return {
        "type": 4,
        "data": {"content": msg, "flags": EPHEMERAL_MSG_FLAG}
    }

def delete_discord_user_in_server(server_id: int, user_id: int, qu: QueryUtils) -> int:
    # removes discord user association with leetcode name from server
    # if user has no other discord servers, remove it from the discord DB altogether
    # returns number of servers the user is still registered in
    qu.delete_server_user(server_id, user_id)
    ct_servers_left = qu.count_user_servers(user_id)
    logging.info(f"deleted user now only in {ct_servers_left}")
    if ct_servers_left == 0:
        qu.delete_discord_user(user_id)
    qu.commit()
    return ct_servers_left

def handle_unregister_user(request_json):
    qu = QueryUtils(get_db())
    user_id=request_json['member']['user']['id']
    server_id = request_json['guild_id']
    leetcode_in_db = qu.get_leetcode_username(server_id, user_id)
    if leetcode_in_db:
        ct_servers_left = delete_discord_user_in_server(server_id, user_id, qu)
        msg = f"Successfully unregistered your association with leetcode user '{leetcode_in_db[0]}' from this server."
        if ct_servers_left > 0:
            msg += f" Your discord user is still registered in {ct_servers_left} other discord servers."
    else:
        msg = "Your user is not registered with the bot in this server"

    logging.info(msg)

    return {
        "type": 4,
        "data": {"content": msg, "flags": EPHEMERAL_MSG_FLAG}
    }

def handle_admin_unregister_user(request_json):
    qu = QueryUtils(get_db())
    server_id = request_json['guild_id']
    leetcode_username = request_json['data']['options'][0]['value']
    discord_user_ids = qu.get_discord_user_in_server_with_leetcode_username(server_id, leetcode_username)
    if not discord_user_ids:
        msg = f"No user found with leetcode username '{leetcode_username}' in this server"
    else:
        if len(discord_user_ids) > 1:
            discord_usernames = []
            for discord_user_id in discord_user_ids:
                discord_usernames.append(qu.get_discord_username(discord_user_id)[0])
            msg = f"Found multiple users with leetcode username '{leetcode_username}' in this server: {', '.join(discord_usernames)}\nThis should not be possible. Skipping removal to avoid unregistering the wrong user."
        else:
            discord_username = qu.get_discord_username(discord_user_ids[0])[0]
            delete_discord_user_in_server(server_id, discord_user_ids[0], qu)
            msg = f"Successfully unregistered leetcode user '{leetcode_username}' ({discord_username}) from this server."

    logging.info(msg)

    return {
        "type": 4,
        "data": {"content": msg, "flags": EPHEMERAL_MSG_FLAG}
    }

@bp.route('/interactions', methods=['POST'])
def interactions():
    signature = request.headers["X-Signature-Ed25519"]
    timestamp = request.headers["X-Signature-Timestamp"]
    body = request.data.decode("utf-8")

    try:
        VERIFY_KEY.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
    except BadSignatureError:
        return "invalid request signature", 401
    
    logging.info(request.json)

    # Handle discord ping
    if request.json["type"] == 1:
        return {"type": 1}

    # Handle slash commands 
    if request.json["type"] == 2:
        data = request.json["data"]
        if data["name"] == "register_leetcode_user":
            return handle_register_user(request.json)
        if data["name"] == "unregister_leetcode_user":
            return handle_unregister_user(request.json)
        if data["name"] == "admin_unregister_leetcode_user":
            return handle_admin_unregister_user(request.json)
        return  {"type": 4, "data": {"content": "Unknown command"}}

        


    
@bp.route('/for-fun', methods=['GET'])
def for_fun():
    return "for fun"


