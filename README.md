# ✦ tuya mood & weather lamp (ﾉ◕ヮ◕)ﾉ

a cozy little python script that turns any tuya-compatible smart rgb/cct bulb into a real-time ambient weather, temperature, and humidity lamp using the free [open-meteo](https://open-meteo.com/) api, no cloud subscription or account required.

## features
- **temperature gradient**: smoothly shifts from deep blue (cold) → cyan/green (mild) → red (hot) in `°c` or `°f`
- **humidity mode**: warm amber when dry → teal when comfy → deep blue when humid
- **live weather (wmo codes)**: maps 28 distinct sky conditions (clear daylight, moody overcast, drizzle, rain, snow, thunderstorms) to custom cct white or rgb colors
- **palette test mode**: preview any individual weather code or cycle through all 28 in a 1.5s demo loop

---

## how do i know if i have a tuya bulb?

if you have your smart lighting, and the box, manual, or QR code tells you to use the Smart Life or Tuya Smart app, or a store-branded clone that looks identical to Smart Life (like LSC Smart Connect, Calex Smart, or Globe Suite), it uses the tuya platform, which means it is compatible with this software.

---

## requirements
- **python 3.8+**
- a **tuya / smart life** rgb+cct smart bulb on your local wi-fi network
- your bulb's **device id**, **local ip**, and **local key**
- python packages:
  - `tinytuya`
  - `requests`

---

## setup

### 1. clone & install dependencies
git clone [https://github.com/soapysoph/weather-lighting-tuya.git](https://github.com/soapysoph/weather-lighting-tuya.git)
```bash
cd weather-lighting-tuya
pip install tinytuya requests
```

### 2. get your tuya bulb credentials
because `tinytuya` talks directly to your bulb over your local network, you'll need its `device id` and `local key` once:

1. pair your bulb in the **smart life** or **tuya smart** app as normal.
2. use [`tuya-local-key`](https://github.com/tuya-local-key/tuya-local-key) (or `npx tuya-local-key` / `pip install tuya-local-key`) to pull your bulb's **device id** and **local key** from your smart life / tuya account.
3. find your bulb's **local ip** on your router (or run `python -m tinytuya scan` on your network) and note its **protocol version** (usually `3.3` or `3.4`).

### 3. run the script
```bash
python weather-lighting.py
```

on your first run, the script will ask for your bulb details and save them locally to `config.json` (which is gitignored so your keys stay private):

```text
  ✦ first-time setup (｡•ᴗ•｡)♡
  let's pair your tuya bulb (saved locally to config.json)

  › bulb nickname (default: smart bulb): desk lamp
  › device id: your_device_id
  › local ip (e.g. 192.168.1.50): 192.168.1.50
  › local key: your_local_key
  › protocol version (default: 3.3): 3.3
```

---

## usage
once configured, pick any mode from the menu:

```text
  ╭───────────────────────────────────────────────────╮
  │  ✦ desk lamp - mood & weather lamp      (ﾉ◕ヮ◕)ﾉ  │
  ├───────────────────────────────────────────────────┤
  │  [1]  temperature · blue → red (°c)               │
  │  [2]  temperature · blue → red (°f)               │
  │  [3]  humidity (%)                                │
  │  [4]  live weather · wmo sky codes                │
  │  [5]  test palette · preview all codes            │
  │  [q]  quit & restore warm white                   │
  ╰───────────────────────────────────────────────────╯
```

- live modes poll open-meteo every **2 minutes** (`120s`).
- press `Ctrl+C` at any time to return to the main menu, or `q` to quit and restore your bulb to a cozy warm white.

---

## troubleshooting
- **bulb doesn't respond / connection timeout**: make sure your computer and bulb are on the same 2.4ghz wi-fi network, and close the smart life app on your phone (some tuya bulbs only accept one local socket connection at a time).
- **wrong protocol version**: newer tuya bulbs often use `3.4` or `3.5` instead of `3.3`. you can edit `"version"` directly inside `config.json`.
