# gestion_ventas/decorators.py (CORREGIDO)

from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps
from .models import UsuarioPrivilegio

def privilegio_requerido(privilegio_nombre):
    """
    Decorador que verifica si un usuario tiene un privilegio específico.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                tiene_permiso = UsuarioPrivilegio.objects.filter(
                    usuario__username=request.user.username,
                    privilegio__nombre=privilegio_nombre 
                ).exists()

                if not tiene_permiso:
                    return redirect(reverse('gestion_ventas:acceso_denegado'))
                else:
                    return view_func(request, *args, **kwargs)

            except Exception:
                return redirect(reverse('gestion_ventas:acceso_denegado'))
                
        return _wrapped_view
    return decorator