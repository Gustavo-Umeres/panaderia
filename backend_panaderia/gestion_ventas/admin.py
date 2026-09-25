# gestion_ventas/admin.py

from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django.forms import ModelForm, CharField, PasswordInput, ValidationError

# Asegúrate de que los modelos importados coincidan con los de models.py
from .models import (
    Usuario, Privilegio, UsuarioPrivilegio,
    PreguntaSeguridad, UsuarioPreguntaRespuesta,
    Boleta, Categoria, Producto, DetalleBoleta,
    ReporteBoletas, ReporteCaja, ReporteEgresos, ReporteCierreCaja,
    NotaCredito, DetalleNotaCredito, Denominacion, DetalleReporteCaja,
    DetalleReporteBoleta
)

# ... (El código de UsuarioPreguntaRespuestaForm se mantiene igual, es correcto)
class UsuarioPreguntaRespuestaForm(ModelForm):
    respuesta_en_claro = CharField(label="Respuesta de Seguridad", widget=PasswordInput(render_value=False), required=False, help_text="Dejar en blanco para no cambiar.")
    class Meta:
        model = UsuarioPreguntaRespuesta
        fields = ('usuario', 'pregunta', 'respuesta_en_claro')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance or not self.instance.pk: self.fields['respuesta_en_claro'].required = True
    def save(self, commit=True):
        instance = super().save(commit=False)
        respuesta = self.cleaned_data.get('respuesta_en_claro')
        if respuesta: instance.respuesta_hash = make_password(respuesta)
        if commit: instance.save()
        return instance

# --- DEFINICIÓN DE INLINES ---
class UsuarioPrivilegioInline(admin.TabularInline): model = UsuarioPrivilegio; extra = 1
class UsuarioPreguntaRespuestaInline(admin.StackedInline): model = UsuarioPreguntaRespuesta; form = UsuarioPreguntaRespuestaForm; extra = 1
class DetalleBoletaInline(admin.TabularInline): model = DetalleBoleta; extra = 0; readonly_fields = ('precio_unitario_venta', 'monto_parcial')
class DetalleNotaCreditoInline(admin.TabularInline): model = DetalleNotaCredito; extra = 0
class DetalleReporteCajaInline(admin.TabularInline): model = DetalleReporteCaja; extra = 0; readonly_fields = ('denominacion', 'cantidad', 'monto_parcial')
class DetalleReporteBoletaInline(admin.TabularInline): model = DetalleReporteBoleta; extra = 0; readonly_fields = ('boleta', 'monto_parcial')

# --- CLASES DE ADMINISTRACIÓN PERSONALIZADAS ---
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username', 'nombre', 'apellido', 'dni', 'estado')
    inlines = [UsuarioPrivilegioInline, UsuarioPreguntaRespuestaInline]
    # ... (El resto de la clase UsuarioAdmin que ya tienes es correcto) ...

@admin.register(Boleta)
class BoletaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_emision', 'empleado', 'monto_total', 'estado')
    readonly_fields = ('id', 'fecha_emision', 'hora_emision', 'empleado', 'monto_total', 'metodo_pago')
    inlines = [DetalleBoletaInline]

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo_producto', 'nombre_producto', 'categoria', 'precio_unitario', 'stock', 'estado')
    list_editable = ('nombre_producto', 'precio_unitario', 'stock', 'estado')
    
@admin.register(ReporteBoletas)
class ReporteBoletasAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_registro', 'empleado', 'monto_total')
    readonly_fields = ('fecha_registro', 'empleado', 'monto_total')
    inlines = [DetalleReporteBoletaInline] 

@admin.register(ReporteCierreCaja)
class ReporteCierreCajaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_registro', 'empleado', 'descuadre')
    readonly_fields = ('fecha_registro', 'hora_registro', 'empleado', 'descuadre', 'razon',
                       'reporte_boletas', 'reporte_caja', 'reporte_egresos')
    # No se necesita ningún inline aquí en la versión simple

# --- REGISTRO DEL RESTO DE MODELOS ---
admin.site.register(Categoria)
admin.site.register(Privilegio)
admin.site.register(PreguntaSeguridad)
admin.site.register(ReporteCaja)
admin.site.register(ReporteEgresos)
admin.site.register(NotaCredito)
admin.site.register(Denominacion)