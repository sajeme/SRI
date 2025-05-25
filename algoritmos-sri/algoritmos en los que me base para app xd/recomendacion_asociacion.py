from flask import Flask, request, jsonify
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
import json
from typing import List, Dict, Any, Tuple

app = Flask(__name__)

# REGLAS: Si te gusta ELDEN RING, te puede gustar DS3
# REGLAS: Como te gustaron X1, X2, ..., Xn juegos, tambien de pueden gustar Y1, Y1, ... Yn juegos

# Variables globales para almacenar los datos cargados y las reglas de asociación
# Se cargarán una vez al iniciar la aplicación para optimizar el rendimiento.
interacciones_data: Dict = {}
datos_juegos_data: Dict = {}
usuarios_data: Dict = {}
game_id_to_name: Dict[str, str] = {}
name_to_game_id: Dict[str, str] = {}
rules: pd.DataFrame = pd.DataFrame() # DataFrame para almacenar las reglas de asociación

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

def prepare_apriori_data_and_generate_rules():
    """
    Prepara los datos para Apriori y genera las reglas de asociación.
    Esta función se ejecuta solo una vez al iniciar la aplicación.
    """
    global interacciones_data, datos_juegos_data, usuarios_data, game_id_to_name, name_to_game_id, rules

    interacciones_data = load_json_data('interacciones.json')
    datos_juegos_data = load_json_data('datos_juegos.json')
    usuarios_data = load_json_data('usuarios.json')

    if not (interacciones_data and datos_juegos_data and usuarios_data):
        print("No se pudieron cargar todos los archivos JSON necesarios. Las recomendaciones Apriori pueden no funcionar.")
        return

    # Crear mapeo de IDs de juegos a nombres y viceversa
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

            # Criterio: un juego se considera 'jugado y gustado' si la calificación es >= 3.5 O 'like' es verdadero
            if (interaction.get('calificacion', 0) >= 3.5 or interaction.get('like', False)):
                user_game_matrix[user_id][game_name] = 1
            else:
                user_game_matrix[user_id][game_name] = 0

    df_games = pd.DataFrame.from_dict(user_game_matrix, orient='index').fillna(0).astype(bool)

    if df_games.empty:
        print("La matriz de usuario-juego está vacía. No se pueden generar reglas de asociación.")
        return

    # Generar Itemsets Frecuentes y Reglas de Asociación
    try:
        # Ajusta min_support y min_threshold si es necesario para tu dataset
        frequent_itemsets = apriori(df_games, min_support=0.01, use_colnames=True)
        rules = association_rules(frequent_itemsets, metric='confidence', min_threshold=0.05)
        print(f"Número de itemsets frecuentes encontrados: {len(frequent_itemsets)}")
        print(f"Número de reglas de asociación encontradas: {len(rules)}")
    except Exception as e:
        print(f"Error al generar reglas de asociación: {e}")
        rules = pd.DataFrame() # Asegurar que rules sea un DataFrame vacío en caso de error


# --- Función de Recomendación Principal para Apriori ---
def recomendar_juegos_apriori(
    user_id: int,
    reglas: pd.DataFrame,
    game_id_to_name_map: Dict[str, str],
    name_to_game_id_map: Dict[str, str],
    all_interactions_data: Dict,
    datos_juegos_map: Dict,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Genera recomendaciones de juegos para un usuario específico utilizando reglas de asociación Apriori.
    Incluye un fallback a recomendaciones globales si no se encuentran reglas específicas para el usuario.
    La salida incluye los juegos del usuario que activaron la recomendación.
    """
    juegos_gustados_usuario_nombres_set = set()
    juegos_gustados_usuario_info: List[Dict[str, Any]] = []

    # Recopilar juegos 'gustados' por el usuario
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
            break # Una vez que se encuentra el usuario, salimos del bucle

    recomendaciones_generadas: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {} # {game_name: (max_confidence, [based_on_games])}

    if juegos_gustados_usuario_nombres_set and not reglas.empty:
        # Buscar reglas donde los antecedentes sean un subconjunto de los juegos gustados del usuario
        for _, row in reglas.iterrows():
            antecedents_as_set = frozenset(row['antecedents']) # Convertir a frozenset para comparación
            if antecedents_as_set.issubset(juegos_gustados_usuario_nombres_set):
                # Obtener los juegos del usuario que coinciden con los antecedentes de esta regla
                matched_user_games = [
                    game_info for game_info in juegos_gustados_usuario_info
                    if game_info['nombre'] in antecedents_as_set
                ]

                # Excluir juegos que el usuario ya ha jugado
                new_recommendations = row['consequents'] - juegos_gustados_usuario_nombres_set
                for game_name_consequent in new_recommendations:
                    current_confidence = row['confidence']
                    
                    # Guardar la recomendación con la confianza más alta y sus juegos base
                    if game_name_consequent not in recomendaciones_generadas or \
                       current_confidence > recomendaciones_generadas[game_name_consequent][0]:
                        recomendaciones_generadas[game_name_consequent] = (current_confidence, matched_user_games)

    final_recomendaciones_info: List[Dict[str, Any]] = []

    if recomendaciones_generadas:
        # Ordenar recomendaciones por confianza y seleccionar las top_n
        sorted_recommendations = sorted(
            recomendaciones_generadas.items(),
            key=lambda item: item[1][0], # Ordenar por la confianza (primer elemento de la tupla)
            reverse=True
        )[:top_n]

        for game_name, (confidence, based_on_games) in sorted_recommendations:
            game_id = name_to_game_id_map.get(game_name)
            if game_id:
                final_recomendaciones_info.append({
                    "id": game_id,
                    "nombre": game_name,
                    "score": round(confidence, 2), # Usamos la confianza como "score"
                    "based_on_games": based_on_games # Incluye los juegos que activaron la regla
                })
    else:
        # Fallback: Si no hay juegos gustados que activen reglas, o no hay reglas para el usuario,
        # se recomiendan los juegos más populares globalmente.
        print(f"No se encontraron recomendaciones basadas en reglas de asociación para el usuario {user_id}. Recurriendo a los juegos más populares.")
        
        popular_games_list = sorted(
            datos_juegos_map.items(),
            key=lambda item: item[1].get('popularity_score', 0), # Asume un 'popularity_score' si lo tienes, o un valor por defecto.
            reverse=True
        )
        
        # Filtrar juegos ya jugados por el usuario y limitar al top_n
        count = 0
        for game_id, details in popular_games_list:
            game_name = game_id_to_name_map.get(game_id, f"Juego Desconocido ({game_id})")
            # Asegurarse de no recomendar juegos que el usuario ya ha "gustado"
            if game_name not in juegos_gustados_usuario_nombres_set:
                final_recomendaciones_info.append({
                    "id": game_id,
                    "nombre": game_name,
                    "score": None # No hay score de confianza aquí, ya que no viene de una regla específica.
                })
                count += 1
                if count >= top_n:
                    break

    return final_recomendaciones_info

# --- Cargar datos y generar reglas al iniciar la aplicación Flask ---
with app.app_context():
    prepare_apriori_data_and_generate_rules()

# --- Endpoint de Flask para Recomendaciones Apriori (MODIFICADO A GET) ---
@app.route('/recommendations/apriori/<int:user_id>', methods=['GET'])
def get_apriori_recommendations(user_id):
    """
    Endpoint para obtener recomendaciones de juegos basadas en reglas de asociación Apriori para un usuario específico.
    El user_id se pasa como parte de la URL.
    """
    if rules.empty:
        # Se devuelve un 500 porque el servidor no pudo generar las reglas necesarias.
        return jsonify({"error": "No se han cargado reglas de asociación o no se pudieron generar. Intenta reiniciar el servidor si los archivos existen y los parámetros son adecuados."}), 500

    recommendations = recomendar_juegos_apriori(
        user_id,
        rules,
        game_id_to_name,
        name_to_game_id,
        interacciones_data,
        datos_juegos_data,
        top_n=10 # Puedes ajustar este número
    )
    
    # Si no hay recomendaciones específicas para el usuario (ni siquiera el fallback encontró algo),
    # se devuelve un mensaje informativo sin error HTTP.
    if not recommendations:
        return jsonify({
            "user_id": user_id,
            "recommendations": [],
            "message": "No se encontraron recomendaciones Apriori para este usuario. Asegúrate de que el usuario haya calificado juegos o que existan reglas de asociación aplicables."
        }), 404 # 404 Not Found, ya que el recurso (recomendaciones para ese user_id) no se pudo generar.

    return jsonify({"user_id": user_id, "recommendations": recommendations})

if __name__ == '__main__':
    app.run(debug=True, port=5000)