import json
import requests

DISCORD_BASE_URL = 'https://discord.com/api' 
DISCORD_MESSAGES_URL = DISCORD_BASE_URL + '/channels/{channel_id}/messages'
DISCORD_MESSAGE_URL = DISCORD_MESSAGES_URL + '/{message_id}' 
DISCORD_USER_URL = DISCORD_BASE_URL + '/users/{id}'
DISCORD_CHANNEL_URL = DISCORD_BASE_URL + '/channels/{id}'
DISCORD_GUILD_URL = DISCORD_BASE_URL + '/guilds/{id}'


SECRETS = json.loads(open("SECRETS.txt").read())
TOKEN = SECRETS['TOKEN']
DISCORD_AUTH_HEADER = {'Authorization': f'Bot {TOKEN}'}

TEST_CHANNEL_ID = 1143698636929245254

EPHEMERAL_MSG_FLAG = 1<<6 # only the interacting user can see the message


def get_discord_resource(resource_url, resource_id):
    response = requests.get(url=resource_url.format(id=resource_id), headers=DISCORD_AUTH_HEADER)
    return json.loads(response.content.decode('utf-8'))

def get_user(user_id):
    return get_discord_resource(DISCORD_USER_URL, user_id)

def get_channel(channel_id):
    return get_discord_resource(DISCORD_CHANNEL_URL, channel_id)

def get_guild(guild_id):
    return get_discord_resource(DISCORD_GUILD_URL, guild_id)

def post_message(message, channel_id=TEST_CHANNEL_ID):
    response = requests.post(url=DISCORD_MESSAGES_URL.format(channel_id=channel_id), headers=DISCORD_AUTH_HEADER, json={'content': message})
    print(response.status_code)
    print(response.content)

def get_message(message_id, channel_id=TEST_CHANNEL_ID):
    response = requests.get(url=DISCORD_MESSAGE_URL.format(channel_id=channel_id, message_id=message_id), headers=DISCORD_AUTH_HEADER)
    print(response.status_code)
    return response.content

def edit_message(new_content, message_id, channel_id=TEST_CHANNEL_ID):
    response = requests.patch(url=DISCORD_MESSAGE_URL.format(channel_id=channel_id, message_id=message_id), headers=DISCORD_AUTH_HEADER, json={'content': new_content})
    print(response.status_code)
    return response.content

def delete_message(channel_id, message_id):
    response = requests.delete(url=DISCORD_MESSAGE_URL.format(channel_id=channel_id, message_id=message_id), headers=DISCORD_AUTH_HEADER)
    print(response.status_code)
    print(response.content)
