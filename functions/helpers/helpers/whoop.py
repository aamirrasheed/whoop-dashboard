import requests
import base64
import hmac
import hashlib
import json
from datetime import datetime, timezone, time, timedelta

SCOPES = "offline read:sleep read:recovery read:workout"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
AUTHORIZATION_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_API_ENDPOINT = "https://api.prod.whoop.com/developer"
SLEEP_URL = "/v1/activity/sleep"
WORKOUT_URL = "/v1/activity/workout"
SLEEP_DAYS_FOR_AVERAGE = 10
WORKOUT_DAYS_FOR_TOTAL = 7

"""
Function that gets and calculates zone 2 and zone 5 total mins over the last week
"""
def calculate_workout_stats(access_token: str) -> tuple[float, float]:
    # the last week's worth of data
    start_date_utc = datetime.combine(datetime.now(timezone.utc), time.min) - timedelta(WORKOUT_DAYS_FOR_TOTAL)
    start_date_z = start_date_utc.isoformat() + 'Z'
    workout_query_params = {
        "limit": "25",
        "start": start_date_z
    }

    # get workout data
    workouts_endpoint = _add_params_to_url(WHOOP_API_ENDPOINT + WORKOUT_URL, workout_query_params)
    response = requests.get(workouts_endpoint, headers=_get_request_header(access_token))
    response.raise_for_status()
    data = response.json()

    # calculate total zone 2 minutes
    zone_2_millis = [x["score"]["zone_duration"]["zone_two_milli"] for x in data["records"]]
    total_zone_2_mins = sum(zone_2_millis) / 1000 / 60
    total_zone_2_rounded = int(round(total_zone_2_mins, 0))

    # calculate total zone 5 minutes
    zone_5_millis = [x["score"]["zone_duration"]["zone_five_milli"] for x in data["records"]]
    total_zone_5_mins = sum(zone_5_millis) / 1000 / 60
    total_zone_5_rounded = int(round(total_zone_5_mins, 0))

    print("total zone 2 mins over last 7 days:", total_zone_2_rounded)
    print("total zone 5 mins over last 7 days:", total_zone_5_rounded)
    return (total_zone_2_rounded, total_zone_5_rounded)

"""
Function that gets and calculates sleep average over the last ten days
"""
def calculate_sleep_stats(access_token: str) -> float:
    # last 10 nights of sleep
    start_date_utc = datetime.combine(datetime.now(timezone.utc), time.min) - timedelta(SLEEP_DAYS_FOR_AVERAGE - 1)
    start_date_z = start_date_utc.isoformat() + 'Z'
    sleep_query_params = {
        "limit": "25",
        "start": start_date_z
    }

    # get sleep data
    sleeps_endpoint = _add_params_to_url(WHOOP_API_ENDPOINT + SLEEP_URL, sleep_query_params)
    response = requests.get(sleeps_endpoint, headers=_get_request_header(access_token))
    response.raise_for_status()
    data = response.json()

    # calculate average sleep excluding naps
    sleep_times = [x["score"]["stage_summary"]["total_in_bed_time_milli"] for x in data["records"] if not x["nap"]]
    total_sleep_hrs = sum(sleep_times) / 1000 / 60 / 60
    avg_sleep = total_sleep_hrs / SLEEP_DAYS_FOR_AVERAGE
    avg_sleep_rounded = round(avg_sleep, 2)

    print(f"avg sleep over the last {SLEEP_DAYS_FOR_AVERAGE} days:", avg_sleep_rounded)
    return avg_sleep_rounded

"""
Function that validates the headers to the webhook. Help blocks non-Whoop callers to webhook.
"""
def verify_headers(client_secret: str, signature: str, timestamp: str, body: str) -> bool:
    computed_signature = base64.b64encode(
        hmac.new(
            client_secret.encode("utf-8"),
            f"{timestamp}{body}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    return computed_signature == signature

"""
Calls Whoop's token API to refresh access tokens
"""
def refresh_tokens(refresh_token: str, client_id: str, client_secret: str) -> tuple[str, str]:
    # construct payload to request new access token
    payload_dict = {
        "grant_type": "refresh_token",
        "refresh_token": f'{refresh_token}',
        "client_id": f'{client_id}',
        "client_secret": f'{client_secret}',
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
    return response["refresh_token"], response["access_token"]

"""
Helper method to URL encode args to an HTTP endpoing
"""
def _add_params_to_url(url: str, params: dict=None) -> str:
    if params is None:
      return url
    
    # takes args and converts them to URL format
    values_formatted = {key:requests.utils.quote(value, safe="") for (key,value) in params.items()}

    # construct the final URL
    url_payload = ""
    for x,y in values_formatted.items():
        url_payload += f"{x}={y}&"
    formatted_payload = url_payload[:-1]
    return url + "?" + formatted_payload

"""
Helper method that creates the header for GET requests to the WHOOP API
"""
def _get_request_header(access_token: str):
    return {
        "Authorization": f"Bearer {access_token}",
    }