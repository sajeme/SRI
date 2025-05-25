from flask import Flask, request, jsonify
import json
import pandas as pd
from surprise import Dataset, Reader, KNNBasic, SVD
from typing import List, Dict, Tuple
import random

app = Flask(__name__)

# Global variables to store loaded data
users_raw_data: Dict = {}
games_raw_data: Dict = {}
interactions_raw_data: Dict = {}
surprise_formatted_data: List[Tuple[int, int, float]] = []
# Modelo KNNBasic pre-entrenado para similitud de ítems.
item_similarity_model = None
trainset_global = None # El trainset también se guarda para poder usarlo en la búsqueda de ítems


def load_json_data(filepath: str) -> Dict:
    """Loads a JSON file and returns its content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filepath}'. Check file format.")
        return {}

def prepare_surprise_data(
    interactions_data: Dict,
    games_data: Dict,
    users_data: Dict
) -> List[Tuple[int, int, float]]:
    """
    Prepares the data for the Surprise library from the given JSON inputs,
    using only the 'calificacion' field for ratings.
    """
    surprise_data = []
    
    for user_interaction_entry in interactions_data.get("interacciones", []):
        user_id = user_interaction_entry.get("id")
        if user_id is None:
            continue

        for game_interaction in user_interaction_entry.get("interacciones", []):
            game_appid = str(game_interaction.get("id_juego"))
            raw_rating = game_interaction.get("calificacion")
            
            try:
                rating = float(raw_rating)
                if not (0 <= rating <= 5):
                    continue
            except (ValueError, TypeError):
                continue
            surprise_data.append((user_id, int(game_appid), rating))
    return surprise_data

# ============================
# 🔷 Método 1: Filtrado basado en Usuario (User-Based Collaborative Filtering)
# ============================
def recommend_user_based(data_for_surprise: List[Tuple[int, int, float]], games_raw_data: Dict, target_user_id: int, min_n: int = 5, max_n: int = 10) -> List[Dict]:
    df = pd.DataFrame(data_for_surprise, columns=['userID', 'itemID', 'rating'])
    
    if target_user_id not in df['userID'].unique():
        return []

    reader = Reader(rating_scale=(0, 5)) 
    dataset = Dataset.load_from_df(df, reader)
    trainset = dataset.build_full_trainset()
    
    sim_options = {'name': 'cosine', 'user_based': True}
    model = KNNBasic(sim_options=sim_options)
    model.fit(trainset)

    all_game_ids = set(df['itemID'].unique())
    interacted_games = set(df[df['userID'] == target_user_id]['itemID'])
    
    uninteracted_games = all_game_ids - interacted_games

    predictions = []
    for game_id in uninteracted_games:
        prediction = model.predict(target_user_id, game_id)
        predictions.append((game_id, prediction.est))
    
    predictions.sort(key=lambda x: -x[1])
    
    num_recommendations = random.randint(min_n, max_n)
    final_recommendations_raw = predictions[:min(num_recommendations, len(predictions))]

    formatted_recommendations: List[Dict] = []
    for game_id, score in final_recommendations_raw:
        game_name = games_raw_data.get(str(game_id), {}).get("nombre", f"Juego Desconocido (ID: {game_id})")
        formatted_recommendations.append({
            "id": str(game_id),
            "nombre": game_name,
            "score": round(score, 2)
        })
    return formatted_recommendations

# ============================
# 🔷 Método 2: Filtrado basado en Ítems (Item-Based Collaborative Filtering)
# ============================
def recommend_item_based(data_for_surprise: List[Tuple[int, int, float]], games_raw_data: Dict, target_user_id: int, min_n: int = 5, max_n: int = 10) -> List[Dict]:
    df = pd.DataFrame(data_for_surprise, columns=['userID', 'itemID', 'rating'])

    if target_user_id not in df['userID'].unique():
        return []
    
    reader = Reader(rating_scale=(0, 5))
    dataset = Dataset.load_from_df(df, reader)
    trainset = dataset.build_full_trainset()

    sim_options = {'name': 'cosine', 'user_based': False}
    model = KNNBasic(sim_options=sim_options)
    model.fit(trainset)

    all_game_ids = set(df['itemID'].unique())
    interacted_games = set(df[df['userID'] == target_user_id]['itemID'])
    
    uninteracted_games = all_game_ids - interacted_games

    predictions = []
    for game_id in uninteracted_games:
        prediction = model.predict(target_user_id, game_id)
        predictions.append((game_id, prediction.est))
    
    predictions.sort(key=lambda x: -x[1])
    
    num_recommendations = random.randint(min_n, max_n)
    final_recommendations_raw = predictions[:min(num_recommendations, len(predictions))]

    formatted_recommendations: List[Dict] = []
    for game_id, score in final_recommendations_raw:
        game_name = games_raw_data.get(str(game_id), {}).get("nombre", f"Juego Desconocido (ID: {game_id})")
        formatted_recommendations.append({
            "id": str(game_id),
            "nombre": game_name,
            "score": round(score, 2)
        })
    return formatted_recommendations

# ============================
# 🔷 Nuevo Método: Juegos Similares (Basado en Ítems) para un Juego dado
# ============================
def get_similar_games(
    target_game_id: int,
    games_raw_data: Dict,
    model: KNNBasic, # Se pasa el modelo pre-entrenado
    trainset,        # Se pasa el trainset para obtener los inner_id
    top_n: int = 10
) -> List[Dict]:
    """
    Encuentra juegos similares a un juego dado utilizando el modelo KNNBasic (Item-Based).
    """
    try:
        target_game_inner_id = trainset.to_inner_iid(target_game_id)
    except ValueError:
        print(f"Advertencia: El juego con ID {target_game_id} no se encontró en el trainset. No se pueden obtener juegos similares.")
        return []

    neighbors_inner_ids = model.get_neighbors(target_game_inner_id, k=top_n + 1)

    similar_games_info: List[Dict] = []
    
    for inner_id in neighbors_inner_ids:
        if inner_id == target_game_inner_id:
            continue
        
        similar_game_id = trainset.to_raw_iid(inner_id)
        game_name = games_raw_data.get(str(similar_game_id), {}).get("nombre", f"Juego Desconocido (ID: {similar_game_id})")
        
        similarity_score = model.sim[target_game_inner_id, inner_id]

        similar_games_info.append({
            "id": str(similar_game_id),
            "nombre": game_name,
            "score": round(similarity_score, 4) # Usamos la similitud como score
        })
        if len(similar_games_info) >= top_n:
            break
            
    similar_games_info.sort(key=lambda x: x['score'], reverse=True)

    return similar_games_info


# ============================
# 🔷 Método 3: Ranking personalizado con SVD (Singular Value Decomposition)
# ============================
def recommend_svd_ranking(data_for_surprise: List[Tuple[int, int, float]], games_raw_data: Dict, target_user_id: int, min_n: int = 5, max_n: int = 10) -> List[Dict]:
    df = pd.DataFrame(data_for_surprise, columns=['userID', 'itemID', 'rating'])

    if target_user_id not in df['userID'].unique():
        return []

    reader = Reader(rating_scale=(0, 5))
    dataset = Dataset.load_from_df(df, reader)
    trainset = dataset.build_full_trainset()

    model = SVD()
    model.fit(trainset)

    all_game_ids = set(df['itemID'].unique())
    interacted_games = set(df[df['userID'] == target_user_id]['itemID'])
    
    uninteracted_games = all_game_ids - interacted_games

    predictions = []
    for game_id in uninteracted_games:
        prediction = model.predict(target_user_id, game_id)
        predictions.append((game_id, prediction.est))
    
    predictions.sort(key=lambda x: -x[1])
    
    num_recommendations = random.randint(min_n, max_n)
    final_recommendations_raw = predictions[:min(num_recommendations, len(predictions))]

    formatted_recommendations: List[Dict] = []
    for game_id, score in final_recommendations_raw:
        game_name = games_raw_data.get(str(game_id), {}).get("nombre", f"Juego Desconocido (ID: {game_id})")
        formatted_recommendations.append({
            "id": str(game_id),
            "nombre": game_name,
            "score": round(score, 2)
        })
    return formatted_recommendations

# --- Load data and train models when the Flask app starts ---
with app.app_context():
    users_raw_data = load_json_data("usuarios.json")
    games_raw_data = load_json_data("datos_juegos.json")
    interactions_raw_data = load_json_data("interacciones.json")
    
    if users_raw_data and games_raw_data and interactions_raw_data:
        surprise_formatted_data = prepare_surprise_data(
            interactions_raw_data,
            games_raw_data,
            users_raw_data
        )
        
        # Pre-entrenar el modelo Item-Based Collaborative Filtering aquí
        # para el endpoint de /similar-games
        if surprise_formatted_data:
            df_global = pd.DataFrame(surprise_formatted_data, columns=['userID', 'itemID', 'rating'])
            reader_global = Reader(rating_scale=(0, 5))
            dataset_global = Dataset.load_from_df(df_global, reader_global)
            trainset_global = dataset_global.build_full_trainset()
            
            sim_options_global = {'name': 'cosine', 'user_based': False} # ¡Importante: user_based=False para ítems!
            item_similarity_model = KNNBasic(sim_options=sim_options_global)
            item_similarity_model.fit(trainset_global)
            print("Modelo de similitud de ítems pre-entrenado correctamente.")
        else:
            print("No hay datos suficientes para entrenar el modelo de similitud de ítems.")
    else:
        print("Fallo al cargar uno o más archivos JSON necesarios. Los endpoints de recomendación pueden no funcionar correctamente.")


# --- Flask Endpoints (modificados para GET) ---

@app.route('/recommendations/user-based/<int:user_id>', methods=['GET'])
def get_user_based_recommendations(user_id):
    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones"}), 500

    recommendations = recommend_user_based(surprise_formatted_data, games_raw_data, user_id)
    if not recommendations: # Si la lista está vacía, puede ser un error o no hay recomendaciones.
        return jsonify({"message": f"No se encontraron recomendaciones User-Based para el usuario ID: {user_id}"}), 404
        
    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/item-based/<int:user_id>', methods=['GET'])
def get_item_based_recommendations(user_id):
    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones"}), 500

    recommendations = recommend_item_based(surprise_formatted_data, games_raw_data, user_id)
    if not recommendations:
        return jsonify({"message": f"No se encontraron recomendaciones Item-Based para el usuario ID: {user_id}"}), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/svd/<int:user_id>', methods=['GET'])
def get_svd_recommendations(user_id):
    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones"}), 500

    recommendations = recommend_svd_ranking(surprise_formatted_data, games_raw_data, user_id)
    if not recommendations:
        return jsonify({"message": f"No se encontraron recomendaciones SVD para el usuario ID: {user_id}"}), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

# --- Endpoint para juegos similares (modificado para GET) ---
@app.route('/recommendations/similar-games/<int:game_id>', methods=['GET'])
def get_similar_games_endpoint(game_id):
    if not item_similarity_model or not trainset_global:
        return jsonify({"error": "Modelo de similitud de ítems no entrenado o datos no cargados."}), 500

    if str(game_id) not in games_raw_data:
        return jsonify({"error": f"El juego con ID {game_id} no se encuentra en la base de datos de juegos."}), 404

    similar_games = get_similar_games(game_id, games_raw_data, item_similarity_model, trainset_global)
    
    if not similar_games:
        return jsonify({"message": f"No se encontraron juegos similares para el juego ID: {game_id}"}), 404

    return jsonify({"target_game_id": game_id, "similar_games": similar_games})


if __name__ == '__main__':
    app.run(debug=True, port=5000)