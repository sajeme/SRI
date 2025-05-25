import json
from flask import Flask, jsonify

app = Flask(__name__)

# --- Función para obtener los juegos más jugados/con más interacciones ---
def get_most_played_games(interacciones_file, datos_juegos_file, limit=10):
    """
    Calcula los 'limit' juegos más jugados/interactuados basándose en la frecuencia
    de aparición en las interacciones, y devuelve su id, nombre y el conteo de menciones.
    """
    try:
        with open(interacciones_file, 'r', encoding='utf-8') as f:
            interacciones_data = json.load(f)
        with open(datos_juegos_file, 'r', encoding='utf-8') as f:
            datos_juegos_data = json.load(f)
    except FileNotFoundError:
        return {"error": "Uno o ambos archivos JSON no se encontraron."}
    except json.JSONDecodeError:
        return {"error": "Error al decodificar uno o ambos archivos JSON. Asegúrate de que sean válidos."}

    game_mentions = {}

    # Contar la frecuencia de aparición de cada juego en las interacciones
    for user_interaction in interacciones_data.get("interacciones", []):
        for interaction in user_interaction.get("interacciones", []):
            game_id = str(interaction.get("id_juego"))
            game_mentions[game_id] = game_mentions.get(game_id, 0) + 1

    # Ordenar juegos por el número de menciones (de mayor a menor)
    sorted_games_by_mentions = sorted(game_mentions.items(), key=lambda item: item[1], reverse=True)

    # Obtener los juegos según el límite especificado
    top_played_games = []
    for game_id, count in sorted_games_by_mentions[:limit]:
        if game_id in datos_juegos_data:
            game_info = datos_juegos_data[game_id]
            top_played_games.append({
                "id": game_id,
                "nombre": game_info.get("nombre", "Nombre no disponible"),
                "interacciones": count # El score es el número de interacciones/menciones
            })

    return top_played_games

# --- Endpoint para los juegos más jugados ---
@app.route('/games/most_played', methods=['GET'])
def most_played_games_endpoint():
    """
    Endpoint para obtener los 10 juegos más jugados/interactuados globalmente.
    """
    interacciones_file = 'interacciones.json'
    datos_juegos_file = 'datos_juegos.json'
    
    recommendations = get_most_played_games(interacciones_file, datos_juegos_file)

    if "error" in recommendations:
        return jsonify(recommendations), 500
    
    if not recommendations:
        return jsonify({"message": "No se pudieron encontrar juegos más jugados."}), 404

    return jsonify(recommendations)

# --- Función para obtener los juegos mejor valorados ---
def get_top_rated_games(interacciones_file, datos_juegos_file, limit=10):
    """
    Calcula la popularidad de los juegos basándose en el promedio de sus calificaciones,
    y devuelve los 'limit' juegos con la calificación promedio más alta.
    """
    try:
        with open(interacciones_file, 'r', encoding='utf-8') as f:
            interacciones_data = json.load(f)
        with open(datos_juegos_file, 'r', encoding='utf-8') as f:
            datos_juegos_data = json.load(f)
    except FileNotFoundError:
        return {"error": "Uno o ambos archivos JSON no se encontraron."}
    except json.JSONDecodeError:
        return {"error": "Error al decodificar uno o ambos archivos JSON. Asegúrate de que sean válidos."}

    game_ratings_sum = {}
    game_ratings_count = {}

    # Recopilar todas las calificaciones para cada juego
    for user_interaction in interacciones_data.get("interacciones", []):
        for interaction in user_interaction.get("interacciones", []):
            game_id = str(interaction.get("id_juego"))
            rating = interaction.get("calificacion")

            # Solo consideramos calificaciones válidas (no nulas y numéricas)
            if rating is not None and isinstance(rating, (int, float)):
                game_ratings_sum[game_id] = game_ratings_sum.get(game_id, 0) + rating
                game_ratings_count[game_id] = game_ratings_count.get(game_id, 0) + 1

    game_average_ratings = {}
    # Calcular el promedio de las calificaciones para cada juego
    for game_id, total_rating in game_ratings_sum.items():
        count = game_ratings_count[game_id]
        if count > 0:
            game_average_ratings[game_id] = total_rating / count

    # Ordenar juegos por su calificación promedio (de mayor a menor)
    # y asegurarse de que solo se incluyan juegos con al menos una calificación.
    sorted_games_by_average_rating = sorted(
        [item for item in game_average_ratings.items() if item[1] > 0],
        key=lambda item: item[1],
        reverse=True
    )

    # Obtener los juegos según el límite especificado
    top_rated_games = []
    for game_id, avg_rating in sorted_games_by_average_rating[:limit]:
        if game_id in datos_juegos_data:
            game_info = datos_juegos_data[game_id]
            top_rated_games.append({
                "id": game_id,
                "nombre": game_info.get("nombre", "Nombre no disponible"),
                "calificacion_promedio": round(avg_rating, 2) # El score es la calificación promedio
            })

    return top_rated_games

# --- Endpoint para los juegos mejor valorados ---
@app.route('/games/top_rated', methods=['GET'])
def top_rated_games_endpoint():
    """
    Endpoint para obtener los 10 juegos mejor valorados globalmente
    basados en su calificación promedio.
    """
    interacciones_file = 'interacciones.json'
    datos_juegos_file = 'datos_juegos.json'
    
    recommendations = get_top_rated_games(interacciones_file, datos_juegos_file)

    if "error" in recommendations:
        return jsonify(recommendations), 500
    
    if not recommendations:
        return jsonify({"message": "No se pudieron encontrar juegos mejor valorados."}), 404

    return jsonify(recommendations)

# --- Punto de entrada principal para ejecutar la aplicación Flask ---
if __name__ == '__main__':
    app.run(debug=True)