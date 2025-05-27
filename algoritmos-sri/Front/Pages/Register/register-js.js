function clearInput() {
    document.getElementById("loginForm").reset();
}

document.addEventListener("DOMContentLoaded", function () {
  let selectedGenres = [];

  // Manejo de selección de géneros
  document.querySelectorAll('.grid a').forEach(card => {
    card.addEventListener('click', function (e) {
      e.preventDefault();
      const genre = this.querySelector("span")?.textContent.trim();  // lee el texto <span>Acción</span>

      if (!genre) return;

      if (selectedGenres.includes(genre)) {
        selectedGenres = selectedGenres.filter(g => g !== genre);
        this.classList.remove('selected-genre');
      } else {
        selectedGenres.push(genre);
        this.classList.add('selected-genre');
      }
    });
  });

  // Botón de continuar (en segundo slide)
  const finishBtn = document.getElementById("finishBtn");
  if (finishBtn) {
    finishBtn.addEventListener("click", function () {
      const username = document.querySelector('input[name="username"]')?.value;
      const age = parseInt(document.querySelector('input[name="age2"]')?.value);

      if (!username || isNaN(age) || selectedGenres.length === 0) {
        alert("Por favor completa todos los campos.");
        return;
      }

      const newUser = {
        nombre: username,
        edad: age,
        generos_favoritos: selectedGenres
      };

      fetch("http://localhost:5000/usuarios", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(newUser)
        })
        .then(response => {
            if (response.status === 409) {
            return response.json().then(data => {
                alert(data.error); // alerta si nombre duplicado
                throw new Error(data.error);
            });
            }
            return response.json();
        })
        .then(data => {
            console.log("✅ Usuario creado:", data);

            localStorage.setItem("usuario", JSON.stringify({
                id: data.usuario.id,
                nombre: data.usuario.nombre
            }));

            window.location.href = "../Home/home.html";
         })


    });
  }
});

