import requests
import json

from firebase_functions import https_fn, scheduler_fn
from google.cloud import secretmanager

from firebase_admin import initialize_app

from helpers import whoop, notion

PROJECT_ID = "whoop-sleep-data"
WHOOP_CLIENT_ID_SECRET_NAME = "WHOOP_CLIENT_ID"
WHOOP_CLIENT_SECRET_SECRET_NAME = "WHOOP_CLIENT_SECRET"
WHOOP_ACCESS_TOKEN_SECRET_NAME = "WHOOP_ACCESS_TOKEN"
WHOOP_REFRESH_TOKEN_SECRET_NAME = "WHOOP_REFRESH_TOKEN"
NOTION_INTEGRATION_SECRET_SECRET_NAME = "NOTION_INTEGRATION_SECRET"
NOTION_DATABASE_ID_SECRET_NAME = "NOTION_DATABASE_ID"

initialize_app()

"""
This function receives Whoop webhook updates (ie sleep updated, workout updated).
Whoop's API will continually ping this webhook unless a 200 response is sent back quickly, so
this function triggers a pubsub job that triggers the other functions
"""
# TODO: retry in case of race condition with secrets being updated
# Potential TODO: If this function takes too long, Whoop may retry this webhook. Solution: Delegate work via pubsub
@https_fn.on_request()
def whoop_webhook(req: https_fn.Request) -> https_fn.Response:
    # get relevant secrets
    client = secretmanager.SecretManagerServiceClient()
    whoop_access_token_resource_name = client.secret_path(PROJECT_ID, WHOOP_ACCESS_TOKEN_SECRET_NAME) + "/versions/latest"
    whoop_client_secret_resource_name = client.secret_path(PROJECT_ID, WHOOP_CLIENT_SECRET_SECRET_NAME) + "/versions/latest"
    notion_integration_secret_resource_name = client.secret_path(PROJECT_ID, NOTION_INTEGRATION_SECRET_SECRET_NAME) + "/versions/latest"
    notion_database_id_resource_name = client.secret_path(PROJECT_ID, NOTION_DATABASE_ID_SECRET_NAME) + "/versions/latest"

    whoop_access_token = client.access_secret_version(request={"name": whoop_access_token_resource_name}).payload.data.decode("UTF-8")
    whoop_client_secret = client.access_secret_version(request={"name": whoop_client_secret_resource_name}).payload.data.decode("UTF-8")
    notion_integration_secret = client.access_secret_version(request={"name": notion_integration_secret_resource_name}).payload.data.decode("UTF-8")
    notion_database_id = client.access_secret_version(request={"name": notion_database_id_resource_name}).payload.data.decode("UTF-8")

    # check if client sent correct headers - otherwise, it's not Whoop
    # signature = req.headers["x-whoop-signature"]
    # timestamp = req.headers["x-whoop-signature-timestamp"]
    # if not whoop.verify_headers(whoop_client_secret, signature, timestamp, req.get_data()):
    #     print("Whoop webhook headers incorrect, ignoring request.")
    #     return

    # calculate and update stat in Notion
    type = req.json["type"]
    if "sleep" in type:
        avg_sleep_stat = whoop.calculate_sleep_stats(whoop_access_token)
        notion.update_stat(notion.STAT_TYPE.SLEEP, avg_sleep_stat, notion_integration_secret, notion_database_id)
    elif "workout" in type:
        zone_2_stat, zone_5_stat = whoop.calculate_workout_stats(whoop_access_token)
        notion.update_stat(notion.STAT_TYPE.ZONE_2, zone_2_stat, notion_integration_secret, notion_database_id)
        notion.update_stat(notion.STAT_TYPE.ZONE_5, zone_5_stat, notion_integration_secret, notion_database_id)

    return https_fn.Response("Successful")

# TODO: retry in case of race condition with secrets being updated
@https_fn.on_request()
@scheduler_fn.on_schedule(schedule="every day 23:37")
def reconcile_stats(event: scheduler_fn.ScheduledEvent) -> None:
    # use the access token to get and calculate relevant data
    client = secretmanager.SecretManagerServiceClient()
    whoop_access_token_resource_name = client.secret_path(PROJECT_ID, WHOOP_ACCESS_TOKEN_SECRET_NAME) + "/versions/latest"
    whoop_access_token = client.access_secret_version(request={"name": whoop_access_token_resource_name}).payload.data.decode("UTF-8")

    # calculate and update sleep stats in Notion
    avg_sleep_stat = whoop.calculate_sleep_stats(whoop_access_token)
    notion.update_stat(notion.STAT_TYPE.SLEEP, avg_sleep_stat)

    # calculate and update zone2/zone5 stats in Notion
    zone_2_stat, zone_5_stat = whoop.calculate_workout_stats(whoop_access_token)
    notion.update_stat(notion.STAT_TYPE.ZONE_2, zone_2_stat)
    notion.update_stat(notion.STAT_TYPE.ZONE_5, zone_5_stat)

"""
This function refreshes the whoop access and refres tokens
using the refresh token stored in the secrets manager
"""
@scheduler_fn.on_schedule(schedule="every 45 minutes")
def refresh_tokens(event: scheduler_fn.ScheduledEvent) -> None:
    
    client = secretmanager.SecretManagerServiceClient()

    # build resource names for secrets. 
    whoop_client_id_resource_name = client.secret_path(PROJECT_ID, WHOOP_CLIENT_ID_SECRET_NAME) + "/versions/latest"
    whoop_client_secret_resource_name = client.secret_path(PROJECT_ID, WHOOP_CLIENT_SECRET_SECRET_NAME) + "/versions/latest"
    whoop_refresh_token_resource_name = client.secret_path(PROJECT_ID, WHOOP_REFRESH_TOKEN_SECRET_NAME) + "/versions/latest"
    whoop_access_token_resource_name = client.secret_path(PROJECT_ID, WHOOP_ACCESS_TOKEN_SECRET_NAME) + "/versions/latest"

    # access necessary secrets
    whoop_client_id = client.access_secret_version(request={"name": whoop_client_id_resource_name}).payload.data.decode("UTF-8")

    whoop_client_secret = client.access_secret_version(request={"name": whoop_client_secret_resource_name}).payload.data.decode("UTF-8")

    whoop_refresh_token_response = client.access_secret_version(request={"name": whoop_refresh_token_resource_name})
    whoop_refresh_token = whoop_refresh_token_response.payload.data.decode("UTF-8")
    prior_whoop_refresh_token_version_name = whoop_refresh_token_response.name # will destroy this secret later

    whoop_access_token_response = client.access_secret_version(request={"name": whoop_access_token_resource_name})
    prior_whoop_access_token_version_name = whoop_access_token_response.name # will destroy this secret later

    # get new refresh/access tokens
    new_refresh_token, new_access_token = whoop.refresh_tokens(whoop_refresh_token, whoop_client_id, whoop_client_secret)

    # destroy previous secret versions to avoid billing cost
    print("destroying", prior_whoop_refresh_token_version_name)
    client.destroy_secret_version(request={"name": prior_whoop_refresh_token_version_name})
    print("destroying", prior_whoop_access_token_version_name)
    client.destroy_secret_version(request={"name": prior_whoop_access_token_version_name})

    # save access token and refresh token to secrets manager
    encoded_refresh_token = new_refresh_token.encode("UTF-8")
    encoded_access_token = new_access_token.encode("UTF-8")

    whoop_refresh_token_secret_name = client.secret_path(PROJECT_ID, WHOOP_REFRESH_TOKEN_SECRET_NAME)
    whoop_access_token_secret_name = client.secret_path(PROJECT_ID, WHOOP_ACCESS_TOKEN_SECRET_NAME)

    latest_refresh_token_version = client.add_secret_version( request={"parent": whoop_refresh_token_secret_name, "payload": {"data": encoded_refresh_token}})
    latest_access_token_version = client.add_secret_version( request={"parent": whoop_access_token_secret_name, "payload": {"data": encoded_access_token}})
    print("saved new refresh token in", latest_refresh_token_version.name)
    print("saved new access token in", latest_access_token_version.name)
