from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import json
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


TMDB_API_KEY = '9d1bbbbde65732d68b3d9fafccd663c3'

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)


def get_game_info(appid):
    url = f'https://store.steampowered.com/api/appdetails?appids={appid}'
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json().get(str(appid), {})
        if data.get('success'):
            game = data['data']
            genres = ' '.join([g['description'] for g in game.get('genres', [])])
            return {
                'id': appid,
                'title': game.get('name', ''),
                'genres': genres,
                'overview': game.get('short_description', '')
            }
    print(f"[Error Steam] appid {appid}")
    return None

@app.route('/steamspy/details/<int:appid>', methods=['GET'])
def steamspy_details(appid):
    url = f'https://steamspy.com/api.php?request=appdetails&appid={appid}'
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()

        # Obtener tags (géneros)
        tags = data.get('tags')
        if tags and isinstance(tags, dict):
            genres = ', '.join(tags.keys())
        else:
            genres = 'Sin géneros'

        data['genres'] = genres
        return jsonify(data)
    return jsonify({'error': 'No se pudo obtener el detalle del juego'}), 500

# @app.route('/steamspy/details/<int:appid>', methods=['GET'])
# def steamspy_details(appid):
#     url = f'https://steamspy.com/api.php?request=appdetails&appid={appid}'
#     res = requests.get(url)
#     if res.status_code == 200:
#         data = res.json()

#         # Obtener géneros
#         genres = data.get('genre')  # Correct key is 'genre', not 'tags'
#         if genres: # No need to check for isinstance, it's a string
#             #  No need to convert to list, it is already a comma separated string
#             pass
#         else:
#             genres = 'Sin géneros'

#         data['genres'] = genres # Changed key to 'genres' to be consistent.
#         return jsonify(data)
#     return jsonify({'error': 'No se pudo obtener el detalle del juego'}), 500

@app.route('/steamspy/top', methods=['GET'])
def steamspy_top():
    url = 'https://steamspy.com/api.php?request=top100in2weeks'
    res = requests.get(url)
    if res.status_code == 200:
        return jsonify(res.json())
    return jsonify({'error': 'Error al obtener datos de SteamSpy'}), 500

@app.route('/fetch_games', methods=['GET'])
def fetch_games():
    url = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/'
    response = requests.get(url)
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({'error': 'Error al obtener juegos de Steam'}), 500

@app.route('/steam_game/<int:appid>', methods=['GET'])
def steam_game(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    res = requests.get(url)
    if res.status_code == 200:
        return jsonify(res.json())
    else:
        return jsonify({'error': 'Error al obtener detalles del juego'}), 500

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/detalle.html')
def detalle():
    return send_from_directory('.', 'detalle.html')

VALORACIONES_JSON = 'valoraciones.json'

@app.route('/guardar_valoraciones', methods=['POST'])
def guardar_valoraciones():
    data = request.json
    usuario = data.get('usuario')
    valoraciones = data.get('valoraciones')  # dict: {movie_id: rating}

    if not usuario or not valoraciones:
        return jsonify({'error': 'Datos incompletos'}), 400

    # Cargar datos actuales o iniciar diccionario
    if os.path.exists(VALORACIONES_JSON):
        with open(VALORACIONES_JSON, 'r') as f:
            data_json = json.load(f)
    else:
        data_json = {}

    # Si el usuario ya existe, actualizar su info
    if usuario in data_json:
        data_json[usuario].update(valoraciones)
    else:
        data_json[usuario] = valoraciones

    # Guardar de nuevo
    with open(VALORACIONES_JSON, 'w') as f:
        json.dump(data_json, f, indent=2)

    return jsonify({'mensaje': 'Valoraciones guardadas correctamente'})

@app.route('/recomendar', methods=['GET'])
def recomendar():
    usuario = request.args.get('usuario')
    if not usuario:
        return jsonify({'error': 'Usuario no especificado'}), 400

    if not os.path.exists(VALORACIONES_JSON):
        return jsonify({'error': 'No hay valoraciones disponibles'}), 404

    with open(VALORACIONES_JSON, 'r') as f:
        data = json.load(f)

    if usuario not in data:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    valoraciones = data[usuario]

    # Juegos que el usuario calificó con 4 o más
    favoritos = [gid for gid, score in valoraciones.items() if score >= 4]
    if not favoritos:
        return jsonify({'error': 'No hay juegos valorados con 4 o más'}), 400

    juegos_usuario = [get_game_info(gid) for gid in favoritos]

    # Juegos populares de SteamSpy
    populares_res = requests.get('https://steamspy.com/api.php?request=top100in2weeks').json()
    juegos_catalogo = [get_game_info(int(gid)) for gid in list(populares_res.keys())[:20]]

    juegos = {j['id']: j for j in juegos_usuario + juegos_catalogo if j is not None}
    juegos_df = pd.DataFrame(juegos.values())

    juegos_df['features'] = juegos_df['genres'] + ' ' + juegos_df['overview']

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(juegos_df['features'])
    similarity = cosine_similarity(tfidf_matrix)

    favoritos_idx = juegos_df[juegos_df['id'].isin([int(f) for f in favoritos])].index
    promedio_sim = similarity[favoritos_idx].mean(axis=0)

    juegos_df['score'] = promedio_sim
    recomendadas = juegos_df[~juegos_df['id'].isin([int(f) for f in favoritos])]
    top_recomendadas = recomendadas.sort_values(by='score', ascending=False).head(5)

    resultados = top_recomendadas[['id', 'title']].to_dict(orient='records')
    return jsonify(resultados)


@app.route('/recomendar_colaborativo', methods=['GET'])
def recomendar_colaborativo():
    usuario = request.args.get('usuario')
    if not usuario:
        return jsonify({'error': 'Usuario no especificado'}), 400

    if not os.path.exists(VALORACIONES_JSON):
        return jsonify({'error': 'No hay valoraciones'}), 404

    with open(VALORACIONES_JSON, 'r') as f:
        data = json.load(f)

    if usuario not in data:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    df = pd.DataFrame(data).T.fillna(0)

    if len(df) < 2:
        return jsonify({'error': 'No hay otros usuarios para comparar'}), 400

    sim_matrix = cosine_similarity(df)
    sim_df = pd.DataFrame(sim_matrix, index=df.index, columns=df.index)

    similares = sim_df[usuario].sort_values(ascending=False)[1:]

    recomendaciones = pd.Series(dtype='float64')
    for otro_usuario, similitud in similares.items():
        no_vistos = df.loc[otro_usuario][df.loc[usuario] == 0]
        recomendaciones = recomendaciones.add(no_vistos * similitud, fill_value=0)

    top = recomendaciones.sort_values(ascending=False).head(5).index
    juegos_recomendados = [int(gid) for gid in top if str(gid).isnumeric()]

    resultado = []
    for gid in juegos_recomendados:
        info = get_game_info(gid)
        if info:
            resultado.append({'id': gid, 'title': info['title']})

    return jsonify(resultado)


@app.route('/usuarios')
def usuarios():
    if not os.path.exists(VALORACIONES_JSON):
        return jsonify([])
    with open(VALORACIONES_JSON, 'r') as f:
        data = json.load(f)
    return jsonify(list(data.keys()))


#CHORO DE CHAT VALE VERGA
@app.route('/valoradas', methods=['GET'])
def valoradas():
    usuario = request.args.get('usuario')
    if not usuario:
        return jsonify({'error': 'Usuario no especificado'}), 400

    if not os.path.exists(VALORACIONES_JSON):
        return jsonify({'error': 'No hay valoraciones'}), 404

    with open(VALORACIONES_JSON, 'r') as f:
        data = json.load(f)

    if usuario not in data:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    valoradas = []
    for game_id, rating in data[usuario].items():
        info = get_game_info(game_id)
        if info:
            valoradas.append({
                'id': game_id,
                'title': info['title'],
                'rating': rating
            })

    return jsonify(valoradas)


if __name__ == '__main__':
    app.run(debug=True)
