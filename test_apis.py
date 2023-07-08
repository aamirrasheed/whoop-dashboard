import os
import requests
import json
from datetime import datetime, timezone, timedelta, time

AUTHORIZATION_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_API_ENDPOINT = "https://api.prod.whoop.com/developer"
SLEEP_URL = "/v1/activity/sleep"
WORKOUT_URL = "/v1/activity/workout"

access_token = os.getenv("TEMP_WHOOP_ACCESS_TOKEN")

def add_params_to_url(url: str, params: dict=None) -> str:
    if params is None:
      return url
    values_formatted = {key:requests.utils.quote(value, safe="") for (key,value) in params.items()}
    url_payload = ""
    for x,y in values_formatted.items():
        url_payload += f"{x}={y}&"
    formatted_payload = url_payload[:-1]
    return url + "?" + formatted_payload
  
def test_whoop_workout_api():
  # test workouts
  headers = {
        "Authorization": f"Bearer {access_token}",
  }

  # midnight 6 days ago - the last week's worth of data
  start_date_utc = datetime.combine(datetime.now(timezone.utc), time.min) - timedelta(6)
  start_date_z = start_date_utc.isoformat() + 'Z'
  workout_query_params = {
      "limit": "25",
      "start": start_date_z
  }

  # url encode payload data
  workouts_endpoint = add_params_to_url(WHOOP_API_ENDPOINT + WORKOUT_URL, workout_query_params)
  response = requests.get(workouts_endpoint, headers=headers)

  if response.status_code == 200:
      data = response.json()
  else:
      print(f"\nRequest failed with status code {response.status_code}\n")

  zone_2_millis = [x["score"]["zone_duration"]["zone_two_milli"] for x in data["records"]]
  total_zone_2_mins = sum(zone_2_millis) / 1000 / 60
  total_zone_2_rounded = int(round(total_zone_2_mins, 0))

  zone_5_millis = [x["score"]["zone_duration"]["zone_five_milli"] for x in data["records"]]
  total_zone_5_mins = sum(zone_5_millis) / 1000 / 60
  total_zone_5_rounded = int(round(total_zone_5_mins, 0))

  print("total zone 2 mins over last 7 days:", total_zone_2_rounded)
  print("total zone 5 mins over last 7 days:", total_zone_5_rounded)
  print()

def test_whoop_sleep_api():
  # Step 3: Get sleep data using access token
  headers = {
        "Authorization": f"Bearer {access_token}",
  }

  # all sleeps within the past 10 days = 10 nights of sleep
  num_days = 10
  start_date_utc = datetime.combine(datetime.now(timezone.utc), time.min) - timedelta(num_days)
  start_date_z = start_date_utc.isoformat() + 'Z'
  sleep_query_params = {
    "limit": "25",
    "start": start_date_z
  }
  sleeps_endpoint = add_params_to_url(WHOOP_API_ENDPOINT + SLEEP_URL, sleep_query_params)

  response = requests.get(sleeps_endpoint, headers=headers)

  if response.status_code == 200:
      data = response.json()
  else:
      print(f"\nRequest failed with status code {response.status_code}\n")
  
  sleep_times = [x["score"]["stage_summary"]["total_in_bed_time_milli"] for x in data["records"]]
  total_sleep_hrs = sum(sleep_times) / 1000 / 60 / 60
  avg_sleep = total_sleep_hrs / num_days
  avg_sleep_rounded = round(avg_sleep, 2)
  print(f"avg sleep over the last {num_days} days:", avg_sleep_rounded)
  print()

def test_notion_api():
   pass

if __name__ == "__main__":
  test_whoop_workout_api()
  test_whoop_sleep_api()
  print()