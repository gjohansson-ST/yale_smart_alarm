from time import sleep
from yalesmartalarmclient.client import YaleSmartAlarmClient
import requests

try:
    client = YaleSmartAlarmClient("USERNAME", "PASSWORD")
except requests.HTTPError as error:
    if error.response.status_code == 401:
        print("401 fel")
    else:
        print("annat fel")
except requests.ConnectionError as error:
    print("connection error")
except Exception as error:
    print("annat")

# client.lock_api.open_lock(client.lock_api.get("Entre"), "217521")
print(client.get_cycle())
"""sleep(0.2)
print(client.get_cycle())
sleep(0.2)
print(client.get_cycle())
sleep(0.2)
print(client.get_cycle())"""
