// Detectar si estamos en local o producción
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000/api' 
    : '/api';

// ... resto del código igual ...

let csvData = '';
let archivoSeleccionado = null;

// ... variables existentes ...

// ✨ TEMA OSCURO/CLARO
const themeToggle = document.getElementById('theme-toggle');
const toggleIcon = themeToggle.querySelector('.toggle-icon');

// Cargar tema guardado o detectar preferencia del sistema
function cargarTema() {
    const temaGuardado = localStorage.getItem('theme');
    const preferenciaSistema = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const tema = temaGuardado || preferenciaSistema;
    
    aplicarTema(tema);
}

// Aplicar tema
function aplicarTema(tema) {
    document.documentElement.setAttribute('data-theme', tema);
    toggleIcon.textContent = tema === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('theme', tema);
}

// Cambiar tema
function cambiarTema() {
    const temaActual = document.documentElement.getAttribute('data-theme');
    const nuevoTema = temaActual === 'dark' ? 'light' : 'dark';
    aplicarTema(nuevoTema);
}

// Event listener del toggle
themeToggle.addEventListener('click', cambiarTema);

// Cargar tema al iniciar
cargarTema();

// Detectar cambios en preferencia del sistema
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        aplicarTema(e.matches ? 'dark' : 'light');
    }
});

// ... resto del código existente ...

// Elementos del DOM
const textoInput = document.getElementById('texto-input');
const generarBtn = document.getElementById('generar-btn');
const limpiarBtn = document.getElementById('limpiar-btn');
const descargarBtn = document.getElementById('descargar-btn');
const loading = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const resultado = document.getElementById('resultado');
const tarjetasPreview = document.getElementById('tarjetas-preview');
const numTarjetasGeneradas = document.getElementById('num-tarjetas-generadas');
const charCount = document.getElementById('char-count');
const statusBadge = document.getElementById('status-badge');
const tipoContenido = document.getElementById('tipo-contenido');

// Elementos de archivo
const dropZone = document.getElementById('drop-zone');
const dropContent = document.getElementById('drop-content');
const fileInput = document.getElementById('file-input');
const filePreview = document.getElementById('file-preview');
const previewContent = document.getElementById('preview-content');
const removeFileBtn = document.getElementById('remove-file');
const btnSelectFile = document.querySelector('.btn-select-file');

// Elementos de control de tarjetas
const radioAuto = document.querySelector('input[value="auto"]');
const radioManual = document.querySelector('input[value="manual"]');
const sliderContainer = document.getElementById('slider-container');
const slider = document.getElementById('num-tarjetas-slider');
const sliderValueDisplay = document.getElementById('slider-value-display');

// Verificar estado
verificarEstado();

// Event Listeners
generarBtn.addEventListener('click', generarTarjetas);
limpiarBtn.addEventListener('click', limpiarTodo);
descargarBtn.addEventListener('click', descargarCSV);
textoInput.addEventListener('input', actualizarContador);

// File handlers
dropZone.addEventListener('click', () => fileInput.click());
btnSelectFile.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});
dropZone.addEventListener('dragover', handleDragOver);
dropZone.addEventListener('dragleave', handleDragLeave);
dropZone.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    removerArchivo();
});

// Ctrl+V para pegar imágenes
document.addEventListener('paste', handlePaste);

// Control de tarjetas
radioAuto.addEventListener('change', toggleModoTarjetas);
radioManual.addEventListener('change', toggleModoTarjetas);
slider.addEventListener('input', () => {
    sliderValueDisplay.textContent = slider.value;
});

function toggleModoTarjetas() {
    if (radioManual.checked) {
        sliderContainer.classList.remove('hidden');
    } else {
        sliderContainer.classList.add('hidden');
    }
}

async function verificarEstado() {
    try {
        const response = await fetch(`${API_URL}/salud`);
        const data = await response.json();
        
        if (data.gemini_configurado) {
            statusBadge.innerHTML = '<span class="status-dot"></span> Gemini Listo';
            statusBadge.classList.add('online');
        } else {
            statusBadge.innerHTML = '<span class="status-dot"></span> No configurado';
            statusBadge.classList.add('offline');
            generarBtn.disabled = true;
        }
    } catch (error) {
        statusBadge.innerHTML = '<span class="status-dot"></span> Servidor offline';
        statusBadge.classList.add('offline');
    }
}

function actualizarContador() {
    charCount.textContent = textoInput.value.length;
}

function handleDragOver(e) {
    e.preventDefault();
    dropZone.classList.add('drag-over');
}

function handleDragLeave() {
    dropZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        procesarArchivo(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        procesarArchivo(files[0]);
    }
}

async function handlePaste(e) {
    const items = e.clipboardData?.items;
    if (!items) return;
    
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.indexOf('image') !== -1) {
            e.preventDefault();
            const blob = item.getAsFile();
            const file = new File([blob], `imagen-pegada-${Date.now()}.png`, {
                type: item.type
            });
            procesarArchivo(file);
            mostrarNotificacion('Imagen pegada correctamente', 'success');
            return;
        }
    }
}

function procesarArchivo(file) {
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/gif', 'image/webp'];
    
    if (!allowedTypes.includes(file.type)) {
        mostrarNotificacion('Tipo de archivo no soportado', 'error');
        return;
    }
    
    if (file.size > 20 * 1024 * 1024) {
        mostrarNotificacion('El archivo es muy grande. Máximo 20MB', 'error');
        return;
    }
    
    archivoSeleccionado = file;
    mostrarPreview(file);
}

function mostrarPreview(file) {
    if (file.type === 'application/pdf') {
        previewContent.innerHTML = `
            <div class="pdf-icon">📄</div>
            <div class="file-info">${file.name}</div>
            <div class="file-size">${(file.size / 1024 / 1024).toFixed(2)} MB</div>
        `;
    } else {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewContent.innerHTML = `
                <img src="${e.target.result}" alt="Preview">
                <div class="file-info">${file.name}</div>
                <div class="file-size">${(file.size / 1024).toFixed(0)} KB</div>
            `;
        };
        reader.readAsDataURL(file);
    }
    
    dropContent.style.display = 'none';
    filePreview.classList.remove('hidden');
}

function removerArchivo() {
    archivoSeleccionado = null;
    fileInput.value = '';
    dropContent.style.display = 'block';
    filePreview.classList.add('hidden');
}

async function generarTarjetas() {
    const texto = textoInput.value.trim();
    
    if (!texto && !archivoSeleccionado) {
        mostrarNotificacion('Proporciona texto o un archivo', 'error');
        return;
    }
    
    loading.classList.remove('hidden');
    resultado.classList.add('hidden');
    generarBtn.disabled = true;
    
    if (archivoSeleccionado) {
        loadingText.textContent = archivoSeleccionado.type === 'application/pdf' 
            ? 'Extrayendo texto del PDF...' 
            : 'Analizando imagen...';
    } else {
        loadingText.textContent = 'Generando tarjetas...';
    }
    
    try {
        const formData = new FormData();
        
        if (texto) {
            formData.append('texto', texto);
        }
        
        if (archivoSeleccionado) {
            formData.append('archivo', archivoSeleccionado);
        }
        
        // Agregar número de tarjetas si es manual
        if (radioManual.checked) {
            formData.append('num_tarjetas', slider.value);
        }
        
        const response = await fetch(`${API_URL}/generar`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al generar tarjetas');
        }
        
        csvData = data.csv;
        mostrarTarjetas(data.tarjetas, data.num_tarjetas, data.tipo_contenido);
        mostrarNotificacion(`${data.num_tarjetas} tarjetas generadas`, 'success');
        
    } catch (error) {
        mostrarNotificacion(error.message, 'error');
        console.error(error);
    } finally {
        loading.classList.add('hidden');
        generarBtn.disabled = false;
    }
}

function mostrarTarjetas(tarjetasTexto, numTarjetas, tipoContenidoStr) {
    const lineas = tarjetasTexto.trim().split('\n');
    let html = '';
    
    lineas.forEach((linea) => {
        if (linea.includes('|||')) {
            const partes = linea.split('|||');
            if (partes.length >= 2) {
                const pregunta = partes[0].trim().replace(/^\d+[\.\)]\s*/, '');
                const respuesta = partes[1].trim();
                
                if (pregunta && respuesta) {
                    const preguntaHTML = renderizarLatexParaVista(pregunta);
                    const respuestaHTML = renderizarLatexParaVista(respuesta);
                    
                    html += `
                        <div class="tarjeta-item">
                            <div class="tarjeta-pregunta">${preguntaHTML}</div>
                            <div class="tarjeta-respuesta">${respuestaHTML}</div>
                        </div>
                    `;
                }
            }
        }
    });
    
    if (html) {
        tarjetasPreview.innerHTML = html;
        numTarjetasGeneradas.textContent = numTarjetas;
        tipoContenido.textContent = `📊 Fuente: ${tipoContenidoStr}`;
        resultado.classList.remove('hidden');
        
        setTimeout(() => {
            resultado.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
}

function renderizarLatexParaVista(texto) {
    if (!texto) return '';
    
    try {
        const div = document.createElement('div');
        div.textContent = texto;
        let textoEscapado = div.innerHTML;
        
        textoEscapado = textoEscapado.replace(/\\?\\\(/g, '<span class="math-inline">').replace(/\\?\\\)/g, '</span>');
        textoEscapado = textoEscapado.replace(/\\?\\\[/g, '<div class="math-block">').replace(/\\?\\\]/g, '</div>');
        
        return textoEscapado;
    } catch (error) {
        return texto;
    }
}

function descargarCSV() {
    if (!csvData) {
        mostrarNotificacion('No hay tarjetas para descargar', 'error');
        return;
    }
    
    const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    const fecha = new Date().toISOString().slice(0, 10);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `anki-tarjetas-${fecha}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    mostrarNotificacion('Archivo descargado', 'success');
}

function limpiarTodo() {
    textoInput.value = '';
    removerArchivo();
    resultado.classList.add('hidden');
    csvData = '';
    actualizarContador();
}

function mostrarNotificacion(mensaje, tipo = 'info') {
    const notif = document.createElement('div');
    notif.className = `notificacion notificacion-${tipo}`;
    notif.textContent = mensaje;
    
    document.body.appendChild(notif);
    setTimeout(() => notif.classList.add('mostrar'), 10);
    
    setTimeout(() => {
        notif.classList.remove('mostrar');
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}