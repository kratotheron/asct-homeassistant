from datetime import datetime
import time

from requests import get, post
import json
import logging

import sys

if len(sys.argv) < 2:
    print("You need at least 2 arguments!")
    print("\t1. The Home Assistant Url (http://homeassistant.local:8123/api/)")
    print("\t2. The token for the authorization")
    exit(1)
base_url = str(sys.argv[1])
print(base_url)

# Max current
max_current = 6
# Max night current
max_night_current = 10
# Start of the night
start_night = 0
# End of the night
end_night = 7
# Seconds to wait before raising the current again
seconds_to_wait = 10
# Max wattage while charging (House + Tesla)
stop_limit = 2800

token = str(sys.argv[2])

print(token)

headers = {
    "Authorization": "Bearer " + token,
    "content-type": "application/json",
}

headers_services = {
    "Authorization": "Bearer " + token
}


def get_current_consumption() -> float:
    url = f"{base_url}states/sensor.generale_casa_channel_1_power"
    response = get(url, headers=headers)
    if response.status_code != 200:
        return None

    data = json.loads(response.text)
    return float(data["state"])


def is_charging() -> bool:
    url = f"{base_url}states/binary_sensor.charging"
    response = get(url, headers=headers)
    if response.status_code != 200:
        return None

    data = json.loads(response.text)
    return data["state"] == "on"


def api_working() -> bool:
    try:
        response = get(base_url, headers=headers)
        if response.status_code != 200:
            return False
    except Exception as e:
        logging.error(f"Error while checking the API {e}")
        return False
    return True


def turn_on_charging() -> bool:
    url = f"{base_url}services/switch/turn_on"
    data = {
        "entity_id": "switch.charger"
    }
    response = post(url, headers=headers_services, json=data)
    if response.status_code != 200:
        return False
    return True


def turn_off_charging() -> bool:
    url = f"{base_url}services/switch/turn_off"
    data = {
        "entity_id": "switch.charger"
    }
    response = post(url, headers=headers_services, json=data)
    if response.status_code != 200:
        return False
    return True


def set_charging_current(current: int) -> bool:
    logging.info(f"Setting new charging current to {current}")
    url = f"{base_url}services/number/set_value"
    data = {
        "entity_id": "number.charging_amps",
        "value": current
    }
    response = post(url, headers=headers_services, json=data)
    if response.status_code != 200:
        return False
    return True


def get_charging_current() -> int:
    url = f"{base_url}states/number.charging_amps"

    response = get(url, headers=headers)
    if response.status_code != 200:
        return None
    data = json.loads(response.text)
    return int(data["state"])


def is_at_home() -> bool:
    url = f"{base_url}states/device_tracker.location_tracker"

    response = get(url, headers=headers)
    if response.status_code != 200:
        return False
    data = json.loads(response.text)
    return data["state"] == "home"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()
    last_subtract = 0
    while True:
        time.sleep(1)
        if not api_working():
            logger.error("API not working")
            continue
        logger.debug("API working")
        current_consumption = get_current_consumption()
        logger.info(f"Current consumption {current_consumption} W")
        if not is_at_home():
            logger.info("Tesla not at home...")
            time.sleep(60)
            continue
        if is_charging():
            if current_consumption >= stop_limit:
                new_charging_current = get_charging_current() - 1
                set_charging_current(new_charging_current)
                last_subtract = time.time()
            else:
                if (time.time() - last_subtract) > seconds_to_wait:
                    new_charging_current = 0
                    if start_night <= datetime.now().hour <= end_night:
                        new_charging_current = min(get_charging_current() + 1, max_night_current)
                    else:
                        new_charging_current = min(get_charging_current() + 1, max_current)
                    if new_charging_current != get_charging_current():
                        set_charging_current(new_charging_current)
        else:
            logger.debug("Not charging")
            time.sleep(2)
            if start_night <= datetime.now().hour <= end_night:
                logger.info("Starting night charging")
                turn_on_charging()
