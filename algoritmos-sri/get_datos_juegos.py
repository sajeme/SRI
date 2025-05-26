import requests
import json
import time
import os

STEAM_API_URL = "https://store.steampowered.com/api/appdetails"

steam_appids = [
    1086940, 892970, 1144200, 1091500, 1172470, 1245620, 1593500, 730,
    578080, 271590, 990080, 1938090, 252490, 236390, 1692250, 1966720,
    1238840, 289070, 1971650, 1904540, 1874880, 1817070, 1659040, 1623730,
    1222670, 1840080, 1506830, 1850570, 1326470, 1943950, 1361210, 108600,
    1843760, 1677740, 230410, 739630, 105600, 1716740, 232090, 552500,
    1643310, 1818750, 1341290, 1985810, 1328670, 1492040, 1551360, 2002100,
    2050650, 1627720, 2005010, 2059190, 1774580, 1930570, 228380, 1286830,
    1939160, 282800, 1263850, 1085660, 1118200, 236850, 1295510, 1708520,
    1824220, 251570, 668580, 221100, 960090, 2087030, 1533390, 251530,
    1973710, 1509510, 1599340, 570, 1174180, 1466060,  # Tainted Grail: The Fall of Avalon
    1430190,  # Killing Floor 3
    2140100,  # Whisker Squadron: Survivor
    1771300,  # Kingdom Come: Deliverance II
    3314060,  # The Sims Legacy Collection
    3314070,  # The Sims 2 Legacy Collection
    239140,   # Dying Light
    2104890,  # RoadCraft
    2457220,  # Avowed
    2012190,  # Kaiserpunk
    3559850,  # Rift of the NecroDancer
    2442460,  # Citizen Sleeper 2: Starward Vector
    2545360,  # Lonely Mountains: Snow Riders
    2754380,  # The Roottrees are Dead
    3159330,  # Assassin’s Creed: Shadows
    2246340,  # Monster Hunter Wilds
    2001120,  # Split Fiction
    2016460   # Tales of the Shire
]

def obtener_datos_juego(appid):
    params = {
        "appids": appid,
        "cc": "mx",
        "l": "spanish"
    }

    try:
        response = requests.get(STEAM_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data[str(appid)]['success']:
            print(f"No se pudo obtener información para el juego con appid {appid}")
            return None

        game_data = data[str(appid)]['data']
        
        juego = {
            "appid": appid,
            "nombre": game_data.get("name"),
            "descripcion_corta": game_data.get("short_description"),
            "descripcion_larga": game_data.get("about_the_game"),
            "edad_minima": game_data.get("required_age"),
            "categorias": [cat["description"] for cat in game_data.get("categories", [])],
            "tags": list(game_data.get("genres", [])),
            "capturas": [screenshot["path_full"] for screenshot in game_data.get("screenshots", [])],
            "portada": game_data.get("header_image"),
            "fondo": game_data.get("background"),
            "link_juego": f"https://store.steampowered.com/app/{appid}/",

            # Nuevos campos
            "fecha_publicacion": game_data.get("release_date", {}).get("date"),
            "precio": game_data.get("price_overview", {}).get("final_formatted"),
            "resumen_precio": game_data.get("price_overview", {}),
            "desarrolladores": game_data.get("developers", []),
            "publicadores": game_data.get("publishers", []),
            "plataformas": [plataforma for plataforma, disponible in game_data.get("platforms", {}).items() if disponible],
            "requisitos_pc": {
                "minimos": game_data.get("pc_requirements", {}).get("minimum"),
                "recomendados": game_data.get("pc_requirements", {}).get("recommended")
            }
        }

        return juego

    except Exception as e:
        print(f"Error al obtener datos del juego {appid}: {e}")
        return None

def guardar_juego_en_json(juego, archivo='gamesdata.json'):
    appid = str(juego["appid"])
    try:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            datos = {}

        datos[appid] = juego

        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)

        print(f"✅ Guardado {juego['nombre']} (appid: {appid})")

    except Exception as e:
        print(f"❌ Error al guardar {appid}: {e}")

# --------- Proceso principal ---------
for appid in steam_appids:
    print(f"⏳ Consultando AppID: {appid}")
    juego = obtener_datos_juego(appid)
    if juego:
        guardar_juego_en_json(juego)
    time.sleep(1)  # ⏱ Espera 1 segundo entre llamadas para evitar límite


