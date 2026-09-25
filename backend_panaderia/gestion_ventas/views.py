from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import re
from django.db import transaction, IntegrityError, OperationalError, DatabaseError
from django.forms import ValidationError
from decimal import Decimal, InvalidOperation
from django.db import models
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
import json
from django.utils import timezone
import traceback
from datetime import datetime
import openpyxl
from django.db.models import Sum, OuterRef, Subquery, DecimalField, Value, F
from django.db.models.functions import Coalesce
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from django.urls import reverse
from .decorators import privilegio_requerido
import logging
import locale
from django.db.models import Q

logger = logging.getLogger(__name__)

from .models import (
    DetalleReporteBoleta,
    Usuario,
    Privilegio,
    UsuarioPrivilegio,
    Producto,
    Categoria,
    Boleta,
    DetalleBoleta,
    Denominacion,
    ReporteBoletas,
    ReporteCaja,
    ReporteCierreCaja,
    NotaCredito,
    DetalleNotaCredito,
    DetalleReporteCaja,
    PreguntaSeguridad,
    ReporteEgresos,
    UsuarioPreguntaRespuesta
)
import logging
logger = logging.getLogger(__name__)

def ejecutar_consulta_segura(consulta_func):
    error_en_bd = None
    resultado = None
    try:
        resultado = consulta_func()
    except (OperationalError, IntegrityError, DatabaseError) as e:
        # This will print the actual database error and its traceback to your console
        logger.error(f"DATABASE ERROR caught in ejecutar_consulta_segura: {e}")
        logger.error(traceback.format_exc())
        error_en_bd = e # Pass the original exception object
    except Exception as e:
        # This catches any other unexpected Python errors
        logger.error(f"GENERAL ERROR caught in ejecutar_consulta_segura: {e}")
        logger.error(traceback.format_exc())
        error_en_bd = e # Pass the original exception object
    return resultado, error_en_bd

def error_bd(request, e, is_ajax=False):
    if request.user.is_authenticated:
        logout(request)
    if is_ajax:
        return JsonResponse({'status': 'error', 'message': 'ERROR EN BD', 'redirect_to_login': True}, status=500)
    else:
        return render(request, 'modulo_seguridad/ErrorBD.html')


def acceso_denegado(request):
    logout(request)
    return render(request, 'modulo_seguridad/AccesoDenegado.html')


@login_required(login_url='gestion_ventas:acceso_denegado')
def inicio(request):
    return render(request, 'base.html')


def login_view(request):
    if request.method == 'POST':
        if("btn_ingresar" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        username_input = request.POST.get('txt_usuario')
        password_input = request.POST.get('txt_password')

        if not username_input or not password_input:
            context = {
                'modal_message': {
                    'title': 'Mensaje',
                    'body': 'LOS DATOS INGRESADOS NO SON VÁLIDOS',
                    'type': 'error'
                }
            }
            return render(request, 'modulo_seguridad/FormAutenticarUsuario.html', context)
        
        usuario_custom, error_usuario_custom = ejecutar_consulta_segura(lambda: Usuario.objects.get(username=username_input))

        if error_usuario_custom:
            return error_bd(request, error_usuario_custom)

        if error_usuario_custom and isinstance(error_usuario_custom, Usuario.DoesNotExist):
            context = {
                'modal_message': {
                    'title': 'Mensaje',
                    'body': 'USUARIO NO ENCONTRADO',
                    'type': 'error'
                }
            }
            return render(request, 'modulo_seguridad/FormAutenticarUsuario.html', context)
        
        if not check_password(password_input, usuario_custom.contrasena_hash):
            context = {
                'modal_message': {
                    'title': 'Mensaje',
                    'body': 'PASSWORD INGRESADO NO COINCIDE',
                    'type': 'error'
                }
            }
            return render(request, 'modulo_seguridad/FormAutenticarUsuario.html', context)

        if usuario_custom.estado == 0:
            context = {
                'modal_message': {
                    'title': 'Mensaje',
                    'body': 'USUARIO DESHABILITADO, CONTACTE CON EL ADMINISTRADOR',
                    'type': 'error'
                }
            }
            return render(request, 'modulo_seguridad/FormAutenticarUsuario.html', context)

        def get_or_create_django_user():
            user_django, created = User.objects.get_or_create(username=usuario_custom.username)
            if created or not user_django.check_password(password_input):
                user_django.set_password(password_input)
                user_django.save()
            return user_django

        user_django, error_django_user = ejecutar_consulta_segura(get_or_create_django_user)

        if error_django_user:
            return error_bd(request, error_django_user)

        user = authenticate(request, username=user_django.username, password=password_input)

        if user is not None:
            login(request, user)
            return redirect('gestion_ventas:inicio')
        else:
            return redirect('gestion_ventas:acceso_denegado')
    modal_message = request.session.pop('modal_message', None)
    context = {'modal_message': modal_message} if modal_message else {}
    return render(request, 'modulo_seguridad/FormAutenticarUsuario.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
def logout_view(request):
    logout(request)
    return redirect('gestion_ventas:login_view')


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Usuarios')
def gestionar_usuario(request):
    modal_message = request.session.pop('modal_message', None)
    consulta = lambda: Usuario.objects.all().order_by('apellido', 'nombre')
    usuarios, error_en_bd_usuario = ejecutar_consulta_segura(consulta)

    if error_en_bd_usuario:
        return error_bd(request, error_en_bd_usuario)
    context = {
        'usuarios': usuarios,
        'modal_message': modal_message
    }
    return render(request, 'modulo_seguridad/FormGestionarUsuario.html', context)




@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Usuarios')
def crear_usuario(request):
    preguntas_seguridad, error_preguntas = ejecutar_consulta_segura(lambda: PreguntaSeguridad.objects.all())
    if error_preguntas:
        return error_bd(request, error_preguntas)
    
    privilegios, error_privilegios = ejecutar_consulta_segura(lambda: Privilegio.objects.all())
    if error_privilegios:
        return error_bd(request, error_privilegios)
    
    context_for_render = {
        'preguntas_seguridad': preguntas_seguridad,
        'privilegios': privilegios,
    }

    if request.method == 'POST':
        if("btnRegistrar" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        
        # --- Recopilación de datos del formulario ---
        nombre = request.POST.get('txt_nombre')
        apellido = request.POST.get('txt_apellido')
        dni = request.POST.get('txt_dni')
        username = request.POST.get('txt_usuario')
        contrasena = request.POST.get('txt_contrasena')
        confirmar_contrasena = request.POST.get('txt_confirmar_contrasena')
        privilegios_seleccionados_ids = request.POST.getlist('chbx_seleccion')

        preguntas_seleccionadas_ids = []
        respuestas_seguridad = []
        
        pregunta1_id = request.POST.get('cmb_pregunta1')
        respuesta1 = request.POST.get('txt_respuesta1')
        if pregunta1_id and respuesta1:
            preguntas_seleccionadas_ids.append(int(pregunta1_id))
            respuestas_seguridad.append({'pregunta_id': int(pregunta1_id), 'respuesta': respuesta1})

        pregunta2_id = request.POST.get('cmb_pregunta2')
        respuesta2 = request.POST.get('txt_respuesta2')
        if pregunta2_id and respuesta2:
            preguntas_seleccionadas_ids.append(int(pregunta2_id))
            respuestas_seguridad.append({'pregunta_id': int(pregunta2_id), 'respuesta': respuesta2})

        pregunta3_id = request.POST.get('cmb_pregunta3')
        respuesta3 = request.POST.get('txt_respuesta3')
        if pregunta3_id and respuesta3:
            preguntas_seleccionadas_ids.append(int(pregunta3_id))
            respuestas_seguridad.append({'pregunta_id': int(pregunta3_id), 'respuesta': respuesta3})
        
        # --- Re-poblar contexto en caso de error ---
        context_for_render.update({
            'nombre': nombre, 'apellido': apellido, 'dni': dni, 'username': username,
            'selected_preguntas_ids': [int(pregunta1_id or 0), int(pregunta2_id or 0), int(pregunta3_id or 0)],
            'selected_respuestas': [respuesta1 or '', respuesta2 or '', respuesta3 or ''],
            'selected_privilegios_ids': list(map(int, privilegios_seleccionados_ids))
        })

        # --- Validaciones ---
        if not (nombre and apellido and dni and username and contrasena and confirmar_contrasena):
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "DEBE COMPLETAR TODOS LOS CAMPOS", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)
        
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre) or not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellido):
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "NOMBRE Y APELLIDOS NO DEBE CONTENER NÚMEROS", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)

        if contrasena != confirmar_contrasena:
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "CONTRASEÑAS NO SON IGUALES", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)
            
        if len(contrasena) < 8:
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "LA CONTRASEÑA DEBE TENER MÍNIMO 8 CARACTERES", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)

        if Usuario.objects.filter(dni=dni).exists():
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "DNI YA ESTÁ REGISTRADO", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)
            
        if Usuario.objects.filter(username=username).exists():
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "EL USUARIO YA ESTA REGISTRADO", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)

        if len(preguntas_seleccionadas_ids) < 3:
             context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "DEBES RESPONDER TODAS LAS PREGUNTAS", 'type': 'error'}
             return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)
        
        if len(set(preguntas_seleccionadas_ids)) != 3:
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "NO SE SELECCIONÓ UNA PREGUNTA DE SEGURIDAD O LA SELECCIÓN SE REPITE", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)

        if not privilegios_seleccionados_ids:
            context_for_render['modal_message'] = {'title': 'Mensaje', 'body': "DEBE SELECCIONAR AL MENOS UN PRIVILEGIO", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)

        # --- Transacción en la base de datos ---
        try:
            with transaction.atomic():
                usuario = Usuario.objects.create(
                    nombre=nombre,
                    apellido=apellido,
                    dni=int(dni),
                    username=username,
                    contrasena_hash=make_password(contrasena),
                    estado=1,
                )

                for item in respuestas_seguridad:
                    pregunta = PreguntaSeguridad.objects.get(id=item['pregunta_id'])
                    UsuarioPreguntaRespuesta.objects.create(
                        usuario=usuario,
                        pregunta=pregunta,
                        respuesta_hash=make_password(item['respuesta'])
                    )

                for priv_id in privilegios_seleccionados_ids:
                    privilegio = Privilegio.objects.get(id=priv_id)
                    UsuarioPrivilegio.objects.create(usuario=usuario, privilegio=privilegio)

            request.session['modal_message'] = {
                'title': 'Mensaje',
                'body': f'USUARIO REGISTRADO EXITOSAMENTE',
                'type': 'success'
            }
            return redirect('gestion_ventas:gestionar_usuario')

        except Exception as e:
            return error_bd(request, e)
            
    return render(request, 'modulo_seguridad/FormAgregarUsuario.html', context_for_render)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Usuarios')
def editar_usuario(request, usuario_id):
    # --- Obtención de datos para la vista (GET y POST) ---
    usuario, error_usuario = ejecutar_consulta_segura(lambda: get_object_or_404(Usuario, pk=usuario_id))
    if error_usuario:
        return error_bd(request, error_usuario)
    
    privilegios_disponibles, error_privilegios = ejecutar_consulta_segura(lambda: Privilegio.objects.all())
    if error_privilegios:
        return error_bd(request, error_privilegios)
        
    usuario_privilegios_ids, error_priv_ids = ejecutar_consulta_segura(lambda: list(usuario.usuarioprivilegio_set.values_list('privilegio__id', flat=True)))
    if error_priv_ids:
        return error_bd(request, error_priv_ids)

    # Nota: Las preguntas de seguridad no se pueden editar, solo se muestran.
    usuario_preguntas_respuestas, error_preg_resp = ejecutar_consulta_segura(lambda: list(UsuarioPreguntaRespuesta.objects.filter(usuario=usuario).order_by('pregunta__id')))
    if error_preg_resp:
        return error_bd(request, error_preg_resp)

    if request.method == 'POST':
        if("btnGuardar" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        # --- Recopilación de datos del POST ---
        nuevo_contrasena = request.POST.get('txt_contrasena')
        confirmar_nuevo_contrasena = request.POST.get('txt_confirmar_contrasena')
        nuevos_privilegios_seleccionados_ids = request.POST.getlist('privilegios')

        # --- Contexto para recargar el formulario en caso de error ---
        context_on_error = {
            'usuario': usuario,
            'privilegios': privilegios_disponibles,
            'selected_privilegios_ids': list(map(int, nuevos_privilegios_seleccionados_ids)),
            'usuario_preguntas_respuestas': usuario_preguntas_respuestas
        }

        # --- Validaciones ---
        if nuevo_contrasena:
            if nuevo_contrasena != confirmar_nuevo_contrasena:
                context_on_error['modal_message'] = {'title': 'Mensaje', 'body': "CONTRASEÑAS NO SON IGUALES", 'type': 'error'}
                return render(request, 'modulo_seguridad/FormModificarUsuario.html', context_on_error)
            
            if len(nuevo_contrasena) < 8:
                context_on_error['modal_message'] = {'title': 'Mensaje', 'body': "LA CONTRASENA DEBE TENER MÍNIMO 8 CÁRACTERES", 'type': 'error'}
                return render(request, 'modulo_seguridad/FormModificarUsuario.html', context_on_error)

        if not nuevos_privilegios_seleccionados_ids:
            context_on_error['modal_message'] = {'title': 'Mensaje', 'body': "DEBE SELECCIONAR AL MENOS UN PRIVILEGIO", 'type': 'error'}
            return render(request, 'modulo_seguridad/FormModificarUsuario.html', context_on_error)

        # --- Transacción en la base de datos ---
        try:
            with transaction.atomic():
                if nuevo_contrasena:
                    usuario.contrasena_hash = make_password(nuevo_contrasena)
                
                # Actualizar privilegios
                UsuarioPrivilegio.objects.filter(usuario=usuario).delete()
                for priv_id in nuevos_privilegios_seleccionados_ids:
                    privilegio = Privilegio.objects.get(id=priv_id)
                    UsuarioPrivilegio.objects.create(usuario=usuario, privilegio=privilegio)
                
                usuario.save()

            request.session['modal_message'] = {
                'title': 'Mensaje',
                'body': 'EL USUARIO SE EDITÓ CON ÉXITO',
                'type': 'success'
            }
            return redirect('gestion_ventas:gestionar_usuario')

        except Exception as e:
            return error_bd(request, e)

    # --- Contexto para la carga inicial de la página (GET) ---
    context_for_get = {
        'usuario': usuario,
        'privilegios': privilegios_disponibles,
        'selected_privilegios_ids': usuario_privilegios_ids,
        'usuario_preguntas_respuestas': usuario_preguntas_respuestas,
    }
    return render(request, 'modulo_seguridad/FormModificarUsuario.html', context_for_get)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Usuarios')
def cambiar_estado_usuario(request, usuario_id):
    producto, error_producto = ejecutar_consulta_segura(lambda: get_object_or_404(Usuario, id=usuario_id))
    if error_producto:
        return error_bd(request, error_producto)
    
    if request.method == 'POST':
        estado_switch_value = request.POST.get('estado_switch')
        nuevo_estado = 1 if estado_switch_value == '1' else 0
        if producto.estado != nuevo_estado:
            def save_producto_estado():
                producto.estado = nuevo_estado
                producto.save()
            
            _, error_en_bd = ejecutar_consulta_segura(save_producto_estado)

            if error_en_bd:
                return error_bd(request, error_en_bd)
            else:
                if producto.estado == 1:
                    request.session['modal_message'] = {
                        'title': 'Mensaje',
                        'body': 'USUARIO HABILITADO CORRECTAMENTE',
                        'type': 'success'
                    }
                else:
                    request.session['modal_message'] = {
                        'title': 'Mensaje',
                        'body': 'USUARIO INHABILITADO CORRECTAMENTE',
                        'type': 'success'
                    }

    return redirect('gestion_ventas:gestionar_usuario')


def recuperar_contrasena_paso1_dni(request):
    if request.method == 'POST':
        if("btn_aceptar" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        dni_str = request.POST.get('txt_dni')
        if not dni_str or not re.fullmatch(r'^\d{8}$', dni_str):
            context = {'modal_message': {'title': 'Mensaje', 'body': 'NÚMERO DE DNI NO VÁLIDO', 'type': 'error'}}
            return render(request, 'modulo_seguridad/FormValidarDNI.html', context)
        
        dni = int(dni_str)

        usuario, error_usuario = ejecutar_consulta_segura(lambda: Usuario.objects.get(dni=dni, estado=1))

        if error_usuario:
            if isinstance(error_usuario, Usuario.DoesNotExist):
                context = {'modal_message': {'title': 'Mensaje', 'body': 'DNI NO ENCONTRADO', 'type': 'error'}}
                return render(request, 'modulo_seguridad/FormValidarDNI.html', context)
            
            return error_bd(request, error_usuario)
        
        preguntas_existen, error_preguntas = ejecutar_consulta_segura(lambda: UsuarioPreguntaRespuesta.objects.filter(usuario=usuario).exists())
        
        if error_preguntas:
            return error_bd(request, error_preguntas)

        if not preguntas_existen:
            context = {'modal_message': {'title': 'Mensaje', 'body': 'DNI NO ENCONTRADO', 'type': 'error'}}
            return render(request, 'modulo_seguridad/FormValidarDNI.html', context)

        request.session['temp_user_id_recuperacion'] = usuario.id
        request.session['temp_dni_recuperacion'] = dni_str
        return redirect('gestion_ventas:recuperar_contrasena_paso2_pregunta')

    modal_message = request.session.pop('modal_message', None)
    return render(request, 'modulo_seguridad/FormValidarDNI.html', {'modal_message': modal_message})

def recuperar_contrasena_paso2_pregunta(request):
    user_id = request.session.get('temp_user_id_recuperacion')
    usuario, error_usuario = ejecutar_consulta_segura(lambda: Usuario.objects.get(id=user_id, estado=1))
    if error_usuario:
        if isinstance(error_usuario, Usuario.DoesNotExist):
            return redirect('gestion_ventas:acceso_denegado')
        return error_bd(request, error_usuario)

    preguntas_usuario, error_preguntas_usuario = ejecutar_consulta_segura(lambda: UsuarioPreguntaRespuesta.objects.filter(usuario=usuario).select_related('pregunta'))
    if error_preguntas_usuario:
        return error_bd(request, error_preguntas_usuario)

    if request.method == 'POST':
        if("btn_siguiente" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        pregunta_id_seleccionada = request.POST.get('cmb_pregunta')
        respuesta_dada = request.POST.get('txt_respuesta')

        if not pregunta_id_seleccionada:
            context = {
                'preguntas': preguntas_usuario,
                'modal_message': {'title': 'Mensaje', 'body': 'SELECCIONE UNA DE LAS PREGUNTAS', 'type': 'error'}
            }
            return render(request, 'modulo_seguridad/FormRecuperarContraseña.html', context)
        
        if not respuesta_dada:
            context = {
                'preguntas': preguntas_usuario,
                'modal_message': {'title': 'Mensaje', 'body': 'LOS DATOS INGRESADOS NO SON VÁLIDOS', 'type': 'error'}
            }
            return render(request, 'modulo_seguridad/FormRecuperarContraseña.html', context)

        pregunta_respuesta_correcta, error_pregunta_correcta = ejecutar_consulta_segura(
            lambda: UsuarioPreguntaRespuesta.objects.get(
                usuario=usuario,
                pregunta__id=pregunta_id_seleccionada
            )
        )

        if error_pregunta_correcta:
            if isinstance(error_pregunta_correcta, UsuarioPreguntaRespuesta.DoesNotExist):
                context = {
                    'preguntas': preguntas_usuario,
                    'modal_message': {'title': 'Mensaje', 'body': 'LOS DATOS INGRESADOS NO SON VÁLIDOS', 'type': 'error'}
                }
                return render(request, 'modulo_seguridad/FormRecuperarContraseña.html', context)
            
            return error_bd(request, error_pregunta_correcta)
            
        es_correcta = check_password(respuesta_dada, pregunta_respuesta_correcta.respuesta_hash)

        if not es_correcta:
            context = {
                'preguntas': preguntas_usuario,
                'modal_message': {
                    'title': 'Mensaje',
                    'body': 'RESPUESTA INCORRECTA',
                    'type': 'error'
                }
            }
            return render(request, 'modulo_seguridad/FormRecuperarContraseña.html', context)

        request.session['pregunta_seguridad_ok'] = True
        return redirect('gestion_ventas:recuperar_contrasena_paso3_reset')

    modal_message = request.session.pop('modal_message', None)
    context = {'preguntas': preguntas_usuario, 'modal_message': modal_message}
    return render(request, 'modulo_seguridad/FormRecuperarContraseña.html', context)

def recuperar_contrasena_paso3_reset(request):
    user_id = request.session.get('temp_user_id_recuperacion')
    pregunta_ok = request.session.get('pregunta_seguridad_ok')

    if not user_id or not pregunta_ok:
        if 'temp_user_id_recuperacion' in request.session: del request.session['temp_user_id_recuperacion']
        if 'pregunta_seguridad_ok' in request.session: del request.session['pregunta_seguridad_ok']
        if 'temp_dni_recuperacion' in request.session: del request.session['temp_dni_recuperacion']
        return redirect('gestion_ventas:acceso_denegado')

    usuario, error_usuario = ejecutar_consulta_segura(lambda: Usuario.objects.get(id=user_id, estado=1))
    if error_usuario:
        if isinstance(error_usuario, Usuario.DoesNotExist):
            if 'temp_user_id_recuperacion' in request.session: del request.session['temp_user_id_recuperacion']
            if 'pregunta_seguridad_ok' in request.session: del request.session['pregunta_seguridad_ok']
            if 'temp_dni_recuperacion' in request.session: del request.session['temp_dni_recuperacion']
            return redirect('gestion_ventas:acceso_denegado')
        
        return error_bd(request, error_usuario)

    if request.method == 'POST':
        nueva_contrasena = request.POST.get('txt_new_password')
        repetir_contrasena = request.POST.get('txt_re_new_password')
        if("btn_aceptar" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        
        if nueva_contrasena != repetir_contrasena:
            context = {'modal_message': {'title': 'Mensaje', 'body': 'LAS CONTRASEÑAS NO SON IGUALES', 'type': 'error'}}
            return render(request, 'modulo_seguridad/FormReestablecerContraseña.html', context)

        if len(nueva_contrasena or repetir_contrasena) < 8:
            context = {'modal_message': {'title': 'Mensaje', 'body': 'LA CONTRASEÑA DEBE TENER MÍNIMO 8 CÁRACTERES', 'type': 'error'}}
            return render(request, 'modulo_seguridad/FormReestablecerContraseña.html', context)

        def reset_password_transaction():
            usuario.contrasena_hash = make_password(nueva_contrasena)
            usuario.save()

            user_django, created = User.objects.get_or_create(username=usuario.username)
            user_django.set_password(nueva_contrasena)
            user_django.save()

        _, error_en_bd = ejecutar_consulta_segura(reset_password_transaction)

        if error_en_bd:
            return error_bd(request, error_en_bd)
            
        if 'temp_user_id_recuperacion' in request.session: del request.session['temp_user_id_recuperacion']
        if 'pregunta_seguridad_ok' in request.session: del request.session['pregunta_seguridad_ok']
        if 'temp_dni_recuperacion' in request.session: del request.session['temp_dni_recuperacion']
            
        request.session['modal_message'] = {
            'title': 'Mensaje',
            'body': 'SE ACTUALIZO LA CONTRASEÑA CON ÉXITO',
            'type': 'success'
        }
            
        return redirect('gestion_ventas:login_view')

    modal_message = request.session.pop('modal_message', None)
    context = {'modal_message': modal_message}
    return render(request, 'modulo_seguridad/FormReestablecerContraseña.html', context)

@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Productos')
def gestionar_productos(request):
    modal_message = request.session.pop('modal_message', None)
    estado_filtro = request.GET.get('estado', 'todos')
    def get_productos_filtrados():
        if estado_filtro == 'todos':
            return Producto.objects.all().order_by('nombre_producto')
        else:
            return Producto.objects.filter(estado=int(estado_filtro)).order_by('nombre_producto')

    productos, error_en_bd_productos = ejecutar_consulta_segura(get_productos_filtrados)

    if error_en_bd_productos:
        return error_bd(request, error_en_bd_productos)

    return render(request, 'modulo_ventas/FormGestionarProductos.html', {
        'productos': productos,
        'estado_filtro': estado_filtro,
        'modal_message': modal_message
    })


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Productos')
def registrar_producto(request):
    categorias, error_categorias = ejecutar_consulta_segura(lambda: Categoria.objects.all())
    if error_categorias:
        return error_bd(request, error_categorias)

    if request.method == 'POST':
        if("btnRegistrar" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        
        nombre = request.POST.get('txt_nombre')
        precio_str = request.POST.get('txt_precio')
        stock_str = request.POST.get('txt_stock')
        categoria_id = request.POST.get('cmb_categoria')

        # VALIDACIÓN 1: Campos de texto y número vacíos
        if not (nombre and precio_str and stock_str):
            context = {
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "DEBE COMPLETAR TODOS LOS CAMPOS", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormRegistrarProducto.html', context)

        # VALIDACIÓN 2: Categoría no seleccionada
        if not categoria_id:
            context = {
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "NO SE SELECCIONÓ NINGUNA CATEGORÍA PARA EL PRODUCTO", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormRegistrarProducto.html', context)

        if not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            context = {
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "SE DETECTARON CARACTERES NO VALIDOS", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormRegistrarProducto.html', context)
        
        # VALIDACIÓN 3: Verificar si el producto ya existe por nombre
        producto_existente, error_consulta_producto = ejecutar_consulta_segura(lambda: Producto.objects.filter(nombre_producto__iexact=nombre).exists())
        if error_consulta_producto:
            return error_bd(request, error_consulta_producto)
        if producto_existente:
            context = {
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "YA EXISTE UN PRODUCTO CON EL MISMO NOMBRE", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormRegistrarProducto.html', context)

        precio = Decimal(precio_str.replace(',', '.'))
        stock = int(stock_str)
        if stock <= 0:
            context = {
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "EL STOCK DEBE SER MAYOR A CERO", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormRegistrarProducto.html', context)

        if precio <= 0:
            context = {
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "EL PRECIO DEBE SER MAYOR A CERO", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormRegistrarProducto.html', context)

        categoria, error_categoria_obj = ejecutar_consulta_segura(lambda: Categoria.objects.get(pk=categoria_id))
        if error_categoria_obj:
            if isinstance(error_categoria_obj, Categoria.DoesNotExist):
                context = {
                    'categorias': categorias,
                    'modal_message': {'title': 'Mensaje', 'body': "LA CATEGORÍA SELECCIONADA NO ES VÁLIDA", 'type': 'error'}
                }
                return render(request, 'modulo_ventas/FormRegistrarProducto.html', context)
            
            return error_bd(request, error_categoria_obj)
            
        try:
            with transaction.atomic():
                prefix = categoria.nombre_categoria[0].upper()
                last_product_of_category = Producto.objects.filter(codigo_producto__startswith=prefix).order_by('-codigo_producto').first()
                
                if last_product_of_category:
                    try:
                        last_num = int(last_product_of_category.codigo_producto[1:])
                        new_num = last_num + 1
                        codigo_producto = f'{prefix}{new_num:03d}'
                    except (ValueError, IndexError):
                        codigo_producto = f'{prefix}001'
                else:
                    codigo_producto = f'{prefix}001'

                while Producto.objects.filter(codigo_producto=codigo_producto).exists():
                    current_num = int(codigo_producto[1:])
                    codigo_producto = f'{prefix}{current_num + 1:03d}'
                    
                # Creación del producto
                Producto.objects.create(
                    codigo_producto=codigo_producto,
                    nombre_producto=nombre,
                    precio_unitario=precio,
                    stock=stock,
                    categoria=categoria,
                    estado=1
                )
                
                request.session['modal_message'] = {
                    'title': 'Mensaje',
                    'body': 'PRODUCTO REGISTRADO EXITOSAMENTE',
                    'type': 'success'
                }
                return redirect('gestion_ventas:gestionar_productos')

        except Exception as e:
            return error_bd(request, e)
    return render(request, 'modulo_ventas/FormRegistrarProducto.html', {'categorias': categorias})


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Productos')
def editar_producto(request, producto_id):
    producto, error_producto = ejecutar_consulta_segura(lambda: get_object_or_404(Producto, codigo_producto=producto_id))
    if error_producto:
        return error_bd(request, error_producto)

    categorias, error_categorias = ejecutar_consulta_segura(lambda: Categoria.objects.all())
    if error_categorias:
        return error_bd(request, error_categorias)

    if request.method == 'POST':
        if("btnGuardar" not in request.POST):
            return redirect('gestion_ventas:acceso_denegado')
        nombre = request.POST.get('txt_nombre')
        precio_str = request.POST.get('txt_precio')
        stock_str = request.POST.get('txt_stock')
        categoria_id = request.POST.get('cmb_categoria')

        if not (nombre and precio_str and stock_str and categoria_id):
            context = {
                'producto': producto,
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "DEBE COMPLETAR TODOS LOS CAMPOS", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormEditarProducto.html', context)

        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s]+$', nombre):
            context = {
                'producto': producto,
                'categorias': categorias,
                'modal_message': {'title': 'Mensaje', 'body': "SE DETECTARON CARACTERES NO VALIDOS", 'type': 'error'}
            }
            return render(request, 'modulo_ventas/FormEditarProducto.html', context)

        try:
            precio = Decimal(precio_str.replace(',', '.'))
            stock = int(stock_str)

            categoria, error_categoria_obj = ejecutar_consulta_segura(lambda: Categoria.objects.get(pk=categoria_id))
            if error_categoria_obj:
                return error_bd(request, error_categoria_obj)

            with transaction.atomic():
                if nombre != producto.nombre_producto:
                    if Producto.objects.filter(nombre_producto__iexact=nombre).exclude(codigo_producto=producto.codigo_producto).exists():
                        context = {
                            'producto': producto,
                            'categorias': categorias,
                            'modal_message': {'title': 'Mensaje', 'body': "YA EXISTE UN PRODUCTO CON EL MISMO NOMBRE", 'type': 'error'}
                        }
                        return render(request, 'modulo_ventas/FormEditarProducto.html', context)

                producto.nombre_producto = nombre
                producto.precio_unitario = precio
                producto.stock = stock
                producto.categoria = categoria
                producto.save()

            request.session['modal_message'] = {
                'title': 'Mensaje',
                'body': "EL PRODUCTO SE EDITÓ CON ÉXITO",
                'type': 'success'
            }
            return redirect('gestion_ventas:gestionar_productos')
        except Exception as e:
            return error_bd(request, e)

    return render(request, 'modulo_ventas/FormEditarProducto.html', {'producto': producto, 'categorias': categorias})



@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Gestionar Productos')
def cambiar_estado_producto(request, producto_id):
    if request.method == 'POST':
        producto, error_producto = ejecutar_consulta_segura(lambda: get_object_or_404(Producto, codigo_producto=producto_id))
        if error_producto:
            return error_bd(request, error_producto)
    
        estado_switch_value = request.POST.get('estado')
        nuevo_estado = 1 if estado_switch_value == '1' else 0

        if producto.estado != nuevo_estado:
            def save_producto_estado():
                producto.estado = nuevo_estado
                producto.save()
            
            _, error_en_bd_estado = ejecutar_consulta_segura(save_producto_estado)

            if error_en_bd_estado:
                return error_bd(request, error_en_bd_estado)
            else:
                if producto.estado == 1:
                    request.session['modal_message'] = {
                        'title': 'Mensaje',
                        'body': 'EL PRODUCTO HA SIDO HABILITADO CON ÉXITO',
                        'type': 'success'
                    }
                else:
                    request.session['modal_message'] = {
                        'title': 'Mensaje',
                        'body': 'EL PRODUCTO HA SIDO DESHABILITADO CON ÉXITO',
                        'type': 'success'
                    }
            
    return redirect('gestion_ventas:gestionar_productos')



def numero_a_letras(numero):
    unidades = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
    dieces = ['DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISEIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE']
    decs = ['', '', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
    centenas = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']

    def _convert_group(n):
        output = []
        if n >= 100:
            if n == 100:
                output.append('CIEN')
            else:
                output.append(centenas[n // 100])
            n %= 100
        if n >= 20:
            output.append(decs[n // 10])
            n %= 10
            if n > 0:
                output.append('Y')
        if n >= 10:
            output.append(dieces[n - 10])
            n = 0
        if n > 0:
            output.append(unidades[n])
        return ' '.join(output).strip()

    numero = Decimal(numero).quantize(Decimal('0.01'))
    entero = int(numero)
    decimal_parte = int(round((numero - entero) * 100))
    
    if entero == 0 and decimal_parte == 0:
        return "CERO Y 00/100 SOLES"

    letras_entero = ""
    if entero == 0:
        letras_entero = "CERO"
    elif 1 <= entero < 1000:
        letras_entero = _convert_group(entero)
    elif 1000 <= entero < 1000000:
        miles = entero // 1000
        resto = entero % 1000
        letras_miles = _convert_group(miles)
        if miles == 1:
            letras_miles = "UN"
        
        letras_entero = f"{letras_miles} MIL"
        if resto > 0:
            letras_entero += f" {_convert_group(resto)}"
    elif 1000000 <= entero < 1000000000:
        millones = entero // 1000000
        resto = entero % 1000000
        if millones == 1:
            letras_entero = "UN MILLON"
        else:
            letras_entero = f"{_convert_group(millones)} MILLONES"
        if resto > 0:
            resto_letras = numero_a_letras(resto).rsplit(' Y ', 1)[0]
            letras_entero += f" {resto_letras}"

    centimos_str = f"{decimal_parte:02d}/100 SOLES"
    
    return f"{letras_entero.strip()} Y {centimos_str}".replace("  ", " ").strip()


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Boleta')
def emitir_boleta(request):
    return render(request, 'modulo_ventas/FormEmitirBoleta.html')


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Boleta')
def buscar_productos(request):
    query = request.GET.get('query', '').strip()
    def get_productos_by_query():
        return Producto.objects.filter(
            Q(nombre_producto__icontains=query) | Q(codigo_producto__icontains=query),
            estado=1,    # Active products only
            stock__gt=0  # Only products with stock > 0
        ).select_related('categoria')
    results, error_producto_bd = ejecutar_consulta_segura(get_productos_by_query)

    if error_producto_bd:
        return error_bd(request, error_producto_bd, is_ajax=True)
    
    if not results:
        return JsonResponse({
            'status': 'not_found',
            'message': 'PRODUCTO NO ENCONTRADO O SE ENCUENTRA INHABILITADO'
        })
    productos_data = [{
        'codigo_producto': p.codigo_producto,
        'nombre_producto': p.nombre_producto,
        'precio_unitario': float(p.precio_unitario),
        'stock': p.stock,
        'categoria_nombre': p.categoria.nombre_categoria,
    } for p in results]
        
    return JsonResponse({'status': 'success', 'productos': productos_data})

@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Boleta')
def obtener_carrito(request):
    try:
        cart = request.session.get('cart', {})
        for item_code, item_data in cart.items():
            if isinstance(item_data.get('precio_unitario'), str):
                item_data['precio_unitario'] = float(item_data['precio_unitario'])
            if isinstance(item_data.get('subtotal'), str):
                item_data['subtotal'] = float(item_data['subtotal'])
        return JsonResponse({'status': 'success', 'cart': cart})
    except Exception as e:
        return error_bd(request, e, is_ajax=True)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Boleta')
def actualizar_carrito(request):
    if request.method == 'POST':
        try:
            cart_data = json.loads(request.body)
            request.session['cart'] = cart_data
            request.session.modified = True
            return JsonResponse({'status': 'success', 'cart': cart_data})
        except Exception as e:
            return error_bd(request, e, is_ajax=True)         
    return acceso_denegado(request)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Boleta')
@transaction.atomic
def procesar_boleta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart = data.get('cart', {})
            metodo_pago = data.get('metodo_pago', 'Efectivo')

            def create_boleta_transaction():
                with transaction.atomic():
                    detalles_para_boleta = []
                    monto_total_boleta = Decimal('0.00')
                    
                    empleado_usuario = Usuario.objects.get(username=request.user.username)

                    for item_code, item_data in cart.items():
                        producto = get_object_or_404(Producto, codigo_producto=item_code)
                        cantidad_vendida = int(item_data['cantidad'])
                        precio_unitario_venta = Decimal(str(item_data['precio_unitario']))
                        
                        # --- MODIFICACIÓN AQUÍ ---
                        # Se mantiene la validación, pero el error se lanza sin mensaje.
                        if producto.stock < cantidad_vendida:
                            raise ValidationError() 
                        
                        monto_parcial_item = precio_unitario_venta * cantidad_vendida
                        monto_total_boleta += monto_parcial_item

                        detalles_para_boleta.append({
                            'producto': producto,
                            'cantidad': cantidad_vendida,
                            'precio_unitario_venta': precio_unitario_venta,
                            'monto_parcial': monto_parcial_item
                        })

                        producto.stock -= cantidad_vendida
                        producto.save()
                    
                    fecha_correcta = timezone.localdate()
                    hora_correcta = timezone.localtime().time()

                    boleta = Boleta.objects.create(
                        fecha_emision=fecha_correcta,
                        hora_emision=hora_correcta,
                        metodo_pago=metodo_pago,
                        monto_total=monto_total_boleta,
                        empleado=empleado_usuario,
                        estado=1,
                    )

                    for detalle_data in detalles_para_boleta:
                        DetalleBoleta.objects.create(
                            id_boleta=boleta,
                            codigo_producto=detalle_data['producto'],
                            cantidad=detalle_data['cantidad'],
                            precio_unitario_venta=detalle_data['precio_unitario_venta'],
                            monto_parcial=detalle_data['monto_parcial']
                        )
                    return boleta

            boleta_creada, error_crear_boleta_bd = ejecutar_consulta_segura(create_boleta_transaction)

            if error_crear_boleta_bd:
                if isinstance(error_crear_boleta_bd, ValidationError):
                    return JsonResponse({'status': 'error'}, status=400)
                
                return error_bd(request, error_crear_boleta_bd, is_ajax=True)
                
            if 'cart' in request.session:
                del request.session['cart']
            request.session.modified = True

            return JsonResponse({'status': 'success', 'boleta_id': boleta_creada.id})
        
        except Exception as e:
            return error_bd(request, e, is_ajax=True)
            
    return acceso_denegado(request)



@login_required(login_url='gestion_ventas:acceso_denegado')
def ver_boleta(request, boleta_id):
    boleta, error_boleta = ejecutar_consulta_segura(lambda: get_object_or_404(Boleta, pk=boleta_id))
    if error_boleta:
        return error_bd(request, error_boleta)

    detalles_boleta, error_detalles = ejecutar_consulta_segura(lambda: boleta.detalleboleta_set.select_related('codigo_producto'))
    if error_detalles:
        return error_bd(request, error_detalles)

    context = {
        'boleta': boleta,
        'detalles_boleta': detalles_boleta,
        'importe_letras': numero_a_letras(boleta.monto_total)
    }
    return render(request, 'modulo_ventas/TemplateBoletaVenta.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Exportar Boletas')
def historial_boletas_view(request):
    selected_month = None
    selected_year = None
    boletas_base_query = Boleta.objects.all()
    modal_message_for_render = request.session.pop('modal_message', None)

    if request.method == 'POST':
        month_year_str = request.POST.get('month_year_filter')
        if month_year_str:
            try:
                parsed_date = datetime.strptime(month_year_str, '%Y-%m')
                selected_month = parsed_date.month
                selected_year = parsed_date.year
                
                temp_boletas_query, error_filtro = ejecutar_consulta_segura(
                    lambda: boletas_base_query.filter(
                        fecha_emision__month=selected_month,
                        fecha_emision__year=selected_year
                    )
                )
                if error_filtro:
                    return error_bd(request, error_filtro)
                else:
                    boletas_base_query = temp_boletas_query

            except ValueError:
                modal_message_for_render = {'title': 'Mensaje', 'body': 'TIENE QUE SELECCIONAR EL MES QUE DESEA EXPORTAR', 'type': 'error'}
                boletas_base_query = Boleta.objects.none()
                selected_month = None
                selected_year = None
        else:
            now = timezone.localdate()
            selected_month = now.month
            selected_year = now.year
            temp_boletas_query, error_filtro = ejecutar_consulta_segura(
                lambda: boletas_base_query.filter(fecha_emision__month=selected_month, fecha_emision__year=selected_year)
            )
            if error_filtro:
                return error_bd(request, error_filtro)
            else:
                boletas_base_query = temp_boletas_query
            
            if not modal_message_for_render:
                modal_message_for_render = {'title': 'Mensaje', 'body': 'TIENE QUE SELECCIONAR EL MES QUE DESEA EXPORTAR', 'type': 'error'}
    else:
        now = timezone.localdate()
        selected_month = now.month
        selected_year = now.year
        temp_boletas_query, error_filtro = ejecutar_consulta_segura(
            lambda: boletas_base_query.filter(fecha_emision__month=selected_month, fecha_emision__year=selected_year)
        )
        if error_filtro:
            return error_bd(request, error_filtro)
        else:
            boletas_base_query = temp_boletas_query

    def annotate_boletas():
        total_devoluciones_subquery = Subquery(
            NotaCredito.objects.filter(boleta=OuterRef('pk'))
            .values('boleta')
            .annotate(sum_devolucion=Sum('monto_total'))
            .values('sum_devolucion'),
            output_field=DecimalField()
        )
        return boletas_base_query.annotate(
            total_devolucion=Coalesce(total_devoluciones_subquery, Value(0), output_field=DecimalField())
        ).order_by('-fecha_emision', '-hora_emision')

    boletas_filtradas, error_boletas_filtradas = ejecutar_consulta_segura(annotate_boletas)
    if error_boletas_filtradas:
        return error_bd(request, error_boletas_filtradas)
    
    total_boletas_filtradas = boletas_filtradas.count()

    if total_boletas_filtradas == 0 and not modal_message_for_render:
        modal_message_for_render = {'title': 'Mensaje', 'body': 'NO HAY BOLETAS REGISTRADAS PARA EL MES SELECCIONADO', 'type': 'error'}

    boletas_para_mostrar = boletas_filtradas[:20]
    total_monto_ventas = boletas_filtradas.aggregate(Sum('monto_total'))['monto_total__sum'] or 0

    context = {
        'boletas': boletas_para_mostrar,
        'total_boletas_filtradas': total_boletas_filtradas,
        'total_monto_ventas': total_monto_ventas,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'modal_message': modal_message_for_render,
    }
    return render(request, 'modulo_ventas/FormExportarBoletas.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Nota de Credito')
def devolucion_total(request, boleta_id):
    boleta, error_boleta = ejecutar_consulta_segura(lambda: get_object_or_404(Boleta, pk=boleta_id))
    if error_boleta:
        return error_bd(request, error_boleta)
    return render(request, 'modulo_ventas/FormNotaCreditoTotal.html', {'boleta': boleta})


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Nota de Credito')
def devolucion_parcial(request, boleta_id):
    boleta, error_boleta = ejecutar_consulta_segura(lambda: get_object_or_404(Boleta, pk=boleta_id))
    if error_boleta:
        return error_bd(request, error_boleta)
    detalles_boleta, error_detalles = ejecutar_consulta_segura(lambda: boleta.detalleboleta_set.select_related('codigo_producto').all())
    if error_detalles:
        return error_bd(request, error_detalles)
        
    return render(request, 'modulo_ventas/FormNotaCreditoParcial.html', {
        'boleta': boleta,
        'detalles_boleta': detalles_boleta
    })

@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Nota de Credito')
def seleccionar_tipo_nota_credito(request, boleta_id):
    boleta, error_boleta = ejecutar_consulta_segura(lambda: get_object_or_404(Boleta, pk=boleta_id))
    if error_boleta:
        return error_bd(request, error_boleta)
    context = {'boleta': boleta}
    return render(request, 'modulo_ventas/FormNotasCredito.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Nota de Credito')
def confirmar_nota_credito(request):
    data = json.loads(request.body)
    boleta_id = data.get('boleta_id')
    tipo_devolucion_accion = data.get('tipo_devolucion')
    detalles_texto = data.get('detalles', '')
    items_devolucion = data.get('items_devolucion', [])

    boleta_referencia, error_boleta = ejecutar_consulta_segura(lambda: get_object_or_404(Boleta, pk=boleta_id))
    if error_boleta:
        return error_bd(request, error_boleta, is_ajax=True)

    nota_credito_existente, error_nc_existente = ejecutar_consulta_segura(lambda: NotaCredito.objects.filter(boleta=boleta_referencia).exists())
    if error_nc_existente:
        return error_bd(request, error_nc_existente, is_ajax=True)
    def create_nota_credito_transaction():
        with transaction.atomic():
            total_monto_devolver = Decimal('0.00')
            detalles_para_guardar = []
            stock_para_actualizar = {}
            
            empleado_usuario = Usuario.objects.get(username=request.user.username)
            boleta_referencia.estado = 0
            boleta_referencia.save()

            if tipo_devolucion_accion == 'total':
                detalles_originales = boleta_referencia.detalleboleta_set.select_related('codigo_producto').all()
                for item in detalles_originales:
                    total_monto_devolver += item.monto_parcial
                    detalles_para_guardar.append({'producto': item.codigo_producto, 'cantidad': item.cantidad, 'monto_parcial': item.monto_parcial})
                    stock_para_actualizar[item.codigo_producto.codigo_producto] = stock_para_actualizar.get(item.codigo_producto.codigo_producto, 0) + item.cantidad
            
            elif tipo_devolucion_accion == 'parcial':
                for item_data in items_devolucion:
                    producto = get_object_or_404(Producto, codigo_producto=item_data['codigo_producto'])
                    
                    try:
                        cantidad_devolver = int(item_data['cantidad'])
                        if cantidad_devolver <= 0:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    detalle_boleta_original = get_object_or_404(DetalleBoleta, id_boleta=boleta_referencia, codigo_producto=producto)

                    monto_parcial_devolver = cantidad_devolver * detalle_boleta_original.precio_unitario_venta
                    total_monto_devolver += monto_parcial_devolver
                    detalles_para_guardar.append({'producto': producto, 'cantidad': cantidad_devolver, 'monto_parcial': monto_parcial_devolver})
                    stock_para_actualizar[producto.codigo_producto] = stock_para_actualizar.get(producto.codigo_producto, 0) + cantidad_devolver

            nueva_nota_credito = NotaCredito.objects.create(
                empleado=empleado_usuario,
                boleta=boleta_referencia,
                monto_total=total_monto_devolver,
                detalles=detalles_texto
            )

            for item in detalles_para_guardar:
                DetalleNotaCredito.objects.create(
                    nota_credito=nueva_nota_credito,
                    producto=item['producto'],
                    cantidad_devuelta=item['cantidad'],
                    monto_devuelto=item['monto_parcial']
                )
                
            for prod_code, quantity_to_add in stock_para_actualizar.items():
                Producto.objects.filter(codigo_producto=prod_code).update(stock=F('stock') + quantity_to_add)
            return nueva_nota_credito

    nueva_nota_credito, error_en_bd = ejecutar_consulta_segura(create_nota_credito_transaction)

    if error_en_bd:
        if isinstance(error_en_bd, ValidationError):
            error_message = error_en_bd.messages[0] if error_en_bd.messages else str(error_en_bd)
            return JsonResponse({'status': 'error', 'message': error_message.upper()}, status=400)
        
        return error_bd(request, error_en_bd, is_ajax=True)
            
    redirect_url = reverse('gestion_ventas:ver_nota_credito', args=[nueva_nota_credito.id])
    return JsonResponse({'status': 'success', 'nota_credito_id': nueva_nota_credito.id, 'redirect_url': redirect_url})



@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Nota de Credito')
def ver_nota_credito(request, nota_credito_id):
    nota_credito, error_nota_credito = ejecutar_consulta_segura(lambda: get_object_or_404(NotaCredito, pk=nota_credito_id))
    if error_nota_credito:
        return error_bd(request, error_nota_credito)

    detalles_nota_credito, error_detalles_nc = ejecutar_consulta_segura(lambda: nota_credito.detalles_de_nota.select_related('producto').all())
    if error_detalles_nc:
        return error_bd(request, error_detalles_nc)
        
    context = {
        'nota_credito': nota_credito,
        'detalles_nota_credito': detalles_nota_credito,
    }
    return render(request, 'modulo_ventas/TemplateNotaCredito.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Nota de Credito')
def emitir_nota_credito(request):
    modal_message = request.session.pop('modal_message', None)
    return render(request, 'modulo_ventas/FormEmitirNotaCredito.html', {'modal_message': modal_message})


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Emitir Nota de Credito')
def buscar_boleta_ajax(request):
    query = request.GET.get('query', '').strip()
    boleta_id = int(query)
    
    boleta, error_boleta = ejecutar_consulta_segura(lambda: Boleta.objects.select_related('empleado').get(id=boleta_id))

    if error_boleta:
        if isinstance(error_boleta, Boleta.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'BOLETA NO ENCONTRADA'})
        return error_bd(request, error_boleta, is_ajax=True)
            
    nota_existente, _ = ejecutar_consulta_segura(lambda: NotaCredito.objects.filter(boleta=boleta).exists())

    boleta_encontrada = {
        'status': 'success',
        'boleta': {
            'id': boleta.id,
            'fecha_emision': boleta.fecha_emision.strftime('%d/%m/%Y'),
            'hora_emision': boleta.hora_emision.strftime('%H:%M:%S'),
            'monto_total': str(boleta.monto_total),
            'empleado_username': f"{boleta.empleado.nombre} {boleta.empleado.apellido}",
            'tiene_nota_credito': nota_existente
        }
    }
    return JsonResponse(boleta_encontrada)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def cierre_caja(request):
    modal_message = request.session.pop('modal_message', None)
    today = timezone.localdate()

    def get_reporte_statuses():
        reporte_boletas_hecho = ReporteBoletas.objects.filter(fecha_registro=today).exists()
        reporte_caja_hecho = ReporteCaja.objects.filter(fecha_registro=today).exists()
        reporte_egresos_hecho = ReporteEgresos.objects.filter(fecha_registro=today).exists()
        cierre_final_hecho = ReporteCierreCaja.objects.filter(fecha_registro=today).exists()
        return reporte_boletas_hecho, reporte_caja_hecho, reporte_egresos_hecho, cierre_final_hecho
    
    (reporte_boletas_hecho, reporte_caja_hecho, reporte_egresos_hecho, cierre_final_hecho), error_estados = ejecutar_consulta_segura(get_reporte_statuses)
    if error_estados:
        return error_bd(request, error_estados)

    context = {
        'modal_message': modal_message,
        'today': today,
        'reporte_boletas_hecho': reporte_boletas_hecho,
        'reporte_caja_hecho': reporte_caja_hecho,
        'reporte_egresos_hecho': reporte_egresos_hecho,
        'cierre_final_hecho': cierre_final_hecho,
    }
    return render(request, 'modulo_ventas/FormCierreCaja.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def reporte_boletas_view(request):
    modal_message = request.session.pop('modal_message', None)
    today = timezone.localdate()
    
    def get_boletas_del_dia():
        return Boleta.objects.filter(fecha_emision=today).order_by('hora_emision')

    boletas_del_dia, error_boletas = ejecutar_consulta_segura(get_boletas_del_dia)
    if error_boletas:
        return error_bd(request, error_boletas)

    total_ventas_del_dia, error_total_ventas = ejecutar_consulta_segura(lambda: boletas_del_dia.aggregate(Sum('monto_total'))['monto_total__sum'] or 0)
    if error_total_ventas:
        return error_bd(request, error_total_ventas)

    context = {
        'today_date': today,
        'boletas_del_dia': boletas_del_dia,
        'total_ventas_del_dia': total_ventas_del_dia,
        'modal_message': modal_message
    }
    return render(request, 'modulo_ventas/FormReporteBoletas.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def generar_reporte_boletas(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    today = timezone.localdate()

    def create_reporte_boletas_transaction():
        if ReporteBoletas.objects.filter(fecha_registro=today).exists():
            raise ValidationError('EL REPORTE DE BOLETAS PARA HOY YA FUE GENERADO.')

        boletas_del_dia = Boleta.objects.filter(fecha_emision=today)
        if not boletas_del_dia.exists():
            raise ValidationError('NO HAY BOLETAS EMITIDAS HOY PARA GENERAR UN REPORTE.')

        total_monto_boletas = boletas_del_dia.aggregate(Sum('monto_total'))['monto_total__sum'] or 0
        empleado_logueado = Usuario.objects.get(username=request.user.username)

        reporte_boletas = ReporteBoletas.objects.create(
            empleado=empleado_logueado,
            fecha_registro=today,
            hora_registro=timezone.localtime().time(),
            monto_total=total_monto_boletas
        )

        for boleta in boletas_del_dia:
            DetalleReporteBoleta.objects.create(reporte=reporte_boletas, boleta=boleta, monto_parcial=boleta.monto_total)
        return reporte_boletas

    reporte_boletas_obj, error_en_bd = ejecutar_consulta_segura(create_reporte_boletas_transaction)

    if error_en_bd:
        if isinstance(error_en_bd, ValidationError):
            error_message = error_en_bd.messages[0] if error_en_bd.messages else str(error_en_bd)
            return JsonResponse({'status': 'error', 'message': error_message}, status=400)
        return JsonResponse({'status': 'error', 'message': 'Error interno del servidor'}, status=500)

    report_url = reverse('gestion_ventas:ver_template_reporte_boletas', args=[reporte_boletas_obj.id])
    
    return JsonResponse({
        'status': 'success',
        'report_url': report_url
    })


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def ver_template_reporte_boletas(request, reporte_id):
    reporte, error_reporte = ejecutar_consulta_segura(lambda: get_object_or_404(ReporteBoletas, id=reporte_id))
    if error_reporte:
        return error_bd(request, error_reporte)

    detalles_reporte_boletas, error_detalles = ejecutar_consulta_segura(lambda: DetalleReporteBoleta.objects.filter(reporte=reporte))
    if error_detalles:
        return error_bd(request, error_detalles)

    modal_message = request.session.pop('modal_message', None)
    context = {
        'reporte': reporte,
        'detalles_reporte_boletas': detalles_reporte_boletas,
        'modal_message': modal_message,
    }
    return render(request, 'modulo_ventas/TemplateReporteBoletas.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def reporte_de_caja_view(request):
    modal_message = request.session.pop('modal_message', None)
    
    denominaciones_billetes, error_billetes = ejecutar_consulta_segura(lambda: Denominacion.objects.filter(denominacion__gte=10).order_by('-denominacion'))
    if error_billetes:
        return error_bd(request, error_billetes)
    
    denominaciones_monedas, error_monedas = ejecutar_consulta_segura(lambda: Denominacion.objects.filter(denominacion__lt=10).order_by('-denominacion'))
    if error_monedas:
        return error_bd(request, error_monedas)

    context = {
        'today_date': timezone.localdate(),
        'denominaciones_billetes': denominaciones_billetes,
        'denominaciones_monedas': denominaciones_monedas,
        'modal_message': modal_message,
    }
    return render(request, 'modulo_ventas/FormReporteCaja.html', context)

@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def generar_reporte_caja(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                today = timezone.localdate()

                if ReporteCaja.objects.filter(fecha_registro=today).exists():
                    raise ValidationError('YA SE HA GENERADO UN REPORTE DE CAJA EL DÍA DE HOY')
                
                monto_total_contado_str = request.POST.get('monto_total_contado', '0')
                try:
                    monto_total_contado = Decimal(monto_total_contado_str.replace(',', '.'))
                except InvalidOperation:
                    raise ValidationError('SE ENCONTRARON CARACTERES NO VÁLIDOS EN UNO O MAS CAMPOS')

                if monto_total_contado <= 0:
                    # This message is on the allowed list
                    raise ValidationError('EL TOTAL DEBE SER MAYOR A CERO')
                
                empleado_logueado = Usuario.objects.get(username=request.user.username)
                reporte_caja = ReporteCaja.objects.create(
                    empleado=empleado_logueado,
                    fecha_registro=today,
                    hora_registro=timezone.localtime().time(),
                    monto_total=monto_total_contado
                )
                
                for denom in Denominacion.objects.all():
                    cantidad_str = request.POST.get(f'denominacion_{denom.id}')
                    # The client-side validation ensures these are valid numbers
                    if cantidad_str and int(cantidad_str) > 0:
                        cantidad = int(cantidad_str)
                        DetalleReporteCaja.objects.create(
                            reporte=reporte_caja,
                            denominacion=denom,
                            cantidad=cantidad,
                            monto_parcial=denom.denominacion * cantidad
                        )
                
                report_url = reverse('gestion_ventas:ver_template_reporte_caja', args=[reporte_caja.id])
                redirect_url = reverse('gestion_ventas:cierre_caja')
                
                return JsonResponse({
                    'status': 'success',
                    'report_url': report_url,
                    'redirect_url': redirect_url
                })
        except ValidationError as e:
            error_message = e.messages[0] if e.messages else str(e)
            return JsonResponse({'status': 'error', 'message': error_message}, status=400)
        except Exception:
            # For any other server error, return a generic message that the client will ignore.
            return JsonResponse({'status': 'error', 'message': 'SERVER_ERROR'}, status=500)

    return redirect('gestion_ventas:reporte_de_caja_view')



@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def ver_template_reporte_caja(request, reporte_id):
    reporte, error_reporte = ejecutar_consulta_segura(lambda: get_object_or_404(ReporteCaja, id=reporte_id))
    if error_reporte:
        return error_bd(request, error_reporte)

    todas_las_denominaciones, error_denominaciones = ejecutar_consulta_segura(lambda: Denominacion.objects.order_by('-denominacion'))
    if error_denominaciones:
        return error_bd(request, error_denominaciones)

    detalles_guardados, error_detalles_guardados = ejecutar_consulta_segura(lambda: DetalleReporteCaja.objects.filter(reporte=reporte))
    if error_detalles_guardados:
        return error_bd(request, error_detalles_guardados)

    mapa_detalles = {detalle.denominacion_id: detalle for detalle in detalles_guardados}

    detalles_completos = []
    for denom in todas_las_denominaciones:
        detalle = mapa_detalles.get(denom.id)
        if detalle:
            detalles_completos.append(detalle)
        else:
            detalles_completos.append(
                DetalleReporteCaja(
                    reporte=reporte,
                    denominacion=denom,
                    cantidad=0,
                    monto_parcial=0
                )
            )

    modal_message = request.session.pop('modal_message', None)
    context = {
        'reporte': reporte,
        'detalles_reporte_caja': detalles_completos,
        'modal_message': modal_message,
    }
    return render(request, 'modulo_ventas/TemplateReporteCaja.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def gestionar_egresos(request):
    modal_message = request.session.pop('modal_message', None)
    today = timezone.localdate()

    total_notas_credito_hoy, error_notas_credito = ejecutar_consulta_segura(
        lambda: NotaCredito.objects.filter(fecha_emision=today).aggregate(
            total=Coalesce(Sum('monto_total'), Decimal('0.00'))
        )['total']
    )
    if error_notas_credito:
        return error_bd(request, error_notas_credito)

    reporte_existente, error_reporte_existente = ejecutar_consulta_segura(lambda: ReporteEgresos.objects.filter(fecha_registro=today).first())
    if error_reporte_existente:
        return error_bd(request, error_reporte_existente)

    gastos_guardados = reporte_existente.total_gastos if reporte_existente else ""

    context = {
        'modal_message': modal_message,
        'total_notas_credito_hoy': total_notas_credito_hoy,
        'gastos_guardados': gastos_guardados,
    }
    return render(request, 'modulo_ventas/FormReporteEgresos.html', context)


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def generar_reporte_egresos(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                today = timezone.localdate()
                if ReporteEgresos.objects.filter(fecha_registro=today).exists():
                    raise ValidationError('YA SE HA GENERADO UN REPORTE DE GASTOS EL DIA DE HOY')

                # Un campo vacío se tratará como '0'.
                total_gastos_str = request.POST.get('txt_monto_gastos', '0').strip()
                if not total_gastos_str:
                    total_gastos_str = '0'

                # Permite números y un signo negativo opcional para validarlo después.
                if not re.match(r'^-?[0-9]+([,.][0-9]{1,2})?$', total_gastos_str):
                    raise ValidationError('SE ENCONTRARON CARACTERES NO VÁLIDOS EN UNO O MAS CAMPOS')
                
                total_gastos = Decimal(total_gastos_str.replace(',', '.'))
                
                # La validación ahora es solo para números negativos.
                if total_gastos < 0:
                    raise ValidationError('EL TOTAL DE GASTOS NO PUEDE SER MENOR A CERO')

                empleado_logueado = Usuario.objects.get(username=request.user.username)
                total_notas_credito = NotaCredito.objects.filter(fecha_emision=today).aggregate(total=Coalesce(Sum('monto_total'), Decimal('0.00')))['total']
                total_final_egresos = total_gastos + total_notas_credito
                
                reporte_egresos_obj = ReporteEgresos.objects.create(
                    fecha_registro=today,
                    empleado=empleado_logueado,
                    total_gastos=total_gastos,
                    total_nota_credito=total_notas_credito,
                    total_reporte_egresos=total_final_egresos,
                    hora_registro=timezone.localtime().time()
                )
                
                report_url = reverse('gestion_ventas:ver_reporte_egresos', args=[reporte_egresos_obj.id])
                redirect_url = reverse('gestion_ventas:cierre_caja')
                
                return JsonResponse({
                    'status': 'success',
                    'report_url': report_url,
                    'redirect_url': redirect_url
                })

        except ValidationError as e:
            error_message = e.messages[0] if e.messages else str(e)
            return JsonResponse({'status': 'error', 'message': error_message}, status=400)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'SERVER_ERROR'}, status=500)

    return redirect('gestion_ventas:gestionar_egresos')


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def ver_reporte_egresos(request, reporte_id):
    reporte, error_reporte = ejecutar_consulta_segura(lambda: get_object_or_404(ReporteEgresos, id=reporte_id))
    if error_reporte:
        return error_bd(request, error_reporte)

    modal_message = request.session.pop('modal_message', None)
    context = {
        'reporte': reporte,
        'modal_message': modal_message,
    }
    return render(request, 'modulo_ventas/TemplateReporteEgresos.html', context)

@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def reporte_cierre_de_caja_view(request):
    today = timezone.localdate()

    # ReporteBoletas.fecha_registro is DateTimeField, so __date is correct
    reporte_boletas_hoy, error_rb_hoy = ejecutar_consulta_segura(lambda: ReporteBoletas.objects.filter(fecha_registro__date=today).order_by('-fecha_registro').first())
    if error_rb_hoy:
        return error_bd(request, error_rb_hoy)

    # ReporteCaja.fecha_registro is DateTimeField, so __date is correct
    reporte_caja_hoy, error_rc_hoy = ejecutar_consulta_segura(lambda: ReporteCaja.objects.filter(fecha_registro__date=today).order_by('-fecha_registro').first())
    if error_rc_hoy:
        return error_bd(request, error_rc_hoy)

    # ReporteEgresos.fecha_registro is DateField, REMOVE __date
    reporte_egresos_hoy, error_re_hoy = ejecutar_consulta_segura(lambda: ReporteEgresos.objects.filter(fecha_registro=today).order_by('-fecha_registro').first())
    if error_re_hoy:
        return error_bd(request, error_re_hoy)
    
    # ReporteCierreCaja.fecha_registro is DateField, REMOVE __date
    reporte_cierre_caja_hoy, error_rcc_hoy = ejecutar_consulta_segura(lambda: ReporteCierreCaja.objects.filter(fecha_registro=today).order_by('-fecha_registro').first())
    if error_rcc_hoy:
        return error_bd(request, error_rcc_hoy)


    # Safely calculate total_salidas, ensuring it's Decimal
    total_salidas = reporte_egresos_hoy.total_reporte_egresos if reporte_egresos_hoy else Decimal('0.00')
    
    # Safely calculate ingresos_netos, ensuring it's Decimal
    ingresos_netos = reporte_boletas_hoy.monto_total if reporte_boletas_hoy else Decimal('0.00')
    
    efectivo_esperado_total = ingresos_netos - total_salidas
    
    # Safely calculate descuadre, ensuring it's Decimal
    descuadre = (reporte_caja_hoy.monto_total if reporte_caja_hoy else Decimal('0.00')) - efectivo_esperado_total

    # Determine if each report "has been done today" for the frontend JavaScript
    boletas_hecho = reporte_boletas_hoy is not None
    caja_hecho = reporte_caja_hoy is not None
    egresos_hecho = reporte_egresos_hoy is not None
    cierre_final_hecho = reporte_cierre_caja_hoy is not None

    context = {
        'today_date': today,
        'reporte_boletas_hoy': reporte_boletas_hoy,
        'reporte_caja_hoy': reporte_caja_hoy,
        'reporte_egresos_hoy': reporte_egresos_hoy,
        'total_egresos_general': total_salidas,
        'descuadre': descuadre,
        'reporte_boletas_hecho': boletas_hecho,
        'reporte_caja_hecho': caja_hecho,
        'reporte_egresos_hecho': egresos_hecho,
        'cierre_final_hecho': cierre_final_hecho,
    }
    return render(request, 'modulo_ventas/FormReporteCierreCaja.html', context)



@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def confirmar_cierre_caja(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    today = timezone.localdate()
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos'}, status=400)

    def create_cierre_caja_transaction():
        with transaction.atomic():
            if ReporteCierreCaja.objects.filter(fecha_registro=today).exists():
                raise ValidationError('YA SE HA GENERADO UN REPORTE DE CIERRE DE CAJA')

            descuadre_str = data.get('descuadre', '0')
            descuadre_final = Decimal(descuadre_str.replace(',', '.'))
            razon_texto = data.get('razon', '').strip()

            if descuadre_final != 0 and not razon_texto:
                raise ValidationError('DEBE COMPLETAR TODOS LOS CAMPOS')
            
            if len(razon_texto) > 500:
                raise ValidationError('EL TEXTO INGRESADO NO DEBE SUPERAR LOS 500 CARACTERES')

            reporte_boletas = get_object_or_404(ReporteBoletas, id=data.get('reporte_boletas_id'))
            reporte_caja = get_object_or_404(ReporteCaja, id=data.get('reporte_caja_id'))
            reporte_egresos = get_object_or_404(ReporteEgresos, id=data.get('reporte_egresos_id'))
            empleado_logueado = Usuario.objects.get(username=request.user.username)
            
            cierre_caja_obj = ReporteCierreCaja.objects.create(
                empleado=empleado_logueado,
                fecha_registro=today,
                hora_registro=timezone.localtime().time(),
                reporte_boletas=reporte_boletas,
                reporte_caja=reporte_caja,
                reporte_egresos=reporte_egresos,
                descuadre=descuadre_final,
                razon=razon_texto or None
            )
            return cierre_caja_obj

    cierre_caja_obj, error_en_bd = ejecutar_consulta_segura(create_cierre_caja_transaction)

    if error_en_bd:
        if isinstance(error_en_bd, ValidationError):
            error_message = error_en_bd.messages[0] if error_en_bd.messages else str(error_en_bd)
            return JsonResponse({'status': 'error', 'message': error_message}, status=400)
        return error_bd(request, error_en_bd, is_ajax=True)
    
    report_url = reverse('gestion_ventas:ver_template_cierre_caja', args=[cierre_caja_obj.id])
    redirect_url = reverse('gestion_ventas:cierre_caja')
    
    return JsonResponse({
        'status': 'success',
        'report_url': report_url,
        'redirect_url': redirect_url
    })


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Cierre de Caja')
def ver_template_cierre_caja(request, cierre_id):
    cierre_caja, error_cierre = ejecutar_consulta_segura(lambda: get_object_or_404(ReporteCierreCaja, id=cierre_id))
    if error_cierre:
        return error_bd(request, error_cierre)

    total_ventas = cierre_caja.reporte_boletas.monto_total or Decimal('0.00')
    total_egresos = cierre_caja.reporte_egresos.total_reporte_egresos
    saldo_esperado = total_ventas - total_egresos

    modal_message = request.session.pop('modal_message', None)
    context = {
        'cierre_caja': cierre_caja,
        'modal_message': modal_message,
        'saldo_esperado': saldo_esperado,
    }
    return render(request, 'modulo_ventas/TemplateReporteCierreCaja.html', context)



@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Exportar Boletas')
def verificar_boletas_para_exportar(request):
    month_year_str = request.GET.get('month_year_filter', '')
    if not month_year_str:
        return JsonResponse({'status': 'error', 'boletas_exist': False}, status=400)

    try:
        parsed_date = datetime.strptime(month_year_str, '%Y-%m')
        month = parsed_date.month
        year = parsed_date.year
    except ValueError:
        return JsonResponse({'status': 'error', 'boletas_exist': False}, status=400)

    existen_boletas, error = ejecutar_consulta_segura(
        lambda: Boleta.objects.filter(fecha_emision__month=month, fecha_emision__year=year).exists()
    )

    if error:
        return error_bd(request, error, is_ajax=True)

    return JsonResponse({'status': 'success', 'boletas_exist': existen_boletas})


@login_required(login_url='gestion_ventas:acceso_denegado')
@privilegio_requerido('Exportar Boletas')
def exportar_boletas_excel(request):
    if request.method == 'POST':
        month_year_str = request.POST.get('month_year_filter')
        
        if not month_year_str:
            request.session['modal_message'] = {'title': 'Mensaje', 'body': 'NO SE HA PROPORCIONADO UN MES Y AÑO PARA EXPORTAR.', 'type': 'error'}
            return redirect('gestion_ventas:historial_boletas_view')

        try:
            parsed_date = datetime.strptime(month_year_str, '%Y-%m')
            month = parsed_date.month
            year = parsed_date.year
            try:
                locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
                periodo_str = parsed_date.strftime('%B %Y').upper()
            except locale.Error:
                periodo_str = parsed_date.strftime('%B %Y').upper()
            finally:
                locale.setlocale(locale.LC_TIME, '')
        except ValueError:
            request.session['modal_message'] = {'title': 'Mensaje', 'body': 'EL FORMATO DE FECHA ES INVÁLIDO. USE EL SELECTOR.', 'type': 'error'}
            return redirect('gestion_ventas:historial_boletas_view')

        def get_boletas_for_excel():
            total_devoluciones_subquery = Subquery(NotaCredito.objects.filter(boleta=OuterRef('pk')).values('boleta').annotate(s=Sum('monto_total')).values('s'), output_field=DecimalField())
            return Boleta.objects.filter(fecha_emision__month=month, fecha_emision__year=year).annotate(total_devolucion=Coalesce(total_devoluciones_subquery, Value(0), output_field=DecimalField())).order_by('fecha_emision', 'hora_emision')

        boletas, error_boletas = ejecutar_consulta_segura(get_boletas_for_excel)
        if error_boletas:
            return error_bd(request, error_boletas)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="reporte_ventas_mensual_{month_year_str.replace("-", "_")}.xlsx"'
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Reporte de Ventas"
        
        sheet['A1'] = "REPORTE DE VENTAS MENSUAL - PANADERÍA CHRISTIAN"
        sheet.merge_cells('A1:F1')
        sheet['A1'].font = Font(bold=True, size=16)
        sheet['A2'] = f"PERÍODO : {periodo_str}"
        sheet.merge_cells('A2:F2')
        sheet['A2'].font = Font(bold=True, size=12)
        sheet.append([])
        headers = ["CÓDIGO DE BOLETA", "FECHA DE EMISIÓN", "DESCRIPCIÓN PRODUCTO", "EMITIDO POR", "MONTO TOTAL", "DEVOLUCIÓN"]
        sheet.append(headers)
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        for col_num, header_text in enumerate(headers, 1):
            cell = sheet.cell(row=sheet.max_row, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            column_letter = get_column_letter(col_num)
            if column_letter == 'A': sheet.column_dimensions[column_letter].width = 15
            elif column_letter == 'B': sheet.column_dimensions[column_letter].width = 22
            elif column_letter == 'C': sheet.column_dimensions[column_letter].width = 45
            elif column_letter == 'D': sheet.column_dimensions[column_letter].width = 25
            else: sheet.column_dimensions[column_letter].width = 15
            
        total_ventas = 0
        total_devoluciones_acumulado = 0
        for boleta in boletas:
            productos_desc, error_productos_desc = ejecutar_consulta_segura(lambda: ", ".join([d.codigo_producto.nombre_producto for d in boleta.detalleboleta_set.all()]).upper())
            if error_productos_desc:
                return error_bd(request, error_productos_desc)

            row_data = [
                f"B{boleta.id:04d}",
                boleta.fecha_emision.strftime('%d/%m/%Y') + ' ' + boleta.hora_emision.strftime('%H:%M:%S'),
                productos_desc,
                f"{boleta.empleado.nombre.upper()} {boleta.empleado.apellido.upper()}",
                float(boleta.monto_total),
                float(boleta.total_devolucion),
            ]
            sheet.append(row_data)
            total_ventas += float(boleta.monto_total)
            total_devoluciones_acumulado += float(boleta.total_devolucion)
            
        sheet.append([])
        total_row_data = ["TOTAL VENTAS", "", "", "", total_ventas, total_devoluciones_acumulado]
        sheet.append(total_row_data)
        total_font = Font(bold=True)
        last_row = sheet.max_row
        sheet.cell(row=last_row, column=5).font = total_font
        sheet.cell(row=last_row, column=5).number_format = '0.00'
        sheet.cell(row=last_row, column=6).font = total_font
        sheet.cell(row=last_row, column=6).number_format = '0.00'
        sheet.merge_cells(start_row=last_row, start_column=1, end_row=last_row, end_column=4)
        sheet.cell(row=last_row, column=1).alignment = Alignment(horizontal="left", vertical="center")

        workbook.save(response)
        return response
        
    return redirect('gestion_ventas:historial_boletas_view')

def csrf_failure(request, reason=""):
    return redirect('gestion_ventas:acceso_denegado')