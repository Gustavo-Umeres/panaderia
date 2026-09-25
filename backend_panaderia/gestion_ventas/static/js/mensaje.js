// gestion_ventas/static/gestion_ventas/js/mensajes.js

// Se definen las constantes para acceder al modal una sola vez.
const modalOverlay = document.getElementById('custom-modal-overlay');
const modalTitle = document.getElementById('modal-title');
const modalIcon = document.getElementById('custom-modal-icon');
const modalText = document.getElementById('custom-modal-text');
const singleButtonContainer = document.getElementById('single-button-container');
const confirmButtonsContainer = document.getElementById('confirm-buttons-container');
const btnClose = document.getElementById('btn-close');
// --- INICIO DE LA CORRECCIÓN ---
// btnConfirm ahora es 'let' en lugar de 'const' porque lo reasignaremos.
let btnConfirm = document.getElementById('btn-confirm'); 
// --- FIN DE LA CORRECCIÓN ---
const btnCancel = document.getElementById('btn-cancel');
let onCloseCallback = null;

// --- INICIO DE LA CORRECCIÓN ---
// Guardamos el handler del click de confirmación en una variable para poder añadirlo y quitarlo.
let currentConfirmHandler = null;
// --- FIN DE LA CORRECCIÓN ---

// Función para OCULTAR el modal
function hideModal() {
    if (modalOverlay) modalOverlay.style.display = 'none';
    if (typeof onCloseCallback === 'function') {
        onCloseCallback();
        onCloseCallback = null; // Limpiar para que no se ejecute de nuevo
    }
}

// Función para MOSTRAR y configurar el modal
function showModal(options) {
    if (!modalOverlay) return; // Si no existe el modal en la página, no hace nada.
    
    const config = { ...options };
    onCloseCallback = typeof config.onClose === 'function' ? config.onClose : null;

    modalTitle.innerText = 'Mensaje';
    modalText.innerText = config.body || '';

    const iconClasses = {
        success: 'icon-success', error: 'icon-error', warning: 'icon-warning',
        confirm: 'icon-confirm', info: 'icon-info'
    };
    modalIcon.className = 'modal-icon ' + (iconClasses[config.type] || 'icon-info');
    
    if (config.type === 'confirm') {
        singleButtonContainer.style.display = 'none';
        confirmButtonsContainer.style.display = 'flex';
        btnConfirm.className = 'modal-button btn-success';
        btnCancel.className = 'modal-button btn-danger';
        btnConfirm.innerText = config.confirmText || 'Sí';
        btnCancel.innerText = config.cancelText || 'No';

        // --- INICIO DE LA CORRECCIÓN ---
        // 1. Si existe un 'handler' (función de click) anterior, lo eliminamos.
        if (currentConfirmHandler) {
            btnConfirm.removeEventListener('click', currentConfirmHandler);
        }

        // 2. Creamos el nuevo handler para el click actual.
        currentConfirmHandler = () => {
            hideModal();
            if (typeof config.onConfirm === 'function') {
                config.onConfirm();
            }
        };
        
        // 3. Añadimos el nuevo event listener.
        btnConfirm.addEventListener('click', currentConfirmHandler);
        // --- FIN DE LA CORRECCIÓN ---

        btnCancel.onclick = hideModal;
    } else {
        singleButtonContainer.style.display = 'block';
        confirmButtonsContainer.style.display = 'none';
        const btnColors = {
            success: 'btn-success', error: 'btn-danger',
            warning: 'btn-warning', info: 'btn-success'
        };
        btnClose.className = 'modal-button ' + (btnColors[config.type] || 'btn-success');
        btnClose.innerText = config.closeText || 'Cerrar';
        btnClose.onclick = hideModal;
    }
    modalOverlay.style.display = 'flex';
}