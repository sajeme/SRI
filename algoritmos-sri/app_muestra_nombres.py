import json
import pandas as pd
import numpy as np
import random
from collections import defaultdict
from typing import List, Dict, Any, Tuple

from flask import Flask, request, jsonify

# Importar las bibliotecas específicas de cada módulo
# Para recomendacion_asociacion.py
from mlxtend.frequent_patterns import apriori, association_rules

# Para recomendacion_contenido_usuario.py
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# Para recomendaciones_colaborativo_surprise.py
from surprise import Dataset, Reader, KNNBasic, SVD


app = Flask(__name__)

# --- Variables Globales para cargar datos una sola vez ---
interacciones_data: Dict = {}
datos_juegos_data: Dict = {}
usuarios_data: Dict = {}

# Para Apriori
game_id_to_name: Dict[str, str] = {}
name_to_game_id: Dict[str, str] = {}
rules: pd.DataFrame = pd.DataFrame()

# Para Cold Start
cold_start_recommender = None # Se inicializará como una instancia de ColdStartRecommender

# Para Contenido (TF-IDF)
games_df_content: pd.DataFrame = pd.DataFrame()
tfidf_matrix = None
content_similarity_df: pd.DataFrame = pd.DataFrame()

# Para Colaborativo (Surprise)
surprise_formatted_data: List[Tuple[int, int, float]] = []
item_similarity_model = None
trainset_global = None


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

# --- Lógica de Inicialización de todos los Modelos y Carga de Datos ---
# Se ejecutará una sola vez al iniciar la aplicación
with app.app_context():
    print("Iniciando carga de datos y pre-cálculo de modelos...")

    # Carga de datos base (comunes a varios módulos)
    interacciones_data = load_json_data('interacciones.json')
    datos_juegos_data = load_json_data('datos_juegos.json')
    usuarios_data = load_json_data('usuarios.json')

    if not (interacciones_data and datos_juegos_data and usuarios_data):
        print("Advertencia: No se pudieron cargar todos los archivos JSON necesarios. Algunas recomendaciones pueden no funcionar.")

    # --- Inicialización para Apriori (recomendacion_asociacion.py) ---
    print("Preparando Apriori...")
    if datos_juegos_data:
        game_id_to_name = {str(game_id): details['nombre'] for game_id, details in datos_juegos_data.items()}
        name_to_game_id = {details['nombre']: str(game_id) for game_id, details in datos_juegos_data.items()}

    user_game_matrix = {}
    if interacciones_data:
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

    if not df_games.empty:
        try:
            frequent_itemsets = apriori(df_games, min_support=0.01, use_colnames=True)
            rules = association_rules(frequent_itemsets, metric='confidence', min_threshold=0.05)
            print(f"Apriori: {len(frequent_itemsets)} itemsets frecuentes, {len(rules)} reglas de asociación.")
        except Exception as e:
            print(f"Error al generar reglas de asociación Apriori: {e}")
            rules = pd.DataFrame()
    else:
        print("Apriori: Matriz de usuario-juego vacía, no se generaron reglas.")

    # --- Inicialización para Cold Start (recomendacion_coldstart_edad_categorias.py) ---
    print("Preparando Cold Start Recommender...")
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
            print(f"Cold Start: Cargados {len(self.game_features)} juegos.")
        
        def load_user_data_from_json(self, users_data_loaded: Dict):
            for user_profile in users_data_loaded.get("usuarios", []):
                user_id = user_profile.get("id")
                if user_id is not None:
                    self.user_profiles[user_id] = {
                        'nombre': user_profile.get("nombre", "Desconocido"),
                        'edad': user_profile.get("edad", 0),
                        'generos_favoritos': user_profile.get("generos_favoritos", [])
                    }
            print(f"Cold Start: Cargados {len(self.user_profiles)} usuarios.")

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

            print(f"Cold Start: Pesos de categorías actualizados.")

        def recommend_for_user(self, user_id: int, min_n: int = 5, max_n: int = 10) -> List[Dict[str, Any]]:
            if user_id not in self.user_profiles:
                raise ValueError(f"Usuario con ID {user_id} no registrado en los perfiles de cold start.")
                
            user = self.user_profiles[user_id]
            user_age = user['edad']
            user_fav_genres = [g.lower() for g in user['generos_favoritos']]

            scores: List[Tuple[str, float]] = []
            
            for game_id, game in self.game_features.items():
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
                game_name = self.game_features.get(game_id, {}).get('nombre', 'Nombre Desconocido')
                formatted_recommendations.append({
                    "id": game_id,
                    "nombre": game_name,
                    "score": round(score, 2)
                })
                
            return formatted_recommendations

    cold_start_recommender = ColdStartRecommender()
    cold_start_recommender.load_game_data_from_json(datos_juegos_data)
    cold_start_recommender.calculate_category_weights_from_interactions(interacciones_data)
    cold_start_recommender.load_user_data_from_json(usuarios_data)
    print("Cold Start Recommender listo.")

    # --- Inicialización para Contenido (recomendacion_contenido_usuario.py) ---
    print("Preparando recomendaciones basadas en Contenido...")
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

    if not games_df_content.empty:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(games_df_content['content'])
        content_similarity_matrix = cosine_similarity(tfidf_matrix)

        content_similarity_df = pd.DataFrame(content_similarity_matrix, 
                                            index=games_df_content.index, 
                                            columns=games_df_content.index)
        print("Recomendaciones de Contenido: Matriz de similitud calculada.")
    else:
        print("Recomendaciones de Contenido: No hay contenido de juego disponible para calcular la similitud.")

    # --- Inicialización para Colaborativo (recomendaciones_colaborativo_surprise.py) ---
    print("Preparando modelos colaborativos...")
    def prepare_surprise_data(
        interactions_data_loaded: Dict,
        games_data_loaded: Dict, # No se usa directamente aquí, pero se mantiene para consistencia
        users_data_loaded: Dict # No se usa directamente aquí, pero se mantiene para consistencia
    ) -> List[Tuple[int, int, float]]:
        surprise_data = []
        for user_interaction_entry in interactions_data_loaded.get("interacciones", []):
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

    if interacciones_data and datos_juegos_data and usuarios_data:
        surprise_formatted_data = prepare_surprise_data(
            interacciones_data,
            datos_juegos_data,
            usuarios_data
        )
        
        if surprise_formatted_data:
            df_global = pd.DataFrame(surprise_formatted_data, columns=['userID', 'itemID', 'rating'])
            reader_global = Reader(rating_scale=(0, 5))
            dataset_global = Dataset.load_from_df(df_global, reader_global)
            trainset_global = dataset_global.build_full_trainset()
            
            sim_options_global = {'name': 'cosine', 'user_based': False}
            item_similarity_model = KNNBasic(sim_options=sim_options_global)
            item_similarity_model.fit(trainset_global)
            print("Modelos colaborativos: Modelo de similitud de ítems pre-entrenado.")
        else:
            print("Modelos colaborativos: No hay datos suficientes para entrenar el modelo de similitud de ítems.")
    else:
        print("Modelos colaborativos: Fallo al cargar datos para entrenar.")
    
    print("Todos los modelos y datos pre-cargados listos.")

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
            if game_id:
                final_recomendaciones_info.append({
                    "id": game_id,
                    "nombre": game_name,
                    "score": round(confidence, 2),
                    "based_on_games": based_on_games
                })
    else:
        print(f"No se encontraron recomendaciones basadas en reglas de asociación para el usuario {user_id}. Recurriendo a los juegos más populares.")
        
        count = 0
        for game_id, details in datos_juegos_data.items(): # Itera sobre todos los juegos cargados
            game_name = game_id_to_name_map.get(game_id, f"Juego Desconocido ({game_id})")
            if game_name not in juegos_gustados_usuario_nombres_set:
                final_recomendaciones_info.append({
                    "id": game_id,
                    "nombre": game_name,
                    "score": None # No hay score de confianza aquí
                })
                count += 1
                if count >= top_n:
                    break

    return final_recomendaciones_info


# --- Desde recomendacion_contenido_usuario.py ---
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
    for game_id_to_predict in games_df_content.index: # Usar games_df_content.index que ya está cargado globalmente
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
                    else: # If no rating, assume a max rating for 'like' or 'horas_jugadas'
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
            final_recommendations_info.append({
                "id": game_id,
                "nombre": game_name,
                "score": round(float(score_value), 4)
            })
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
        game_name = games_raw_data.get(str(game_id), {}).get("nombre", f"Juego Desconocido (ID: {game_id})")
        formatted_recommendations.append({
            "id": str(game_id),
            "nombre": game_name,
            "score": round(score, 2)
        })
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
        game_name = games_raw_data.get(str(game_id), {}).get("nombre", f"Juego Desconocido (ID: {game_id})")
        formatted_recommendations.append({
            "id": str(game_id),
            "nombre": game_name,
            "score": round(score, 2)
        })
    return formatted_recommendations

def get_similar_games(
    target_game_id: int,
    games_raw_data: Dict,
    model: KNNBasic, # Se pasa el modelo pre-entrenado
    trainset,        # Se pasa el trainset para obtener los inner_id
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
        if inner_id == target_game_inner_id:
            continue
        
        similar_game_id = trainset.to_raw_iid(inner_id)
        game_name = games_raw_data.get(str(similar_game_id), {}).get("nombre", f"Juego Desconocido (ID: {similar_game_id})")
        
        # Similitud de ítems se accede a través de la matriz de similitud del modelo
        # Los índices inner_id corresponden a las filas/columnas de la matriz sim
        similarity_score = model.sim[target_game_inner_id, inner_id]

        similar_games_info.append({
            "id": str(similar_game_id),
            "nombre": game_name,
            "score": round(similarity_score, 4)
        })
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
        game_name = games_raw_data.get(str(game_id), {}).get("nombre", f"Juego Desconocido (ID: {game_id})")
        formatted_recommendations.append({
            "id": str(game_id),
            "nombre": game_name,
            "score": round(score, 2)
        })
    return formatted_recommendations

# --- Desde recomendaciones_globales.py ---
def get_most_played_games(interacciones_data_loaded: Dict, datos_juegos_data_loaded: Dict, limit=10):
    game_mentions = {}
    for user_interaction in interacciones_data_loaded.get("interacciones", []):
        for interaction in user_interaction.get("interacciones", []):
            game_id = str(interaction.get("id_juego"))
            game_mentions[game_id] = game_mentions.get(game_id, 0) + 1

    sorted_games_by_mentions = sorted(game_mentions.items(), key=lambda item: item[1], reverse=True)

    top_played_games = []
    for game_id, count in sorted_games_by_mentions[:limit]:
        if game_id in datos_juegos_data_loaded:
            game_info = datos_juegos_data_loaded[game_id]
            top_played_games.append({
                "id": game_id,
                "nombre": game_info.get("nombre", "Nombre no disponible"),
                "interacciones": count
            })
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

    sorted_games_by_average_rating = sorted(
        [item for item in game_average_ratings.items() if item[1] > 0],
        key=lambda item: item[1],
        reverse=True
    )

    top_rated_games = []
    for game_id, avg_rating in sorted_games_by_average_rating[:limit]:
        if game_id in datos_juegos_data_loaded:
            game_info = datos_juegos_data_loaded[game_id]
            top_rated_games.append({
                "id": game_id,
                "nombre": game_info.get("nombre", "Nombre no disponible"),
                "calificacion_promedio": round(avg_rating, 2)
            })
    return top_rated_games


# --- Endpoints de Flask unificados ---

# Endpoints de Recomendaciones Globales
@app.route('/global/most_played', methods=['GET'])
def global_most_played_games_endpoint():
    """
    Endpoint para obtener los 10 juegos más jugados/interactuados globalmente.
    """
    recommendations = get_most_played_games(interacciones_data, datos_juegos_data)

    if "error" in recommendations:
        return jsonify(recommendations), 500
    
    if not recommendations:
        return jsonify({"message": "No se pudieron encontrar juegos más jugados globalmente."}), 404

    return jsonify(recommendations)

@app.route('/global/top_rated', methods=['GET'])
def global_top_rated_games_endpoint():
    """
    Endpoint para obtener los 10 juegos mejor valorados globalmente
    basados en su calificación promedio.
    """
    recommendations = get_top_rated_games(interacciones_data, datos_juegos_data)

    if "error" in recommendations:
        return jsonify(recommendations), 500
    
    if not recommendations:
        return jsonify({"message": "No se pudieron encontrar juegos mejor valorados globalmente."}), 404

    return jsonify(recommendations)

# Endpoint de Recomendaciones por Asociación
@app.route('/recommendations/association/<int:user_id>', methods=['GET'])
def get_apriori_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones de juegos basadas en reglas de asociación (Apriori) para un usuario específico.
    """
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
            "message": "No se encontraron recomendaciones Apriori para este usuario."
        }), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

# Endpoint de Recomendaciones Cold Start
@app.route('/recommendations/cold-start/<int:user_id>', methods=['GET'])
def get_cold_start_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones para usuarios en "cold start"
    basadas en sus datos de perfil (edad, géneros favoritos).
    """
    if cold_start_recommender is None:
        return jsonify({"error": "El sistema de recomendación Cold Start no está inicializado."}), 500

    try:
        recommendations = cold_start_recommender.recommend_for_user(user_id, min_n=5, max_n=10)
        
        if not recommendations:
            return jsonify({
                "user_id": user_id,
                "recommendations": [],
                "message": f"No se encontraron recomendaciones de cold start para el usuario ID: {user_id}."
            }), 404

        return jsonify({"user_id": user_id, "recommendations": recommendations})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Error interno al generar recomendaciones de cold start: {e}"}), 500

# Endpoint de Recomendaciones Basadas en Contenido
@app.route('/recommendations/content-based/<int:user_id>', methods=['GET'])
def user_content_recommendations_endpoint(user_id):
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
        top_n=10
    )

    if "error" in recommendations:
        return jsonify(recommendations), 500
    elif "message" in recommendations:
        return jsonify(recommendations), 404
    
    return jsonify(recommendations)

# Endpoints de Recomendaciones Colaborativas (Surprise)
@app.route('/recommendations/collaborative/user-based/<int:user_id>', methods=['GET'])
def get_user_based_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones colaborativas basadas en usuario para un usuario específico.
    """
    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones colaborativas."}), 500

    recommendations = recommend_user_based(surprise_formatted_data, datos_juegos_data, user_id)
    if not recommendations:
        return jsonify({"message": f"No se encontraron recomendaciones colaborativas User-Based para el usuario ID: {user_id}"}), 404
        
    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/collaborative/item-based/<int:user_id>', methods=['GET'])
def get_item_based_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones colaborativas basadas en ítem para un usuario específico.
    """
    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones colaborativas."}), 500

    recommendations = recommend_item_based(surprise_formatted_data, datos_juegos_data, user_id)
    if not recommendations:
        return jsonify({"message": f"No se encontraron recomendaciones colaborativas Item-Based para el usuario ID: {user_id}"}), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/collaborative/svd-rating/<int:user_id>', methods=['GET'])
def get_svd_recommendations_endpoint(user_id):
    """
    Endpoint para obtener recomendaciones colaborativas SVD para un usuario específico.
    """
    if not surprise_formatted_data:
        return jsonify({"error": "Datos no cargados para recomendaciones colaborativas."}), 500

    recommendations = recommend_svd_ranking(surprise_formatted_data, datos_juegos_data, user_id)
    if not recommendations:
        return jsonify({"message": f"No se encontraron recomendaciones colaborativas SVD para el usuario ID: {user_id}"}), 404

    return jsonify({"user_id": user_id, "recommendations": recommendations})

@app.route('/recommendations/collaborative/similar-games/<int:game_id>', methods=['GET'])
def get_similar_games_endpoint_consolidated(game_id):
    """
    Endpoint para obtener juegos similares (basado en colaborativo de ítems) para un juego específico.
    """
    if not item_similarity_model or not trainset_global:
        return jsonify({"error": "Modelo de similitud de ítems no entrenado o datos no cargados."}), 500

    if str(game_id) not in datos_juegos_data:
        return jsonify({"error": f"El juego con ID {game_id} no se encuentra en la base de datos de juegos."}), 404

    similar_games = get_similar_games(game_id, datos_juegos_data, item_similarity_model, trainset_global)
    
    if not similar_games:
        return jsonify({"message": f"No se encontraron juegos similares para el juego ID: {game_id}"}), 404

    return jsonify({"target_game_id": game_id, "similar_games": similar_games})

# --- Punto de entrada principal para ejecutar la aplicación Flask ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)