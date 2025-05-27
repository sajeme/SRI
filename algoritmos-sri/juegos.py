import json
from collections import Counter

# Cargar el archivo JSON
with open("datos_juegos.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Contadores
categoria_counter = Counter()
tag_counter = Counter()

# Recorrer todos los juegos
for juego in data.values():
    # Contar categorías
    for categoria in juego.get("categorias", []):
        categoria_counter[categoria] += 1
    # Contar tags
    for tag in juego.get("tags", []):
        tag_description = tag.get("description")
        if tag_description:
            tag_counter[tag_description] += 1

# Mostrar los resultados ordenados
print("Categorías más populares:")
for categoria, count in categoria_counter.most_common():
    print(f"{categoria}: {count}")

print("\nTags más populares:")
for tag, count in tag_counter.most_common():
    print(f"{tag}: {count}")
