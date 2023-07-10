import requests
import json
from typing import Dict, Any
from enum import Enum

# Notion API constants
NOTION_PAGES_ENDPOINT = "https://api.notion.com/v1/pages"
SLEEP_STAT_STRING = "Average Sleep (last 10 days)"
SLEEP_TARGET_STRING = ">7.5 hrs"
ZONE_2_STAT_STRING = "Zone 2 (last 7 days)"
ZONE_2_TARGET_STRING = ">150 mins"
ZONE_5_STAT_STRING = "Zone 5 (last 7 days)"
ZONE_5_TARGET_STRING = ">16 mins"
class STAT_TYPE(Enum):
    SLEEP = 1
    ZONE_2 = 2
    ZONE_5 = 3


def update_stat(stat_type: STAT_TYPE, stat_value: float, integration_secret: str, database_id: str):
    if stat_type == STAT_TYPE.SLEEP:
        stat_string = SLEEP_STAT_STRING
        target_string = SLEEP_TARGET_STRING
    elif stat_type == STAT_TYPE.ZONE_2:
        stat_string = ZONE_2_STAT_STRING
        target_string = ZONE_2_TARGET_STRING
    elif stat_type == STAT_TYPE.ZONE_5:
        stat_string = ZONE_5_STAT_STRING
        target_string = ZONE_5_TARGET_STRING
    else:
        raise ValueError(f"Unknown stat_type argument: {stat_type}")

    payload = _create_db_entry_payload(stat_string, str(stat_value), target_string, database_id)
    existing_entry = _get_db_entry_by_stat(stat_string, integration_secret, database_id)

    if existing_entry:
        _update_db_entry(existing_entry["id"], payload, integration_secret)
    else:
        _create_db_entry(payload, integration_secret)
    
    print("Finished updating notion")

def _create_db_entry_payload(stat: str, value: str, target :str, database_id: str):
    return {
        "parent": {"database_id": database_id},
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

def _get_db_entry_by_stat(stat: str, integration_secret: str, database_id: str):
    body = {"filter": {"property": "Stat", "title": {"equals": stat}}}
    response = requests.post(
        _construct_database_endpoint(database_id),
        headers=_construct_headers(integration_secret),
        data=json.dumps(body),
    )
    response.raise_for_status()
    response = response.json()
    results = response["results"]
    if len(results) > 0:
        return results[0]
    else:
        return None

def _update_db_entry(page_id: str, payload: Dict[str, Any], integration_secret:str):
    response = requests.patch(
        NOTION_PAGES_ENDPOINT + f"/{page_id}",
        headers=_construct_headers(integration_secret),
        data=json.dumps(payload)
    )
    response.raise_for_status()

def _create_db_entry(payload: Dict[str, Any], integration_secret: str):
    response = requests.post(
        NOTION_PAGES_ENDPOINT,
        headers=_construct_headers(integration_secret),
        data=json.dumps(payload)
    )
    response.raise_for_status()

def _construct_headers(integration_secret: str):
    return {
        "Authorization": f"Bearer {integration_secret}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

def _construct_database_endpoint(database_id: str):
    return f"https://api.notion.com/v1/databases/{database_id}/query"
