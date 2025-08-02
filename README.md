# Nest Thermostat Control

CLI for setting and enforcing nest thermostats.

## Why?

The model of Nest we have doesn't support locking and this was cheaper than buying new ones.

## Setup Instructions

NOTE: Get or use an existing gmail.com address for everythign here. Do not use a Google Workspace domain for your Google Cloud, Nest Developer account or anything else. Google is a hassle and refuses to support Google Workspace domains. 

Believe me, you will lose hours to this, and $5 to a Nest Developer account you'll never be able to use. Save the time.

### 1. Register for Device Access

Using a gmail address.

1. Visit [Google Nest Device Access Console](https://console.nest.google.com/device-access)
2. Accept the terms and pay the one-time $5 fee
3. Create a project (note your **Project ID**)
4. Link your Google Account with Nest devices to this project

---

### 2. Set Up Google Cloud

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the **Smart Device Management API**
4. Go to **APIs & Services > Credentials**
5. Click **Create credentials > OAuth client ID**
   - Choose **Desktop app**
6. Add `http://localhost` as an authorized redirect URI
7. Save the generated **Client ID** and **Client Secret**

---

### 3. Link Your OAuth Client to the Nest Project

Construct a URL like this (replace values):

```
https://nestservices.google.com/partnerconnections/YOUR_PROJECT_ID/auth?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&response_type=code&scope=https://www.googleapis.com/auth/sdm.service&access_type=offline&prompt=consent
```

Paste it in a browser, approve access, and capture the `code=...` from the URL you're redirected to.

---

### 4. Exchange the Code for Tokens

```bash
curl -L -X POST 'https://oauth2.googleapis.com/token' \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d code=THE_CODE_YOU_COPIED \
  -d grant_type=authorization_code \
  -d redirect_uri=http://localhost
```

Save the response into `config.json`:

```json
{
  "project_id": "enterprises/YOUR_PROJECT_ID",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "refresh_token": "YOUR_REFRESH_TOKEN"
}
```

---

## 💻 Usage

### 1. List All Thermostats

Run this to see your devices and their names:

```bash
python nest_thermostat_control.py --config config.json
```

You’ll get output like:

```
[Bedroom Thermostat] Mode: COOL, Setpoint: 75.0°F
[Living Room Thermostat] Mode: OFF
...
```

**Take note of the thermostat names** you want to manage.

---

### 2. Enforce Temperature Limits

Now you can enforce minimum and/or maximum temperatures (in Fahrenheit) for selected devices:

```bash
python nest_thermostat_control.py \
  --config config.json \
  --enforce-min 70 \
  --thermostats "Thermostat Name 1,Thermostat Name 2"
```

- Only thermostats that are ON and in COOL mode are affected
- Others are left unchanged
