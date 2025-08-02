import argparse
import json
import requests
import sys
import time

TOKEN_URL = "https://oauth2.googleapis.com/token"
API_URL = "https://smartdevicemanagement.googleapis.com/v1"
SDM_SCOPE = "https://www.googleapis.com/auth/sdm.service"

FAHRENHEIT_TO_CELSIUS = lambda f: (f - 32) * 5.0 / 9.0
CELSIUS_TO_FAHRENHEIT = lambda c: c * 9.0 / 5.0 + 32

def refresh_access_token(config):
    payload = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": config["refresh_token"],
        "grant_type": "refresh_token",
    }
    response = requests.post(TOKEN_URL, data=payload)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to refresh access token: {response.status_code} {response.text}"
        )
    return response.json()["access_token"]

def get_devices(project_id, access_token):
    url = f"{API_URL}/{project_id}/devices"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"API error: {response.status_code} {response.text}")
    return response.json().get("devices", [])

def set_cooling_temperature(device_id, access_token, celsius):
    url = f"{API_URL}/{device_id}:executeCommand"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool",
        "params": {"coolCelsius": celsius},
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Setpoint error: {response.status_code} {response.text}")

def log_to_datadog(config, message, level="info", tags=None):
    api_key = config.get("datadog_api_key")
    if not api_key:
        return
    log_entry = {
        "ddsource": "nest-cli",
        "ddtags": ",".join(tags) if tags else "",
        "hostname": "nest-enforcer",
        "message": message,
        "service": "nest-thermostat",
        "status": level,
    }
    response = requests.post(
        "https://http-intake.logs.datadoghq.com/v1/input",
        headers={"Content-Type": "application/json", "DD-API-KEY": api_key},
        data=json.dumps(log_entry),
    )
    if response.status_code >= 300:
        print(f"Failed to log to Datadog: {response.status_code} {response.text}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--enforce-min", type=int)
    parser.add_argument("--enforce-max", type=int)
    parser.add_argument("--thermostats", type=str)
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    access_token = refresh_access_token(config)
    project_id = config["project_id"]

    devices = get_devices(project_id, access_token)
    names_filter = (
        set(name.strip() for name in args.thermostats.split(","))
        if args.thermostats
        else None
    )

    for device in devices:
        traits = device.get("traits", {})
        name = traits.get("sdm.devices.traits.Info", {}).get("customName")
        mode = traits.get("sdm.devices.traits.ThermostatMode", {}).get("mode")
        setpoint_c = traits.get("sdm.devices.traits.ThermostatTemperatureSetpoint", {}).get("coolCelsius")

        if names_filter and name not in names_filter:
            continue

        print(f"[{name}] Mode: {mode}, Setpoint: {setpoint_c if setpoint_c else 'None'}")

        if mode != "COOL" or setpoint_c is None:
            continue

        setpoint_f = CELSIUS_TO_FAHRENHEIT(setpoint_c)
        updated = False

        if args.enforce_min and setpoint_f < args.enforce_min:
            new_c = FAHRENHEIT_TO_CELSIUS(args.enforce_min)
            set_cooling_temperature(device["name"], access_token, new_c)
            updated = True
            print(f"  → Raised setpoint to {args.enforce_min}°F")
            log_to_datadog(
                config,
                f"Updated {name}: raised cooling setpoint from {setpoint_f:.1f} to {args.enforce_min}°F",
                tags=[f"thermostat:{name}", "action:raise"],
            )

        if args.enforce_max and setpoint_f > args.enforce_max:
            new_c = FAHRENHEIT_TO_CELSIUS(args.enforce_max)
            set_cooling_temperature(device["name"], access_token, new_c)
            updated = True
            print(f"  → Lowered setpoint to {args.enforce_max}°F")
            log_to_datadog(
                config,
                f"Updated {name}: lowered cooling setpoint from {setpoint_f:.1f} to {args.enforce_max}°F",
                tags=[f"thermostat:{name}", "action:lower"],
            )

if __name__ == "__main__":
    main()
