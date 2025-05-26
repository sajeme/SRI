import json
from datetime import datetime
from collections import defaultdict
import locale
import dateparser
from flask import Flask, jsonify

app = Flask(__name__)

# --- Data Loading and Preprocessing (Same as before) ---

# Establecer la localización para parsear fechas con meses en español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except locale.Error:
        print("Advertencia: No se pudo establecer la localización 'es_ES'. Las fechas pueden no parsearse correctamente sin dateparser.")


# Carga de datos
try:
    with open('usuarios.json', 'r') as f:
        usuarios_data = json.load(f)["usuarios"]
    with open('interacciones.json', 'r') as f:
        interacciones_data = json.load(f)["interacciones"]
    with open('datos_juegos.json', 'r', encoding='utf-8') as f:
        juegos_raw_data = json.load(f)
except FileNotFoundError as e:
    print(f"Error: Archivo no encontrado - {e}. Asegúrate de que todos los archivos JSON estén en el mismo directorio.")
    exit()

# Convertir listas a diccionarios para fácil acceso
usuarios_dict = {user["id"]: user for user in usuarios_data} 

# Procesar los datos de juegos
juegos_dict = {}
for appid_str, game_info_raw in juegos_raw_data.items():
    appid = int(appid_str)
    
    game_tags = [tag['description'].lower() for tag in game_info_raw.get('tags', [])]
    game_categories = [cat.lower() for cat in game_info_raw.get('categorias', [])]
    all_genres_tags = list(set(game_tags + game_categories)) # Combine tags and categories

    fecha_publicacion_str = game_info_raw.get("fecha_publicacion")
    fecha_lanzamiento = None
    if fecha_publicacion_str:
        # Use dateparser to parse the date string reliably
        parsed_date = dateparser.parse(fecha_publicacion_str, languages=["es"])
        if parsed_date:
            fecha_lanzamiento = parsed_date.strftime("%Y-%m-%d")
        else:
            pass # Keep fecha_lanzamiento as None if parsing fails

    # Store all original game info, then update/add processed fields
    processed_game_info = game_info_raw.copy()
    processed_game_info["id_juego"] = appid # Keep internal id_juego for consistency in logic
    processed_game_info["generos"] = all_genres_tags # Use 'generos' for combined tags/categories
    processed_game_info["fecha_lanzamiento"] = fecha_lanzamiento
    # Remove redundant original keys if desired, or keep them if they don't clash
    # processed_game_info.pop("appid", None) # Do NOT pop appid if you want it in the final output
    processed_game_info.pop("fecha_publicacion", None) # fecha_publicacion is now fecha_lanzamiento
    processed_game_info.pop("tags", None) # tags are merged into generos
    processed_game_info.pop("categorias", None) # categories are merged into generos

    juegos_dict[appid] = processed_game_info

# Crear una estructura para interacciones por juego (used for average rating calculation)
juego_interacciones = defaultdict(list)
for user_interaction_set in interacciones_data:
    for interaction in user_interaction_set["interacciones"]:
        game_id = interaction["id_juego"]
        if game_id in juegos_dict:
            juego_interacciones[game_id].append({"id_usuario": user_interaction_set["id"], **interaction})

# Calcular rating promedio de los juegos (solo calificaciones numéricas)
game_average_rating = {}
for game_id, interactions in juego_interacciones.items():
    valid_ratings = [inter["calificacion"] for inter in interactions if "calificacion" in inter]
    if valid_ratings:
        game_average_rating[game_id] = sum(valid_ratings) / len(valid_ratings)
    else:
        game_average_rating[game_id] = 0.0 # If no ratings, the average is 0

# --- General Recommendation Function (as refined previously) ---

def get_general_cold_start_recommendations(
    num_recommendations=5,
    target_category=None,
    date_start=None,
    date_end=None,
    category_boost_factor=1.5,
    date_boost_factor=1.2,
    strict_category_filter=False,
    strict_date_filter=False
):
    candidate_games_scores = {}

    if target_category:
        target_category = target_category.lower()

    parsed_start_date = None
    parsed_end_date = None
    if date_start and date_end:
        try:
            parsed_start_date = datetime.strptime(date_start, "%Y-%m-%d")
            parsed_end_date = datetime.strptime(date_end, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Formato de fecha inválido para el rango {date_start} a {date_end}. Usa 'YYYY-MM-DD'.")
            return []

    for game_id, game_info in juegos_dict.items():
        base_score = game_average_rating.get(game_id, 0.0)

        category_match = False
        if target_category:
            game_genres = set(game_info.get("generos", []))
            if target_category in game_genres:
                category_match = True
                base_score *= category_boost_factor

        date_match = False
        if parsed_start_date and parsed_end_date:
            game_release_date_str = game_info.get("fecha_lanzamiento")
            if game_release_date_str:
                try:
                    game_release_date_obj = datetime.strptime(game_release_date_str, "%Y-%m-%d")
                    if parsed_start_date <= game_release_date_obj <= parsed_end_date:
                        date_match = True
                        base_score *= date_boost_factor
                except ValueError:
                    pass

        should_include = True
        if strict_category_filter and not category_match:
            should_include = False
        if strict_date_filter and not date_match:
            should_include = False
        
        if should_include:
            candidate_games_scores[game_id] = base_score

    sorted_recommendations = sorted(candidate_games_scores.items(), key=lambda item: item[1], reverse=True)
    
    final_recs = []
    for game_id, score in sorted_recommendations:
        game_info = juegos_dict.get(game_id, {})
        
        # Construct the detailed game information based on your example
        # Use 'appid' as the top-level key for the game ID
        detailed_game_rec = {
            "appid": game_id, # This is the change
            "nombre": game_info.get("nombre", "Desconocido"),
            "descripcion_corta": game_info.get("descripcion_corta", "N/A"),
            "descripcion_larga": game_info.get("descripcion_larga", "N/A"),
            "edad_minima": game_info.get("edad_minima", "N/A"),
            "generos": game_info.get("generos", []), # This now contains combined tags and categories
            "capturas": game_info.get("capturas", []),
            "portada": game_info.get("portada", "N/A"),
            "fondo": game_info.get("fondo", "N/A"),
            "link_juego": game_info.get("link_juego", "N/A"),
            "fecha_lanzamiento": game_info.get("fecha_lanzamiento", "N/A"),
            "precio": game_info.get("precio", "N/A"),
            "resumen_precio": game_info.get("resumen_precio", {}),
            "desarrolladores": game_info.get("desarrolladores", []),
            "publicadores": game_info.get("publicadores", []),
            "plataformas": game_info.get("plataformas", []),
            "requisitos_pc": game_info.get("requisitos_pc", {}),
            "puntuacion_final": round(score, 2)
        }
        final_recs.append(detailed_game_rec)

        if len(final_recs) >= num_recommendations:
            break
            
    if not final_recs:
        return []

    return final_recs

# --- Flask Endpoints ---

@app.route('/recommend/rpg', methods=['GET'])
def recommend_rpg_games():
    """
    Endpoint para recomendar juegos de 'rol' con boosting, sin filtro de fecha.
    """
    recommendations = get_general_cold_start_recommendations(
        num_recommendations=5,
        target_category="rol",
        category_boost_factor=2.0, # Strong boost for RPGs
        strict_category_filter=False # Don't strictly filter, just boost matching ones
    )
    if not recommendations:
        return jsonify({"message": "No se encontraron recomendaciones de juegos de rol."}), 404
    return jsonify({"recommendations": recommendations}) # Wrapped in "recommendations" key

@app.route('/recommend/action2025', methods=['GET'])
def recommend_action_2025_games():
    """
    Endpoint para recomendar juegos de 'acción' lanzados entre 2025-01-01 y 2025-05-22.
    """
    recommendations = get_general_cold_start_recommendations(
        num_recommendations=5,
        target_category="acción",
        date_start="2025-01-01",
        date_end="2025-05-22",
        category_boost_factor=1.5, # Boost for action games
        date_boost_factor=1.8, # Strong boost for date range
        strict_category_filter=False, # Don't strictly filter action, just boost
        strict_date_filter=True # Strictly filter by date range
    )
    if not recommendations:
        return jsonify({"message": "No se encontraron recomendaciones de juegos de acción para el período especificado."}), 404
    return jsonify({"recommendations": recommendations}) # Wrapped in "recommendations" key


if __name__ == '__main__':
    app.run(debug=True)