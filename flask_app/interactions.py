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
            msg = "user already in db for different discord, assigned leetcode username for this discord server"
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

    # Handle discord ping
    if request.json["type"] == 1:
        return {"type": 1}

    # Handle slash commands 
    if request.json["type"] == 2:
        data = request.json["data"]
        if data["name"] == "register_leetcode_user":
            return handle_register_user(request.json)
        return  {"type": 4, "data": {"content": "Unknown command"}}

        


    
@bp.route('/for-fun', methods=['GET'])
def for_fun():
    return "for fun"


