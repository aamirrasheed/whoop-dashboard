"""
This script allows the user to test the Google Secret Manager. You'll need to 
install the gcloud cli to use this file correctly. See the root directory's
README.md for more info.
"""

import requests
from google.cloud import secretmanager

SCOPES = "offline read:sleep read:recovery read:workout"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
PROJECT_ID = "whoop-sleep-data"
WHOOP_CLIENT_ID_SECRET_NAME = "WHOOP_CLIENT_ID"
WHOOP_CLIENT_SECRET_SECRET_NAME = "WHOOP_CLIENT_SECRET"
WHOOP_ACCESS_TOKEN_SECRET_NAME = "WHOOP_ACCESS_TOKEN"
WHOOP_REFRESH_TOKEN_SECRET_NAME = "WHOOP_REFRESH_TOKEN"
VERSION_ID = "latest"

client = secretmanager.SecretManagerServiceClient()

# build resource names for secrets. TODO: Ensure that these are fully qualified path names
whoop_client_id_resource_name = client.secret_path(PROJECT_ID, WHOOP_CLIENT_ID_SECRET_NAME) + "/versions/latest"
whoop_client_secret_resource_name = client.secret_path(PROJECT_ID, WHOOP_CLIENT_SECRET_SECRET_NAME) + "/versions/latest"
whoop_refresh_token_resource_name = client.secret_path(PROJECT_ID, WHOOP_REFRESH_TOKEN_SECRET_NAME) + "/versions/latest"
whoop_access_token_resource_name = client.secret_path(PROJECT_ID, WHOOP_ACCESS_TOKEN_SECRET_NAME) + "/versions/latest"

# access necessary secrets for Whoop API
whoop_client_id = client.access_secret_version(request={"name": whoop_client_id_resource_name}).payload.data.decode("UTF-8")

whoop_client_secret = client.access_secret_version(request={"name": whoop_client_secret_resource_name}).payload.data.decode("UTF-8")

whoop_refresh_token_response = client.access_secret_version(request={"name": whoop_refresh_token_resource_name})
whoop_refresh_token = whoop_refresh_token_response.payload.data.decode("UTF-8")
prior_whoop_refresh_token_version_name = whoop_refresh_token_response.name # will destroy this later

whoop_access_token_response = client.access_secret_version(request={"name": whoop_access_token_resource_name})
whoop_access_token = whoop_access_token_response.payload.data.decode("UTF-8")
prior_whoop_access_token_version_name = whoop_access_token_response.name # will destroy this later

# construct payload to request new access token
payload_dict = {
    "grant_type": "refresh_token",
    "refresh_token": f'{whoop_refresh_token}',
    "client_id": f'{whoop_client_id}',
    "client_secret": f'{whoop_client_secret}',
    "scope": SCOPES,
}

# prepare & send request for new access & refresh tokens
payload = {key:requests.utils.quote(value, safe="") for (key,value) in payload_dict.items()}
headers = {"Content-Type": "application/x-www-form-urlencoded"}
r = requests.post(
    WHOOP_TOKEN_URL,
    headers=headers,
    data=payload,
)
r.raise_for_status()
response = r.json()
print("Old refresh token:", whoop_refresh_token)
print("New refresh token:", response["refresh_token"])
print("Old access token:", whoop_access_token)
print("New access token:", response["access_token"])

# save access token and refresh token to secrets manager
encoded_refresh_token = response["refresh_token"].encode("UTF-8")
encoded_access_token = response["access_token"].encode("UTF-8")

whoop_refresh_token_secret_name = f"projects/{PROJECT_ID}/secrets/{WHOOP_REFRESH_TOKEN_SECRET_NAME}",
whoop_access_token_secret_name = f"projects/{PROJECT_ID}/secrets/{WHOOP_ACCESS_TOKEN_SECRET_NAME}"

whoop_refresh_token_secret_name = client.secret_path(PROJECT_ID, WHOOP_REFRESH_TOKEN_SECRET_NAME)
whoop_access_token_secret_name = client.secret_path(PROJECT_ID, WHOOP_ACCESS_TOKEN_SECRET_NAME)

latest_refresh_token_version = client.add_secret_version( request={"parent": whoop_refresh_token_secret_name, "payload": {"data": encoded_refresh_token}})
latest_access_token_version = client.add_secret_version( request={"parent": whoop_access_token_secret_name, "payload": {"data": encoded_access_token}})
print("latest refresh token secret name", latest_refresh_token_version.name)
print("latest access token secret name", latest_access_token_version.name)

# destroy previous secret versions to avoid billing cost
print("destroying", prior_whoop_refresh_token_version_name)
client.destroy_secret_version(request={"name": prior_whoop_refresh_token_version_name})
print("destroying", prior_whoop_access_token_version_name)
client.destroy_secret_version(request={"name": prior_whoop_access_token_version_name})

