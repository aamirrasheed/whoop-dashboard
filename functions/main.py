import requests
import json

from firebase_functions import https_fn, scheduler_fn, pubsub_fn
from google.cloud import secretmanager, pubsub

from firebase_admin import initialize_app


SCOPES = "offline read:sleep read:recovery read:workout"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
PROJECT_ID = "whoop-sleep-data"
WHOOP_CLIENT_ID_SECRET_NAME = "WHOOP_CLIENT_ID"
WHOOP_CLIENT_SECRET_SECRET_NAME = "WHOOP_CLIENT_SECRET"
WHOOP_ACCESS_TOKEN_SECRET_NAME = "WHOOP_ACCESS_TOKEN"
WHOOP_REFRESH_TOKEN_SECRET_NAME = "WHOOP_REFRESH_TOKEN"
VERSION_ID = "latest"
PUBSUB_TOPIC_NAME = "whoop-webhook"

initialize_app()
initialize_app()

@https_fn.on_request()
def whoop_webhook(req: https_fn.Request) -> https_fn.Response:
  # TODO: check that the headers for this request are correct with the client secret, otherwise reject: https://developer.whoop.com/docs/developing/webhooks/#webhooks-security
  req_body = req.json 

  # trigger update_data() via pub/sub
  publisher = pubsub.PublisherClient()
  message_data = {
    'id': req_body["id"],
    'type': req_body["type"]
  }

  # Convert the message data to JSON string
  message_data_str = json.dumps(message_data)

  # Convert the message data string to bytes
  message_data_bytes = message_data_str.encode('utf-8')

  # Publish the message
  topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC_NAME)
  message_future = publisher.publish(topic_path, data=message_data_bytes)
  message_future.result()

  return https_fn.Response("Pubsub message sent")

# may need to retry in order to do it successfully, incase of race condition with secrets being updated
@pubsub_fn.on_message_published(topic="whoop-webhook")
def update_data(event: pubsub_fn.CloudEvent[pubsub_fn.MessagePublishedData]):
  # Get the `name` attribute of the PubSub message JSON body.
  try:
      data = event.data.message.json
  except ValueError:
      print("PubSub message was not JSON")
      return
  if data is None:
      return
  if "id" not in data:
      print("No 'id' key")
      return
  if "type" not in data:
      print("No 'type' key")
      return
  id = data["id"]
  type = data["type"]
  print("received data from pubsub topic whoop-webhook:", id, type)

  # use the access token to GET relevant data

  # calculate data

  # update Notion page

# We also need a function that regularly refreshes access tokens every 45 minutes or so
@scheduler_fn.on_schedule(schedule="*/45 * * * *")
def refresh_access_tokens(event: scheduler_fn.ScheduledEvent) -> None:
    
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
  prior_whoop_refresh_token_version_name = whoop_refresh_token_response.name # will destroy this later

  whoop_access_token_response = client.access_secret_version(request={"name": whoop_access_token_resource_name})
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

  # save access token and refresh token to secrets manager
  encoded_refresh_token = response["refresh_token"].encode("UTF-8")
  encoded_access_token = response["access_token"].encode("UTF-8")

  whoop_refresh_token_secret_name = client.secret_path(PROJECT_ID, WHOOP_REFRESH_TOKEN_SECRET_NAME)
  whoop_access_token_secret_name = client.secret_path(PROJECT_ID, WHOOP_ACCESS_TOKEN_SECRET_NAME)

  latest_refresh_token_version = client.add_secret_version( request={"parent": whoop_refresh_token_secret_name, "payload": {"data": encoded_refresh_token}})
  latest_access_token_version = client.add_secret_version( request={"parent": whoop_access_token_secret_name, "payload": {"data": encoded_access_token}})
  print("created", latest_refresh_token_version.name)
  print("created", latest_access_token_version.name)

  # destroy previous secret versions to avoid billing cost
  print("destroying", prior_whoop_refresh_token_version_name)
  client.destroy_secret_version(request={"name": prior_whoop_refresh_token_version_name})
  print("destroying", prior_whoop_access_token_version_name)
  client.destroy_secret_version(request={"name": prior_whoop_access_token_version_name})

# A reconciliation function that runs once a day at 11am to ensure that  data for the last 10 days is correct
# @scheduler_fn.on_schedule("every day 11:00")
# def reconcile_data(event: scheduler_fn.ScheduledEvent) -> None:
#     pass