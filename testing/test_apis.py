"""
This file assists with testing the WHOOP and Notion APIs. All sensitive info are
stored as environment variables - you'll need to set them on your local machine
to use this script. See the root directory's README.md for more info.
"""

import os
import requests
import json
from datetime import datetime, timezone, timedelta, time
from typing import Dict, Any, Optional
from enum import Enum

# Whoop API constants
AUTHORIZATION_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_API_ENDPOINT = "https://api.prod.whoop.com/developer"
SLEEP_URL = "/v1/activity/sleep"
WORKOUT_URL = "/v1/activity/workout"
WHOOP_ACCESS_TOKEN = os.getenv("TEMP_WHOOP_ACCESS_TOKEN")

# Notion API constants
NOTION_INTEGRATION_SECRET = os.getenv("NOTION_SECRET_FOR_WHOOP_INTEGRATION")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID_FOR_WHOOP_INTEGRATION")
NOTION_PAGES_ENDPOINT = "https://api.notion.com/v1/pages"
NOTION_QUERY_DATABASE_ENDPOINT = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
NOTION_API_HEADERS = {
  "Authorization": f"Bearer {NOTION_INTEGRATION_SECRET}",
  "Notion-Version": "2022-06-28",
  "Content-Type": "application/json",
}
SLEEP_STAT_STRING = "Average Sleep (last 10 days)"
SLEEP_TARGET_STRING = ">7.5 hrs"
ZONE_2_STAT_STRING = "Zone 2 (last 7 days)"
ZONE_2_TARGET_STRING = ">150 mins"
ZONE_5_STAT_STRING = "Zone 5 (last 7 days)"
ZONE_5_TARGET_STRING = ">16 mins"
class STAT(Enum):
    SLEEP = 1
    ZONE_2 = 2
    ZONE_5 = 3

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
        "Authorization": f"Bearer {WHOOP_ACCESS_TOKEN}",
  }

  # midnight 6 days ago - the last week's worth of data
  start_date_utc = datetime.combine(datetime.now(timezone.utc), time.min) - timedelta(7)
  start_date_z = start_date_utc.isoformat() + 'Z'
  workout_query_params = {
      "limit": "25",
      "start": start_date_z
  }

  # url encode payload data
  workouts_endpoint = add_params_to_url(WHOOP_API_ENDPOINT + WORKOUT_URL, workout_query_params)
  response = requests.get(workouts_endpoint, headers=headers)
  response.raise_for_status()

  if response.status_code == 200:
      data = response.json()
  else:
      print(f"\nRequest failed with status code {response.status_code}\n")
  print(json.dumps(data, indent=2))
  zone_2_millis = [x["score"]["zone_duration"]["zone_two_milli"] for x in data["records"]]
  total_zone_2_mins = sum(zone_2_millis) / 1000 / 60
  total_zone_2_rounded = int(round(total_zone_2_mins, 0))

  zone_5_millis = [x["score"]["zone_duration"]["zone_five_milli"] for x in data["records"]]
  print(json.dumps(zone_5_millis, indent=2))
  total_zone_5_mins = sum(zone_5_millis) / 1000 / 60
  print(total_zone_5_mins)
  total_zone_5_rounded = int(round(total_zone_5_mins, 0))

  print("total zone 2 mins over last 7 days:", total_zone_2_rounded)
  print("total zone 5 mins over last 7 days:", total_zone_5_rounded)
  print()

def test_whoop_sleep_api():
    headers = {
        "Authorization": f"Bearer {WHOOP_ACCESS_TOKEN}",
    }

    # all sleeps within the past 10 days = 10 nights of sleep
    num_days = 10
    start_date_utc = datetime.combine(datetime.now(), time.min) - timedelta(num_days - 1)
    print("start date: ", start_date_utc)
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
    
    print(json.dumps(data, indent=2))
    sleep_times = [x["score"]["stage_summary"]["total_in_bed_time_milli"] for x in data["records"] if not x["nap"]]
    print(sleep_times)
    total_sleep_hrs = sum(sleep_times) / 1000 / 60 / 60
    avg_sleep = total_sleep_hrs / num_days
    avg_sleep_rounded = round(avg_sleep, 2)
    print(f"avg sleep over the last {num_days} days:", avg_sleep_rounded)
    print()

def test_notion_api(stat_type: STAT, stat_value: float):
    def create_db_entry_payload(stat: str, value: str, target:str):
        return {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
            "Stat": {
                "title": [
                    {
                        "text": {
                        "content": stat
                        }
                    }
                ]
            },
            "Value": {
                "rich_text": [
                    {
                        "text": {
                        "content": value 
                        }
                    }
                ]
            },
            "Target": {
                "rich_text": [
                    {
                        "text": {
                        "content": target
                        }
                    }
                ]
            }
            }
        }

    def get_db_entry_by_stat(stat: str):
        body = {"filter": {"property": "Stat", "title": {"equals": stat}}}
        response = requests.post(
            NOTION_QUERY_DATABASE_ENDPOINT,
            headers=NOTION_API_HEADERS,
            data=json.dumps(body),
        )
        response.raise_for_status()
        response = response.json()
        results = response["results"]
        if len(results) > 0:
            return results[0]
        else:
            return None

    def update_db_entry(page_id: str, payload: Dict[str, Any]):
        response = requests.patch(
            NOTION_PAGES_ENDPOINT + f"/{page_id}",
            headers=NOTION_API_HEADERS,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        print("Finished updating sleep entry")

    def create_db_entry(payload: Dict[str, Any]):
        response = requests.post(
            NOTION_PAGES_ENDPOINT,
            headers=NOTION_API_HEADERS,
            data=json.dumps(payload)
        )
        response.raise_for_status()
        print("Finished creating sleep entry")

    if stat_type == STAT.SLEEP:
        stat_string = SLEEP_STAT_STRING
        target_string = SLEEP_TARGET_STRING
    elif stat_type == STAT.ZONE_2:
        stat_string = ZONE_2_STAT_STRING
        target_string = ZONE_2_TARGET_STRING
    elif stat_type == STAT.ZONE_5:
        stat_string = ZONE_5_STAT_STRING
        target_string = ZONE_5_TARGET_STRING
    else:
        raise ValueError(f"Unknown stat_type argument: {stat_type}")


    payload = create_db_entry_payload(stat_string, str(stat_value), target_string)
    existing_entry = get_db_entry_by_stat(stat_string)

    if existing_entry:
        update_db_entry(existing_entry["id"], payload)
    else:
        create_db_entry(payload)

    

if __name__ == "__main__":
    # test_whoop_workout_api()
    test_whoop_sleep_api()
    # test_notion_api(STAT.SLEEP, 7.55)