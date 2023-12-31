"""
As of 7-12-23, WHOOP's API uses the OAuth2.0 protocol, which is geared towards
apps that request WHOOP data on behalf of its users. It makes a lot of sense for
WHOOP because those are the type of projects they're expecting to support.

Unfortunately, this isn't ideal for personal projects such as this one. To access
our own data, we need to go through the three-step OAuth2.0 handshake, which is
what this script implements.

The resulting access tokens expire within an hour, so it's convenient to
periodically re-run this script during the course of development of the app.

"""
import os
import requests
import random
import json
from datetime import datetime, timedelta, timezone

from urllib.parse import parse_qs, urlparse


# logging.basicConfig(level=logging.DEBUG)

CLIENT_ID = os.environ["WHOOP_CLIENT_ID"]
CLIENT_SECRET = os.environ["WHOOP_CLIENT_SECRET"]
AUTHORIZATION_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_ENDPOINT = "https://api.prod.whoop.com/developer"
SLEEP_DATA_URL = "/v1/activity/sleep"
SCOPE = ["offline", "read:sleep", "read:workout", "read:recovery"]
REDIRECT_URL = "https://www.aamir.me/"

scope_string = " ".join(SCOPE)

# TODO: Check state key is correct when returned by Whoop

# Step 1: Request authorization code

# generate eight character state string
state = '%008x' % random.randrange(16**8)

# construct URL payload
payload = {
    "response_type":"code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URL,
    "scope": scope_string,
    "state": state

}
# url encode the payload data
payload_formatted = {key:requests.utils.quote(value, safe="") for (key,value) in payload.items()}

# convert the dictionary into a string - this is the payload
auth_payload = ""
for x,y in payload_formatted.items():
    auth_payload += f"{x}={y}&"
auth_payload = auth_payload[:-1]

# construct the full authorization URL with the payload
auth_url = f"{AUTHORIZATION_URL}?" + auth_payload

# prompt the user to enter the URL in the browser
print("\nGo to the following URL and grant access via Whoop:\n" + auth_url)

# prompt the user to enter the received authorization code (embedded in redirect URL payload)
auth_code_url = input("\nEnter the raw redirect link:\n")
print() 

# Extract authorization code from redirect URL
parsed_url = urlparse(auth_code_url)
query_params = parse_qs(parsed_url.query)
auth_code = query_params.get("code", [None])[0]

# Step 2: Request access token using authorization code

# Construct POST request payload
token_payload = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": scope_string,
    "redirect_uri": REDIRECT_URL
}
# url encode the payload data
token_payload_formatted = {key:requests.utils.quote(value, safe="") for (key,value) in token_payload.items()}

# convert the dictionary into a string - this is the payload
payload = ""
for x,y in token_payload_formatted.items():
    payload += f"{x}={y}&"
payload = payload[:-1]

# Since this is a POST request we're making from Python, we need to construct the header as well
headers = {"Content-Type": "application/x-www-form-urlencoded"}

# make the POST request to get the access token
r = requests.post(
    TOKEN_URL,
    headers=headers,
    data=payload,
)
response = r.json()
print("\nToken URL Response:\n", json.dumps(response, indent=2), "\n")
access_token = response["access_token"]
print("\nAccess token:", access_token)
print()

refresh_token = response["refresh_token"]
print("\nRefresh token:", refresh_token)
print()
