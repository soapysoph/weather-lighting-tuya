import json
import os
import time
import requests
import tinytuya

config_file = "config.json"

# high-contrast WMO mapping: each weather group gets its own distinct color family
# mode "white" -> (brightness 10-1000, colourtemp 0-1000)
# mode "rgb"   -> (R, G, B)
wmo_open_meteo = {
    # clear & clouds -> CCT white (bright crisp daylight -> dim moody overcast)
    0:  ("clear sky",                        "white", (1000, 900)),
    1:  ("mainly clear",                     "white", (800, 650)),
    2:  ("partly cloudy",                    "white", (550, 400)),
    3:  ("overcast",                         "white", (280, 150)),

    # fog -> misty warm amber vs frosty mint
    45: ("fog",                              "rgb",   (255, 165, 50)),
    48: ("depositing rime fog",              "rgb",   (120, 255, 190)),

    # drizzle -> aqua / turquoise
    51: ("drizzle: light",                   "rgb",   (80, 255, 210)),
    53: ("drizzle: moderate",                "rgb",   (0, 220, 180)),
    55: ("drizzle: dense",                   "rgb",   (0, 160, 140)),

    # freezing drizzle -> electric ice-cyan
    56: ("freezing drizzle: light",          "rgb",   (100, 235, 255)),
    57: ("freezing drizzle: dense",          "rgb",   (0, 200, 255)),

    # rain -> pure royal / cobalt blue
    61: ("rain: slight",                     "rgb",   (50, 120, 255)),
    63: ("rain: moderate",                   "rgb",   (0, 60, 255)),
    65: ("rain: heavy",                      "rgb",   (0, 10, 255)),

    # freezing rain -> sharp cyan-blue
    66: ("freezing rain: light",             "rgb",   (0, 160, 255)),
    67: ("freezing rain: heavy",             "rgb",   (0, 110, 255)),

    # snow -> cool periwinkle / lavender-ice
    71: ("snow fall: slight",                "rgb",   (195, 185, 255)),
    73: ("snow fall: moderate",              "rgb",   (165, 140, 255)),
    75: ("snow fall: heavy",                 "rgb",   (135, 95, 255)),
    77: ("snow grains",                      "rgb",   (230, 220, 255)),

    # rain showers -> deep indigo / blue-violet
    80: ("rain showers: slight",             "rgb",   (90, 40, 255)),
    81: ("rain showers: moderate",           "rgb",   (115, 0, 255)),
    82: ("rain showers: violent",            "rgb",   (145, 0, 255)),

    # snow showers -> orchid / pink-violet
    85: ("snow showers: slight",             "rgb",   (235, 130, 255)),
    86: ("snow showers: heavy",              "rgb",   (220, 60, 255)),

    # thunderstorms -> magenta -> hot pink-red -> crimson hail alert
    95: ("thunderstorm: slight or moderate", "rgb",   (255, 0, 190)),
    96: ("thunderstorm with slight hail",    "rgb",   (255, 0, 80)),
    99: ("thunderstorm with heavy hail",     "rgb",   (255, 0, 0)),
}


def load_or_create_config():
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    print("\n  ✦ first-time setup (｡•ᴗ•｡)♡")
    print("  let's pair your tuya bulb (saved locally to config.json)\n")

    bulb_name = input("  › bulb nickname (default: smart bulb): ").strip() or "smart bulb"
    bulb_id = input("  › device id: ").strip()
    bulb_ip = input("  › local ip (e.g. 192.168.1.50): ").strip()
    local_key = input("  › local key: ").strip()
    version_str = input("  › protocol version (default: 3.3): ").strip() or "3.3"

    cfg = {
        "bulb_name": bulb_name,
        "bulb_id": bulb_id,
        "bulb_ip": bulb_ip,
        "local_key": local_key,
        "version": float(version_str),
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    print(f"\n  ✧ saved to {config_file} — you're all set (ﾉ´ヮ`)ﾉ*: ･ﾟ\n")
    return cfg


def clamp(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))


def temp_c_to_rgb(temp_c: float, min_c: float = -10.0, max_c: float = 35.0):
    # maps temperature smoothly from blue (cold) -> green/cyan (mid) -> red (hot)
    t = (clamp(temp_c, min_c, max_c) - min_c) / (max_c - min_c)
    if t < 0.5:
        u = t / 0.5
        r = 0
        g = int(80 + u * (255 - 80))
        b = int(255 - u * (255 - 120))
    else:
        u = (t - 0.5) / 0.5
        r = int(u * 255)
        g = int(255 - u * 255)
        b = int(120 - u * 120)
    return r, g, b


def humidity_to_rgb(humidity: float):
    # maps relative humidity (%) to warm amber (dry) -> cyan/teal (comfy) -> deep blue (humid)
    h = clamp(humidity, 0.0, 100.0)
    if h < 35.0:
        u = h / 35.0
        r = 255
        g = int(110 + u * 80)
        b = int(u * 40)
    elif h <= 65.0:
        u = (h - 35.0) / 30.0
        r = int(255 * (1.0 - u))
        g = int(190 + u * 45)
        b = int(40 + u * 215)
    else:
        u = (h - 65.0) / 35.0
        r = int(u * 90)
        g = int(235 * (1.0 - u * 0.8))
        b = 255
    return r, g, b


def apply_weather_light(bulb, code: int, label: str = ""):
    desc, mode, val = wmo_open_meteo.get(
        code, (f"unknown code ({code})", "white", (700, 400))
    )
    prefix = f"  [{label}]  " if label else "  "
    print(f"{prefix}code {code:>2} · {desc}  →  {mode} {val}")

    if mode == "rgb":
        bulb.set_colour(*val)
    else:
        bulb.set_white(brightness=val[0], colourtemp=val[1])


def test_menu(bulb):
    bulb.turn_on()
    while True:
        print("\n  ╭───────────────────────────────────────────────────────────╮")
        print("  │  ✦ weather code test menu                       (✿◠‿◠)    │")
        print("  ╰───────────────────────────────────────────────────────────╯")
        for code, (desc, mode, val) in wmo_open_meteo.items():
            print(f"    [{code:>2}]  {desc:<34} {mode:<5} {val}")
        print("\n    [all] cycle through all 28 codes (1.5s each)")
        print("    [b]   back to main menu")

        choice = input("\n  › pick a code, 'all', or 'b': ").strip().lower()

        if choice == "b":
            return
        elif choice == "all":
            print("\n  ✧ cycling all 28 codes... press Ctrl+C to stop (￣▽￣)\n")
            try:
                for code in wmo_open_meteo:
                    apply_weather_light(bulb, code, label="demo")
                    time.sleep(1.5)
            except KeyboardInterrupt:
                print("\n  · demo paused (｡•́︿•̀｡)")
        elif choice.isdigit() and int(choice) in wmo_open_meteo:
            apply_weather_light(bulb, int(choice), label="test")
        else:
            print("  · hmm, not on the list — try again (´･ω･`)")


def pick_city():
    while True:
        query = input("\n  › city name (e.g. sapporo, london, seoul): ").strip()
        if not query:
            continue

        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 8, "language": "en", "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []

        if not results:
            print("  · couldn't find that city, try another (´･_･`)")
            continue

        print("\n  ✦ matching locations")
        for idx, place in enumerate(results, start=1):
            name = place.get("name", "").lower()
            admin1 = place.get("admin1", "").lower()
            country = place.get("country", "").lower()
            lat = place["latitude"]
            lon = place["longitude"]
            region = f", {admin1}" if admin1 else ""
            print(f"    [{idx}]  {name}{region} ({country})  ·  {lat:.2f}, {lon:.2f}")

        choice = input(f"\n  › pick [1-{len(results)}] or 's' to search again: ").strip()
        if choice.lower() == "s":
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            selected = results[int(choice) - 1]
            city_label = selected["name"].lower()
            country_label = selected.get("country", "").lower()
            print(f"\n  ✧ locked in: {city_label}, {country_label} (˃ᴗ˂)ﻭ")
            return city_label, selected["latitude"], selected["longitude"]

        print("  · invalid choice, try again (´･ω･`)")


def fetch_current_conditions(lat: float, lon: float, unit: str = "celsius"):
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
            "temperature_unit": unit,
        },
        timeout=10,
    )
    resp.raise_for_status()
    current = resp.json()["current"]
    return (
        current["temperature_2m"],
        current["relative_humidity_2m"],
        current["weather_code"],
    )


def run_live_mode(bulb, mode_choice: str):
    city_name, lat, lon = pick_city()
    unit = "fahrenheit" if mode_choice == "temp_f" else "celsius"
    unit_label = "°f" if mode_choice == "temp_f" else "°c"

    print(f"\n  ✦ syncing [{mode_choice}] for {city_name} · Ctrl+C to return (｡•̀ᴗ-)✧\n")
    bulb.turn_on()

    try:
        while True:
            try:
                temp, humidity, code = fetch_current_conditions(lat, lon, unit=unit)

                if mode_choice == "temp_c":
                    r, g, b = temp_c_to_rgb(temp, min_c=-10.0, max_c=35.0)
                    print(f"  [{city_name}]  temp: {temp:.1f}°c  →  rgb({r}, {g}, {b})")
                    bulb.set_colour(r, g, b)

                elif mode_choice == "temp_f":
                    r, g, b = temp_c_to_rgb(temp, min_c=14.0, max_c=95.0)
                    print(f"  [{city_name}]  temp: {temp:.1f}°f  →  rgb({r}, {g}, {b})")
                    bulb.set_colour(r, g, b)

                elif mode_choice == "humidity":
                    r, g, b = humidity_to_rgb(humidity)
                    print(f"  [{city_name}]  humidity: {humidity:.0f}%  →  rgb({r}, {g}, {b})")
                    bulb.set_colour(r, g, b)

                elif mode_choice == "weather":
                    apply_weather_light(bulb, code, label=f"{city_name} · {temp:.1f}{unit_label}")

            except Exception as err:
                print(f"  · fetch error (´；ω；`): {err}")

            time.sleep(120)
    except KeyboardInterrupt:
        print("\n  · stopped live sync (・ω・)ノ")


def main():
    cfg = load_or_create_config()
    bulb = tinytuya.BulbDevice(
        cfg["bulb_id"],
        cfg["bulb_ip"],
        cfg["local_key"],
        version=cfg.get("version", 3.3),
    )
    bulb.set_socketPersistent(True)

    try:
        while True:
            title = f"✦ {cfg['bulb_name'].lower()} — weather light system"
            print("\n  ╭───────────────────────────────────────────────────╮")
            print(f"  │  {title:<40}(・ω・)ﾉ │")
            print("  ├───────────────────────────────────────────────────┤")
            print("  │  [1]  temperature · blue → red (°c)               │")
            print("  │  [2]  temperature · blue → red (°f)               │")
            print("  │  [3]  humidity (%)                                │")
            print("  │  [4]  live weather · wmo sky codes                │")
            print("  │  [5]  test palette · preview all codes            │")
            print("  │  [q]  quit & restore warm white                   │")
            print("  ╰───────────────────────────────────────────────────╯")

            choice = input("\n  › what do you wanna run? ").strip().lower()
            if choice == "1":
                run_live_mode(bulb, "temp_c")
            elif choice == "2":
                run_live_mode(bulb, "temp_f")
            elif choice == "3":
                run_live_mode(bulb, "humidity")
            elif choice == "4":
                run_live_mode(bulb, "weather")
            elif choice == "5":
                test_menu(bulb)
            elif choice == "q":
                break
            else:
                print("  · not an option, try again (´･ω･`)")
    except KeyboardInterrupt:
        pass
    finally:
        print("\n  ✧ restoring warm white... night night ( ˘ ω˘)♥\n")
        bulb.set_white(brightness=650, colourtemp=200)


if __name__ == "__main__":
    main()