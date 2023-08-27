import json
import requests

DISCORD_BASE_URL = 'https://discord.com/api' 
SECRETS = json.loads(open('SECRETS.txt').read())
APPLICATION_ID = SECRETS['APPLICATION_ID']
TOKEN = SECRETS['TOKEN']
DISCORD_AUTH_HEADER = {'Authorization': f'Bot {TOKEN}'}

COMMAND_API_URL = DISCORD_BASE_URL + f'/applications/{APPLICATION_ID}/commands'

def register_command(cmd_json):
    response = requests.post(COMMAND_API_URL, headers=DISCORD_AUTH_HEADER, json=cmd_json)

    print(response.status_code)
    print(response.content)

def delete_command(cmd_id):
    requests.delete(COMMAND_API_URL+f'/{cmd_id}')

def get_cmd_list():
    response = requests.get(COMMAND_API_URL, headers=DISCORD_AUTH_HEADER)
    print(response.status_code)
    print(response.content)
    return json.loads(response.content.decode('utf-8'))

REGISTER_LEETCODE_USER_COMMAND = {
    "name": "register_leetcode_user",
    "type": 1,
    "description": "Associate a user on a given discord server with a leetcode user",
    "options": [
        {
            "name": "leetcode_username",
            "description": "self-explanatory",
            "type": 3,
            "required": True,
        }
    ]
}

for cmd in get_cmd_list():
    delete_command(cmd['id'])

for cmd in (
    REGISTER_LEETCODE_USER_COMMAND,
):
    register_command(cmd)



