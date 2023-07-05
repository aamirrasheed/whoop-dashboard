import requests
import os

from firebase_functions import https_fn, scheduler_fn
from firebase_functions.params import SecretParam
from google.cloud import secretmanager

from firebase_admin import initialize_app


SCOPES = "offline read:sleep read:recovery read:workout"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
PROJECT_ID = "whoop-sleep-data"
WHOOP_CLIENT_ID_SECRET_NAME = "WHOOP_CLIENT_ID"
WHOOP_CLIENT_SECRET_SECRET_NAME = "WHOOP_CLIENT_SECRET"
WHOOP_ACCESS_TOKEN_SECRET_NAME = "WHOOP_ACCESS_TOKEN"
WHOOP_REFRESH_TOKEN_SECRET_NAME = "WHOOP_REFRESH_TOKEN"
VERSION_ID = "latest"

initialize_app()
# TODO: Need to handle when refresh_access_tokens is running at the same time as whoop_webhook
# see this for help: https://stackoverflow.com/questions/49290380/how-do-you-avoid-a-possible-race-condition-with-firebase-cloud-functions
@https_fn.on_request()
def whoop_webhook(req: https_fn.Request) -> https_fn.Response:
    # check that the headers for this request are correct with the client secret, otherwise reject

    # use the access token located in secrets to GET sleep data within the last hour

    # record sleep, workout, or recovery to Realtime Database

    # update Notion page

    # return status 200

    original = req.args.get("text")
    if original is None:
        return https_fn.Response("No text parameter provided", status=400)

    return https_fn.Response(f"Hello world! Parameter = {original}")

# We also need a function that regularly refreshes access tokens every 45 minutes or so
# TODO: Schedule function every 45 mins instead
@scheduler_fn.on_schedule("every 2 minutes")
def refresh_access_tokens(event: scheduler_fn.ScheduledEvent) -> None:
    
    client = secretmanager.SecretManagerServiceClient()

    # build resource names for secrets
    whoop_client_id_secret_string = client.secret_path(PROJECT_ID, "WHOOP_CLIENT_ID")
    whoop_client_secret_secret_string = client.secret_path(PROJECT_ID, "WHOOP_CLIENT_SECRET")
    whoop_refresh_token_secret_string = client.secret_path(PROJECT_ID, "WHOOP_REFRESH_TOKEN")
    whoop_access_token_secret_string = client.secret_path(PROJECT_ID, "WHOOP_ACCESS_TOKEN")

    # get secrets for making the request to Whoop
    whoop_client_id = client.access_secret_version(request={"name": whoop_client_id_secret_string})
    whoop_client_secret = client.access_secret_version(request={"name": whoop_client_secret_secret_string})
    whoop_refresh_token = client.access_secret_version(request={"name": whoop_refresh_token_secret_string})

    # construct payload to request new access token
    payload_dict = {
        "grant_type": "refresh_token",
        "refresh_token": f'{whoop_refresh_token}',
        "client_id": f'{whoop_client_id}',
        "client_secret": f'{whoop_client_secret}',
        "scope": SCOPES,
    }

    # prepare and send request
    payload = {key:requests.utils.quote(value, safe="") for (key,value) in payload_dict.items()}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(
        WHOOP_TOKEN_URL,
        headers=headers,
        data=payload,
    )
    r.raise_for_status()
    response = r.json()

    # save access token and refresh token to secrets manager

    # destroy previous secrets to avoid incurring cost on them

    pass

# A reconciliation function that runs once a day at 11am to ensure that  data for the last 10 days is correct
# @scheduler_fn.on_schedule("every day 11:00")
# def reconcile_data(event: scheduler_fn.ScheduledEvent) -> None:
#     pass