import argparse
import json
import requests

API_BASE = "https://smartdevicemanagement.googleapis.com/v1"

def enforce_temperature_bounds(config, access_token, thermostat_names, min_f=None, max_f=None):
    project_id = config["project_id"]
    url = f"{API_BASE}/{project_id}/devices"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch devices: {response.status_code} {response.text}")

    devices = response.json().get("devices", [])
    target_names = set(name.strip() for name in thermostat_names.split(","))

    min_c = (min_f - 32) * 5 / 9 if min_f is not None else None
    max_c = (max_f - 32) * 5 / 9 if max_f is not None else None

    for device in devices:
        name = device["name"]
        traits = device.get("traits", {})
        info = traits.get("sdm.devices.traits.Info", {})
        mode = traits.get("sdm.devices.traits.ThermostatMode", {}).get("mode")
        setpoint = traits.get("sdm.devices.traits.ThermostatTemperatureSetpoint", {}).get("coolCelsius")
        custom_name = info.get("customName", "")

        if custom_name not in target_names:
            continue

        print(f"[{custom_name}] Mode: {mode}, Setpoint: {setpoint}")

        if mode != "COOL" or setpoint is None:
            continue

        should_patch = False
        new_setpoint = setpoint

        if min_c is not None and setpoint < min_c:
            new_setpoint = min_c
            should_patch = True
        elif max_c is not None and setpoint > max_c:
            new_setpoint = max_c
            should_patch = True

        if should_patch:
            patch_url = f"{API_BASE}/{name}:executeCommand"
            body = {
                "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool",
                "params": {"coolCelsius": new_setpoint}
            }
            patch_response = requests.post(patch_url, headers=headers, json=body)
            if patch_response.status_code == 200:
                print(f"✔ Updated {custom_name} to {new_setpoint * 9 / 5 + 32:.1f}°F")
            else:
                print(f"✘ Failed to update {custom_name}: {patch_response.status_code} {patch_response.text}")


def refresh_access_token(config):
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": config["refresh_token"],
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to refresh access token: {response.status_code} {response.text}"
        )
    return response.json()["access_token"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("list", action="store_true", help="List thermostats")
    parser.add_argument("--enforce-min", type=float, help="Minimum temperature in Fahrenheit")
    parser.add_argument("--enforce-max", type=float, help="Maximum temperature in Fahrenheit")
    parser.add_argument("--thermostats", type=str, help="Comma-separated list of thermostat names")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    access_token = refresh_access_token(config)

    if args.list:
        enforce_temperature_bounds(config, access_token, args.thermostats or "", args.enforce_min, args.enforce_max)
    else:
        print("Use --list with --thermostats and optionally --enforce-min/--enforce-max")

if __name__ == "__main__":
    main()

