// =========================================================
//  CONFIG GLOBAL
// =========================================================
// Tu API está corriendo en el 8000, no en el 8001
const API_URL = "https://lafornace-pizzeria.onrender.com";


// =========================================================
//  SESIÓN LOCALSTORAGE
// =========================================================
function saveSession(token, usuario) {
    localStorage.setItem("token", token);
    localStorage.setItem("usuario", JSON.stringify(usuario));
}

function getToken() {
    return localStorage.getItem("token");
}

function getUsuario() {
    try {
        return JSON.parse(localStorage.getItem("usuario"));
    } catch {
        return null;
    }
}

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    window.location.href = "index.html";
}


// =========================================================
//  API REQUEST UNIVERSAL
// =========================================================
async function apiRequest(endpoint, method = "GET", data = null, auth = false) {

    const headers = {
        "Content-Type": "application/json"
    };

    if (auth) {
        const token = getToken();
        if (token) headers["Authorization"] = "Bearer " + token;
    }

    const options = { method, headers };

    if (data) options.body = JSON.stringify(data);

    const response = await fetch(API_URL + endpoint, options);

    let json;
    try {
        json = await response.json();
    } catch {
        throw { detail: "Error procesando respuesta del servidor" };
    }

    if (!response.ok) {
        if (json.detail === "Token inválido o expirado") {
            logout();
        }
        throw json;
    }

    return json;
}


// =========================================================
//  VALIDACIÓN DE RUTAS
// =========================================================
const protectedPages = [
    "us05-carrito.html",
    "us06-pago.html",
    "us07-boleta.html",
];

const adminPages = [
    "us08-despacho.html",
    "us10-admin.html"
];

function validateRoute() {
    const path = window.location.pathname.split("/").pop();
    const usuario = getUsuario();
    const token = getToken();

    // Rutas que requieren login
    if (protectedPages.includes(path)) {
        if (!token) {
            alert("Debes iniciar sesión para acceder.");
            window.location.href = "us02-login.html";
            return;
        }
    }

    // Rutas admin
    if (adminPages.includes(path)) {
        if (!usuario || usuario.es_admin !== true) {
            alert("Acceso solo para administradores.");
            window.location.href = "index.html";
            return;
        }
    }
}

validateRoute();


// =========================================================
//  NAVBAR DINÁMICO
// =========================================================
function renderNavbar() {
    const usuario = getUsuario();
    const navUL = document.querySelector(".offcanvas-body ul");
    if (!navUL) return;

    if (usuario) {
        navUL.innerHTML = `
            <li class="nav-item">
                <span class="nav-link disabled">Hola, ${usuario.nombre}</span>
            </li>

            <li class="nav-item"><a class="nav-link" href="us04-menu.html">Menú</a></li>
            <li class="nav-item"><a class="nav-link" href="us05-carrito.html">Carrito</a></li>
            <li class="nav-item"><a class="nav-link" href="us09-seguimiento.html">Seguimiento</a></li>

            <li class="nav-item mt-2"><hr class="border-secondary"></li>
            <li class="nav-item"><a class="nav-link text-danger" href="#" onclick="logout()">Cerrar sesión</a></li>
        `;

        if (usuario.es_admin) {
            navUL.innerHTML += `
                <li class="nav-item mt-2"><hr class="border-secondary"></li>
                <li class="nav-item"><a class="nav-link text-warning" href="us08-despacho.html">Despacho (Admin)</a></li>
                <li class="nav-item"><a class="nav-link text-warning" href="us10-admin.html">Productos (Admin)</a></li>
            `;
        }
    }
    else {
        navUL.innerHTML = `
            <li class="nav-item"><a class="nav-link" href="index.html">Inicio</a></li>
            <li class="nav-item"><a class="nav-link" href="us04-menu.html">Menú</a></li>
            <li class="nav-item"><a class="nav-link" href="us02-login.html">Iniciar sesión</a></li>
            <li class="nav-item"><a class="nav-link" href="us01-registro.html">Registrarme</a></li>
        `;
    }
}

renderNavbar();


// =========================================================
//  LLAMADAS A LA API
// =========================================================

// ---------- REGISTRO ----------
// OJO: el backend espera: nombre, correo, contrasena, direccion, telefono
async function registrarUsuario(nombre, email, password, direccion, telefono) {
    const payload = {
        nombre: nombre,
        email: email,
        password: password,
        direccion: direccion || null,
        telefono: telefono || null
    };

    return await apiRequest("/usuarios/registro", "POST", payload);
}

// ---------- LOGIN ----------
// El backend también espera: correo y contrasena
async function loginUsuario(email, password) {
    const res = await apiRequest("/usuarios/login", "POST", {
        email: email,
        password: password
    });

    saveSession(res.token, res.usuario);
    return res.usuario;
}


// ---------- PIZZAS ----------
async function getPizzas() {
    return await apiRequest("/pizzas", "GET");
}

// ---------- PEDIDOS ----------
async function crearPedido(usuario_id, items) {
    return await apiRequest("/pedidos", "POST", { usuario_id, items }, true);
}

async function getSeguimiento(codigo) {
    return await apiRequest(`/pedidos/seguimiento/${codigo}`, "GET");
}
