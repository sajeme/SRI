import locale
import dateparser
import json
import pandas as pd
import numpy as np
import random
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from datetime import datetime
from flask import Flask, request, jsonify

# Importar las bibliotecas específicas de cada módulo
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from surprise import Dataset, Reader, KNNBasic, SVD

# Configuración de la localización para parsear fechas con meses en español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except locale.Error:
        print("Advertencia: No se pudo establecer la localización 'es_ES'. Las fechas pueden no parsearse correctamente sin dateparser.")

app = Flask(__name__)

# --- Funciones Auxiliares Comunes ---
def load_json_data(filepath: str) -> Dict:
    """Carga un archivo JSON y devuelve su contenido."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: El archivo '{filepath}' no fue encontrado.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: No se pudo decodificar JSON desde '{filepath}'. Verifica el formato del archivo.")
        return {}

def _load_base_json_data():
    """Carga los datos base de interacciones, juegos y usuarios."""
    interacciones = load_json_data('interacciones.json')
    juegos = load_json_data('datos_juegos.json')
    usuarios = load_json_data('usuarios.json')
    return interacciones, juegos, usuarios

# --- Lógica de Preprocesamiento y Entrenamiento por Modelo (llamadas por endpoint) ---

def prepare_apriori_models(interacciones_data: Dict, datos_juegos_data: Dict):
    """Prepara y entrena el modelo Apriori."""
    game_id_to_name = {str(game_id): details['nombre'] for game_id, details in datos_juegos_data.items()}
    name_to_game_id = {details['nombre']: str(game_id) for game_id, details in datos_juegos_data.items()}

    user_game_matrix = {}
    for user_interaction in interacciones_data.get('interacciones', []):
        user_id = user_interaction.get('id')
        if user_id is None:
            continue
        user_game_matrix[user_id] = {}
        for interaction in user_interaction.get('interacciones', []):
            game_id = str(interaction.get('id_juego'))
            game_name = game_id_to_name.get(game_id, f"Juego Desconocido ({game_id})")

            if (interaction.get('calificacion', 0) >= 3.5 or interaction.get('like', False)):
                user_game_matrix[user_id][game_name] = 1
            else:
                user_game_matrix[user_id][game_name] = 0

    df_games = pd.DataFrame.from_dict(user_game_matrix, orient='index').fillna(0).astype(bool)

    rules = pd.DataFrame()
    if not df_games.empty:
        try:
            frequent_itemsets = apriori(df_games, min_support=0.01, use_colnames=True)
            rules = association_rules(frequent_itemsets, metric='confidence', min_threshold=0.05)
            print(f"Apriori: {len(frequent_itemsets)} itemsets frecuentes, {len(rules)} reglas de asociación.")
        except Exception as e:
            print(f"Error al generar reglas de asociación Apriori: {e}")
    else:
        print("Apriori: Matriz de usuario-juego vacía, no se generaron reglas.")
    return rules, game_id_to_name, name_to_game_id

def prepare_cold_start_recommender(interacciones_data: Dict, datos_juegos_data: Dict, usuarios_data: Dict):
    """Prepara y entrena el Cold Start Recommender."""
    class ColdStartRecommender:
        def __init__(self):
            self.user_profiles: Dict[int, Dict] = {}
            self.game_features: Dict[str, Dict] = {}
            self.category_weights: Dict[str, float] = defaultdict(lambda: 0.5)

        def load_game_data_from_json(self, games_data_loaded: Dict):
            for appid, game_info in games_data_loaded.items():
                game_id_str = str(appid)
                nombre = game_info.get("nombre", "Desconocido")
                categorias = game_info.get("categorias", [])
                tags = [tag.get("description") for tag in game_info.get("tags", []) if tag.get("description")]
                
                edad_minima_str = game_info.get("edad_minima", "0")
                try:
                    edad_minima = int(edad_minima_str)
                except ValueError:
                    edad_minima = 0
                self.game_features[game_id_str] = {
                    'nombre': nombre,
                    'categorias': categorias,
                    'tags': tags,
                    'edad_minima': edad_minima
                }
            # print(f"Cold Start: Cargados {len(self.game_features)} juegos.")

        def load_user_data_from_json(self, users_data_loaded: Dict):
            for user_profile in users_data_loaded.get("usuarios", []):
                user_id = user_profile.get("id")
                if user_id is not None:
                    self.user_profiles[user_id] = {
                        'nombre': user_profile.get("nombre", "Desconocido"),
                        'edad': user_profile.get("edad", 0),
                        'generos_favoritos': user_profile.get("generos_favoritos", [])
                    }
            # print(f"Cold Start: Cargados {len(self.user_profiles)} usuarios.")

        def calculate_category_weights_from_interactions(self, interactions_data_loaded: Dict):
            category_ratings_sum = defaultdict(float)
            category_ratings_count = defaultdict(int)

            for user_interaction_entry in interactions_data_loaded.get("interacciones", []):
                for game_played in user_interaction_entry.get("interacciones", []):
                    game_appid = str(game_played["id_juego"])
                    
                    if game_appid in self.game_features:
                        game_info = self.game_features[game_appid]
                        
                        rating = 0.0
                        if "calificacion" in game_played and game_played["calificacion"] is not None:
                            try:
                                rating = float(game_played["calificacion"])
                            except ValueError:
                                rating = 0.0
                        elif game_played.get("like"):
                            rating = 5.0
                        elif not game_played.get("like") and game_played.get("calificacion") is None:
                            rating = 1.0
                        
                        all_game_content_attributes = game_info.get('categorias', []) + game_info.get('tags', [])
                        for attribute in all_game_content_attributes:
                            normalized_attribute = attribute.lower()
                            category_ratings_sum[normalized_attribute] += rating
                            category_ratings_count[normalized_attribute] += 1
            
            for category, total_rating in category_ratings_sum.items():
                count = category_ratings_count[category]
                if count > 0:
                    self.category_weights[category] = (total_rating / count) / 5.0
                else:
                    self.category_weights[category] = 0.5

            # print(f"Cold Start: Pesos de categorías actualizados.")

        def recommend_for_user(self, user_id: int, min_n: int = 5, max_n: int = 10) -> List[Dict[str, Any]]:
            if user_id not in self.user_profiles:
                return []
                
            user = self.user_profiles[user_id]
            user_age = user['edad']
            user_fav_genres = [g.lower() for g in user['generos_favoritos']]

            scores: List[Tuple[str, float]] = []
            
            interacted_game_ids = set()
            for user_interaction_entry in interacciones_data.get('interacciones', []):
                if user_interaction_entry.get('id') == user_id:
                    for interaction in user_interaction_entry.get('interacciones', []):
                        interacted_game_ids.add(str(interaction.get('id_juego')))
                    break


            for game_id, game in self.game_features.items():
                if game_id in interacted_game_ids:
                    continue
                if user_age < game['edad_minima']:
                    continue
                
                game_score = 0.0
                all_game_content_attributes = [attr.lower() for attr in game['categorias'] + game['tags']]
                matched_fav_genres_for_game = set() 

                for content_item in all_game_content_attributes:
                    base_weight = self.category_weights[content_item] 
                    game_score += base_weight

                    if user_fav_genres:
                        if content_item in user_fav_genres and content_item not in matched_fav_genres_for_game:
                            game_score += 0.3
                            matched_fav_genres_for_game.add(content_item)

                if game_score > 0:
                    scores.append((game_id, game_score))
            
            scores.sort(key=lambda x: x[1], reverse=True)
            num_recommendations = random.randint(min_n, max_n)
            final_recommendations_raw = scores[:min(num_recommendations, len(scores))]
            
            formatted_recommendations: List[Dict[str, Any]] = []
            for game_id, score in final_recommendations_raw:
                game_info = datos_juegos_data.get(game_id, {}).copy()
                if game_info:
                    game_info['id'] = game_id
                    game_info['score'] = round(score, 2)
                    game_info['id_user'] = user_id
                    formatted_recommendations.append(game_info)
                
            return formatted_recommendations

    cold_start_recommender = ColdStartRecommender()
    cold_start_recommender.load_game_data_from_json(datos_juegos_data)
    cold_start_recommender.calculate_category_weights_from_interactions(interacciones_data)
    cold_start_recommender.load_user_data_from_json(usuarios_data)
    return cold_start_recommender

def prepare_content_based_models(datos_juegos_data: Dict):
    """Prepara el modelo de similitud de contenido (TF-IDF)."""
    game_content_list = []
    game_ids_ordered = []

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

    tfidf_matrix = None
    content_similarity_df = pd.DataFrame()
    if not games_df_content.empty:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(games_df_content['content'])
        content_similarity_matrix = cosine_similarity(tfidf_matrix)

        content_similarity_df = pd.DataFrame(content_similarity_matrix, 
                                            index=games_df_content.index, 
                                            columns=games_df_content.index)
        # print("Recomendaciones de Contenido: Matriz de similitud calculada.")
    else:
        print("Recomendaciones de Contenido: No hay contenido de juego disponible para calcular la similitud.")
    return content_similarity_df, games_df_content

def prepare_surprise_data_and_models(interacciones_data: Dict):
    """Prepara los datos para Surprise y entrena el modelo KNN básico (item-based)."""
    surprise_formatted_data = []
    for user_interaction_entry in interacciones_data.get("interacciones", []):
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
            surprise_formatted_data.append((user_id, int(game_appid), rating))
    
    item_similarity_model = None
    trainset_global = None
    if surprise_formatted_data:
        df_global = pd.DataFrame(surprise_formatted_data, columns=['userID', 'itemID', 'rating'])
        reader_global = Reader(rating_scale=(0, 5))
        dataset_global = Dataset.load_from_df(df_global, reader_global)
        trainset_global = dataset_global.build_full_trainset()
        
        sim_options_global = {'name': 'cosine', 'user_based': False}
        item_similarity_model = KNNBasic(sim_options=sim_options_global)
        item_similarity_model.fit(trainset_global)
        # print("Modelos colaborativos: Modelo de similitud de ítems pre-entrenado.")
    else:
        print("Modelos colaborativos: No hay datos suficientes para entrenar el modelo de similitud de ítems.")
    
    return surprise_formatted_data, item_similarity_model, trainset_global

def prepare_boosting_data(interacciones_data: Dict, datos_juegos_data: Dict, usuarios_data: Dict):
    """Prepara los datos para el algoritmo de Boosting."""
    juegos_dict = {}
    usuarios_dict = {user["id"]: user for user in usuarios_data.get("usuarios", [])}
    juego_interacciones = defaultdict(list)
    game_average_rating = {}

    for appid_str, game_info_raw in datos_juegos_data.items():
        appid = int(appid_str)
        
        game_tags = [tag['description'].lower() for tag in game_info_raw.get('tags', [])]
        game_categories = [cat.lower() for cat in game_info_raw.get('categorias', [])]
        all_genres_tags = list(set(game_tags + game_categories))

        fecha_publicacion_str = game_info_raw.get("fecha_publicacion")
        fecha_lanzamiento = None
        if fecha_publicacion_str:
            parsed_date = dateparser.parse(fecha_publicacion_str, languages=["es"])
            if parsed_date:
                fecha_lanzamiento = parsed_date.strftime("%Y-%m-%d")

        processed_game_info = game_info_raw.copy()
        processed_game_info["id_juego"] = appid
        processed_game_info["generos"] = all_genres_tags
        processed_game_info["fecha_lanzamiento"] = fecha_lanzamiento
        processed_game_info.pop("fecha_publicacion", None)
        processed_game_info.pop("tags", None)
        processed_game_info.pop("categorias", None)

        juegos_dict[appid] = processed_game_info

    for user_interaction_set in interacciones_data.get("interacciones", []):
        for interaction in user_interaction_set["interacciones"]:
            game_id = interaction["id_juego"]
            if game_id in juegos_dict:
                juego_interacciones[game_id].append({"id_usuario": user_interaction_set["id"], **interaction})

    for game_id, interactions in juego_interacciones.items():
        valid_ratings = [inter["calificacion"] for inter in interactions if "calificacion" in inter]
        if valid_ratings:
            game_average_rating[game_id] = sum(valid_ratings) / len(valid_ratings)
        else:
            game_average_rating[game_id] = 0.0
    
    return juegos_dict, usuarios_dict, juego_interacciones, game_average_rating


# --- Funciones de Recomendación (extraídas de los archivos originales) ---

# --- Desde recomendacion_asociacion.py ---
def recomendar_juegos_apriori(
    user_id: int,
    reglas: pd.DataFrame,
    game_id_to_name_map: Dict[str, str],
    name_to_game_id_map: Dict[str, str],
    all_interactions_data: Dict,
    datos_juegos_map: Dict,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    juegos_gustados_usuario_nombres_set = set()
    juegos_gustados_usuario_info: List[Dict[str, Any]] = []

    for user_interaction in all_interactions_data.get('interacciones', []):
        if user_interaction.get('id') == user_id:
            for interaction in user_interaction.get('interacciones', []):
                game_id = str(interaction.get('id_juego'))
                game_name = game_id_to_name_map.get(game_id, f"Juego Desconocido ({game_id})")
                if (interaction.get('calificacion', 0) >= 3.5 or interaction.get('like', False)):
                    juegos_gustados_usuario_nombres_set.add(game_name)
                    juegos_gustados_usuario_info.append({
                        "id": game_id,
                        "nombre": game_name
                    })
            break

    recomendaciones_generadas: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}

    if juegos_gustados_usuario_nombres_set and not reglas.empty:
        for _, row in reglas.iterrows():
            antecedents_as_set = frozenset(row['antecedents'])
            if antecedents_as_set.issubset(juegos_gustados_usuario_nombres_set):
                matched_user_games = [
                    game_info for game_info in juegos_gustados_usuario_info
                    if game_info['nombre'] in antecedents_as_set
                ]
                new_recommendations = row['consequents'] - juegos_gustados_usuario_nombres_set
                for game_name_consequent in new_recommendations:
                    current_confidence = row['confidence']
                    if game_name_consequent not in recomendaciones_generadas or \
                       current_confidence > recomendaciones_generadas[game_name_consequent][0]:
                        recomendaciones_generadas[game_name_consequent] = (current_confidence, matched_user_games)

    final_recomendaciones_info: List[Dict[str, Any]] = []

    if recomendaciones_generadas:
        sorted_recommendations = sorted(
            recomendaciones_generadas.items(),
            key=lambda item: item[1][0],
            reverse=True
        )[:top_n]

        for game_name, (confidence, based_on_games) in sorted_recommendations:
            game_id = name_to_game_id_map.get(game_name)
            if game_id and game_id in datos_juegos_map:
                game_data = datos_juegos_map[game_id].copy()
                game_data['id'] = game_id
                game_data['score'] = round(confidence, 2)
                game_data['id_user'] = user_id
                game_data['based_on_games'] = based_on_games
                final_recomendaciones_info.append(game_data)
    else:
        print(f"No se encontraron recomendaciones basadas en reglas de asociación para el usuario {user_id}. Recurriendo a los juegos más populares.")
        pass

    return final_recomendaciones_info


# --- Desde recomendacion_contenido_usuario.py ---
def recomendar_juegos_tfidf(user_id, all_interactions, all_games_data, content_sim_df, games_df_content, top_n=5):
    
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
        return []

    predicted_scores = {}
    for game_id_to_predict in games_df_content.index: # Usa games_df_content para iterar sobre los juegos disponibles
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
        return []
    
    final_recommendations_info = []
    count = 0
    for game_id, score_value in recommended_games_raw:
        if count >= top_n:
            break
        game_info = all_games_data.get(game_id, {}).copy()
        if game_info:
            game_info['id'] = game_id
            game_info['score'] = round(float(score_value), 4)
            game_info['id_user'] = user_id
            final_recommendations_info.append(game_info)
            count += 1
    
    return final_recommendations_info

# --- Desde recomendaciones_colaborativo_surprise.py ---
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
        game_info = games_raw_data.get(str(game_id), {}).copy()
        if game_info:
            game_info['id'] = str(game_id)
            game_info['score'] = round(score, 2)
            game_info['id_user'] = target_user_id
            formatted_recommendations.append(game_info)
    return formatted_recommendations

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
        game_info = games_raw_data.get(str(game_id), {}).copy()
        if game_info:
            game_info['id'] = str(game_id)
            game_info['score'] = round(score, 2)
            game_info['id_user'] = target_user_id
            formatted_recommendations.append(game_info)
    return formatted_recommendations

def get_similar_games(
    target_game_id: int,
    games_raw_data: Dict,
    model: KNNBasic,
    trainset,
    top_n: int = 10
) -> List[Dict]:
    try:
        target_game_inner_id = trainset.to_inner_iid(target_game_id)
    except ValueError:
        print(f"Advertencia: El juego con ID {target_game_id} no se encontró en el trainset. No se pueden obtener juegos similares.")
        return []

    neighbors_inner_ids = model.get_neighbors(target_game_inner_id, k=top_n + 1)

    similar_games_info: List[Dict] = []
    
    for inner_id in neighbors_inner_ids:
        similar_game_id = trainset.to_raw_iid(inner_id)
        
        similarity_score = model.sim[target_game_inner_id, inner_id]

        game_info = games_raw_data.get(str(similar_game_id), {}).copy()
        if game_info:
            game_info['id'] = str(similar_game_id)
            game_info['score'] = round(similarity_score, 4)
            game_info['id_game_base'] = target_game_id
            similar_games_info.append(game_info)
        
        if len(similar_games_info) >= top_n:
            break
            
    similar_games_info.sort(key=lambda x: x['score'], reverse=True)

    return similar_games_info

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
        game_info = games_raw_data.get(str(game_id), {}).copy()
        if game_info:
            game_info['id'] = str(game_id)
            game_info['score'] = round(score, 2)
            game_info['id_user'] = target_user_id
            formatted_recommendations.append(game_info)
    return formatted_recommendations

# --- Desde recomendaciones_globales.py ---
def get_most_played_games(interacciones_data_loaded: Dict, datos_juegos_data_loaded: Dict, limit=10):
    game_playtime = defaultdict(float)
    for user_interaction in interacciones_data_loaded.get("interacciones", []):
        for interaction in user_interaction.get("interacciones", []):
            game_id = str(interaction.get("id_juego"))
            hours_played = interaction.get("horas_jugadas", 0.0)
            game_playtime[game_id] += hours_played if hours_played > 0 else 1

    sorted_games_by_playtime = sorted(game_playtime.items(), key=lambda item: item[1], reverse=True)

    top_played_games = []
    for game_id, score_value in sorted_games_by_playtime[:limit]:
        if game_id in datos_juegos_data_loaded:
            game_info = datos_juegos_data_loaded[game_id].copy()
            game_info['id'] = game_id
            game_info['score'] = round(score_value, 2)
            top_played_games.append(game_info)
    return top_played_games

def get_top_rated_games(interacciones_data_loaded: Dict, datos_juegos_data_loaded: Dict, limit=10):
    game_ratings_sum = {}
    game_ratings_count = {}

    for user_interaction in interacciones_data_loaded.get("interacciones", []):
        for interaction in user_interaction.get("interacciones", []):
            game_id = str(interaction.get("id_juego"))
            rating = interaction.get("calificacion")

            if rating is not None and isinstance(rating, (int, float)):
                game_ratings_sum[game_id] = game_ratings_sum.get(game_id, 0) + rating
                game_ratings_count[game_id] = game_ratings_count.get(game_id, 0) + 1

    game_average_ratings = {}
    for game_id, total_rating in game_ratings_sum.items():
        count = game_ratings_count[game_id]
        if count > 0:
            game_average_ratings[game_id] = total_rating / count
        else: # Si no hay calificaciones, asigna 0.0 para evitar divisiones por cero
            game_average_ratings[game_id] = 0.0

    sorted_games_by_average_rating = sorted(
        [item for item in game_average_ratings.items() if item[1] > 0], # Filtra juegos con rating > 0
        key=lambda item: item[1],
        reverse=True
    )

    top_rated_games = []
    for game_id, score_value in sorted_games_by_average_rating[:limit]:
        if game_id in datos_juegos_data_loaded:
            game_info = datos_juegos_data_loaded[game_id].copy()
            game_info['id'] = game_id
            game_info['score'] = round(score_value, 2)
            top_rated_games.append(game_info)
    return top_rated_games

# --- Función de Recomendación General con Boosting (desde recommender_boosting_flask.py) ---
def get_general_cold_start_recommendations(
    juegos_dict: Dict,
    game_average_rating: Dict,
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
        
        detailed_game_rec = {
            "appid": game_id,
            "nombre": game_info.get("nombre", "Desconocido"),
            "descripcion_corta": game_info.get("descripcion_corta", "N/A"),
            "descripcion_larga": game_info.get("descripcion_larga", "N/A"),
            "edad_minima": game_info.get("edad_minima", "N/A"),
            "generos": game_info.get("generos", []),
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


# --- Endpoints de Flask unificados ---

# Endpoints de Recomendaciones Globales
@app.route('/global/most_played', methods=['GET'])
def global_most_played_games_endpoint():
    """
    Endpoint para obtener los 10 juegos más jugados/interactuados globalmente.
    Recarga interacciones y datos de juegos en cada solicitud.
    """
    interacciones_data, datos_juegos_data, _ = _load_base_json_data()
    recommendations = get_most_played_games(interacciones_data, datos_juegos_data)

    if not recommendations:
        return jsonify({"message": "No se pudieron encontrar juegos más jugados globalmente."}), 404

    return jsonify({"recommendations": recommendations})

@app.route('/global/top_rated', methods=['GET'])
def global_top_rated_games_endpoint():
    """
    Endpoint para obtener los 10 juegos mejor valorados globalmente
    basados en su calificación promedio.
    Recarga interacciones y datos de juegos en cada solicitud.
    """
    interacciones_data, datos_juegos_data, _ = _load_base_json_data()
    recommendations = get_top_rated_games(interacciones_data, datos_juegos_data)

    if not recommendations:
        return jsonify({"message": "No se pudieron encontrar juegos mejor valorados globalmente."}), 404

    return jsonify({"recommendations": recommendations})

# Endpoint de Recomendaciones por Asociación
@app.route('/recommendations/association/<int:user_id>', methods=['GET'])
def get_apriori_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones de juegos basadas en reglas de asociación (Apriori) para un usuario específico.
    Carga datos y entrena el modelo Apriori en cada solicitud.
    """
    interacciones_data, datos_juegos_data, _ = _load_base_json_data()
    rules, game_id_to_name, name_to_game_id = prepare_apriori_models(interacciones_data, datos_juegos_data)

    if rules.empty:
        return jsonify({"error": "No se han cargado reglas de asociación o no se pudieron generar."}), 500

    recommendations = recomendar_juegos_apriori(
        user_id,
        rules,
        game_id_to_name,
        name_to_game_id,
        interacciones_data,
        datos_juegos_data,
        top_n=10
    )
    
    if not recommendations:
        return jsonify({
            "user_id": user_id,
            "recommendations": [],
            "message": "No se encontraron recomendaciones Apriori para este usuario. Podría ser un nuevo usuario o no tener interacciones relevantes."
        }), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

# Endpoint de Recomendaciones Cold Start
@app.route('/recommendations/cold-start/<int:user_id>', methods=['GET'])
def get_cold_start_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones para usuarios en "cold start"
    basadas en sus datos de perfil (edad, géneros favoritos).
    Carga datos y prepara el Cold Start Recommender en cada solicitud.
    """
    interacciones_data, datos_juegos_data, usuarios_data = _load_base_json_data()
    cold_start_recommender = prepare_cold_start_recommender(interacciones_data, datos_juegos_data, usuarios_data)

    try:
        user_exists = any(u['id'] == user_id for u in usuarios_data.get('usuarios', []))
        if not user_exists:
            return jsonify({"error": f"El usuario con ID {user_id} no se encuentra en la base de datos."}), 404

        recommendations = cold_start_recommender.recommend_for_user(user_id, min_n=5, max_n=10)
        
        if not recommendations:
            return jsonify({
                "user_id": user_id,
                "recommendations": [],
                "message": f"No se encontraron recomendaciones de cold start para el usuario ID: {user_id}. Esto puede deberse a la falta de datos de perfil o juegos adecuados."
            }), 404

        return jsonify({"user_id": user_id, "recommendations": recommendations})
    except Exception as e:
        return jsonify({"error": f"Error interno al generar recomendaciones de cold start: {e}"}), 500

# Endpoint de Recomendaciones Basadas en Contenido
@app.route('/recommendations/content-based/<int:user_id>', methods=['GET'])
def user_content_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones de juegos basadas en contenido
    para un usuario específico.
    Carga datos y prepara el modelo de contenido en cada solicitud.
    """
    interacciones_data, datos_juegos_data, usuarios_data = _load_base_json_data()
    user_exists = any(u['id'] == user_id for u in usuarios_data.get('usuarios', []))
    if not user_exists:
        return jsonify({"error": f"El usuario con ID {user_id} no se encuentra en la base de datos."}), 404

    content_similarity_df, games_df_content = prepare_content_based_models(datos_juegos_data)

    recommendations = recomendar_juegos_tfidf(
        user_id,
        interacciones_data,
        datos_juegos_data,
        content_similarity_df,
        games_df_content, # Pasar games_df_content
        top_n=10
    )

    if not recommendations:
        return jsonify({"user_id": user_id, "recommendations": [], "message": f"No se encontraron recomendaciones de contenido para el usuario {user_id}. Asegúrese de que el usuario tenga interacciones significativas."}), 404
    
    return jsonify({"user_id": user_id, "recommendations": recommendations})

# Endpoints de Recomendaciones Colaborativas (Surprise)
@app.route('/recommendations/collaborative/user-based/<int:user_id>', methods=['GET'])
def get_user_based_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones colaborativas basadas en usuario para un usuario específico.
    Carga datos y entrena el modelo KNN user-based en cada solicitud.
    Si no hay interacciones para el usuario, devuelve juegos populares.
    """
    interacciones_data, datos_juegos_data, usuarios_data = _load_base_json_data()
    surprise_formatted_data, _, _ = prepare_surprise_data_and_models(interacciones_data) 

    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones colaborativas."}), 500

    user_exists = any(u['id'] == user_id for u in usuarios_data.get('usuarios', []))
    if not user_exists:
        return jsonify({"error": f"El usuario con ID {user_id} no se encuentra en la base de datos."}), 404

    recommendations = recommend_user_based(surprise_formatted_data, datos_juegos_data, user_id)
    
    if not recommendations:
        # Si no se encontraron recomendaciones User-Based, proporcionar un fallback de juegos populares
        print(f"No se encontraron recomendaciones User-Based para el usuario ID: {user_id}. Proporcionando fallback de juegos populares.")
        
        most_played = get_most_played_games(interacciones_data, datos_juegos_data, limit=10)
        top_rated = get_top_rated_games(interacciones_data, datos_juegos_data, limit=10)
        
        fallback_recommendations = []
        seen_game_ids = set()
        
        # Intercalar recomendaciones de 5 a 10
        max_fallback_recs = random.randint(5, 10)
        
        i, j = 0, 0
        while len(fallback_recommendations) < max_fallback_recs and (i < len(top_rated) or j < len(most_played)):
            if i < len(top_rated):
                game = top_rated[i]
                if game['id'] not in seen_game_ids:
                    fallback_recommendations.append(game)
                    seen_game_ids.add(game['id'])
                i += 1
            
            if len(fallback_recommendations) < max_fallback_recs and j < len(most_played):
                game = most_played[j]
                if game['id'] not in seen_game_ids:
                    fallback_recommendations.append(game)
                    seen_game_ids.add(game['id'])
                j += 1
        
        # Si aún no hay suficientes, añadir el resto de los más jugados/mejor puntuados sin orden específico
        # (esto es poco probable si ya se intercala, pero como seguridad)
        remaining_games = []
        if i < len(top_rated):
            remaining_games.extend(top_rated[i:])
        if j < len(most_played):
            remaining_games.extend(most_played[j:])
        
        for game in remaining_games:
            if len(fallback_recommendations) < max_fallback_recs and game['id'] not in seen_game_ids:
                fallback_recommendations.append(game)
                seen_game_ids.add(game['id'])
        
        if not fallback_recommendations:
            return jsonify({
                "user_id": user_id,
                "recommendations": [],
                "message": f"No se encontraron recomendaciones User-Based para el usuario ID: {user_id}, y no se pudieron generar recomendaciones populares como fallback."
            }), 404
        
        return jsonify({"user_id": user_id, "recommendations": fallback_recommendations, "message": "Recomendaciones populares como fallback."})

    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/collaborative/item-based/<int:user_id>', methods=['GET'])
def get_item_based_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones colaborativas basadas en ítem para un usuario específico.
    Carga datos y entrena el modelo KNN item-based en cada solicitud.
    """
    interacciones_data, datos_juegos_data, usuarios_data = _load_base_json_data()
    surprise_formatted_data, _, _ = prepare_surprise_data_and_models(interacciones_data) # No necesitamos el modelo de ítems aquí

    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones colaborativas."}), 500

    user_exists = any(u['id'] == user_id for u in usuarios_data.get('usuarios', []))
    if not user_exists:
        return jsonify({"error": f"El usuario con ID {user_id} no se encuentra en la base de datos."}), 404

    recommendations = recommend_item_based(surprise_formatted_data, datos_juegos_data, user_id)
    if not recommendations:
        return jsonify({"user_id": user_id, "recommendations": [], "message": f"No se encontraron recomendaciones colaborativas Item-Based para el usuario ID: {user_id}. Es posible que no haya suficientes juegos similares o interacciones."}), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/collaborative/svd-rating/<int:user_id>', methods=['GET'])
def get_svd_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones colaborativas SVD para un usuario específico.
    Carga datos y entrena el modelo SVD en cada solicitud.
    """
    interacciones_data, datos_juegos_data, usuarios_data = _load_base_json_data()
    surprise_formatted_data, _, _ = prepare_surprise_data_and_models(interacciones_data) # No necesitamos el modelo de ítems aquí

    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones colaborativas."}), 500

    user_exists = any(u['id'] == user_id for u in usuarios_data.get('usuarios', []))
    if not user_exists:
        return jsonify({"error": f"El usuario con ID {user_id} no se encuentra en la base de datos."}), 404

    recommendations = recommend_svd_ranking(surprise_formatted_data, datos_juegos_data, user_id)
    if not recommendations:
        return jsonify({"user_id": user_id, "recommendations": [], "message": f"No se encontraron recomendaciones colaborativas SVD para el usuario ID: {user_id}. Es posible que no haya suficientes interacciones o datos para el modelo."}), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/collaborative/similar-games/<int:game_id>', methods=['GET'])
def get_similar_games_endpoint_consolidated(game_id):
    """
    Endpoint para obtener juegos similares (basado en colaborativo de ítems) para un juego específico.
    Carga datos y entrena el modelo KNN item-based en cada solicitud.
    """
    interacciones_data, datos_juegos_data, _ = _load_base_json_data()
    surprise_formatted_data, item_similarity_model, trainset_global = prepare_surprise_data_and_models(interacciones_data)

    if not item_similarity_model or not trainset_global:
        return jsonify({"error": "Modelo de similitud de ítems no entrenado o datos no cargados."}), 500

    if str(game_id) not in datos_juegos_data:
        return jsonify({"error": f"El juego con ID {game_id} no se encuentra en la base de datos de juegos."}), 404

    similar_games = get_similar_games(game_id, datos_juegos_data, item_similarity_model, trainset_global)
    
    if not similar_games:
        return jsonify({"message": f"No se encontraron juegos similares para el juego ID: {game_id}."}), 404

    return jsonify({"target_game_id": game_id, "similar_games": similar_games})

# --- Nuevos Endpoints de Boosting (desde recommender_boosting_flask.py) ---
@app.route('/recommend/rpg', methods=['GET'])
def recommend_rpg_games():
    """
    Endpoint para recomendar juegos de 'rol' con boosting, sin filtro de fecha.
    Carga datos y prepara los datos para boosting en cada solicitud.
    """
    interacciones_data, datos_juegos_data, usuarios_data = _load_base_json_data()
    juegos_dict, _, _, game_average_rating = prepare_boosting_data(interacciones_data, datos_juegos_data, usuarios_data)

    recommendations = get_general_cold_start_recommendations(
        juegos_dict,
        game_average_rating,
        num_recommendations=5,
        target_category="rol",
        category_boost_factor=2.0,
        strict_category_filter=False
    )
    if not recommendations:
        return jsonify({"message": "No se encontraron recomendaciones de juegos de rol."}), 404
    return jsonify({"recommendations": recommendations})

@app.route('/recommend/action2025', methods=['GET'])
def recommend_action_2025_games():
    """
    Endpoint para recomendar juegos de 'acción' lanzados entre 2025-01-01 y 2025-05-22.
    Carga datos y prepara los datos para boosting en cada solicitud.
    """
    interacciones_data, datos_juegos_data, usuarios_data = _load_base_json_data()
    juegos_dict, _, _, game_average_rating = prepare_boosting_data(interacciones_data, datos_juegos_data, usuarios_data)

    recommendations = get_general_cold_start_recommendations(
        juegos_dict,
        game_average_rating,
        num_recommendations=5,
        target_category="acción",
        date_start="2025-01-01",
        date_end="2025-05-22",
        category_boost_factor=1.5,
        date_boost_factor=1.8,
        strict_category_filter=False,
        strict_date_filter=True
    )
    if not recommendations:
        return jsonify({"message": "No se encontraron recomendaciones de juegos de acción para el período especificado."}), 404
    return jsonify({"recommendations": recommendations})


# Ruta raíz para verificar que la API está activa
@app.route('/', methods=['GET'])
def home():
    return "API de Recomendación de Videojuegos Activa!"

# Punto de entrada principal para ejecutar la aplicación Flask
if __name__ == '__main__':
    # No se llama a initialize_models_and_data() aquí.
    # Cada endpoint cargará y entrenará lo que necesite.
    print("La API está activa. Los modelos se entrenarán por solicitud en cada endpoint.")
    app.run(debug=True, port=5000)