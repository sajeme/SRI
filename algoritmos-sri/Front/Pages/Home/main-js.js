// main-js.js

// 1) VARIABLES GLOBALES para el tipo de recomendación
let newAndNoteworthyRecType = 'general';
let popularRecType          = 'general';
let adventureRecType        = 'general';
let accionRecType           = 'general';

// 2) FUNCIÓN que actualiza los títulos
function updateDynamicTitles() {
  const n = document.getElementById('newAndNoteworthyDynamicTitle');
  const p = document.getElementById('popularDynamicTitle');
  const a = document.getElementById('adventureDynamicTitle');
  const c = document.getElementById('accionDynamicTitle');
  if (!n||!p||!a||!c) return console.error("Título dinámico no encontrado");

  // Lo Nuevo...
  if (newAndNoteworthyRecType === 'apriori')      n.textContent = "Juegos jugados por otros usuarios que te podrían interesar";
  else if (newAndNoteworthyRecType === 'cold-start') n.textContent = "Basado en la información que nos proporcionaste de ti :)";
  else                                               n.textContent = "Lo Nuevo de 2025";

  // Populares...
  if (popularRecType === 'association')            p.textContent = "De acuerdo a tus gustos";
  else if (popularRecType === 'top-rated-fallback') p.textContent = "Los Más Valorados por los Usuarios";
  else                                               p.textContent = "Los más Jugados por los Usuarios";

  // carousel aventura
  if (adventureRecType === 'item-based')          a.textContent = "Recomendaciones por otros usuarios con preferencias similares a ti";
  else if (adventureRecType === 'top-rated-fallback') a.textContent = "Los juegos mejor valorados por usuarios";
  // else se queda con el HTML por defecto

  // Acción carousel
  if (accionRecType === 'content-based')          c.textContent = "Recomendaciones basadas en las Historias que te gustan";
  // else se queda con el HTML por defecto
}

function openNav() {
    document.getElementById("myNav").style.width = "50%";
    var elements = document.getElementsByClassName("bg");
    for(var i=0; i<elements.length; i++) {
        elements[i].style.opacity='20%';
    }
}

function closeNav() {
    document.getElementById("myNav").style.width = "0%";
    var elements = document.getElementsByClassName("bg");
    for(var i=0; i<elements.length; i++) {
        elements[i].style.opacity='100%';
    }
}

// Helper function for text truncation
function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length > maxLength) {
        return text.substring(0, maxLength) + '...';
    }
    return text;
}

// Función para construir el carrusel con un item por slide (para 'demo' - "Lo Nuevo de 2025")
function buildSingleItemCarousel(containerId, gamesData) {
    const carouselContainer = document.getElementById(containerId);
    if (!carouselContainer) {
        console.error(`Contenedor de carrusel con ID '${containerId}' no encontrado.`);
        return;
    }

    carouselContainer.innerHTML = ''; // Limpiar contenido existente

    if (!gamesData || gamesData.length === 0) {
        carouselContainer.innerHTML = '<p>No hay juegos para mostrar en este carrusel.</p>';
        return;
    }

    let indicatorsHtml = '<ul class="carousel-indicators">';
    let innerHtml = '<div class="carousel-inner">';

    gamesData.forEach((game, index) => {
        const activeClass = index === 0 ? 'active' : '';
        const imageUrl = game.portada || 'https://via.placeholder.com/1920x1080?text=No+Image';
        const gameId   = game.id  
               || game.appid 
               || game.game_id; 
        const gameLink = `../Products/product.html?game_id=${gameId}`;

        indicatorsHtml += `<li data-target="#${containerId}" data-slide-to="${index}" class="${activeClass}"></li>`;

        innerHtml += `
            <div class="carousel-item ${activeClass}">
                <a href="${gameLink}">
                    <img src="${imageUrl}" alt="${game.nombre || 'Juego'}" style="width:100%;">
                </a>
            </div>
        `;
    });

    indicatorsHtml += '</ul>';
    innerHtml += '</div>';

    const controlsHtml = `
        <a class="carousel-control-prev" href="#${containerId}" data-slide="prev">
            <span class="carousel-control-prev-icon"></span>
        </a>
        <a class="carousel-control-next" href="#${containerId}" data-slide="next">
            <span class="carousel-control-next-icon"></span>
        </a>
    `;

    carouselContainer.innerHTML = indicatorsHtml + innerHtml + controlsHtml;
    // Inicializar el carrusel de Bootstrap después de que se haya añadido el contenido
    $(`#${containerId}`).carousel({
        interval: 5000 // Puedes ajustar el intervalo de cambio de slides
    });
}

// Nueva función para construir el carrusel con múltiples items por slide (para 'demo2' - "Juegos más populares")
function buildMultiItemCarousel(containerId, gamesData, itemsPerSlide = 3, recommendationType = 'general') {
    const carouselContainer = document.getElementById(containerId);
    if (!carouselContainer) {
        console.error(`Contenedor de carrusel con ID '${containerId}' no encontrado.`);
        return;
    }

    carouselContainer.innerHTML = ''; // Limpiar contenido existente

    if (!gamesData || gamesData.length === 0) {
        carouselContainer.innerHTML = '<p>No hay juegos para mostrar en este carrusel.</p>';
        return;
    }

    let indicatorsHtml = '<ul class="carousel-indicators" style="display: none;">';
    let innerHtml = '<div class="carousel-inner">';

    // Agrupar juegos en slides de 'itemsPerSlide'
    for (let i = 0; i < gamesData.length; i += itemsPerSlide) {
        const slideGames = gamesData.slice(i, i + itemsPerSlide);
        const activeClass = i === 0 ? 'active' : '';

        indicatorsHtml += `<li data-target="#${containerId}" data-slide-to="${i / itemsPerSlide}" class="${activeClass}"></li>`;
        innerHtml += `<div class="carousel-item ${activeClass}">`;

        slideGames.forEach(game => {
            const imageUrl = game.portada || 'https://via.placeholder.com/600x400?text=No+Image';
            const recommendedGameId = game.id || game.appid || game.game_id;
            const gameLink = `../Products/product.html?game_id=${recommendedGameId}`;
            const gameName = game.nombre || 'Nombre Desconocido';
            const gamePrice = game.resumen_precio && game.resumen_precio.final_formatted
                                ? game.resumen_precio.final_formatted
                                : 'Gratis';

            let associationReasonHtml = ''; // This will be an empty string if no association reason
            // Check if it's an association recommendation and if the game has 'based_on_games' info
            if (recommendationType === 'association' && game.based_on_games && game.based_on_games.length > 0) {
                const basedOnGame = game.based_on_games[0]; // Take the first game as the basis
                // Ensure basedOnGame.id is available for linking
                if (basedOnGame && basedOnGame.id && basedOnGame.nombre) {
                    const basedOnGameLink = `../Products/product.html?game_id=${basedOnGame.id}`;
                    associationReasonHtml = `
                        <div class="association-reason" style="position: absolute; top: 5px; left: 5px; background-color: rgba(40, 88, 126, 0.9); color: white; padding: 5px 8px; font-size: 0.75em; border-radius: 4px; z-index: 10; max-width: 90%;">
                            Porque te gustó <a href="${basedOnGameLink}" style="color: #a7d5f1; text-decoration: underline;" target="_blank">${truncateText(basedOnGame.nombre, 25)}</a>
                        </div>
                    `;
                }
            }

            // Corrected line: The JavaScript comment is removed from here.
            // associationReasonHtml will either contain the div or be an empty string.
            innerHtml += `
                <div class="carouselItem" style="background-image: url(${imageUrl});">
                    ${associationReasonHtml} 
                    <a href="${gameLink}">
                        <img class="carouselImg" src="${imageUrl}" alt="${gameName}">
                        <span class="carouselCaption">${gameName} <br> ${gamePrice}</span>
                    </a>
                </div>
            `;
        });
        innerHtml += `</div>`; // Cierra carousel-item
    }

    indicatorsHtml += '</ul>';
    innerHtml += '</div>';

    const controlsHtml = `
        <a class="carousel-control-prev" href="#${containerId}" data-slide="prev">
            <span class="carousel-control-prev-icon"></span>
        </a>
        <a class="carousel-control-next" href="#${containerId}" data-slide="next">
            <span class="carousel-control-next-icon"></span>
        </a>
    `;

    carouselContainer.innerHTML = indicatorsHtml + innerHtml + controlsHtml;
    // Inicializar el carrusel de Bootstrap después de que se haya añadido el contenido
    $(`#${containerId}`).carousel({
        interval: 5000 // Puedes ajustar el intervalo de cambio de slides
    });
}

// Nueva función para construir el carrusel "Explora la AVENTURA" (aventura-card style)
function buildAdventureCarousel(containerId, gamesData, itemsPerSlide = 3) {
    const carouselContainer = document.getElementById(containerId);
    if (!carouselContainer) {
        console.error(`Contenedor de carrusel con ID '${containerId}' no encontrado.`);
        return;
    }

    carouselContainer.innerHTML = ''; // Limpiar contenido existente

    if (!gamesData || gamesData.length === 0) {
        carouselContainer.innerHTML = '<p>No hay juegos para mostrar en este carrusel.</p>';
        return;
    }

    let indicatorsHtml = '<ul class="carousel-indicators" style="display: none;">'; // Ocultar indicadores
    let innerHtml = '<div class="carousel-inner">';

    // Agrupar juegos en slides de 'itemsPerSlide'
    for (let i = 0; i < gamesData.length; i += itemsPerSlide) {
        const slideGames = gamesData.slice(i, i + itemsPerSlide);
        const activeClass = i === 0 ? 'active' : '';

        indicatorsHtml += `<li data-target="#${containerId}" data-slide-to="${i / itemsPerSlide}" class="${activeClass}"></li>`;
        innerHtml += `<div class="carousel-item ${activeClass}">`;

        slideGames.forEach(game => {
            const imageUrl = game.portada || 'https://via.placeholder.com/600x400?text=No+Image'; // Fallback image
            const gameLink = `../Products/product.html?game_id=${game.id}`;
            const gameName = game.nombre || 'Nombre Desconocido';
            const gamePrice = game.resumen_precio && game.resumen_precio.final_formatted
                                ? game.resumen_precio.final_formatted
                                : 'Gratis';
            const shortDescription = truncateText(game.descripcion_corta, 70); // Truncate description to ~70 characters

            innerHtml += `
                <div class="carouselItem aventura-card" style="background-image: url(${imageUrl});">
                    <a href="${gameLink}">
                        <img class="carouselImg" src="${imageUrl}" alt="${gameName}">
                        <div class="card-ribbon">${gamePrice}</div>
                        <div class="card-hover">
                            <h3 class="card-title">${gameName}</h3>
                            <p class="card-desc">${shortDescription}</p>
                        </div>
                    </a>
                </div>
            `;
        });
        innerHtml += `</div>`; // Cierra carousel-item
    }

    indicatorsHtml += '</ul>';
    innerHtml += '</div>';

    const controlsHtml = `
        <a class="carousel-control-prev" href="#${containerId}" data-slide="prev">
            <span class="carousel-control-prev-icon"></span>
        </a>
        <a class="carousel-control-next" href="#${containerId}" data-slide="next">
            <span class="carousel-control-next-icon"></span>
        </a>
    `;

    carouselContainer.innerHTML = indicatorsHtml + innerHtml + controlsHtml;
    // Inicializar el carrusel de Bootstrap después de que se haya añadido el contenido
    $(`#${containerId}`).carousel({
        interval: 5000 // Puedes ajustar el intervalo de cambio de slides
    });
}


// Función para obtener datos de la API para "Lo Nuevo de 2025" (demo)
async function fetchCarouselDataNewAndNoteworthy(isLoggedIn, userId = null) {
    if (isLoggedIn && userId !== null) {
        let proceedToColdStart = false;
        let proceedToUserBased = false;

        // 1) Check user interactions using the new endpoint
        const checkInteractionsUrl = `http://localhost:5000/interacciones/${userId}/check`;
        console.log(`Checking interactions for user ${userId} at ${checkInteractionsUrl}`);
        try {
            const respCheck = await fetch(checkInteractionsUrl);
            if (respCheck.ok) {
                const checkData = await respCheck.json();
                console.log(`Interaction check for user ${userId}:`, checkData);
                if (checkData.exists && checkData.has_interactions) { // User exists and has interactions
                    proceedToUserBased = true;
                } else { // User exists but no interactions, or user doesn't exist in interacciones.json (new user for recommendations)
                    proceedToColdStart = true;
                }
            } else if (respCheck.status === 404) { // User not found by the check endpoint, definite cold-start case
                console.log(`User ${userId} not found in interactions system, proceeding to cold-start.`);
                proceedToColdStart = true;
            } else {
                // Other HTTP error checking interactions, might fallback to general or try cold-start as a guess
                console.error(`Error checking interactions for user ${userId}: ${respCheck.status}. Falling back.`);
                // Decide fallback: could be cold-start or general. For now, let's try cold-start.
                proceedToColdStart = true; // Or set a flag to go to general recommendations later
            }
        } catch (e) {
            console.error(`Network error checking interactions for user ${userId}:`, e);
            // Network error, might fallback to general or try cold-start
            proceedToColdStart = true; // Or set a flag to go to general recommendations later
        }

        // 2) If NO interactions or new user -> Cold-Start
        if (proceedToColdStart) {
            newAndNoteworthyRecType = 'cold-start';
            const coldStartUrl = `http://localhost:5000/recommendations/cold-start/${userId}`;
            console.log(`User ${userId} requires cold-start. Fetching from: ${coldStartUrl}`);
            try {
                const respCold = await fetch(coldStartUrl);
                if (respCold.ok) {
                    const dataCold = await respCold.json();
                    // Ensure dataCold and its recommendations are valid before returning
                    if (dataCold && dataCold.recommendations) {
                        console.log(`Cold-start recommendations for user ${userId}:`, dataCold.recommendations);
                        return dataCold.recommendations;
                    } else {
                        console.warn(`Cold-start response for user ${userId} is OK but no recommendations array found or data is null.`);
                        return [];
                    }
                } else {
                    console.error(`Error fetching cold-start recommendations for user ${userId}: ${respCold.status}`);
                    return []; // Fallback to empty if cold-start API fails
                }
            } catch (e) {
                console.error(`Network error fetching cold-start for user ${userId}:`, e);
                return [];
            }
        }

        // 3) If HAS interactions -> Collaborative user-based
        if (proceedToUserBased) {
            newAndNoteworthyRecType = 'apriori'; // Or 'user-based'
            const collabUrl = `http://localhost:5000/recommendations/collaborative/user-based/${userId}`;
            console.log(`User ${userId} has interactions. Fetching collaborative user-based from: ${collabUrl}`);
            try {
                const respCollab = await fetch(collabUrl);
                if (respCollab.ok) {
                    const dataCollab = await respCollab.json();
                    if (dataCollab && dataCollab.recommendations) {
                        console.log(`Collaborative recommendations for user ${userId}:`, dataCollab.recommendations);
                        return dataCollab.recommendations;
                    } else {
                        console.warn(`Collaborative response for user ${userId} is OK but no recommendations array found or data is null.`);
                        return [];
                    }
                } else {
                    console.error(`Error fetching collaborative recommendations for user ${userId}: ${respCollab.status}`);
                    return []; // Fallback to empty if collaborative API fails
                }
            } catch (e) {
                console.error(`Network error fetching collaborative for user ${userId}:`, e);
                return [];
            }
        }
        // If neither proceedToColdStart nor proceedToUserBased is true after the check (shouldn't happen with current logic, but as a safeguard)
        // Fall through to general recommendations for non-logged-in users.
    }

    // 4) Fallback or Flow for non-logged-in users
    newAndNoteworthyRecType = 'general';
    const generalUrl = 'http://localhost:5000/recommend/action2025'; // Assuming this is your general endpoint
    console.log("Fetching general 'New and Noteworthy' recommendations.");
    try {
        const respGeneral = await fetch(generalUrl);
        if (respGeneral.ok) {
            const dataGeneral = await respGeneral.json();
            if (dataGeneral && dataGeneral.recommendations) {
                return dataGeneral.recommendations;
            } else {
                console.warn('General recommendations response is OK but no recommendations array found or data is null.');
                return [];
            }
        } else {
            console.error(`Error fetching general recommendations: ${respGeneral.status}`);
            return [];
        }
    } catch (e) {
        console.error('Network error fetching general recommendations:', e);
        return [];
    }
}


// Nueva función para obtener datos de la API para "Juegos más populares" (demo2)
async function fetchCarouselDataPopular(isLoggedIn, userId = null) {
    let recommendations = [];

    if (isLoggedIn && userId !== null) {
        // 1. Try to get association recommendations first for logged-in users
        const associationUrl = `http://localhost:5000/recommendations/association/${userId}`;
        console.log(`Attempting to fetch association recommendations for user ${userId}.`);

        try {
            const responseAssociation = await fetch(associationUrl);
            if (responseAssociation.ok) {
                const dataAssociation = await responseAssociation.json();
                recommendations = dataAssociation.recommendations || [];
                if (recommendations.length > 0) {
                    console.log(`Association recommendations found for user ${userId}:`, recommendations);
                    popularRecType = 'association';
                    return recommendations; // If association recommendations exist, return them
                } else {
                    console.log(`No association recommendations found for user ${userId}. Falling back to top_rated.`);
                    // Fall through to the top_rated logic if no association recommendations
                }
            } else {
                console.error(`HTTP error (${responseAssociation.status}) fetching association recommendations for user ${userId}. Falling back to top_rated.`);
                // Fall through to the top_rated logic on error
            }
        } catch (error) {
            console.error('Network error fetching association recommendations:', error);
            // Fall through to the top_rated logic on network error
        }

        // 2. If no association recommendations were found or there was an error, get global top-rated recommendations
        const topRatedUrl = 'http://localhost:5000/global/top_rated';
        console.log(`Soliciting global top-rated recommendations as a fallback for user ${userId}.`);

        try {
            const responseTopRated = await fetch(topRatedUrl);
            if (!responseTopRated.ok) {
                console.error(`HTTP error! status: ${responseTopRated.status} from ${topRatedUrl}`);
                return []; // Return empty if top-rated fails
            }
            const dataTopRated = await responseTopRated.json();
            recommendations = dataTopRated.recommendations || [];
            popularRecType = 'top-rated-fallback';
            console.log(`Global top-rated recommendations obtained:`, recommendations);
            return recommendations;
        } catch (error) {
            console.error('Error fetching global top-rated recommendations:', error);
            return [];
        }

    } else {
        // Logic for non-logged-in users (always uses the global "Most Played" endpoint)
        const mostPlayedUrl = 'http://localhost:5000/global/most_played';
        popularRecType = 'general';
        console.log("Fetching global most played games for non-logged-in user.");
        try {
            const response = await fetch(mostPlayedUrl);
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status} from ${mostPlayedUrl}`);
                // If 'most_played' also fails for non-logged-in, you could add another fallback here if needed.
                return [];
            }
            const data = await response.json();
            return data.recommendations || [];
        } catch (error) {
            console.error('Error fetching "Most Played" carousel data for non-logged-in user:', error);
            return [];
        }
    }
}

// Nueva función para obtener datos de la API para "Explora la AVENTURA"
async function fetchCarouselDataAdventure(isLoggedIn, userId = null) {
    let url;
    if (isLoggedIn && userId !== null) {
        url = `http://localhost:5000/recommendations/collaborative/item-based/${userId}`;
        adventureRecType = 'item-based'
        console.log(`Workspaceing item-based collaborative recommendations for user ${userId} for Adventure carousel.`);
    } else {
        url = 'http://localhost:5000/global/top_rated';
        adventureRecType = 'top-rated-fallback'
        console.log("Fetching global top-rated games for Adventure carousel (non-logged-in or fallback).");
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status} from ${url}`);
            return [];
        }

        const data = await response.json();
        const recs = data.recommendations || data.items || [];

        return recs;
    } catch (error) {
        console.error('Error fetching "Explora la AVENTURA" carousel data:', error);
        return [];
    }
}


function buildAccionCarousel(containerId, gamesData, itemsPerSlide = 3) {
    const carouselContainer = document.getElementById(containerId);
    if (!carouselContainer) {
        console.error(`Contenedor de carrusel con ID '${containerId}' no encontrado.`);
        return;
    }

    carouselContainer.innerHTML = ''; // Limpiar contenido existente

    if (!gamesData || gamesData.length === 0) {
        // Si no hay datos, no construimos nada o mostramos un mensaje,
        // pero la lógica de ocultar título/carrusel ya lo manejará en DOMContentLoaded
        return;
    }

    let indicatorsHtml = '<ul class="carousel-indicators" style="display: none;">';
    let innerHtml = '<div class="carousel-inner">';

    // Agrupar juegos en slides de 'itemsPerSlide'
    for (let i = 0; i < gamesData.length; i += itemsPerSlide) {
        const slideGames = gamesData.slice(i, i + itemsPerSlide);
        const activeClass = i === 0 ? 'active' : '';

        indicatorsHtml += `<li data-target="#${containerId}" data-slide-to="${i / itemsPerSlide}" class="${activeClass}"></li>`;
        innerHtml += `<div class="carousel-item ${activeClass}">`;

        slideGames.forEach(game => {
            const imageUrl = game.portada || 'https://via.placeholder.com/600x400?text=No+Image'; // Fallback image
            const gameLink = `../Products/product.html?game_id=${game.id}`;
            const gameName = game.nombre || 'Nombre Desconocido';
            let gamePrice = game.resumen_precio && game.resumen_precio.final_formatted
                                        ? game.resumen_precio.final_formatted
                                        : 'Gratis';
            gamePrice = gamePrice.replace(/Mxn\s*/g, ''); // Remover "Mxn" y espacios

            // Limitar a los primeros 4 tags
            const tagsHtml = game.tags ? game.tags.slice(0, 4).map(tag => `<span class="tag">${tag.description}</span>`).join('') : '';

            innerHtml += `
                <div class="carouselItem accion-card" style="background-image: url(${imageUrl});">
                    <a href="${gameLink}">
                        <img class="carouselImg" src="${imageUrl}" alt="${gameName}">
                        <div class="card-overlay">
                            <div class="card-tags">
                                ${tagsHtml}
                            </div>
                        </div>
                        <span class="card-price">${gamePrice}</span>
                        <span class="card-title">${gameName}</span>
                    </a>
                </div>
            `;
        });
        innerHtml += `</div>`; // Cierra carousel-item
    }

    indicatorsHtml += '</ul>';
    innerHtml += '</div>';

    const controlsHtml = `
        <a class="carousel-control-prev" href="#${containerId}" data-slide="prev">
            <span class="carousel-control-prev-icon"></span>
        </a>
        <a class="carousel-control-next" href="#${containerId}" data-slide="next">
            <span class="carousel-control-next-icon"></span>
        </a>
    `;

    carouselContainer.innerHTML = indicatorsHtml + innerHtml + controlsHtml;
    $(`#${containerId}`).carousel({
        interval: 5000
    });
}

// Nuevo: Función para obtener datos para el carrusel de "Lo mejor en ACCIÓN"
async function fetchCarouselDataAccion(isLoggedIn, userId = null) {
    let url;
    if (isLoggedIn && userId !== null) {
        url = `http://localhost:5000/recommendations/content-based/${userId}`;
        console.log(`Workspaceing content-based recommendations for user ${userId} for Accion carousel.`);
    } else {
        console.log("No logged-in user, skipping content-based recommendations for Accion carousel.");
        return [];
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status} from ${url}`);
            return [];
        }

        const data = await response.json();
        const recs = data.recommendations || [];

        // ← Aquí asignas el recType antes de devolver
        accionRecType = recs.length > 0
            ? 'content-based'
            : 'general';

        return recs;
    } catch (error) {
        console.error('Error fetching "Accion" carousel data:', error);
        return [];
    }
}



// ... (todas tus funciones anteriores, incluyendo fetchCarouselDataAdventure y buildAdventureCarousel) ...

document.addEventListener("DOMContentLoaded", async () => {
    const user = JSON.parse(localStorage.getItem("usuario"));
    const cuentaMenu = document.getElementById("cuentaMenu");
    const cuentaOpciones = document.getElementById("cuentaOpciones");

    const mainCarouselId = "demo";
    const popularCarouselId = "demo2";
    const adventureCarouselId = "demoAventura";
    const adventureTitleContainerId = "adventureTitleContainer";
    const accionCarouselId = "demoAccion";
    const accionTitleContainerId = "accionTitleContainer";


    if (!cuentaMenu || !cuentaOpciones) return;

    let gamesNewAndNoteworthy = [];
    let gamesPopular = [];
    let gamesAdventure = [];
    let gamesAccion = [];
    let userId = null;

    if (user && user.id) {
        console.log("Usuario logeado:", user.nombre, "ID:", user.id);
        userId = user.id;
        cuentaMenu.textContent = `Hola, ${user.nombre}`;
        cuentaOpciones.innerHTML = `<a class="dropdown-item menuItem" href="#" id="logoutBtn">Cerrar sesión</a>`;
        document.getElementById("logoutBtn").addEventListener("click", () => {
            localStorage.removeItem("usuario");
            window.location.href = "../Login/login.html";
        });

        // Fetch data in parallel for logged-in user
        [
            gamesNewAndNoteworthy,
            gamesPopular,
            gamesAdventure,
            gamesAccion
        ] = await Promise.all([
            fetchCarouselDataNewAndNoteworthy(true, userId),
            fetchCarouselDataPopular(true, userId),
            fetchCarouselDataAdventure(true, userId),
            fetchCarouselDataAccion(true, userId)
        ]);

    } else {
        console.log("Usuario no logeado o sin ID.");
        cuentaMenu.textContent = "Cuenta";
        cuentaOpciones.innerHTML = `
            <a class="dropdown-item menuItem" href="../Login/login.html">Inicia Sesión</a>
            <a class="dropdown-item menuItem" href="../Register/register.html">Regístrate</a>
        `;
        // Fetch data for non-logged-in user
        [
            gamesNewAndNoteworthy,
            gamesPopular,
            gamesAdventure, // Will get 'top-rated-fallback'
            gamesAccion     // Will be empty as per fetchCarouselDataAccion logic
        ] = await Promise.all([
            fetchCarouselDataNewAndNoteworthy(false),
            fetchCarouselDataPopular(false),
            fetchCarouselDataAdventure(false),
            fetchCarouselDataAccion(false)
        ]);
    }

    buildSingleItemCarousel(mainCarouselId, gamesNewAndNoteworthy);
    // Pass popularRecType (which is set globally by fetchCarouselDataPopular)
    buildMultiItemCarousel(popularCarouselId, gamesPopular, 3, popularRecType);


    const adventureCarouselDiv = document.getElementById(adventureCarouselId);
    const adventureTitleDiv = document.getElementById(adventureTitleContainerId);
    if (user && gamesAdventure.length === 0) {
        if (adventureCarouselDiv) adventureCarouselDiv.style.display = 'none';
        if (adventureTitleDiv) adventureTitleDiv.style.display = 'none';
        console.log("AVENTURA carousel oculto: Logeado sin recomendaciones.");
    } else {
        if (adventureCarouselDiv) adventureCarouselDiv.style.display = 'inline-block';
        if (adventureTitleDiv) adventureTitleDiv.style.display = 'block';
        buildAdventureCarousel(adventureCarouselId, gamesAdventure);
    }

    const accionCarouselDiv = document.getElementById(accionCarouselId);
    const accionTitleDiv = document.getElementById(accionTitleContainerId);
    // Accion carousel is primarily for logged-in users with content-based recs
    if (accionRecType === 'content-based' && gamesAccion.length > 0) {
        if (accionCarouselDiv) accionCarouselDiv.style.display = 'inline-block';
        if (accionTitleDiv) accionTitleDiv.style.display = 'block';
        buildAccionCarousel(accionCarouselId, gamesAccion);
        console.log("ACCIÓN carousel visible: Recomendaciones de contenido encontradas.");
    } else {
        if (accionCarouselDiv) accionCarouselDiv.style.display = 'none';
        if (accionTitleDiv) accionTitleDiv.style.display = 'none';
        if (user && accionRecType !== 'content-based') {
             console.log("ACCIÓN carousel oculto: Logeado pero sin recomendaciones de contenido.");
        } else if (!user) {
             console.log("ACCIÓN carousel oculto: Usuario no logeado.");
        }
    }
    
    // Update global recTypes based on fetched data, primarily for title updates.
    // These are already set within each fetch function, but this re-confirms based on actual data length for logged-in users.
    if (userId) {
        if (newAndNoteworthyRecType !== 'cold-start' && newAndNoteworthyRecType !== 'apriori') { // If not already set by specific logic
             newAndNoteworthyRecType = gamesNewAndNoteworthy.length > 0 ? 'apriori' : 'cold-start'; // Default logic if not set
        }
        // popularRecType is correctly set in fetchCarouselDataPopular
        // adventureRecType is correctly set in fetchCarouselDataAdventure
        // accionRecType is correctly set in fetchCarouselDataAccion
    } else { // For non-logged in users
        newAndNoteworthyRecType = 'general';
        popularRecType          = 'general';
        adventureRecType        = 'top-rated-fallback'; // Or 'general' if you prefer a different default
        accionRecType           = 'general'; // Accion carousel not shown for non-logged in
    }

    updateDynamicTitles();

    document.querySelectorAll('.nav-item.dropdown').forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.classList.add('show');
            item.querySelector('.dropdown-menu').classList.add('show');
        });
        item.addEventListener('mouseleave', () => {
            item.classList.remove('show');
            item.querySelector('.dropdown-menu').classList.remove('show');
        });
    });
});