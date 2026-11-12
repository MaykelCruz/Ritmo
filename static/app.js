/* Interfaz del reproductor. Solo dibuja: toda la lógica de datos está en Python. */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = s => Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");

/* Un color por género: fondo y color de texto con contraste suficiente */
const GENEROS = {
  Rock: ["#2f4bff", "#ffffff"],
  Pop: ["#d62f63", "#ffffff"],
  Salsa: ["#ffb72b", "#0e1633"],
  Folclor: ["#0b7f60", "#ffffff"],
  "Reggaetón": ["#6b3ff0", "#ffffff"],
  Cumbia: ["#c2410c", "#ffffff"],
  Bachata: ["#9d174d", "#ffffff"],
  Merengue: ["#0369a1", "#ffffff"],
  "Regional mexicano": ["#7c2d12", "#ffffff"],
  Balada: ["#a21caf", "#ffffff"],
  "Hip hop": ["#334155", "#ffffff"],
  "Electrónica": ["#22d3ee", "#0e1633"],
  Jazz: ["#a16207", "#ffffff"],
  "Clásica": ["#e2e8f0", "#0e1633"],
  Otro: ["#0e1633", "#ffffff"],
};
const colorGenero = g => GENEROS[g] || GENEROS.Otro;
const estiloG = g => { const [bg, fg] = colorGenero(g); return `--g:${bg};--gt:${fg}`; };
let versionPortadas = Date.now();      // cambia al subir una portada, para que el navegador la recargue
const urlPortada = c => `/portada/${c.id}?v=${versionPortadas}`;
const portada = c => `<div class="port" style="${estiloG(c.genero)}" aria-hidden="true">${c.portada ? `<img src="${urlPortada(c)}" alt="">` : esc(c.titulo.trim()[0].toUpperCase())}</div>`;

const ICONOS = {
  play: '<path d="M8 5v14l11-7z"/>',
  pausa: '<path d="M7 5h4v14H7zM13 5h4v14h-4z"/>',
  sig: '<path d="M6 6l9 6-9 6zM17 6h2v12h-2z"/>',
  ant: '<path d="M18 6l-9 6 9 6zM5 6h2v12H5z"/>',
  mezcla: '<path d="M16 4h4v4M20 4l-6 6M4 20l16-16M16 20h4v-4M20 20l-5-5M4 4l5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  repetir: '<path d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  mas: '<path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  cont: '<path d="M4 7h10M4 12h10M4 17h6M18 9v8M14 13h8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  borrar: '<path d="M5 7h14M10 11v6M14 11v6M8 7l1-3h6l1 3M7 7l1 13h8l1-13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  subir: '<path d="M6 15l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
  bajar: '<path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
  quitar: '<path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  nota: '<path d="M9 18V5l11-2v13M9 18a3 3 0 1 1-3-3 3 3 0 0 1 3 3zm11-2a3 3 0 1 1-3-3 3 3 0 0 1 3 3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  volver: '<path d="M9 14L4 9l5-5M4 9h10a6 6 0 0 1 0 12h-3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
};
const ic = (n, acc, id, titulo, extra = "") =>
  `<button class="ic ${extra}" data-acc="${acc}" ${id != null ? `data-id="${id}"` : ""} title="${titulo}" aria-label="${titulo}"><svg viewBox="0 0 24 24" fill="currentColor">${ICONOS[n]}</svg></button>`;

let S = null;            // estado completo que manda Python
let R = [];              // resultados de la búsqueda en la biblioteca
let metodo = "";
let tabActual = "inicio";
let sonando = false;     // reproducción simulada
let pos = 0;             // segundos transcurridos
let ultimoId = null;
let camino = null;       // camino mostrado en el grafo
let avanzando = false;

const porId = id => S.canciones.find(c => c.id === id);
const actual = () => (S && S.playlist.actual != null ? porId(S.playlist.actual) : null);

/* ---------- audio real (si la canción tiene archivo en musica/) ---------- */
const audio = new Audio();
audio.preload = "auto";
let idAudio = null;      // canción cargada en el elemento de audio
const hayAudio = c => !!(c && c.audio);
/* Duración que manda: la del archivo si está cargado; si no, la que dice el JSON */
const duracionDe = c => (hayAudio(c) && idAudio === c.id && isFinite(audio.duration) ? Math.floor(audio.duration) : c.duracion);

function sincronizarAudio() {
  const c = actual();
  if (!hayAudio(c)) { audio.pause(); return; }
  if (idAudio !== c.id) { audio.src = `/audio/${c.id}`; idAudio = c.id; }
  if (sonando) {
    audio.play().catch(() => { sonando = false; aviso("El navegador bloqueó el audio. Pulsa reproducir."); pintarTodo(); });
  } else audio.pause();
}
audio.addEventListener("timeupdate", () => { if (hayAudio(actual()) && idAudio === actual().id) { pos = Math.floor(audio.currentTime); pintarProgreso(); } });
audio.addEventListener("loadedmetadata", () => { pintarReproductor(); });
audio.addEventListener("ended", () => avanzarSolo());
audio.addEventListener("error", () => { if (audio.src) aviso("No se pudo reproducir el archivo de audio"); });

/* Pasa a la siguiente cuando termina la canción (audio real o simulada) */
async function avanzarSolo() {
  if (avanzando) return;
  avanzando = true;
  try {
    const antes = ultimoId;
    const d = await api("/api/siguiente", "POST");
    if (!d.cambio) sonando = false;
    pos = 0;
    await recargar();
    if (d.cambio && S.playlist.actual === antes && hayAudio(actual())) { audio.currentTime = 0; sincronizarAudio(); }   // lista de una sola canción en bucle
  } finally { avanzando = false; }
}

/* ---------- comunicación con Python ---------- */
async function api(url, metodoHttp = "GET", cuerpo) {
  const r = await fetch(url, {
    method: metodoHttp,
    headers: { "Content-Type": "application/json" },
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { aviso(d.error || "Algo salió mal"); const err = new Error(d.error); err.campos = d.campos; throw err; }
  return d;
}
let temporizadorAviso;
function aviso(texto) {
  const el = $("#aviso");
  el.textContent = texto; el.classList.add("ver");
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => el.classList.remove("ver"), 2400);
}
async function buscar() {
  const q = $("#q").value, campo = $("#campo").value, orden = $("#orden").value;
  const d = await api(`/api/buscar?q=${encodeURIComponent(q)}&campo=${campo}&orden=${orden}`);
  R = d.resultados; metodo = d.metodo;
  pintarBiblioteca();
}
async function recargar() {
  S = await api("/api/estado");
  const id = S.playlist.actual;
  if (id !== ultimoId) { pos = 0; ultimoId = id; }
  if (id == null) sonando = false;
  await buscar();
  pintarTodo();
  sincronizarAudio();
  actualizarSistema();
}

/* ---------- Inicio ---------- */
function pintarInicio() {
  const p = S.playlist, c = actual(), rec = S.recomendaciones;
  const hero = c ? `
    <div class="hero" style="${estiloG(c.genero)}">
      <div>
        <span class="hero-genero">${esc(c.genero)}</span>
        <h1>${esc(c.titulo)}</h1>
        <p class="artista">${esc(c.artista)}</p>
        <div class="hero-ctrl">
          ${ic("ant", "anterior", null, "Anterior")}
          <button class="ic play" data-acc="pp" title="${sonando ? "Pausar" : "Reproducir"}" aria-label="${sonando ? "Pausar" : "Reproducir"}"><svg viewBox="0 0 24 24" fill="currentColor">${sonando ? ICONOS.pausa : ICONOS.play}</svg></button>
          ${ic("sig", "siguiente", null, "Siguiente")}
        </div>
        ${c.audio ? "" : '<p class="aviso-sim">Esta canción no tiene archivo de audio, así que suena en modo simulado. Puedes adjuntarlo desde la biblioteca.</p>'}
      </div>
      <div class="disco ${sonando ? "gira" : ""}"><div class="vinilo"><div class="etiqueta-d" ${c.portada ? `style="background-image:url('${urlPortada(c)}')"` : ""}>${c.portada ? "" : esc(c.artista.trim()[0].toUpperCase())}</div></div></div>
    </div>` : `
    <div class="hero hero-vacio" style="${estiloG("Otro")}">
      <div><h1>Elige algo para escuchar</h1><p class="artista">Tu cola está vacía. Busca una canción en la biblioteca y empieza.</p>
        <button class="btn" data-acc="ir" data-tab="biblioteca">Ir a la biblioteca</button></div>
      <div class="disco"><div class="vinilo"><div class="etiqueta-d">R</div></div></div>
    </div>`;

  const cola = p.ids.map((id, n) => {
    const x = porId(id);
    return `<div class="fila ${id === p.actual ? "suena" : ""}">
      ${portada(x)}
      <div><div class="t">${esc(x.titulo)}</div><div class="a">${esc(x.artista)}</div></div>
      <div class="acc"><span class="dur">${fmt(x.duracion)}</span>${ic("play", "reproducir", id, "Reproducir")}${ic("subir", "subir", id, "Subir en la cola")}${ic("bajar", "bajar", id, "Bajar en la cola")}${ic("quitar", "quitar", id, "Quitar de la cola")}</div>
    </div>`;
  }).join("");
  const recs = rec.canciones.slice(0, 6).map(x => `
    <div class="fila">
      ${portada(x)}
      <div><div class="t">${esc(x.titulo)}</div><div class="a">${esc(x.artista)}${x.distancia === 1 ? "" : ", a dos saltos"}</div></div>
      <div class="acc"><div class="afin" title="Afinidad ${x.afinidad} de 10"><b style="width:${x.afinidad * 10}%"></b></div>${ic("play", "reproducir", x.id, "Reproducir")}${ic("mas", "agregar", x.id, "Añadir a la cola")}</div>
    </div>`).join("");
  const hist = S.historial.map((id, n) => {
    const x = porId(id);
    return `<div class="fila">${portada(x)}<div><div class="t">${esc(x.titulo)}</div><div class="a">${esc(x.artista)}</div></div>${n === 0 ? '<span class="salto">sonando</span>' : "<span></span>"}</div>`;
  }).join("");

  $("#inicio").innerHTML = `${hero}
    <div class="dos-col">
      <section>
        <div class="cab-lista"><h2>Cola de reproducción</h2>
          <div class="btns"><button class="btn sec" data-acc="mezclar">Mezclar</button>
          <button class="btn sec ${p.circular ? "on" : ""}" data-acc="circular" aria-pressed="${p.circular}">Repetir lista</button></div></div>
        <div class="lista">${cola || '<div class="vacio">Añade canciones desde la biblioteca.</div>'}</div>
      </section>
      <div>
        <section class="bloque"><h2>${rec.artista ? "Si te gusta " + esc(rec.artista) : "Para ti"}</h2>
          <div class="lista">${recs || '<div class="vacio">Reproduce una canción y aquí verás artistas parecidos.</div>'}</div></section>
        <section class="bloque"><div class="cab-lista"><h2>Escuchado hace poco</h2><button class="btn sec" data-acc="volver">Volver a la anterior</button></div>
          <div class="lista">${hist || '<div class="vacio">Todavía no has escuchado nada.</div>'}</div></section>
      </div>
    </div>`;
}

/* ---------- Biblioteca ---------- */
const EXT_IMAGEN = /\.(jpe?g|png|webp)$/i, EXT_AUDIO = /\.(mp3|ogg|wav|m4a)$/i;
let editando = null;           // id de la canción que se está editando (null = canción nueva)
let tocados = new Set();       // campos que la persona ya tocó (solo a esos se les muestra el error)
let temporizadorValidar;
let secuenciaValidar = 0;      // numera las consultas: si una respuesta llega tarde, se ignora

/* Revisa un archivo antes de subirlo. Devuelve el mensaje de error, o "" si está bien. */
function revisarArchivo(archivo, tipo) {
  const imagen = tipo === "portada";
  const limiteMb = imagen ? S.limites.portada_mb : S.limites.audio_mb;
  if (!(imagen ? EXT_IMAGEN : EXT_AUDIO).test(archivo.name)) return imagen ? "Usa una imagen jpg, png o webp." : "Usa un audio mp3, ogg, wav o m4a.";
  if (archivo.size === 0) return "El archivo está vacío.";
  if (archivo.size > limiteMb * 1024 * 1024) return `Pesa demasiado (máximo ${limiteMb} MB).`;
  return "";
}
/* Sube el audio o la portada de una canción (el servidor vuelve a validar todo) */
async function subirArchivo(id, archivo, tipo) {
  const mensaje = revisarArchivo(archivo, tipo);
  if (mensaje) { aviso(mensaje); throw new Error(mensaje); }
  const datos = new FormData();
  datos.append("archivo", archivo);
  const r = await fetch(`/api/canciones/${id}/${tipo}`, { method: "POST", body: datos });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { aviso(d.error || "No se pudo subir el archivo"); throw new Error(d.error); }
  if (tipo === "portada") versionPortadas = Date.now();
  return tipo === "portada" ? "Portada guardada" : "Audio guardado";
}
/* Abre el selector de archivos del sistema para una canción de la lista */
function elegirArchivo(selector, id, tipo) {
  return new Promise(resolver => {
    const entrada = $(selector);
    entrada.onchange = async () => {
      const f = entrada.files[0]; entrada.value = "";
      if (f) { try { aviso(await subirArchivo(id, f, tipo)); } catch (_) { } }
      resolver();
    };
    entrada.addEventListener("cancel", resolver, { once: true });
    entrada.click();
  });
}

const datosForm = () => ({ titulo: $("#f-titulo").value, artista: $("#f-artista").value, genero: $("#f-genero").value, duracion: $("#f-duracion").value, excluir_id: editando });
function mostrarError(campo, mensaje) {
  const p = $(`[data-error="${campo}"]`);
  if (p) p.textContent = mensaje || "";
  const entrada = $("#form-cancion").elements[campo];
  if (entrada) entrada.setAttribute("aria-invalid", mensaje ? "true" : "false");
}
function pintarChips(artistas) {
  $("#chips-art").innerHTML = artistas.length > 1
    ? `<span class="suave chico">${artistas.length} artistas:</span>` + artistas.map(a => `<span class="chip-art">${esc(a)}</span>`).join("")
    : "";
}
/* Pregunta al servidor si los datos son válidos y los muestra mientras escribes */
function validarEnVivo({ inmediato = false, todos = false } = {}) {
  clearTimeout(temporizadorValidar);
  const ejecutar = async () => {
    const turno = ++secuenciaValidar;
    const d = await api("/api/validar", "POST", datosForm());
    if (turno !== secuenciaValidar) return d;            // llegó otra consulta más nueva: esta ya no vale
    pintarChips(d.artistas);
    ["titulo", "artista", "genero", "duracion"].forEach(c => mostrarError(c, todos || tocados.has(c) ? d.errores[c] : ""));
    return d;
  };
  if (inmediato || todos) return ejecutar();
  temporizadorValidar = setTimeout(ejecutar, 250);
}
function abrirForm(c) {
  editando = c ? c.id : null;
  tocados = new Set();
  $("#f-titulo").value = c ? c.titulo : "";
  $("#f-artista").value = c ? c.artista : "";
  $("#f-genero").value = c ? c.genero : "Otro";
  $("#f-duracion").value = c ? fmt(c.duracion) : "";
  $("#f-portada").value = ""; $("#f-audio").value = "";
  const vista = $("#vista-portada");
  if (c && c.portada) { vista.src = urlPortada(c); vista.hidden = false; } else { vista.removeAttribute("src"); vista.hidden = true; }
  $("#resumen-form").textContent = c ? `Editar «${c.titulo}»` : "Añadir una canción";
  $("#guardar-form").textContent = c ? "Guardar cambios" : "Guardar canción";
  $("#nota-archivos").hidden = !c;
  ["titulo", "artista", "genero", "duracion", "portada", "audio"].forEach(k => mostrarError(k, ""));
  $("#panel-form").open = true;
  validarEnVivo({ inmediato: true });
  $("#panel-form").scrollIntoView({ behavior: "smooth", block: "start" });
  $("#f-titulo").focus({ preventScroll: true });
}
function cerrarForm() {
  editando = null; tocados = new Set();
  abrirFormVacio();
  $("#panel-form").open = false;
}
function abrirFormVacio() {
  $("#form-cancion").reset();
  $("#f-genero").value = "Otro";
  const vista = $("#vista-portada"); vista.removeAttribute("src"); vista.hidden = true;
  $("#resumen-form").textContent = "Añadir una canción";
  $("#guardar-form").textContent = "Guardar canción";
  $("#nota-archivos").hidden = true;
  pintarChips([]);
  ["titulo", "artista", "genero", "duracion", "portada", "audio"].forEach(k => mostrarError(k, ""));
}

function armarBiblioteca() {
  const L = S.limites;
  $("#biblioteca").innerHTML = `
    <h1 class="titulo-pag">Biblioteca</h1>
    <p class="sub">Busca por título, artista o género y añade lo que quieras a tu cola.</p>
    <div class="herr">
      <input type="search" id="q" maxlength="100" placeholder="Buscar una canción" aria-label="Buscar">
      <select id="campo" aria-label="Buscar en"><option value="titulo">en título</option><option value="artista">en artista</option><option value="genero">en género</option></select>
      <select id="orden" aria-label="Ordenar por"><option value="titulo">ordenar por título</option><option value="artista">ordenar por artista</option><option value="genero">ordenar por género</option><option value="duracion">ordenar por duración</option></select>
    </div>
    <details class="panel-form" id="panel-form"><summary id="resumen-form">Añadir una canción</summary>
      <form id="form-cancion" novalidate autocomplete="off">
        <div class="campo"><label for="f-titulo">Título</label>
          <input id="f-titulo" name="titulo" maxlength="${L.titulo}" required>
          <p class="error" data-error="titulo" role="alert"></p></div>
        <div class="campo"><label for="f-artista">Artistas</label>
          <input id="f-artista" name="artista" maxlength="${L.artista * L.max_artistas}" required aria-describedby="ayuda-artista">
          <p class="ayuda" id="ayuda-artista">Si son varios, sepáralos con coma, &amp;, «feat.» o «y».</p>
          <div class="chips-art" id="chips-art" aria-live="polite"></div>
          <p class="error" data-error="artista" role="alert"></p></div>
        <div class="campo"><label for="f-genero">Género</label>
          <select id="f-genero" name="genero">${S.generos.map(g => `<option>${esc(g)}</option>`).join("")}</select>
          <p class="error" data-error="genero" role="alert"></p></div>
        <div class="campo"><label for="f-duracion">Duración</label>
          <input id="f-duracion" name="duracion" placeholder="3:45" inputmode="numeric" maxlength="8" required>
          <p class="error" data-error="duracion" role="alert"></p></div>
        <div class="campo"><label for="f-portada">Portada (opcional)</label>
          <div class="portada-sel"><img id="vista-portada" alt="Vista previa de la portada" hidden>
            <input id="f-portada" name="portada" type="file" accept="image/jpeg,image/png,image/webp"></div>
          <p class="ayuda">jpg, png o webp, hasta ${L.portada_mb} MB.</p>
          <p class="error" data-error="portada" role="alert"></p></div>
        <div class="campo"><label for="f-audio">Audio (opcional)</label>
          <input id="f-audio" name="audio" type="file" accept="audio/mpeg,audio/ogg,audio/wav,audio/mp4,.mp3,.ogg,.wav,.m4a">
          <p class="ayuda">mp3, ogg, wav o m4a, hasta ${L.audio_mb} MB.</p>
          <p class="error" data-error="audio" role="alert"></p></div>
        <p class="ayuda ancho" id="nota-archivos" hidden>Si no eliges archivos nuevos, se conservan la portada y el audio actuales.</p>
        <div class="acciones-form ancho"><button class="btn" id="guardar-form">Guardar canción</button><button type="button" class="btn sec" id="cancelar-form">Cancelar</button></div>
      </form>
    </details>
    <input type="file" id="archivo-audio" accept="audio/mpeg,audio/ogg,audio/wav,audio/mp4,.mp3,.ogg,.wav,.m4a" hidden>
    <input type="file" id="archivo-imagen" accept="image/jpeg,image/png,image/webp" hidden>
    <p class="dato" id="metodo"></p>
    <div class="lista" id="lista-bib"></div>`;

  let espera;
  ["#q", "#campo", "#orden"].forEach(s => $(s).addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(buscar, 160); }));

  /* Validación mientras escribes: el servidor decide qué es válido */
  ["f-titulo", "f-artista", "f-genero", "f-duracion"].forEach(id => {
    $("#" + id).addEventListener("input", e => { tocados.add(e.target.name); validarEnVivo(); });
  });
  /* Archivos: se revisan al elegirlos, antes de enviar nada */
  [["#f-portada", "portada"], ["#f-audio", "audio"]].forEach(([sel, tipo]) => {
    $(sel).addEventListener("change", e => {
      const f = e.target.files[0];
      const mensaje = f ? revisarArchivo(f, tipo) : "";
      mostrarError(tipo, mensaje);
      if (mensaje) e.target.value = "";
      if (tipo === "portada") {
        const vista = $("#vista-portada");
        if (f && !mensaje) { vista.src = URL.createObjectURL(f); vista.hidden = false; } else { vista.removeAttribute("src"); vista.hidden = true; }
        /* Si el navegador no puede abrirla como imagen, el archivo está dañado o no es una imagen */
        vista.onerror = () => {
          if (!vista.getAttribute("src")) return;
          vista.removeAttribute("src"); vista.hidden = true; e.target.value = "";
          mostrarError("portada", "No se pudo leer esta imagen. Prueba con otra.");
        };
      }
    });
  });
  $("#cancelar-form").addEventListener("click", cerrarForm);
  $("#panel-form").addEventListener("toggle", () => { if (!$("#panel-form").open && editando !== null) cerrarForm(); });

  $("#form-cancion").addEventListener("submit", async e => {
    e.preventDefault();
    ["titulo", "artista", "genero", "duracion"].forEach(c => tocados.add(c));
    const revision = await validarEnVivo({ todos: true });
    const archivos = { portada: $("#f-portada").files[0], audio: $("#f-audio").files[0] };
    let hayError = !revision.ok;
    for (const [tipo, f] of Object.entries(archivos)) {
      const mensaje = f ? revisarArchivo(f, tipo) : "";
      mostrarError(tipo, mensaje);
      if (mensaje) hayError = true;
    }
    if (hayError) { aviso("Revisa los campos marcados."); return; }

    const esEdicion = editando !== null;
    const boton = $("#guardar-form");
    boton.disabled = true;
    try {
      const c = await api(esEdicion ? `/api/canciones/${editando}` : "/api/canciones", esEdicion ? "PUT" : "POST", datosForm());
      const fallidos = [];
      for (const [tipo, f] of Object.entries(archivos)) {
        if (f) { try { await subirArchivo(c.id, f, tipo); } catch (_) { fallidos.push(tipo); } }
      }
      cerrarForm();
      aviso(fallidos.length ? `Canción guardada, pero no se pudo subir: ${fallidos.join(" y ")}.` : esEdicion ? "Cambios guardados" : "Canción guardada");
      await recargar();
    } catch (err) {
      if (err.campos) Object.entries(err.campos).forEach(([campo, mensaje]) => mostrarError(campo, mensaje));
    } finally { boton.disabled = false; }
  });
}
function pintarBiblioteca() {
  const n = R.length;
  $("#metodo").textContent = `${n} ${n === 1 ? "canción" : "canciones"}, búsqueda con ${metodo}`;
  const sue = S ? S.playlist.actual : null;
  const puntos = '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg>';
  $("#lista-bib").innerHTML = n ? R.map(c => `
    <div class="fila ${c.id === sue ? "suena" : ""}">
      ${portada(c)}
      <div><div class="t">${esc(c.titulo)}</div><div class="a">${esc(c.artista)}, ${esc(c.genero)}${c.audio ? "" : ' <span class="salto sin">sin audio</span>'}</div></div>
      <div class="acc"><span class="dur">${fmt(c.duracion)}</span>
        ${ic("play", "reproducir", c.id, "Reproducir")}
        ${ic("mas", "agregar", c.id, "Añadir al final de la cola")}
        <details class="menu"><summary class="ic" title="Más acciones" aria-label="Más acciones">${puntos}</summary>
          <div class="menu-lista">
            <button data-acc="continuacion" data-id="${c.id}">Reproducir a continuación</button>
            <button data-acc="editar" data-id="${c.id}">Editar datos</button>
            <button data-acc="portada" data-id="${c.id}">${c.portada ? "Cambiar portada" : "Añadir portada"}</button>
            <button data-acc="audio" data-id="${c.id}">${c.audio ? "Cambiar audio" : "Añadir audio"}</button>
            <button data-acc="borrar" data-id="${c.id}" class="peligro">Eliminar</button>
          </div></details>
      </div>
    </div>`).join("") : `<div class="vacio">No encontramos canciones con ese texto. Prueba con otro título o artista.</div>`;
}

/* ---------- Mapa de artistas ---------- */
function generoDe(artista) {
  const c = S.canciones.find(x => (x.artistas || [x.artista]).includes(artista));
  return c ? c.genero : "Otro";
}
function pintarMapa() {
  const rec = S.recomendaciones;
  const artistas = Object.keys(S.grafo).sort((a, b) => a.localeCompare(b, "es"));
  const opciones = sel => artistas.map(a => `<option ${a === sel ? "selected" : ""}>${esc(a)}</option>`).join("");
  const a = $("#cam-a") ? $("#cam-a").value : (rec.artistas && rec.artistas[0]) || artistas[0];
  const b = $("#cam-b") ? $("#cam-b").value : (artistas.find(x => x !== a && !(S.grafo[a] || {})[x]) || artistas[0]);
  const generos = [...new Set(artistas.map(generoDe))];
  const aislados = artistas.filter(x => !Object.keys(S.grafo[x]).length);
  const ca = $("#con-a") ? $("#con-a").value : (aislados[0] || artistas[0]);
  const cb = $("#con-b") ? $("#con-b").value : (artistas.find(x => x !== ca && !(S.grafo[ca] || {})[x]) || artistas[0]);
  const cp = $("#con-peso") ? $("#con-peso").value : 6;
  $("#mapa").innerHTML = `
    <h1 class="titulo-pag">Mapa de artistas</h1>
    <p class="sub">Cada línea une a dos artistas que suenan parecido; mientras más gruesa, más afinidad. De aquí salen tus recomendaciones.</p>
    <div class="mapa-grid">
      <div><div class="lienzo">${svgGrafo(rec.artistas)}</div>
        <div class="leyenda">${generos.map(g => `<span><i style="${estiloG(g)}"></i>${esc(g)}</span>`).join("")}</div></div>
      <div>
        <h2>¿Cómo se conectan dos artistas?</h2>
        <div class="herr"><select id="cam-a" aria-label="Desde">${opciones(a)}</select><select id="cam-b" aria-label="Hasta">${opciones(b)}</select></div>
        <button class="btn" data-acc="camino">Buscar el camino</button>
        <div class="camino-res" id="res-camino">${camino ? (camino.length
          ? camino.map(x => `<span class="paso">${esc(x)}</span>`).join(" → ") + `<span class="salto">${camino.length - 1} ${camino.length - 1 === 1 ? "salto" : "saltos"}</span>`
          : '<span class="suave">Estos artistas no están conectados todavía.</span>') : ""}</div>

        <h2 class="sep">Conectar dos artistas</h2>
        <p class="ayuda">Una conexión dice que dos artistas suenan parecido. Así aparecen en las recomendaciones.</p>
        ${aislados.length ? `<p class="ayuda">Sin conexiones todavía: ${aislados.map(esc).join(", ")}.</p>` : ""}
        <div class="herr"><select id="con-a" aria-label="Primer artista">${opciones(ca)}</select><select id="con-b" aria-label="Segundo artista">${opciones(cb)}</select></div>
        <label class="peso" for="con-peso">Afinidad: <output id="con-valor">${cp}</output> de 10
          <input type="range" id="con-peso" min="1" max="10" value="${cp}" oninput="document.getElementById('con-valor').textContent = this.value"></label>
        <button class="btn" data-acc="conectar">Conectar</button>
      </div>
    </div>`;
}
/* Orden de los nodos en el círculo: se camina por el grafo siguiendo la conexión más fuerte,
   así los artistas parecidos quedan juntos y las líneas se cruzan menos. */
function ordenCircular() {
  const todos = Object.keys(S.grafo), orden = [], visto = new Set();
  let cur = todos[0];
  while (orden.length < todos.length) {
    orden.push(cur); visto.add(cur);
    const sig = Object.entries(S.grafo[cur]).filter(([v]) => !visto.has(v)).sort((x, y) => y[1] - x[1])[0];
    cur = sig ? sig[0] : todos.find(t => !visto.has(t));
  }
  return orden;
}
function svgGrafo(actualesA = []) {
  const nombres = ordenCircular(), n = nombres.length, cx = 320, cy = 250, r = 185;
  const pos = {};
  nombres.forEach((nom, i) => {
    const ang = (i / n) * 2 * Math.PI - Math.PI / 2;
    pos[nom] = { x: cx + r * Math.cos(ang), y: cy + r * Math.sin(ang), ang };
  });
  const enCamino = new Set(), aristasCamino = new Set();
  if (camino) camino.forEach((nom, i) => { enCamino.add(nom); if (i) aristasCamino.add([camino[i - 1], nom].sort().join("|")); });
  let lineas = "";
  nombres.forEach(a => Object.entries(S.grafo[a]).forEach(([b, peso]) => {
    if (a < b) {
      const cam = aristasCamino.has([a, b].sort().join("|"));
      lineas += `<line class="arista ${cam ? "camino" : ""}" x1="${pos[a].x}" y1="${pos[a].y}" x2="${pos[b].x}" y2="${pos[b].y}" stroke-width="${cam ? 4 : 1 + peso / 3}" style="opacity:${0.45 + peso / 18}"><title>${esc(a)} y ${esc(b)}: afinidad ${peso} de 10</title></line>`;
    }
  }));
  const hayCamino = enCamino.size > 0;
  const nodos = nombres.map(nom => {
    const p = pos[nom], dx = Math.cos(p.ang), lado = Math.abs(dx) < .2 ? "middle" : dx > 0 ? "start" : "end";
    const clase = actualesA.includes(nom) ? "actual" : enCamino.has(nom) ? "camino" : hayCamino ? "atenuado" : "";
    const [bg] = colorGenero(generoDe(nom));
    return `<g class="nodo-g ${clase}"><circle cx="${p.x}" cy="${p.y}" r="${actualesA.includes(nom) ? 13 : 10}" fill="${bg}"/>
      <text x="${p.x + dx * 19}" y="${p.y + Math.sin(p.ang) * 19 + 4}" text-anchor="${lado}" font-size="12.5">${esc(nom)}</text></g>`;
  }).join("");
  return `<svg viewBox="0 0 640 500" width="100%" role="img" aria-label="Mapa de artistas relacionados">${lineas}${nodos}</svg>`;
}

/* ---------- Bajo el capó: las estructuras por dentro ---------- */
function pintarEstructuras() {
  const st = S.stats, p = S.playlist;
  const cifras = [["canciones", "canciones en la lista"], ["artistas", "nodos del grafo"], ["conexiones", "aristas del grafo"], ["altura_arbol", "niveles del árbol"], ["en_playlist", "nodos en la cadena"], ["en_historial", "elementos en la pila"]]
    .map(([k, t]) => `<div class="cifra"><b>${st[k]}</b><span>${t}</span></div>`).join("");
  const cadena = p.ids.map((id, i) => {
    const c = porId(id);
    const marcas = [i === 0 ? "cabeza" : "", i === p.ids.length - 1 ? "cola" : ""].filter(Boolean).join(" y ");
    return `<div class="eslabon"><div class="caja ${id === p.actual ? "actual" : ""}">${marcas ? `<span class="marca-p">${marcas}</span>` : ""}${esc(c.titulo.length > 16 ? c.titulo.slice(0, 15) + "…" : c.titulo)}<small>id ${id}</small></div><span class="flecha">⇄</span></div>`;
  }).join("");
  const pila = S.historial.map((id, i) => `<div class="caja ${i === 0 ? "actual" : ""}">${esc(porId(id).titulo)}${i === 0 ? "<small>tope de la pila</small>" : ""}</div>`).join("");
  $("#estructuras").innerHTML = `
    <h1 class="titulo-pag">Bajo el capó</h1>
    <p class="sub">Así se organiza Ritmo por dentro: cinco estructuras de datos, cada una con un trabajo concreto. Lo que ves aquí cambia en vivo mientras usas la app.</p>
    <div class="cifras">${cifras}</div>
    <section class="seccion"><h2>Lista doblemente enlazada: tu cola</h2>
      <div class="cadena"><div class="eslabon"><div class="caja nulo">None</div><span class="flecha">⇄</span></div>${cadena}<div class="eslabon"><div class="caja nulo">None</div></div></div>
      <p class="nota">Cada nodo es un diccionario <code>{"id", "anterior", "siguiente"}</code>. «Reproducir a continuación» solo cambia cuatro enlaces, sin mover el resto de la cola.</p></section>
    <section class="seccion"><h2>Árbol binario de búsqueda: el catálogo por título</h2>
      <div class="lienzo">${svgArbol()}</div>
      <p class="nota">Buscar por prefijo baja por el árbol en vez de revisar toda la biblioteca, y el recorrido inorden entrega los títulos de la A a la Z.</p></section>
    <div class="dos-b">
      <section class="seccion"><h2>Pila: lo último que escuchaste</h2><div class="pila-v">${pila || '<div class="vacio">La pila está vacía.</div>'}</div>
        <p class="nota">Lo último que suena queda arriba. «Volver a la anterior» saca el tope.</p></section>
      <section class="seccion donde"><h2>Dónde está cada una</h2>
        <p><b>Lista</b>: biblioteca de canciones, en <code>biblioteca.py</code></p>
        <p><b>Lista enlazada</b>: cola de reproducción, en <code>playlist.py</code></p>
        <p><b>Árbol binario</b>: índice por título, en <code>indice.py</code></p>
        <p><b>Grafo</b>: artistas relacionados, en <code>grafo.py</code></p>
        <p><b>Pila</b>: historial, en <code>historial.py</code></p></section>
    </div>`;
}
function svgArbol() {
  const acc = { x: 0, nodos: [], aristas: [], prof: 0 };
  (function dis(n, d) {
    if (!n) return null;
    const izq = dis(n.izq, d + 1);
    const yo = { n, x: acc.x++, d };
    acc.prof = Math.max(acc.prof, d);
    acc.nodos.push(yo);
    const der = dis(n.der, d + 1);
    if (izq) acc.aristas.push([yo, izq]);
    if (der) acc.aristas.push([yo, der]);
    return yo;
  })(S.arbol, 0);
  const ancho = acc.x * 76 + 20, alto = (acc.prof + 1) * 66 + 20;
  const px = x => 10 + x * 76 + 38, py = d => 10 + d * 66;
  const ramas = acc.aristas.map(([a, b]) => `<path class="rama" d="M${px(a.x)} ${py(a.d) + 28} C${px(a.x)} ${py(b.d)}, ${px(b.x)} ${py(a.d) + 20}, ${px(b.x)} ${py(b.d)}"/>`).join("");
  const nodos = acc.nodos.map(({ n, x, d }) => {
    const t = n.titulo.length > 11 ? n.titulo.slice(0, 10) + "…" : n.titulo;
    return `<g class="nodo-a ${n.ids.includes(S.playlist.actual) ? "actual" : ""}"><rect x="${px(x) - 36}" y="${py(d)}" width="72" height="28" rx="9"/><text x="${px(x)}" y="${py(d) + 18}">${esc(t)}</text><title>${esc(n.titulo)}</title></g>`;
  }).join("");
  return `<svg width="${ancho}" height="${alto}" viewBox="0 0 ${ancho} ${alto}" role="img" aria-label="Árbol binario de búsqueda">${ramas}${nodos}</svg>`;
}

/* ---------- Reproductor fijo ---------- */
function pintarReproductor() {
  const p = S.playlist, c = actual();
  $("#reproductor").innerHTML = `<div class="rep">
    <div class="info">${c ? `${portada(c)}<div style="min-width:0"><b>${esc(c.titulo)}</b><span>${esc(c.artista)}</span></div>` : '<div><b>Nada sonando</b><span>Elige una canción</span></div>'}</div>
    <div class="centro">
      <div class="controles">
        ${ic("mezcla", "mezclar", null, "Mezclar la cola")}
        ${ic("ant", "anterior", null, "Anterior")}
        <button class="ic play" data-acc="pp" title="${sonando ? "Pausar" : "Reproducir"}" aria-label="${sonando ? "Pausar" : "Reproducir"}"><svg viewBox="0 0 24 24" fill="currentColor">${sonando ? ICONOS.pausa : ICONOS.play}</svg></button>
        ${ic("sig", "siguiente", null, "Siguiente")}
        ${ic("repetir", "circular", null, "Repetir lista", p.circular ? "on" : "")}
      </div>
      <div class="progreso"><span id="t-pos">0:00</span><div class="pista" id="pista" role="slider" aria-label="Posición"><div class="riel"><b id="barra"></b></div></div><span>${c ? fmt(duracionDe(c)) : "0:00"}</span></div>
    </div>
    <div class="der"><label class="vol" title="Volumen"><svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9zM16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <input type="range" id="vol" min="0" max="1" step="0.05" value="${audio.volume}" aria-label="Volumen"></label>
      ${ic("volver", "volver", null, "Volver a la canción anterior")}</div>
  </div>`;
  pintarProgreso();
}
function pintarProgreso() {
  const c = actual();
  if (!c || !$("#barra")) return;
  $("#barra").style.width = Math.min(100, (pos / duracionDe(c)) * 100) + "%";
  $("#t-pos").textContent = fmt(pos);
}
/* Modo simulado: solo para canciones sin archivo de audio */
setInterval(() => {
  if (!S || !sonando) return;
  const c = actual();
  if (!c || hayAudio(c)) return;
  pos++;
  if (pos >= c.duracion) avanzarSolo(); else pintarProgreso();
}, 1000);

/* ---------- Pintado general y eventos ---------- */
function pintarTodo() {
  pintarInicio(); pintarBiblioteca(); pintarMapa(); pintarEstructuras(); pintarReproductor();
}
function moverIndicador() {
  const b = $(`#tabs button[data-tab="${tabActual}"]`), ind = $("#indicador");
  ind.style.left = b.offsetLeft + 14 + "px"; ind.style.width = b.offsetWidth - 28 + "px";
}
function irA(tab) {
  tabActual = tab;
  $$("#tabs button").forEach(b => b.classList.toggle("activa", b.dataset.tab === tab));
  $$(".panel").forEach(p => p.classList.toggle("activo", p.id === tab));
  moverIndicador();
  window.scrollTo({ top: 0 });
}

const ACCIONES = {
  reproducir: async id => {
    await api("/api/reproducir", "POST", { id }); sonando = true; pos = 0;
    if (idAudio === id) audio.currentTime = 0;           // misma canción: empieza de nuevo
  },
  portada: id => elegirArchivo("#archivo-imagen", id, "portada"),
  audio: id => elegirArchivo("#archivo-audio", id, "audio"),
  editar: id => abrirForm(porId(id)),
  conectar: async () => {
    await api("/api/grafo/conectar", "POST", { a: $("#con-a").value, b: $("#con-b").value, peso: Number($("#con-peso").value) });
    camino = null; aviso("Artistas conectados");
  },
  agregar: async id => { await api("/api/playlist/agregar", "POST", { id }); aviso("Añadida a tu cola"); },
  continuacion: async id => { await api("/api/playlist/continuacion", "POST", { id }); aviso("Sonará a continuación"); },
  borrar: async id => { if (confirm("¿Eliminar esta canción de la biblioteca?")) await api(`/api/canciones/${id}`, "DELETE"); },
  quitar: id => api("/api/playlist/quitar", "POST", { id }),
  subir: id => api("/api/playlist/mover", "POST", { id, sentido: "subir" }),
  bajar: id => api("/api/playlist/mover", "POST", { id, sentido: "bajar" }),
  mezclar: () => api("/api/playlist/mezclar", "POST"),
  circular: () => api("/api/playlist/circular", "POST"),
  siguiente: async () => { const d = await api("/api/siguiente", "POST"); if (!d.cambio) { sonando = false; aviso("Llegaste al final de la cola"); } else sonando = true; pos = 0; },
  anterior: async () => { const d = await api("/api/anterior", "POST"); if (d.cambio) { sonando = true; pos = 0; } else aviso("Ya estás en la primera"); },
  volver: async () => { await api("/api/volver", "POST"); sonando = true; pos = 0; },
  pp: () => { if (S.playlist.actual != null) sonando = !sonando; },
  camino: async () => {
    const d = await api(`/api/camino?a=${encodeURIComponent($("#cam-a").value)}&b=${encodeURIComponent($("#cam-b").value)}`);
    camino = d.camino || [];
  },
};
document.addEventListener("click", async e => {
  const tab = e.target.closest("#tabs button");
  if (tab) return irA(tab.dataset.tab);
  const pista = e.target.closest(".pista");
  if (pista) {
    const c = actual(); if (!c) return;
    const r = pista.getBoundingClientRect();
    pos = Math.floor(((e.clientX - r.left) / r.width) * duracionDe(c));
    if (hayAudio(c) && idAudio === c.id) audio.currentTime = pos;
    return pintarProgreso();
  }
  const menuActual = e.target.closest("details.menu");
  $$("details.menu[open]").forEach(d => { if (d !== menuActual) d.open = false; });
  const b = e.target.closest("[data-acc]");
  if (!b) return;
  if (menuActual) menuActual.open = false;
  if (b.dataset.acc === "ir") return irA(b.dataset.tab);
  const id = b.dataset.id != null ? Number(b.dataset.id) : undefined;
  try { await ACCIONES[b.dataset.acc](id); await recargar(); } catch (_) { /* el aviso ya se mostró */ }
});
document.addEventListener("change", e => {
  if (e.target.id === "cam-a" || e.target.id === "cam-b") camino = null;
});
window.addEventListener("resize", moverIndicador);
if (document.fonts) document.fonts.ready.then(moverIndicador);

/* Volumen: se recuerda entre visitas */
try { const v = parseFloat(localStorage.getItem("ritmo-volumen")); if (!isNaN(v)) audio.volume = Math.min(1, Math.max(0, v)); } catch (_) { }
document.addEventListener("input", e => {
  if (e.target.id !== "vol") return;
  audio.volume = Number(e.target.value);
  try { localStorage.setItem("ritmo-volumen", String(audio.volume)); } catch (_) { }
});

/* Atajos de teclado: espacio, flechas izquierda y derecha */
document.addEventListener("keydown", async e => {
  if (!S || e.ctrlKey || e.metaKey || e.altKey || e.target.closest("input, select, textarea, button, summary")) return;
  const mapa = { " ": "pp", ArrowRight: "siguiente", ArrowLeft: "anterior" };
  const acc = mapa[e.key];
  if (!acc) return;
  e.preventDefault();
  try { await ACCIONES[acc](); await recargar(); } catch (_) { }
});

/* Título de la pestaña y controles del sistema (pantalla de bloqueo, teclas multimedia) */
function actualizarSistema() {
  const c = actual();
  document.title = c ? `${c.titulo}, ${c.artista} · Ritmo` : "Ritmo · Música en español";
  if (!("mediaSession" in navigator) || !c) return;
  navigator.mediaSession.metadata = new MediaMetadata({
    title: c.titulo, artist: c.artista, album: c.genero,
    artwork: c.portada ? [{ src: urlPortada(c), sizes: "512x512" }] : [],
  });
}
if ("mediaSession" in navigator) {
  const accion = (nombre, f) => { try { navigator.mediaSession.setActionHandler(nombre, f); } catch (_) { } };
  const hacer = a => async () => { try { await ACCIONES[a](); await recargar(); } catch (_) { } };
  accion("play", async () => { if (!sonando) await hacer("pp")(); });
  accion("pause", async () => { if (sonando) await hacer("pp")(); });
  accion("nexttrack", hacer("siguiente"));
  accion("previoustrack", hacer("anterior"));
}

async function iniciar() {
  S = await api("/api/estado");
  armarBiblioteca();
  await recargar();
  irA("inicio");
}
iniciar();