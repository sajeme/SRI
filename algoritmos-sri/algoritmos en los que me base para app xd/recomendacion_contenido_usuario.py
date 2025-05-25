import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import json
from flask import Flask, jsonify

app = Flask(__name__)

# --- 1. Cargar los Datos ---
def load_json_data(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: El archivo {filepath} no fue encontrado.")
        return None
    except json.JSONDecodeError:
        print(f"Error: No se pudo decodificar el archivo JSON {filepath}. Asegúrate de que sea válido.")
        return None

interacciones_data = load_json_data('interacciones.json')
datos_juegos_data = load_json_data('datos_juegos.json')

# Si los datos no se cargan correctamente, la aplicación no debería iniciar o los endpoints deberían manejar el error.
if interacciones_data is None or datos_juegos_data is None:
    print("Faltan archivos de datos esenciales. La aplicación podría no funcionar correctamente.")

# Crear un mapeo de IDs de juego a nombres
game_id_to_name = {str(game_id): details['nombre'] for game_id, details in datos_juegos_data.items()} if datos_juegos_data else {}

# --- 2. Preparar el Contenido del Juego para TF-IDF ---
game_content_list = []
game_ids_ordered = []

if datos_juegos_data:
    for game_id, details in datos_juegos_data.items():
        content_words = []
        if 'categorias' in details and details['categorias']:
            content_words.extend([cat.lower().replace(' ', '_') for cat in details['categorias']])
        if 'tags' in details and details['tags']:
            content_words.extend([tag['description'].lower().replace(' ', '_') for tag in details['tags']])
        
        if content_words:
            game_content_list.append(" ".join(content_words))
            game_ids_ordered.append(str(game_id))

games_df_content = pd.DataFrame({
    'game_id': game_ids_ordered,
    'content': game_content_list
})
games_df_content.set_index('game_id', inplace=True)

# --- 3. Calcular Similitud de Contenido (TF-IDF + Coseno) ---
tfidf_matrix = None
content_similarity_df = None

if not games_df_content.empty:
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(games_df_content['content'])
    content_similarity_matrix = cosine_similarity(tfidf_matrix)

    content_similarity_df = pd.DataFrame(content_similarity_matrix, 
                                           index=games_df_content.index, 
                                           columns=games_df_content.index)
else:
    print("No hay contenido de juego disponible para calcular la similitud. Las recomendaciones de contenido no funcionarán.")

# --- 4. Función para Recomendar Juegos Basados en Contenido y Calificaciones de Usuario ---
def recomendar_juegos_tfidf(user_id, all_interactions, all_games_data, content_sim_df, game_id_to_name_map, top_n=5):
    
    if all_interactions is None or all_games_data is None or content_sim_df is None or content_sim_df.empty:
        return {"error": "Los datos necesarios para las recomendaciones no están disponibles. Asegúrate de que los archivos JSON se hayan cargado correctamente y que el DataFrame de similitud no esté vacío."}

    user_interactions = None
    for interaction_entry in all_interactions.get('interacciones', []):
        if interaction_entry.get('id') == user_id:
            user_interactions = interaction_entry.get('interacciones', [])
            break

    if user_interactions is None or not user_interactions:
        return {"message": f"No se encontraron interacciones para el usuario ID: {user_id}. No se pueden generar recomendaciones basadas en contenido."}

    played_game_ids = set()
    for interaction in user_interactions:
        game_id_str = str(interaction.get('id_juego'))
        played_game_ids.add(game_id_str)

    highly_rated_game_ids = []
    for interaction in user_interactions:
        game_id_str = str(interaction.get('id_juego'))
        if (interaction.get('calificacion', 0) >= 4.0 or interaction.get('like', False)) and interaction.get('horas_jugadas', 0) > 0:
            highly_rated_game_ids.append(game_id_str)

    if not highly_rated_game_ids:
        return {"message": f"El usuario {user_id} no tiene suficientes juegos altamente calificados para generar recomendaciones de contenido. Necesita al menos un juego calificado con 4.0+, 'like' o con horas jugadas > 0."}

    predicted_scores = {}
    for game_id_to_predict in games_df_content.index:
        if game_id_to_predict not in played_game_ids:
            sim_sum = 0
            weighted_score_sum = 0
            
            for liked_game_id in highly_rated_game_ids:
                if liked_game_id in content_sim_df.columns and game_id_to_predict in content_sim_df.index:
                    similarity = content_sim_df.loc[game_id_to_predict, liked_game_id]
                    
                    current_rating = 0
                    for interaction in user_interactions:
                        if str(interaction.get('id_juego')) == liked_game_id:
                            current_rating = interaction.get('calificacion', 0)
                            break
                    
                    if current_rating > 0:
                        weighted_score_sum += similarity * current_rating
                        sim_sum += similarity
                    else:
                        weighted_score_sum += similarity * 5
                        sim_sum += similarity
            
            if sim_sum > 0:
                predicted_scores[game_id_to_predict] = weighted_score_sum / sim_sum
                
    recommended_games_raw = sorted(predicted_scores.items(), key=lambda x: x[1], reverse=True)
    
    if not recommended_games_raw:
        return {"message": f"No se encontraron recomendaciones de contenido para el usuario {user_id}. Esto puede deberse a la falta de juegos similares o interacciones suficientes."}
    
    final_recommendations_info = []
    count = 0
    for game_id, score_value in recommended_games_raw:
        if count >= top_n:
            break
        game_name = game_id_to_name_map.get(game_id)
        if game_name:
            # Aquí se usa 'score' en lugar de 'score_predicho'
            final_recommendations_info.append({
                "id": game_id,
                "nombre": game_name,
                "score": round(float(score_value), 4) # Renombrado a 'score'
            })
            count += 1
    
    return final_recommendations_info

## Endpoint de Flask
@app.route('/recommendations-content/user/<int:user_id>', methods=['GET'])
def user_content_recommendations(user_id):
    """
    Endpoint para obtener recomendaciones de juegos basadas en contenido
    para un usuario específico.
    """
    recommendations = recomendar_juegos_tfidf(
        user_id,
        interacciones_data,
        datos_juegos_data,
        content_similarity_df,
        game_id_to_name,
        top_n=10 # Puedes ajustar este valor
    )

    if "error" in recommendations:
        return jsonify(recommendations), 500
    elif "message" in recommendations:
        return jsonify(recommendations), 404
    
    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(debug=True)