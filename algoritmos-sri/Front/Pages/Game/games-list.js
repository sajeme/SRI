// catalog_script.js - Adaptado para el endpoint /juegos sin búsqueda en el backend

const gameListing = document.getElementById('gameListing');
const gameSearchInput = document.getElementById('searchInput');
const searchGamesButton = document.getElementById('searchButton');


let allCatalogGames = []; // Almacenará todos los juegos del catálogo (después de la carga inicial)
let filteredCatalogGames = []; // Almacenará los juegos filtrados por el término de búsqueda actual
let currentDisplayedGamesCount = 0;
const gamesToLoadPerClick = 12; // Número de juegos a mostrar con cada "cargar más"
const API_BASE_URL = 'http://localhost:5000'; // URL base de tu API Flask

// --- Helper Functions ---

// Función para formatear el precio
function formatPrice(price) {
    if (price === 0.00 || price === undefined || price === null) {
        return 'Gratis';
    }
    return `$${price.toFixed(2)}`;
}

// --- Core Logic for Game Catalog ---

/**
 * Fetches ALL game data from the Flask backend.
 * This function now only fetches all games, filtering will be done client-side.
 * @returns {Promise<Array<Object>>} - A promise that resolves to an array of game objects.
 */
async function fetchAllGamesFromBackend() {
    console.log(`Obteniendo todos los juegos desde: ${API_BASE_URL}/juegos`);
    try {
        const response = await fetch(`${API_BASE_URL}/juegos`); // Usa tu endpoint /juegos
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Error HTTP al obtener todos los juegos: ${response.status} - ${errorText}`);
            return [];
        }
        
        const data = await response.json();
        console.log("Datos de juegos recibidos:", data);
        return data;

    } catch (error) {
        console.error("Error al obtener los juegos del catálogo:", error);
        return [];
    }
}

/**
 * Creates a new game card element for the catalog.
 * @param {Object} game - The game data object.
 * @returns {HTMLElement} - The created div element containing the game card.
 */
function createNewGameCard(game) {
    const colDiv = document.createElement('div');
    colDiv.classList.add('col-xl-3', 'col-lg-4', 'col-md-6', 'col-sm-6'); // Columnas para diseño responsive

    const gameCard = document.createElement('a'); // Toda la tarjeta es un enlace
    gameCard.href = `product.html?appid=${game.appid}`; 
    gameCard.classList.add('game-card-new');

    const img = document.createElement('img');
    img.classList.add('card-img-top');
    img.src = game.img_url || 'https://via.placeholder.com/460x215?text=Imagen no disponible';
    img.alt = game.name;

    const cardBody = document.createElement('div');
    cardBody.classList.add('card-body-new');

    const title = document.createElement('h5');
    title.classList.add('card-title-new');
    title.textContent = game.name;

    const description = document.createElement('p');
    description.classList.add('card-text-new');
    description.textContent = game.description || 'No hay descripción disponible.';

    cardBody.appendChild(title);
    cardBody.appendChild(description);

    const cardFooter = document.createElement('div');
    cardFooter.classList.add('card-footer-new');

    const price = document.createElement('span');
    price.classList.add('game-price-new');
    price.textContent = formatPrice(game.price);

    const releaseDate = document.createElement('span');
    releaseDate.classList.add('game-release-date-new');
    releaseDate.textContent = `Lanzamiento: ${game.release_date || 'Desconocida'}`;

    cardFooter.appendChild(price);
    cardFooter.appendChild(releaseDate);

    gameCard.appendChild(img);
    gameCard.appendChild(cardBody);
    gameCard.appendChild(cardFooter);

    colDiv.appendChild(gameCard);
    return colDiv;
}

/**
 * Renders a subset of games to the DOM.
 * @param {Array<Object>} gamesToRender - An array of game objects to render.
 */
function renderCatalogGames(gamesToRender) {
    gamesToRender.forEach(game => {
        const gameCardElement = createNewGameCard(game);
        gameListing.appendChild(gameCardElement);
    });
}

/**
 * Loads and displays more games based on the current `filteredCatalogGames` array.
 */
function loadMoreCatalogGames() {
    const nextGames = filteredCatalogGames.slice(currentDisplayedGamesCount, currentDisplayedGamesCount + gamesToLoadPerClick);
    renderCatalogGames(nextGames);
    currentDisplayedGamesCount += nextGames.length;

    // Ocultar o mostrar el botón "Cargar Más"
    if (currentDisplayedGamesCount >= filteredCatalogGames.length) {
        loadMoreGamesButton.style.display = 'none';
    } else {
        loadMoreGamesButton.style.display = 'block';
    }
}

/**
 * Filters the `allCatalogGames` based on the search term and updates `filteredCatalogGames`.
 */
function filterGamesClientSide(searchTerm) {
    if (!searchTerm) {
        filteredCatalogGames = [...allCatalogGames]; // Si no hay término, todos los juegos
    } else {
        const lowerCaseSearchTerm = searchTerm.toLowerCase();
        filteredCatalogGames = allCatalogGames.filter(game => 
            game.name && game.name.toLowerCase().includes(lowerCaseSearchTerm)
        );
    }
    gameListing.innerHTML = ''; // Limpiar listado actual
    currentDisplayedGamesCount = 0; // Resetear contador
    loadMoreCatalogGames(); // Cargar los primeros juegos filtrados/todos
}

/**
 * Handles the game search functionality.
 */
function handleGameSearch() {
    const searchTerm = gameSearchInput.value.trim();
    filterGamesClientSide(searchTerm); // Realiza el filtrado en el cliente
}

// --- Event Listeners ---

searchGamesButton.addEventListener('click', handleGameSearch);

// Permite buscar al presionar Enter en el input
gameSearchInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevenir el envío de formulario si está en un form
        handleGameSearch();
    }
});

const loadMoreGamesButton = document.getElementById('loadMoreBtn');


// Inicializar la página al cargar el DOM
document.addEventListener('DOMContentLoaded', async () => {
    // Cargar TODOS los juegos una vez desde el backend
    allCatalogGames = await fetchAllGamesFromBackend();
    filteredCatalogGames = [...allCatalogGames]; // Inicialmente, los filtrados son todos los juegos
    loadMoreCatalogGames(); // Cargar los primeros juegos
});