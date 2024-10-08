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
    return requests.delete(COMMAND_API_URL+f'/{cmd_id}', headers=DISCORD_AUTH_HEADER)

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

UNREGISTER_LEETCODE_USER_COMMAND = {
    "name": "unregister_leetcode_user",
    "type": 1,
    "description": "Remove association between user on a given discord server with a leetcode user",
    "options": []
}

ADMIN_UNREGISTER_LEETCODE_USER_COMMAND = {
    "name": "admin_unregister_leetcode_user",
    "type": 1,
    "description": "(Admin only) Remove association between user on a given discord server with a leetcode user",
    "default_member_permissions": "0",
    "options": [
        {
            "name": "leetcode_username",
            "description": "leetcode username of the user to remove",
            "type": 3,
            "required": True,
        }
    ]
}



if __name__ == '__main__':
    for cmd in get_cmd_list():
        delete_command(cmd['id'])

    for cmd in (
        REGISTER_LEETCODE_USER_COMMAND,
        UNREGISTER_LEETCODE_USER_COMMAND,
        ADMIN_UNREGISTER_LEETCODE_USER_COMMAND,
    ):
        register_command(cmd)



