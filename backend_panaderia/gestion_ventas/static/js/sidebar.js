// gestion_ventas/static/gestion_ventas/js/sidebar.js

// Espera a que todo el HTML esté cargado antes de ejecutar el script.
document.addEventListener('DOMContentLoaded', function() {
    
    // --- LÓGICA PARA DESPLEGAR/PLEGAR SUBMENÚS ---
    document.querySelectorAll('.sidebar-menu > ul > li > a').forEach(item => {
        item.addEventListener('click', function(e) {
            // Revisa si el link tiene un submenú (un elemento <ul> hermano)
            if (this.nextElementSibling && this.nextElementSibling.tagName === 'UL') {
                e.preventDefault(); // Previene la navegación si es un menú principal
                const parentLi = this.parentElement;
                const subMenu = this.nextElementSibling;

                // Cierra otros submenús que puedan estar abiertos
                document.querySelectorAll('.sidebar-menu > ul > li').forEach(otherLi => {
                    if (otherLi !== parentLi && otherLi.classList.contains('active')) {
                        otherLi.classList.remove('active');
                        otherLi.querySelector('ul').style.display = 'none';
                    }
                });

                // Alterna la clase 'active' y la visibilidad del submenú clickeado
                parentLi.classList.toggle('active');
                subMenu.style.display = subMenu.style.display === 'block' ? 'none' : 'block';
            }
        });
    });

    // --- LÓGICA PARA MANTENER ABIERTO EL MENÚ DE LA PÁGINA ACTUAL ---
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-menu ul ul li a').forEach(link => {
        // Si el href del link está contenido en la URL actual de la página...
        if (link.getAttribute('href') && currentPath.includes(link.getAttribute('href'))) {
            const parentUl = link.closest('ul');
            if (parentUl) {
                // ...muestra el submenú...
                parentUl.style.display = 'block';
                // ...y marca el menú principal como 'active'.
                const mainLi = parentUl.closest('li');
                if (mainLi) {
                    mainLi.classList.add('active');
                }
            }
        }
    });

    // ===================================================================
    // --- NUEVO: LÓGICA PARA LA CONFIRMACIÓN DE CERRAR SESIÓN (LOGOUT) ---
    // ===================================================================
    const logoutLink = document.getElementById('logout-link');

    // Verificamos si el enlace de logout existe en la página actual
    if (logoutLink) {
        logoutLink.addEventListener('click', function(event) {
            // Prevenimos que el enlace navegue a la URL de logout inmediatamente
            event.preventDefault(); 
            
            // Guardamos la URL del enlace para usarla después
            const logoutUrl = this.href;

            // Verificamos que la función showModal exista antes de llamarla
            if (typeof showModal === 'function') {
                // Usamos la función showModal (de mensajes.js) para la confirmación
                showModal({
                    type: 'confirm',
                    body: '¿DESEAS CERRAR SESIÓN?',
                    confirmText: 'Sí',
                    cancelText: 'No',
                    // Esto se ejecuta SOLO si el usuario hace clic en 'Sí'
                    onConfirm: function() {
                        // Redirigimos al usuario a la URL de logout para que el backend haga su trabajo
                        window.location.href = logoutUrl;
                    }
                });
            } else {
                // Fallback por si mensajes.js no se cargó: simplemente redirige.
                console.error("La función showModal no está definida. Cargue mensajes.js.");
                window.location.href = logoutUrl;
            }
        });
    }
});