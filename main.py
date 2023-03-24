import time

from requests import get, post
import json
import logging

base_url = "http://192.168.95.229:8123/api/"

# Corrente massima che voglio dare alla macchina
min_current = 3
max_current = 6
stop_limit = 2800

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4MjM2N2UzNWRmNDA0Y2EzODdkYjkzYWY3NWQ1MDI3MiIsImlhdCI6MTY3OTUyMDk4MiwiZXhwIjoxOTk0ODgwOTgyfQ.qtaJjo3WURUuxk5jYzJ6Bbg9MhNOmGnYDT4eKHry6Fk"
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
        logging.error(f"Errore durante il controllo delle API {e}")
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
    while True:
        time.sleep(1)
        if not api_working():
            logger.debug("API not working")
            continue
        logger.debug("API working")
        current_consumption = get_current_consumption()
        if is_charging():
            if current_consumption >= stop_limit:
                new_charging_current = get_charging_current() - 1
                if new_charging_current < min_current:
                    turn_off_charging()
                    time.sleep(60)
                else:
                    set_charging_current(new_charging_current)
                    time.sleep(2)
            else:
                new_charging_current = min(get_charging_current() + 1, max_current)
                if new_charging_current != get_charging_current():
                    set_charging_current(new_charging_current)
                    time.sleep(2)
        else:
            if not is_at_home():
                time.sleep(60)
                continue

            if current_consumption < stop_limit:
                turn_on_charging()




