import json
import requests

DISCORD_BASE_URL = 'https://discord.com/api' 
DISCORD_MESSAGE_URL = DISCORD_BASE_URL + '/channels/{channel_id}/messages'
DISCORD_USER_URL = DISCORD_BASE_URL + '/users/{user_id}'

SECRETS = json.loads(open("SECRETS.txt").read())
TOKEN = SECRETS['TOKEN']
DISCORD_AUTH_HEADER = {'Authorization': f'Bot {TOKEN}'}

TEST_CHANNEL_ID = 1143698636929245254

def get_user(user_id):
    response = requests.get(url=DISCORD_USER_URL.format(user_id=user_id), headers=DISCORD_AUTH_HEADER)
    print(response.status_code)
    return json.loads(response.content.decode('utf-8'))

def post_message(message):
    response = requests.post(url=DISCORD_MESSAGE_URL.format(channel_id=TEST_CHANNEL_ID), headers=DISCORD_AUTH_HEADER, json={'content': message})
    print(response.status_code)
    print(response.content)
