// games-list.js

const gamesContainer = document.getElementById('gamesContainer');
const gameSearchInput = document.getElementById('searchInput');
const searchGamesButton = document.getElementById('searchButton');
const loadMoreGamesButton = document.getElementById('loadMoreBtn');

let allCatalogGames = []; // Almacenará todos los juegos del catálogo
let filteredCatalogGames = []; // Almacenará los juegos filtrados
let currentDisplayedGamesCount = 0;
const gamesToLoadPerClick = 12; // Número de juegos a mostrar con cada "cargar más"
const API_BASE_URL = 'http://localhost:5000'; // URL base de tu API Flask

// --- Helper Functions ---
function formatPrice(price) {
    if (price === 0.00 || price === undefined || price === null) {
        return 'Gratis';
    }
    return `$${price.toFixed(2)}`;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length > maxLength) {
        return text.substring(0, maxLength) + '...';
    }
    return text;
}

// --- Core Logic ---
async function fetchAllGamesFromBackend() {
    const endpointURL = `${API_BASE_URL}/api/juegos`; // CORREGIDO: Usar /api/juegos
    console.log(`Obteniendo todos los juegos desde: ${endpointURL}`);
    try {
        const response = await fetch(endpointURL);
        if (!response.ok) {
            let errorMsg = `Error HTTP: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Sin cuerpo de error JSON */ }
            throw new Error(errorMsg);
        }
        const data = await response.json();
        return Array.isArray(data) ? data : [];
    } catch (error) {
        console.error("Error al obtener los juegos desde el backend:", error);
        if (gamesContainer) {
            gamesContainer.innerHTML = `<p class="text-danger text-center col-12">Error al cargar los juegos: ${error.message}. Intenta de nuevo.</p>`;
        }
        return [];
    }
}

function createGameCardElement(game) {
    if (!game || !game.appid) {
        console.warn("Juego inválido o sin appid:", game);
        return null;
    }
    const gameCardCol = document.createElement('div');
    gameCardCol.className = 'col-lg-3 col-md-4 col-sm-6 mb-4';

    const card = document.createElement('div');
    card.className = 'card game-card h-100 shadow-sm'; // Usar estilos de games-stylesheet.css

    const imgLink = document.createElement('a');
    imgLink.href = `../Products/product.html?game_id=${game.appid}` // Enlace a la página de detalles

    const img = document.createElement('img');
    img.src = game.portada || 'https://via.placeholder.com/350x200.png?text=No+Imagen';
    img.className = 'card-img-top';
    img.alt = game.nombre || 'Imagen del juego'; // Usar game.nombre
    img.onerror = () => { img.src = 'https://via.placeholder.com/350x200.png?text=Error+Img'; };
    imgLink.appendChild(img);

    const cardBody = document.createElement('div');
    cardBody.className = 'card-body d-flex flex-column';

    const title = document.createElement('h5');
    title.className = 'card-title'; // Estilo de games-stylesheet.css
    const titleLink = document.createElement('a');
    titleLink.href = `../Products/product.html?game_id=${game.appid}`
    titleLink.textContent = truncateText(game.nombre || 'Título no disponible', 40); // Usar game.nombre
    titleLink.style.color = 'inherit';
    titleLink.style.textDecoration = 'none';
    titleLink.addEventListener('mouseenter', () => titleLink.style.textDecoration = 'underline');
    titleLink.addEventListener('mouseleave', () => titleLink.style.textDecoration = 'none');
    title.appendChild(titleLink);

    const description = document.createElement('p');
    description.className = 'card-description'; // Estilo de games-stylesheet.css
    description.textContent = truncateText(game.descripcion_corta || 'Descripción no disponible.', 80);

    const cardInfo = document.createElement('div');
    cardInfo.className = 'card-info mt-auto';

    const price = document.createElement('span');
    price.className = 'card-price'; // Estilo de games-stylesheet.css

    const releaseDate = document.createElement('span');
    releaseDate.className = 'card-release-date'; // Estilo de games-stylesheet.css
    releaseDate.textContent = game.fecha_publicacion || 'Próximamente';

    cardInfo.appendChild(price);
    cardInfo.appendChild(releaseDate);

    const detailsButton = document.createElement('a');
    detailsButton.href = `../Products/product.html?game_id=${game.appid}`
    detailsButton.className = 'btn btn-primary btn-sm btn-block mt-2 view-details-btn';
    detailsButton.textContent = 'Ver Detalles';
    detailsButton.setAttribute('role', 'button');

    cardBody.appendChild(title);
    cardBody.appendChild(description);
    cardBody.appendChild(cardInfo);
    cardBody.appendChild(detailsButton);

    card.appendChild(imgLink);
    card.appendChild(cardBody);
    gameCardCol.appendChild(card);

    return gameCardCol;
}

function loadMoreCatalogGames() {
    if (!gamesContainer) return;

    const gamesToShow = filteredCatalogGames.slice(currentDisplayedGamesCount, currentDisplayedGamesCount + gamesToLoadPerClick);
    gamesToShow.forEach(game => {
        const cardElement = createGameCardElement(game);
        if (cardElement) {
            gamesContainer.appendChild(cardElement);
        }
    });
    currentDisplayedGamesCount += gamesToShow.length;

    if (currentDisplayedGamesCount >= filteredCatalogGames.length) {
        if (loadMoreGamesButton) loadMoreGamesButton.style.display = 'none';
    } else {
        if (loadMoreGamesButton) loadMoreGamesButton.style.display = 'block';
    }
}

function filterGamesClientSide(searchTerm) {
    const lowerCaseSearchTerm = searchTerm.toLowerCase();
    if (!searchTerm) {
        filteredCatalogGames = [...allCatalogGames];
    } else {
        filteredCatalogGames = allCatalogGames.filter(game =>
            game.nombre && game.nombre.toLowerCase().includes(lowerCaseSearchTerm) // CORREGIDO: Usar game.nombre
        );
    }

    if (gamesContainer) gamesContainer.innerHTML = ''; // Limpiar listado actual
    currentDisplayedGamesCount = 0;
    loadMoreCatalogGames();

    if (filteredCatalogGames.length === 0 && gamesContainer) {
        gamesContainer.innerHTML = '<p class="text-warning text-center col-12">No se encontraron juegos que coincidan con tu búsqueda.</p>';
        if (loadMoreGamesButton) loadMoreGamesButton.style.display = 'none';
    }
}

function handleGameSearch() {
    const searchTerm = gameSearchInput.value.trim();
    filterGamesClientSide(searchTerm);
}

// --- Event Listeners ---
if (searchGamesButton) {
    searchGamesButton.addEventListener('click', handleGameSearch);
}

if (gameSearchInput) {
    gameSearchInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            handleGameSearch();
        }
    });
}

if (loadMoreGamesButton) {
    loadMoreGamesButton.addEventListener('click', loadMoreCatalogGames);
}

// Inicializar la página
document.addEventListener('DOMContentLoaded', async () => {
    if (!gamesContainer) {
        console.error("El contenedor 'gamesContainer' no fue encontrado.");
        return;
    }
    allCatalogGames = await fetchAllGamesFromBackend();
    if (allCatalogGames.length > 0) {
        filteredCatalogGames = [...allCatalogGames];
        loadMoreCatalogGames();
    } else if (gamesContainer.innerHTML === '') { // Si fetch falló y no mostró mensaje de error
        gamesContainer.innerHTML = '<p class="text-info text-center col-12">No hay juegos disponibles en este momento.</p>';
        if (loadMoreGamesButton) loadMoreGamesButton.style.display = 'none';
    }
});
