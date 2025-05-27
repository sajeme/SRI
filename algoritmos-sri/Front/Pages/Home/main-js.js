// main-js.js
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
        const gameLink = `../Products/product.html?game_id=${game.id}`;

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
function buildMultiItemCarousel(containerId, gamesData, itemsPerSlide = 3) {
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

    let indicatorsHtml = '<ul class="carousel-indicators" style="display: none;">'; // Ocultar indicadores como en el HTML original
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
            // Formatear precio si existe, usando 'Gratis' si no hay datos de precio
            const gamePrice = game.resumen_precio && game.resumen_precio.final_formatted
                                ? game.resumen_precio.final_formatted
                                : 'Gratis';

            innerHtml += `
                <div class="carouselItem" style="background-image: url(${imageUrl});">
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
    let recommendations = [];

    if (isLoggedIn && userId !== null) {
        // 1. Try to get Apriori recommendations first
        const aprioriUrl = `http://localhost:5000/recommendations/collaborative/user-based/${userId}`; // Assuming this is your Apriori endpoint
        console.log(`Attempting to fetch Apriori recommendations for user ${userId}.`);

        try {
            const responseUserBased = await fetch(aprioriUrl);
            if (responseUserBased.ok) {
                const dataUserBased = await responseUserBased.json();
                recommendations = dataUserBased.recommendations || [];

                if (recommendations.length > 0) {
                    console.log(`Apriori recommendations found for user ${userId}:`, recommendations);
                    return recommendations; // If Apriori recommendations exist, return them
                } else {
                    console.log(`No Apriori recommendations found for user ${userId}. Falling back to cold-start.`);
                    // Fall through to the cold-start logic if no Apriori recommendations
                }
            } else {
                console.error(`HTTP error (${responseUserBased.status}) fetching Apriori recommendations for user ${userId}. Falling back to cold-start.`);
                // Fall through to the cold-start logic on error
            }
        } catch (error) {
            console.error('Network error fetching Apriori recommendations:', error);
            // Fall through to the cold-start logic on network error
        }

        // 2. If no Apriori recommendations were found or there was an error, get cold-start recommendations
        const coldStartUrl = `http://localhost:5000/recommendations/cold-start/${userId}`;
        console.log(`Soliciting cold-start recommendations for user ${userId}.`);

        try {
            const responseColdStart = await fetch(coldStartUrl);
            if (!responseColdStart.ok) {
                console.error(`HTTP error! status: ${responseColdStart.status} from ${coldStartUrl}`);
                return []; // Return empty if cold-start fails
            }
            const dataColdStart = await responseColdStart.json();
            recommendations = dataColdStart.recommendations || [];
            console.log(`Cold-start recommendations obtained:`, recommendations);
            return recommendations;
        } catch (error) {
            console.error('Error fetching cold-start recommendations:', error);
            return [];
        }

    } else {
        // Logic for non-logged-in users (always uses the general "New and Noteworthy" endpoint)
        const url = 'http://localhost:5000/recommend/action2025';
        try {
            const response = await fetch(url);
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status} from ${url}`);
                return [];
            }
            const data = await response.json();
            return data.recommendations || [];
        } catch (error) {
            console.error('Error fetching "New and Noteworthy" carousel data for non-logged-in user:', error);
            return [];
        }
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
            console.log(`Global top-rated recommendations obtained:`, recommendations);
            return recommendations;
        } catch (error) {
            console.error('Error fetching global top-rated recommendations:', error);
            return [];
        }

    } else {
        // Logic for non-logged-in users (always uses the global "Most Played" endpoint)
        const mostPlayedUrl = 'http://localhost:5000/global/most_played';
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
        console.log(`Workspaceing item-based collaborative recommendations for user ${userId} for Adventure carousel.`);
    } else {
        url = 'http://localhost:5000/global/top_rated';
        console.log("Fetching global top-rated games for Adventure carousel (non-logged-in or fallback).");
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status} from ${url}`);
            return [];
        }
        const data = await response.json();
        // Adjust based on the actual API response structure if 'recommendations' is nested
        return data.recommendations || data.items || [];
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
        // Si no está logeado, no deberíamos llamar a esta API de recomendaciones de contenido
        // y por lo tanto, no se mostrará el carrusel. Retornamos vacío.
        console.log("No logged-in user, skipping content-based recommendations for Accion carousel.");
        return [];
    }

    try {
        const response = await fetch(url);
        // Manejar errores 400 y 404 específicamente como lista vacía para ocultar
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status} from ${url}`);
            // Si es 404 o 400, o cualquier otro error, se trata como no recomendaciones.
            return [];
        }
        const data = await response.json();
        // Asegúrate de que 'recommendations' es el array correcto en la respuesta JSON
        return data.recommendations || [];
    } catch (error) {
        console.error('Error fetching "Accion" carousel data:', error);
        return [];
    }
}
// main-js.js

// ... (todas tus funciones anteriores, incluyendo fetchCarouselDataAdventure y buildAdventureCarousel) ...

document.addEventListener("DOMContentLoaded", async () => {
    const user = JSON.parse(localStorage.getItem("usuario"));
    const cuentaMenu = document.getElementById("cuentaMenu");
    const cuentaOpciones = document.getElementById("cuentaOpciones");

    const mainCarouselId = "demo";
    const popularCarouselId = "demo2";
    const adventureCarouselId = "demoAventura";
    // Referencia al ID del contenedor del título de Aventura
    const adventureTitleContainerId = "adventureTitleContainer";
    // Nuevos IDs para el carrusel de ACCIÓN
    const accionCarouselId = "demoAccion";
    const accionTitleContainerId = "accionTitleContainer";


    if (!cuentaMenu || !cuentaOpciones) return;

    let gamesNewAndNoteworthy = [];
    let gamesPopular = [];
    let gamesAdventure = [];
    let gamesAccion = []; // **AGREGADO: Variable para las recomendaciones de ACCIÓN**
    let userId = null;

    if (user) {
        console.log("Usuario logeado:", user);
        console.log("ID del usuario:", user.id);
        cuentaMenu.textContent = `Hola, ${user.nombre}`;
        cuentaOpciones.innerHTML = `
            <a class="dropdown-item menuItem" href="#" id="logoutBtn">Cerrar sesión</a>
        `;
        document.getElementById("logoutBtn")
            .addEventListener("click", () => {
                localStorage.removeItem("usuario");
                window.location.href = "../Login/login.html";
            });

        userId = user.id;
        if (userId) {
            gamesNewAndNoteworthy = await fetchCarouselDataNewAndNoteworthy(true, userId);
            gamesPopular = await fetchCarouselDataPopular(true, userId);
            gamesAdventure = await fetchCarouselDataAdventure(true, userId);
            gamesAccion = await fetchCarouselDataAccion(true, userId); // **AGREGADO: Llamada para obtener datos de ACCIÓN**
        } else {
            console.warn("Usuario logeado pero sin ID encontrado. Mostrando recomendaciones generales.");
            gamesNewAndNoteworthy = await fetchCarouselDataNewAndNoteworthy(false);
            gamesPopular = await fetchCarouselDataPopular(false);
            gamesAdventure = await fetchCarouselDataAdventure(false);
            gamesAccion = []; // **AGREGADO: Vacío si no hay userId**
        }

    } else {
        cuentaMenu.textContent = "Cuenta";
        cuentaOpciones.innerHTML = `
            <a class="dropdown-item menuItem" href="../Login/login.html">Inicia Sesión</a>
            <a class="dropdown-item menuItem" href="../Register/register.html">Regístrate</a>
        `;

        gamesNewAndNoteworthy = await fetchCarouselDataNewAndNoteworthy(false);
        gamesPopular = await fetchCarouselDataPopular(false);
        gamesAdventure = await fetchCarouselDataAdventure(false);
        gamesAccion = []; // **AGREGADO: Siempre vacío si no está logeado**
    }

    // Construir los carruseles dinámicamente

    // Carrusel "Lo Nuevo de 2025"
    buildSingleItemCarousel(mainCarouselId, gamesNewAndNoteworthy);

    // Carrusel "Juegos más populares"
    buildMultiItemCarousel(popularCarouselId, gamesPopular);

    // --- Lógica para mostrar/ocultar el carrusel de Aventura ---
    const adventureCarouselDiv = document.getElementById(adventureCarouselId);
    const adventureTitleDiv = document.getElementById(adventureTitleContainerId);

    // Si el usuario está logeado Y no se encontraron recomendaciones de aventura, ocultar la sección
    if (user && gamesAdventure.length === 0) {
        if (adventureCarouselDiv) {
            adventureCarouselDiv.style.display = 'none';
        }
        if (adventureTitleDiv) {
            adventureTitleDiv.style.display = 'none';
        }
        console.log("Explora la AVENTURA carousel y título ocultos: Usuario logeado sin recomendaciones encontradas.");
    } else {
        // Si hay juegos O si el usuario NO está logeado (siempre se mostrará el global/top_rated)
        // entonces se construye el carrusel.
        // Asegúrate de que los elementos sean visibles si antes estaban ocultos (por ejemplo, en un refresco de página donde hubo un error previo)
        if (adventureCarouselDiv) {
            adventureCarouselDiv.style.display = 'inline-block';
        }
        if (adventureTitleDiv) {
            adventureTitleDiv.style.display = 'block';
        }
        buildAdventureCarousel(adventureCarouselId, gamesAdventure);
    }
    // -----------------------------------------------------------

    // --- Lógica para mostrar/ocultar el carrusel de ACCIÓN --- **AGREGADO: Todo este bloque**
    const accionCarouselDiv = document.getElementById(accionCarouselId);
    const accionTitleDiv = document.getElementById(accionTitleContainerId);

    // El carrusel de ACCIÓN solo se muestra si el usuario está logeado Y hay recomendaciones
    if (user && gamesAccion.length > 0) {
        if (accionCarouselDiv) {
            accionCarouselDiv.style.display = 'inline-block'; // Asegura que sea visible
        }
        if (accionTitleDiv) {
            accionTitleDiv.style.display = 'block'; // Asegura que sea visible
        }
        buildAccionCarousel(accionCarouselId, gamesAccion);
    } else {
        // Ocultar si no está logeado O si está logeado pero no hay recomendaciones
        if (accionCarouselDiv) {
            accionCarouselDiv.style.display = 'none';
        }
        if (accionTitleDiv) {
            accionTitleDiv.style.display = 'none';
        }
        if (user && gamesAccion.length === 0) {
            console.log("Lo mejor en ACCIÓN carousel y título ocultos: Usuario logeado sin recomendaciones de contenido.");
        } else {
            console.log("Lo mejor en ACCIÓN carousel y título ocultos: Usuario no logeado.");
        }
    }
    // -----------------------------------------------------------

    // (Opcional) hover para dropdown
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