from requests_oauthlib import OAuth2Session
import os

CLIENT_ID = os.environ["WHOOP_CLIENT_ID"]
CLIENT_SECRET = os.environ["WHOOP_CLIENT_SECRET"]
AUTHORIZATION_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
SLEEP_DATA_URL = "https://api.prod.whoop.com/developer/v1/activity/sleep"
SCOPE = ["read:sleep"]
REDIRECT_URL = "https://aamir.me/"

whoop_session = OAuth2Session(
    client_id=CLIENT_ID,
    redirect_uri=REDIRECT_URL,
    scope=SCOPE
)

authorization_url, state = whoop_session.authorization_url(
    url=AUTHORIZATION_URL
)

print(f'Please go to {authorization_url} to authorize access')

authorization_response = input('Enter the full callback URL: ')

token = whoop_session.fetch_token(
    token_url=TOKEN_URL,
    authorization_response=authorization_response,
    client_secret=CLIENT_SECRET
)

sleep_data = whoop_session.get(
    url=SLEEP_DATA_URL
)

print(sleep_data)
