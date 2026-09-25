# backend_panaderia/gestion_ventas/urls.py
from django.urls import path
from . import views

app_name = 'gestion_ventas'

urlpatterns = [
    # --- Autenticación y Navegación Principal ---
    path('', views.login_view, name='login_view'),
    path('inicio/', views.inicio, name='inicio'),
    path('logout/', views.logout_view, name='logout_view'),
    path('acceso-denegado/', views.acceso_denegado, name='acceso_denegado'),

    # --- Gestión de Usuarios ---
    path('usuarios/', views.gestionar_usuario, name='gestionar_usuario'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/cambiar_estado/<int:usuario_id>/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),

    # --- Recuperación de Contraseña ---
    path('recuperar-contrasena/dni/', views.recuperar_contrasena_paso1_dni, name='recuperar_contrasena_paso1_dni'),
    path('recuperar-contrasena/pregunta/', views.recuperar_contrasena_paso2_pregunta, name='recuperar_contrasena_paso2_pregunta'),
    path('recuperar-contrasena/restablecer/', views.recuperar_contrasena_paso3_reset, name='recuperar_contrasena_paso3_reset'),

    # --- Gestión de Productos ---
    path('productos/', views.gestionar_productos, name='gestionar_productos'),
    path('productos/registrar/', views.registrar_producto, name='registrar_producto'),
    path('productos/editar/<str:producto_id>/', views.editar_producto, name='editar_producto'),
    path('productos/cambiar-estado/<str:producto_id>/', views.cambiar_estado_producto, name='cambiar_estado_producto'),

    # --- Emisión y Gestión de Boletas ---
    path('boletas/emitir/', views.emitir_boleta, name='emitir_boleta'),
    path('boletas/ver/<int:boleta_id>/', views.ver_boleta, name='ver_boleta'),
    path('boletas/ajax/buscar-productos/', views.buscar_productos, name='buscar_productos'),
    path('boletas/ajax/obtener-carrito/', views.obtener_carrito, name='obtener_carrito'),
    path('boletas/ajax/actualizar-carrito/', views.actualizar_carrito, name='actualizar_carrito'),
    path('boletas/ajax/procesar/', views.procesar_boleta, name='procesar_boleta'),

    # --- Notas de Crédito ---
    path('notas-credito/', views.emitir_nota_credito, name='emitir_nota_credito'),
    path('notas-credito/ver/<int:nota_credito_id>/', views.ver_nota_credito, name='ver_nota_credito'),
    path('notas-credito/seleccionar-tipo/<int:boleta_id>/', views.seleccionar_tipo_nota_credito, name='seleccionar_tipo_nota_credito'),
    path('notas-credito/devolucion-total/<int:boleta_id>/', views.devolucion_total, name='devolucion_total'),
    path('notas-credito/devolucion-parcial/<int:boleta_id>/', views.devolucion_parcial, name='devolucion_parcial'),
    path('notas-credito/ajax/buscar-boleta/', views.buscar_boleta_ajax, name='buscar_boleta_ajax'),
    path('notas-credito/ajax/confirmar/', views.confirmar_nota_credito, name='confirmar_nota_credito'),

    # --- Cierre de Caja y Reportes ---
    path('cierre-caja/', views.cierre_caja, name='cierre_caja'),
    
    # 1. Reporte de Boletas
    path('cierre-caja/reporte-boletas/', views.reporte_boletas_view, name='reporte_boletas_view'),
    path('cierre-caja/reporte-boletas/generar/', views.generar_reporte_boletas, name='generar_reporte_boletas'),
    path('cierre-caja/reporte-boletas/ver/<int:reporte_id>/', views.ver_template_reporte_boletas, name='ver_template_reporte_boletas'),

    # 2. Reporte de Caja (Arqueo)
    path('cierre-caja/reporte-caja/', views.reporte_de_caja_view, name='reporte_de_caja_view'),
    path('cierre-caja/reporte-caja/generar/', views.generar_reporte_caja, name='generar_reporte_caja'),
    path('cierre-caja/reporte-caja/ver/<int:reporte_id>/', views.ver_template_reporte_caja, name='ver_template_reporte_caja'),

    # 3. Reporte de Egresos (¡SECCIÓN CORREGIDA Y COMPLETADA!)
    path('cierre-caja/reporte-egresos/', views.gestionar_egresos, name='gestionar_egresos'), # RUTA CORREGIDA: Apunta a la vista correcta para mostrar el formulario.
    path('cierre-caja/reporte-egresos/generar/', views.generar_reporte_egresos, name='generar_reporte_egresos'), # RUTA NUEVA: Procesa el formulario.
    path('cierre-caja/reporte-egresos/ver/<int:reporte_id>/', views.ver_reporte_egresos, name='ver_reporte_egresos'), # RUTA NUEVA: Muestra el reporte generado.
    
    # 4. Reporte Final de Cierre de Caja
    path('cierre-caja/reporte-final/', views.reporte_cierre_de_caja_view, name='reporte_cierre_de_caja_view'),
    path('cierre-caja/reporte-final/confirmar/', views.confirmar_cierre_caja, name='confirmar_cierre_caja'),
    path('cierre-caja/reporte-final/ver/<int:cierre_id>/', views.ver_template_cierre_caja, name='ver_template_cierre_caja'),
    
    # --- Historial y Exportación ---
    path('historial/boletas/', views.historial_boletas_view, name='historial_boletas_view'),
    path('historial/boletas/ajax/verificar/', views.verificar_boletas_para_exportar, name='verificar_boletas_para_exportar'),
    path('historial/boletas/exportar-excel/', views.exportar_boletas_excel, name='exportar_boletas_excel'),
]