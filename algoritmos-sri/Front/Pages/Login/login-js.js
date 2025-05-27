function clearInput() {
    document.getElementById("loginForm").reset();
}

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("loginForm");

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    
    const nombre = form.uname.value.trim();
    if (!nombre) {
      alert("Debes ingresar tu nombre");
      return;
    }

    fetch("http://localhost:5000/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ nombre })
    })
      .then(res => {
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("Usuario no encontrado");
          }
          throw new Error("Error en el servidor");
        }
        return res.json();
      })
      .then(data => {
        localStorage.setItem("usuario", JSON.stringify({
          id: data.usuario.id,
          nombre: data.usuario.nombre
        }));
        window.location.href = "../Home/home.html";
      })
      .catch(err => {
        alert(`❌ ${err.message}`);
        console.error(err);
      });
  });
});
