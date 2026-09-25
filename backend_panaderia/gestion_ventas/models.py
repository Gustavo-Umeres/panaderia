from django.db import models
from django.utils import timezone

class Usuario(models.Model):
    ESTADO_CHOICES = [
        (0, 'Inactivo'),
        (1, 'Activo'),
    ]
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    dni = models.IntegerField(unique=True)
    contrasena_hash = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    estado = models.IntegerField(choices=ESTADO_CHOICES, default=1)
    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Privilegio(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class UsuarioPrivilegio(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    privilegio = models.ForeignKey(Privilegio, on_delete=models.CASCADE)

    class Meta:
        # Define la clave primaria compuesta
        unique_together = (('usuario', 'privilegio'),)
        verbose_name = "Usuario Privilegio"
        verbose_name_plural = "Usuarios Privilegios"

    def __str__(self):
        return f"Usuario: {self.usuario.nombre}, Privilegio: {self.privilegio.nombre}"

class PreguntaSeguridad(models.Model):
    id = models.AutoField(primary_key=True)
    pregunta = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.pregunta

class UsuarioPreguntaRespuesta(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(PreguntaSeguridad, on_delete=models.CASCADE)
    respuesta_hash = models.CharField(max_length=255)

    class Meta:
        # Define la clave primaria compuesta
        unique_together = (('usuario', 'pregunta'),)
        verbose_name = "Usuario Pregunta Respuesta"
        verbose_name_plural = "Usuarios Preguntas Respuestas"

    def __str__(self):
        return f"Usuario: {self.usuario.nombre}, Pregunta: {self.pregunta.pregunta[:30]}..."

class Boleta(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_emision = models.DateField()
    hora_emision = models.TimeField()
    metodo_pago = models.CharField(max_length=50)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    estado = models.IntegerField(default=1) 

    def __str__(self):
        return f"Boleta #{self.id} - {self.fecha_emision}"

class Categoria(models.Model):
    id = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nombre_categoria

class Producto(models.Model):
    ESTADO_CHOICES = [
        (0, 'Inactivo'),
        (1, 'Activo'),
    ]
    codigo_producto = models.CharField(primary_key=True, max_length=10) # Ej: P001, A001
    nombre_producto = models.CharField(max_length=255)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_CHOICES, default=1)
    def __str__(self):
        return self.nombre_producto

class DetalleBoleta(models.Model):
    id_boleta = models.ForeignKey(Boleta, on_delete=models.CASCADE)
    codigo_producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario_venta = models.DecimalField(max_digits=10, decimal_places=2)
    monto_parcial = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        # Define la clave primaria compuesta
        unique_together = (('id_boleta', 'codigo_producto'),)
        verbose_name = "Detalle de Boleta"
        verbose_name_plural = "Detalles de Boleta"

    def __str__(self):
        return f"Detalle Boleta #{self.id_boleta.id} - Producto: {self.codigo_producto.nombre_producto}"

class ReporteBoletas(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    hora_registro = models.TimeField(blank=True, null=True) # Puedes usar auto_now_add para esto
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE, blank=True, null=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Reporte Boletas #{self.id} - {self.fecha_registro.date()}"

class ReporteCaja(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    hora_registro = models.TimeField(blank=True, null=True)
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE, blank=True, null=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Reporte Caja #{self.id} - {self.fecha_registro.date()}"

class ReporteEgresos(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_registro = models.DateField(default=timezone.now)
    hora_registro = models.TimeField()
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    total_gastos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_nota_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_reporte_egresos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Reporte de Egresos #{self.id} del {self.fecha_registro}"

class ReporteCierreCaja(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_registro = models.DateField(default=timezone.now)
    hora_registro = models.TimeField()
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    descuadre = models.DecimalField(max_digits=10, decimal_places=2)
    razon = models.TextField(blank=True, null=True)
    reporte_boletas = models.ForeignKey(ReporteBoletas, on_delete=models.CASCADE)
    reporte_caja = models.ForeignKey(ReporteCaja, on_delete=models.CASCADE)
    reporte_egresos = models.ForeignKey(ReporteEgresos, on_delete=models.CASCADE)

    def __str__(self):
        return f"Cierre de Caja #{self.id} - {self.fecha_registro}"

class NotaCredito(models.Model):
    id = models.AutoField(primary_key=True)
    fecha_emision = models.DateField(auto_now_add=True) # Automatically sets date on creation
    hora_emision = models.TimeField(auto_now_add=True)  # Automatically sets time on creation
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE, blank=True, null=True)
    boleta = models.ForeignKey(Boleta, on_delete=models.CASCADE, blank=True, null=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    detalles = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Nota Crédito #{self.id} - Monto: {self.monto_total}"

class DetalleNotaCredito(models.Model):
    nota_credito = models.ForeignKey(NotaCredito, on_delete=models.CASCADE, related_name='detalles_de_nota')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, blank=True, null=True)
    cantidad_devuelta = models.IntegerField(blank=True, null=True)
    monto_devuelto = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Detalle NC #{self.nota_credito.id} - Prod: {self.producto.nombre_producto[:20]}"

class Denominacion(models.Model):
    id = models.AutoField(primary_key=True)
    denominacion = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.denominacion}"

class DetalleReporteCaja(models.Model):
    # Aquí el PK es 'reporte_id' en tu esquema, pero en Django es mejor tener una PK propia
    # y FKs a los modelos relacionados. Si necesitas la combinación como PK, usa unique_together.
    # Por la descripción, parece que reporte_id sería una FK y luego un PK compuesto.
    # Si 'reporte_id' es el PK en tu esquema, entonces solo debería haber un DetalleReporteCaja por ReporteCaja.
    # Revisé tu DDL y dice "reporte_id" INT [pk, increment], lo que es inusual para una PK con un nombre de FK.
    # Asumo que es una PK normal y que 'denominación_id' es otra columna.
    id = models.AutoField(primary_key=True) # Django crea este por defecto si no pones uno
    reporte = models.ForeignKey(ReporteCaja, on_delete=models.CASCADE)
    denominacion = models.ForeignKey(Denominacion, on_delete=models.CASCADE, db_column='denominación_id') # Usar db_column para el nombre exacto
    cantidad = models.IntegerField(blank=True, null=True)
    monto_parcial = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = "Detalle Reporte Caja"
        verbose_name_plural = "Detalles Reportes Caja"

    def __str__(self):
        return f"Detalle Reporte Caja #{self.reporte.id} - Denom: {self.denominacion.denominacion}"

class DetalleReporteBoleta(models.Model):
    id = models.AutoField(primary_key=True) # Django crea este por defecto
    reporte = models.ForeignKey(ReporteBoletas, on_delete=models.CASCADE)
    boleta = models.ForeignKey(Boleta, on_delete=models.CASCADE)
    monto_parcial = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = "Detalle Reporte Boleta"
        verbose_name_plural = "Detalles Reportes Boleta"

    def __str__(self):
        return f"Detalle Reporte Boleta #{self.reporte.id} - Boleta: {self.boleta.id}"
