import requests


def get_oauth(client_id, client_secret, grant_type='client_credentials'):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': grant_type
    }
    r = requests.post('https://id.twitch.tv/oauth2/token', data=data)
    return r.json()['access_token']

def validate_token(token) -> bool:
    try:
        r = requests.get('https://id.twitch.tv/oauth2/validate', headers={'Authorization': f'Bearer {token}'})
        r.raise_for_status()
        return True
    except requests.exceptions.HTTPError:
        return False