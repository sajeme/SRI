let currentUserId = null; // Para almacenar el ID del usuario logueado
let currentRating = 0; // Para almacenar la calificación actual del usuario
let currentLikeStatus = null; // null: no interactuado, true: like, false: dislike

// El resto de tus funciones openNav, closeNav, logout, fetchGameDetails, etc.
function openNav() {
    document.getElementById("myNav").style.width = "50%";
    const elements = document.getElementsByClassName("bg");
    for (let i = 0; i < elements.length; i++) {
        elements[i].style.opacity = '20%';
    }
}

function closeNav() {
    document.getElementById("myNav").style.width = "0%";
    const elements = document.getElementsByClassName("bg");
    for (let i = 0; i < elements.length; i++) {
        elements[i].style.opacity = '100%';
    }
}

function logout() {
    localStorage.removeItem("usuario");
    window.location.href = "../Login/login.html";
}

async function fetchGameDetails(gameId) {
    console.log(`Buscando detalles para el juego con ID: ${gameId}`);
    try {
        const response = await fetch(`http://localhost:5000/games/${gameId}`);
        if (!response.ok) {
            // Un error HTTP (ej. 404, 500)
            const errorText = await response.text(); // Intenta leer el cuerpo del error
            throw new Error(`Error HTTP: ${response.status} - ${errorText || response.statusText}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Error al obtener los detalles del juego:", error);
        // Si hay un error de red o de parsing, se mostrará aquí
        alert("Error al cargar los detalles del juego. Asegúrate de que el servidor esté funcionando y la URL sea correcta.");
        return null;
    }
}

async function sendGameInteraction(id_usuario, id_juego, calificacion, like) {
    const payload = {
        id_usuario: id_usuario,
        id_juego: id_juego
    };

    // Añadir calificación solo si no es null o 0 (asumiendo que 0 no es una calificación válida para el modelo)
    if (calificacion !== null && calificacion > 0) {
        payload.calificacion = calificacion;
    }

    // Añadir like/dislike solo si no es null
    if (like !== null) {
        payload.like = like;
    }
    
    try {
        const response = await fetch('http://localhost:5000/responder_juego', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload), // Envía el payload construido dinámicamente
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Error al enviar interacción: ${response.status} - ${errorData.error || response.statusText}`);
        }

        const result = await response.json();
        console.log('Interacción enviada con éxito:', result);
        return true;
    } catch (error) {
        console.error("Error al enviar la interacción del juego:", error);
        alert(`Error al registrar tu interacción: ${error.message}. Por favor, verifica la conexión con el servidor.`);
        return false;
    }
}

function displayGameDetails(gameData) {
    const gameHighlightDiv = document.getElementById('game-highlight-div');
    if (!gameHighlightDiv) {
        console.error("El contenedor principal del juego ('game-highlight-div') no se encontró en el DOM.");
        return;
    }

    if (!gameData) {
        console.error("No se encontraron datos del juego para mostrar.");
        gameHighlightDiv.innerHTML = '<p class="text-light text-center p-5">Lo sentimos, no se pudieron cargar los detalles del juego.</p>';
        return;
    }

    document.getElementById('gameName').textContent = gameData.nombre || 'Nombre no disponible';
    document.getElementById('shortDescription').textContent = gameData.descripcion_corta || 'Descripción corta no disponible.';
    document.getElementById('releaseDate').textContent = gameData.fecha_publicacion || 'N/A';
    document.getElementById('developer').textContent = (gameData.desarrolladores && gameData.desarrolladores.length > 0) ? gameData.desarrolladores.join(', ') : 'N/A';
    document.getElementById('publisher').textContent = (gameData.publicadores && gameData.publicadores.length > 0) ? gameData.publicadores.join(', ') : 'N/A';
    document.getElementById('minimumAge').textContent = gameData.edad_minima > 0 ? `${gameData.edad_minima}+` : 'Todas las edades';
    document.getElementById('gamePrice').textContent = gameData.resumen_precio ? gameData.resumen_precio.final_formatted : 'Gratis';
    const longDescriptionElement = document.getElementById('longDescription');
    if (longDescriptionElement) {
        longDescriptionElement.innerHTML = gameData.descripcion_larga || 'Descripción larga no disponible.';
    }

    const carouselIndicators = document.getElementById('carouselIndicators');
    const carouselInner = document.getElementById('carouselInner');
    if (carouselIndicators) carouselIndicators.innerHTML = '';
    if (carouselInner) carouselInner.innerHTML = '';

    if (gameData.capturas && gameData.capturas.length > 0 && carouselIndicators && carouselInner) {
        gameData.capturas.forEach((url, index) => {
            const indicator = document.createElement('li');
            indicator.setAttribute('data-target', '#gameCarousel');
            indicator.setAttribute('data-slide-to', index);
            if (index === 0) indicator.classList.add('active');
            carouselIndicators.appendChild(indicator);

            const carouselItem = document.createElement('div');
            carouselItem.classList.add('carousel-item');
            if (index === 0) carouselItem.classList.add('active');
            const img = document.createElement('img');
            img.src = url;
            img.classList.add('d-block', 'w-100');
            img.alt = `Captura de pantalla ${index + 1}`;
            carouselItem.appendChild(img);
            carouselInner.appendChild(carouselItem);
        });
    } else if (gameData.portada && carouselInner) {
        const carouselItem = document.createElement('div');
        carouselItem.classList.add('carousel-item', 'active');
        const img = document.createElement('img');
        img.src = gameData.portada || 'placeholder.jpg';
        img.classList.add('d-block', 'w-100');
        img.alt = 'Imagen principal del juego';
        carouselItem.appendChild(img);
        carouselInner.appendChild(carouselItem);
        const prevControl = document.querySelector('.carousel-control-prev');
        const nextControl = document.querySelector('.carousel-control-next');
        if (prevControl) prevControl.style.display = 'none';
        if (nextControl) nextControl.style.display = 'none';
        if (carouselIndicators) carouselIndicators.style.display = 'none';
    } else {
        if (carouselInner) {
             carouselInner.innerHTML = '<p class="text-light text-center p-5">No hay imágenes disponibles.</p>';
        }
        const prevControl = document.querySelector('.carousel-control-prev');
        const nextControl = document.querySelector('.carousel-control-next');
        if (prevControl) prevControl.style.display = 'none';
        if (nextControl) nextControl.style.display = 'none';
        if (carouselIndicators) carouselIndicators.style.display = 'none';
    }

    const tagsContainer = document.getElementById('gameTags');
    if (tagsContainer) {
        tagsContainer.innerHTML = '';
        if (gameData.tags && gameData.tags.length > 0) {
            gameData.tags.forEach(tag => {
                const span = document.createElement('span');
                span.textContent = tag.description;
                span.classList.add('tag-badge', 'badge', 'badge-secondary', 'mr-1', 'mb-1', 'text-light', 'smallFont');
                tagsContainer.appendChild(span);
            });
        } else {
            tagsContainer.textContent = 'No hay etiquetas populares disponibles.';
            tagsContainer.classList.add('text-light', 'smallFont');
        }
    }

    const categoriesContainer = document.getElementById('gameCategories');
    if (categoriesContainer) {
        categoriesContainer.innerHTML = '';
        if (gameData.categorias && gameData.categorias.length > 0) {
            gameData.categorias.forEach(category => {
                const span = document.createElement('span');
                span.textContent = category;
                span.classList.add('category-badge', 'badge', 'badge-info', 'mr-1', 'mb-1', 'text-light', 'smallFont');
                categoriesContainer.appendChild(span);
            });
        } else {
            categoriesContainer.textContent = 'No hay categorías disponibles.';
            categoriesContainer.classList.add('text-light', 'smallFont');
        }
    }

    const minimumReqsDiv = document.getElementById('minimumRequirements');
    const recommendedReqsDiv = document.getElementById('recommendedRequirements');
    const systemRequirementsSection = document.getElementById('sysreq');

    if (minimumReqsDiv) minimumReqsDiv.innerHTML = '';
    if (recommendedReqsDiv) recommendedReqsDiv.innerHTML = '';

    if (gameData.requisitos_pc) {
        if (gameData.requisitos_pc.minimos && minimumReqsDiv) {
            const minTitle = document.createElement('h6');
            minTitle.textContent = 'Mínimos:';
            minTitle.classList.add('text-light');
            minimumReqsDiv.appendChild(minTitle);
            const minContent = document.createElement('div');
            minContent.innerHTML = gameData.requisitos_pc.minimos;
            minimumReqsDiv.appendChild(minContent);
        }
        if (gameData.requisitos_pc.recomendados && recommendedReqsDiv) {
            const recTitle = document.createElement('h6');
            recTitle.textContent = 'Recomendados:';
            recTitle.classList.add('text-light');
            recommendedReqsDiv.appendChild(recTitle);
            const recContent = document.createElement('div');
            recContent.innerHTML = gameData.requisitos_pc.recomendados;
            recommendedReqsDiv.appendChild(recContent);
        }
    } else {
        if (systemRequirementsSection) {
            systemRequirementsSection.innerHTML = '<h5 style="color: #66c0f4; text-align: left;">Requisitos del Sistema</h5><p class="smallFont text-light">No hay requisitos del sistema disponibles.</p>';
        }
    }

    // Lógica del botón de compra y calificación/like-dislike
    const buyGameBtn = document.getElementById('buyGameBtn');
    const ratingSection = document.getElementById('ratingSection'); // Sección de estrellas y botón enviar
    const likeDislikeSection = document.getElementById('likeDislikeSection'); // Sección de Like/Dislike
    const buyButtonLink = document.getElementById('buyButtonLink');
    const gameId = gameData.id; // Asumiendo que el ID del juego es 'id' en los datos de la API

    const stars = ratingSection ? ratingSection.querySelectorAll('.star') : [];
    const likeBtn = document.getElementById('likeBtn');
    const dislikeBtn = document.getElementById('dislikeBtn');
    const submitRatingBtn = document.getElementById('submitRatingBtn');

    let selectedRating = 0;
    let selectedLike = null; // true para like, false para dislike, null si no ha seleccionado

    const user = JSON.parse(localStorage.getItem("usuario"));

    // Mostrar/ocultar secciones basadas en el estado de inicio de sesión y compra
    if (user) {
        likeDislikeSection.style.display = 'block'; // Mostrar Like/Dislike si el usuario está logeado
        const userPurchases = JSON.parse(localStorage.getItem(`purchases_${user.id}`)) || [];
        const hasPurchased = userPurchases.includes(gameId);

        if (hasPurchased) {
            buyGameBtn.textContent = "Comprado";
            buyGameBtn.disabled = true;
            buyGameBtn.classList.remove('btn-success');
            buyGameBtn.classList.add('btn-secondary');
            ratingSection.style.display = 'block'; // Mostrar sección de calificación si ya comprado
            if (buyButtonLink) {
                buyButtonLink.removeAttribute('href');
                buyButtonLink.style.cursor = 'default';
            }
        } else {
            // No comprado: El botón de compra habilitado, calificación oculta
            buyGameBtn.addEventListener('click', (event) => {
                event.preventDefault(); // Evita cualquier redirección
                
                console.log(`Usuario ${user.id} ha "comprado" el juego ${gameData.nombre} (ID: ${gameId})`);
                userPurchases.push(gameId);
                localStorage.setItem(`purchases_${user.id}`, JSON.stringify(userPurchases));

                buyGameBtn.textContent = "Comprado";
                buyGameBtn.disabled = true;
                buyGameBtn.classList.remove('btn-success');
                buyGameBtn.classList.add('btn-secondary');
                ratingSection.style.display = 'block'; // Mostrar sección de calificación
                if (buyButtonLink) {
                    buyButtonLink.removeAttribute('href');
                    buyButtonLink.style.cursor = 'default';
                }
            });
        }
    } else {
        // No logeado: El botón de compra redirige a login, like/dislike y calificación ocultos
        likeDislikeSection.style.display = 'none';
        ratingSection.style.display = 'none';
        if (buyButtonLink) {
            buyButtonLink.href = "../Login/login.html";
        } else {
            buyGameBtn.onclick = () => {
                window.location.href = "../Login/login.html";
            };
        }
    }

    // Lógica de calificación por estrellas
    stars.forEach(star => {
        star.addEventListener('click', function() {
            selectedRating = parseFloat(this.dataset.value);
            stars.forEach((s, i) => {
                if (i < selectedRating) {
                    s.style.color = '#ffc107';
                } else {
                    s.style.color = '#e4e4e4';
                }
            });
        });
        star.addEventListener('mouseover', function() {
            stars.forEach((s, i) => {
                if (i < this.dataset.value) {
                    s.style.color = '#ffc107';
                } else {
                    s.style.color = '#e4e4e4';
                }
            });
        });
        star.addEventListener('mouseout', function() {
            stars.forEach((s, i) => {
                if (i < selectedRating) {
                    s.style.color = '#ffc107';
                } else {
                    s.style.color = '#e4e4e4';
                }
            });
        });
    });

    // Lógica para botones de Like/Dislike (siempre visibles para logeados)
    if (likeBtn && dislikeBtn) {
        likeBtn.addEventListener('click', async () => {
            if (user && user.id) {
              
                selectedLike = true;
                likeBtn.classList.add('active');
                dislikeBtn.classList.remove('active');
                likeBtn.style.backgroundColor = '#28a745';
                likeBtn.style.color = 'white';
                dislikeBtn.style.backgroundColor = '';
                dislikeBtn.style.color = '';

                // Si aún no se ha calificado (es decir, ratingSection está oculto)
                // O si la calificación ya se envió pero se quiere cambiar el like/dislike
                if (ratingSection.style.display === 'none' || selectedRating === 0) { // Si solo se da like/dislike sin calificación
                    const success = await sendGameInteraction(user.id, gameId, null, selectedLike); // Envía null para la calificación
                    if (success) {
                        alert('¡Me gusta registrado!');
                    }
                }
            } else {
                alert('Debes iniciar sesión para indicar si te gusta este juego.');
                window.location.href = "../Login/login.html";
            }
        });

        dislikeBtn.addEventListener('click', async () => {
            if (user && user.id) {
                selectedLike = false;
                dislikeBtn.classList.add('active');
                likeBtn.classList.remove('active');
                dislikeBtn.style.backgroundColor = '#dc3545';
                dislikeBtn.style.color = 'white';
                likeBtn.style.backgroundColor = '';
                likeBtn.style.color = '';

                // Si aún no se ha calificado (es decir, ratingSection está oculto)
                if (ratingSection.style.display === 'none' || selectedRating === 0) { // Si solo se da like/dislike sin calificación
                    const success = await sendGameInteraction(user.id, gameId, null, selectedLike); // Envía null para la calificación
                    if (success) {
                        alert('¡No me gusta registrado!');
                    }
                }
            } else {
                alert('Debes iniciar sesión para indicar si te gusta este juego.');
                window.location.href = "../Login/login.html";
            }
        });
    }

    // Evento al enviar calificación (solo si se ha comprado el juego)
    if (submitRatingBtn) {
        submitRatingBtn.addEventListener('click', async () => {
            if (user && user.id) {
                if (selectedRating > 0 && selectedLike !== null) {
                    const success = await sendGameInteraction(user.id, gameId, selectedRating, selectedLike);
                    if (success) {
                        alert('¡Gracias por tu calificación y tu opinión!');
                        // Opcional: Deshabilitar la sección de calificación después de enviar
                        // ratingSection.style.display = 'none';
                    }
                } else {
                    alert('Por favor, selecciona una calificación por estrellas y elige "Me gusta" o "No me gusta".');
                }
            } else {
                alert('Debes iniciar sesión para calificar el juego.');
                window.location.href = "../Login/login.html";
            }
        });
    }
}


async function loadProductDetails() {
    const urlParams = new URLSearchParams(window.location.search);
    const gameId = urlParams.get('game_id');

    const gameHighlightDiv = document.getElementById('game-highlight-div');
    if (!gameHighlightDiv) {
        console.error("El contenedor principal del juego ('game-highlight-div') no se encontró en el DOM al cargar los detalles.");
        return;
    }

    if (gameId) {
        const gameData = await fetchGameDetails(gameId);
        displayGameDetails(gameData);
    } else {
        console.error("No se encontró el ID del juego (game_id) en la URL.");
        gameHighlightDiv.innerHTML = '<p class="text-light text-center p-5">Lo sentimos, no se especificó un juego para mostrar. Por favor, asegúrate de que la URL contenga un parámetro "game_id".</p>';
    }
}

document.addEventListener("DOMContentLoaded", async function () {
    const user = JSON.parse(localStorage.getItem("usuario"));
    const cuentaMenu = document.getElementById("cuentaMenu");
    const cuentaOpciones = document.getElementById("cuentaOpciones");

    if (cuentaMenu && cuentaOpciones) {
        if (user) {
            cuentaMenu.textContent = `Hola, ${user.nombre}`;
            cuentaOpciones.innerHTML = `
                <a class="dropdown-item menuItem" href="#" onclick="logout()">Cerrar sesión</a>
            `;
        } else {
            cuentaMenu.textContent = "Cuenta";
            cuentaOpciones.innerHTML = `
                <a class="dropdown-item menuItem" href="../Login/login.html">Inicia Sesión</a>
                <a class="dropdown-item menuItem" href="../Register/register.html">Regístrate</a>
            `;
        }

        document.querySelectorAll('.nav-item.dropdown').forEach(item => {
            item.addEventListener('mouseenter', () => {
                item.classList.add('show');
                const dropdown = item.querySelector('.dropdown-menu');
                if (dropdown) dropdown.classList.add('show');
            });
            item.addEventListener('mouseleave', () => {
                item.classList.remove('show');
                const dropdown = item.querySelector('.dropdown-menu');
                if (dropdown) dropdown.classList.remove('show');
            });
        });
    } else {
        console.warn("Elementos de menú de cuenta no encontrados. La funcionalidad de usuario puede estar limitada.");
    }

    await loadProductDetails();
});