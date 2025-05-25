from flask import Flask, request, jsonify
import numpy as np
from collections import defaultdict
from typing import List, Dict, Tuple, Any
import json
import random

app = Flask(__name__)

# Instancia global del recomendador de cold start
cold_start_recommender = None

class ColdStartRecommender:
    def __init__(self):
        self.user_profiles: Dict[int, Dict] = {}  # {user_id: {'nombre': str, 'edad': int, 'generos_favoritos': List[str]}}
        self.game_features: Dict[str, Dict] = {}  # {game_id (str): {'nombre': str, 'categorias': List[str], 'tags': List[str], 'edad_minima': int}}
        # Usamos defaultdict para que las categorías/tags no calculadas tengan un peso por defecto
        self.category_weights: Dict[str, float] = defaultdict(lambda: 0.5)

    def load_game_data_from_json(self, filepath="datos_juegos.json"):
        """
        Carga los datos de los juegos desde el archivo JSON y popula game_features.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                games_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: El archivo '{filepath}' no se encontró para los datos de juegos.")
            return

        for appid, game_info in games_data.items():
            game_id_str = str(appid)
            nombre = game_info.get("nombre", "Desconocido")
            categorias = game_info.get("categorias", [])
            tags = [tag.get("description") for tag in game_info.get("tags", []) if tag.get("description")]
            
            edad_minima_str = game_info.get("edad_minima", "0")
            try:
                edad_minima = int(edad_minima_str)
            except ValueError:
                edad_minima = 0 # Default if not a valid number

            self.game_features[game_id_str] = {
                'nombre': nombre,
                'categorias': categorias,
                'tags': tags,
                'edad_minima': edad_minima
            }
        print(f"Cargados {len(self.game_features)} juegos del archivo '{filepath}'.")
    
    def load_user_data_from_json(self, filepath="usuarios.json"):
        """
        Carga los datos de los usuarios desde el archivo JSON y popula user_profiles.
        Solo se cargan los datos de perfil (edad, géneros favoritos), no interacciones individuales.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                users_data_raw = json.load(f)
        except FileNotFoundError:
            print(f"Error: El archivo '{filepath}' no se encontró para los datos de usuarios.")
            return

        for user_profile in users_data_raw.get("usuarios", []):
            user_id = user_profile.get("id")
            if user_id is not None:
                self.user_profiles[user_id] = {
                    'nombre': user_profile.get("nombre", "Desconocido"),
                    'edad': user_profile.get("edad", 0),
                    'generos_favoritos': user_profile.get("generos_favoritos", [])
                }
        print(f"Cargados {len(self.user_profiles)} usuarios del archivo '{filepath}'.")

    def calculate_category_weights_from_interactions(self, interactions_filepath="interacciones.json"):
        """
        Calcula los pesos de las categorías/tags basándose en el promedio de las calificaciones
        en el historial de interacciones de los usuarios.
        Esto se usa para el "conocimiento general" del sistema, no para usuarios individuales.
        """
        try:
            with open(interactions_filepath, 'r', encoding='utf-8') as f:
                interactions_data_raw = json.load(f)
        except FileNotFoundError:
            print(f"Error: El archivo '{interactions_filepath}' no se encontró. No se pudieron calcular los pesos de categorías.")
            return

        category_ratings_sum = defaultdict(float)
        category_ratings_count = defaultdict(int)

        for user_interaction_entry in interactions_data_raw.get("interacciones", []):
            for game_played in user_interaction_entry.get("interacciones", []):
                game_appid = str(game_played["id_juego"])
                
                if game_appid in self.game_features:
                    game_info = self.game_features[game_appid]
                    
                    rating = 0.0
                    if "calificacion" in game_played and game_played["calificacion"] is not None:
                        try:
                            rating = float(game_played["calificacion"])
                        except ValueError:
                            rating = 0.0 # Default if not a valid number
                    elif game_played.get("like"):
                        rating = 5.0 # Assume a 'like' is a perfect 5
                    # Si no hay calificación ni like, se asume un rating bajo
                    elif not game_played.get("like") and game_played.get("calificacion") is None:
                        rating = 1.0 # Considerar como una interacción de bajo interés
                    
                    all_game_content_attributes = game_info.get('categorias', []) + game_info.get('tags', [])
                    for attribute in all_game_content_attributes:
                        normalized_attribute = attribute.lower()
                        category_ratings_sum[normalized_attribute] += rating
                        category_ratings_count[normalized_attribute] += 1
        
        for category, total_rating in category_ratings_sum.items():
            count = category_ratings_count[category]
            if count > 0:
                # Normalizar el promedio a una escala de 0 a 1 (e.g., 5.0 rating -> 1.0 score)
                self.category_weights[category] = (total_rating / count) / 5.0
            else:
                self.category_weights[category] = 0.5 # Default if no interactions

        print(f"Pesos de categorías actualizados basados en {len(interactions_data_raw.get('interacciones', []))} interacciones de usuarios.")


    def recommend_for_user(self, user_id: int, min_n: int = 5, max_n: int = 10) -> List[Dict[str, Any]]:
        """
        Genera recomendaciones basadas en la edad del usuario y sus géneros/categorías favoritos,
        utilizando los pesos de categorías calculados globalmente.
        Devuelve entre min_n y max_n juegos en formato Dict.
        """
        if user_id not in self.user_profiles:
            raise ValueError(f"Usuario con ID {user_id} no registrado en los perfiles de cold start.")
            
        user = self.user_profiles[user_id]
        user_age = user['edad']
        user_fav_genres = [g.lower() for g in user['generos_favoritos']] # Normalizar los géneros favoritos

        scores: List[Tuple[str, float]] = []
        
        for game_id, game in self.game_features.items():
            # 1. Filtrar por edad mínima
            if user_age < game['edad_minima']:
                continue
            
            game_score = 0.0
            
            # 2. Calcular puntaje basado en categorías y tags del juego usando los pesos derivados
            all_game_content_attributes = [attr.lower() for attr in game['categorias'] + game['tags']] # Normalizar atributos del juego
            
            # Usar un set para evitar duplicar el bonus si un género favorito aparece como categoría y tag
            matched_fav_genres_for_game = set() 

            for content_item in all_game_content_attributes:
                # Obtener el peso de la categoría/tag del mapa calculado
                # defaultdict se encarga de dar un valor por defecto si no existe
                base_weight = self.category_weights[content_item] 
                game_score += base_weight

                # 3. Bonus si coincide con categorías/géneros favoritos del usuario
                if user_fav_genres:
                    if content_item in user_fav_genres and content_item not in matched_fav_genres_for_game:
                        # Aumentar peso para coincidencias con géneros favoritos del usuario
                        game_score += 0.3 # Añadir un bonus fijo
                        matched_fav_genres_for_game.add(content_item) # Marcar como ya usado el bonus

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
                "score": round(score, 2) # Redondear el score a 2 decimales
            })
            
        return formatted_recommendations

# --- Inicialización y carga del recomendador de cold start al inicio de la app ---
with app.app_context():
    cold_start_recommender = ColdStartRecommender()
    print("Iniciando carga y entrenamiento del recomendador Cold Start...")
    cold_start_recommender.load_game_data_from_json(filepath="datos_juegos.json")
    cold_start_recommender.calculate_category_weights_from_interactions(interactions_filepath="interacciones.json")
    cold_start_recommender.load_user_data_from_json(filepath="usuarios.json")
    print("Recomendador Cold Start listo.")

# --- Endpoint de Flask para Recomendaciones Cold Start (MODIFICADO A GET) ---
@app.route('/recommendations/cold-start/<int:user_id>', methods=['GET'])
def get_cold_start_recommendations(user_id):
    """
    Endpoint para obtener recomendaciones para usuarios en "cold start"
    basadas en sus datos de perfil (edad, géneros favoritos).
    El user_id se pasa como parte de la URL.
    """
    if cold_start_recommender is None:
        return jsonify({"error": "El sistema de recomendación Cold Start no está inicializado."}), 500

    try:
        recommendations = cold_start_recommender.recommend_for_user(user_id, min_n=5, max_n=10)
        
        if not recommendations:
            return jsonify({
                "user_id": user_id,
                "recommendations": [],
                "message": f"No se encontraron recomendaciones de cold start para el usuario ID: {user_id}. Asegúrate de que el usuario exista y cumpla con los criterios de edad."
            }), 404 # 404 Not Found, ya que el recurso no se pudo generar para ese ID.

        return jsonify({"user_id": user_id, "recommendations": recommendations})
    except ValueError as e:
        # Esto captura el error si el user_id no está en los perfiles cargados
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Error interno al generar recomendaciones de cold start: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)