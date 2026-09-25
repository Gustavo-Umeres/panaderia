# gestion_ventas/context_processors.py

from .models import UsuarioPrivilegio

def menu_privilegios(request):
    """
    Este procesador de contexto añade los privilegios del usuario actual
    a todas las plantillas para construir el menú dinámicamente.
    """
    # Usamos un 'set' para que las búsquedas en la plantilla con "in" sean muy rápidas
    privilegios_usuario = set()

    # Solo ejecutamos la consulta si el usuario ha iniciado sesión
    if request.user.is_authenticated:
        try:
            # Buscamos en la tabla intermedia UsuarioPrivilegio
            privilegios_obj = UsuarioPrivilegio.objects.filter(
                usuario__username=request.user.username
            ).select_related('privilegio') # select_related optimiza la consulta

            # Creamos un conjunto con los NOMBRES de los privilegios
            privilegios_usuario = {up.privilegio.nombre for up in privilegios_obj}

        except Exception:
            # Si hay algún error, el usuario no tendrá privilegios y no verá el menú.
            pass

    return {
        'user_privilegios': privilegios_usuario
    }