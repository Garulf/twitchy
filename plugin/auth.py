import requests

def validate_token(token) -> bool:
    try:
        r = requests.get('https://id.twitch.tv/oauth2/validate', headers={'Authorization': f'Bearer {token}'})
        r.raise_for_status()
        return True
    except requests.exceptions.HTTPError:
        return False