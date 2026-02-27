"""
Migración inicial de it_tickets.

Crea las tablas:
  - it_tickets_equipocomputo
  - it_tickets_ticket
  - it_tickets_historialticket
  - it_tickets_mantenimientoequipo

Y también crea el grupo 'IT' en auth_group si no existe,
usando una data migration integrada al final.
"""
from django.db import migrations, models
import django.db.models.deletion


def crear_grupo_it(apps, schema_editor):
    """
    Crea el grupo 'IT' en auth_group si no existe.
    Este grupo se usa para controlar el acceso a la gestión de tickets.
    Agrega los usuarios al grupo desde el admin de Django.
    """
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='IT')


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('empleados', '0004_empleado_descansa_domingo_empleado_descansa_sabado_and_more'),
    ]

    operations = [
        # --- EquipoComputo ---
        migrations.CreateModel(
            name='EquipoComputo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usuario_nombre', models.CharField(help_text='Nombre del usuario o descripción (ej: Tramitadores, Auxiliar)', max_length=100, verbose_name='Nombre de Usuario / Descripción')),
                ('tipo', models.CharField(choices=[('desktop', 'Desktop'), ('laptop', 'Laptop'), ('servidor', 'Servidor'), ('impresora', 'Impresora'), ('tablet', 'Tablet'), ('otro', 'Otro')], default='desktop', max_length=20, verbose_name='Tipo de Equipo')),
                ('numero_serie', models.CharField(max_length=100, unique=True, verbose_name='Número de Serie')),
                ('marca', models.CharField(max_length=100, verbose_name='Marca')),
                ('modelo', models.CharField(max_length=100, verbose_name='Modelo')),
                ('tiene_monitor', models.BooleanField(default=False, verbose_name='Tiene Monitor')),
                ('marca_monitor', models.CharField(blank=True, max_length=100, verbose_name='Marca del Monitor')),
                ('telefono_serie', models.CharField(blank=True, max_length=100, verbose_name='Serie del Teléfono')),
                ('mac_telefono', models.CharField(blank=True, max_length=50, verbose_name='MAC del Teléfono')),
                ('estado', models.CharField(choices=[('activo', 'Activo'), ('mantenimiento', 'En Mantenimiento'), ('baja', 'De Baja')], default='activo', max_length=20, verbose_name='Estado')),
                ('fecha_ultimo_mantenimiento', models.DateField(blank=True, null=True, verbose_name='Último Mantenimiento')),
                ('fecha_proximo_mantenimiento', models.DateField(blank=True, db_index=True, null=True, verbose_name='Próximo Mantenimiento')),
                ('notas', models.TextField(blank=True, verbose_name='Notas')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('empleado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipos_asignados', to='empleados.empleado', verbose_name='Empleado Asignado')),
            ],
            options={
                'verbose_name': 'Equipo de Cómputo',
                'verbose_name_plural': 'Equipos de Cómputo',
                'ordering': ['marca', 'modelo', 'numero_serie'],
            },
        ),
        migrations.AddIndex(
            model_name='equipocomputo',
            index=models.Index(fields=['estado'], name='idx_equipo_estado'),
        ),
        migrations.AddIndex(
            model_name='equipocomputo',
            index=models.Index(fields=['empleado', 'estado'], name='idx_equipo_empleado_estado'),
        ),

        # --- Ticket ---
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folio', models.CharField(editable=False, max_length=20, unique=True, verbose_name='Folio')),
                ('titulo', models.CharField(max_length=200, verbose_name='Título')),
                ('descripcion', models.TextField(verbose_name='Descripción del Problema')),
                ('categoria', models.CharField(choices=[('hardware', 'Hardware'), ('software', 'Software'), ('red', 'Red / Conectividad'), ('otro', 'Otro')], db_index=True, default='otro', max_length=20, verbose_name='Categoría')),
                ('prioridad', models.CharField(blank=True, choices=[('critica', 'Critica'), ('alta', 'Alta'), ('media', 'Media'), ('baja', 'Baja')], db_index=True, max_length=10, null=True, verbose_name='Prioridad')),
                ('estado', models.CharField(choices=[('creado', 'Creado'), ('pendiente', 'Pendiente'), ('proceso', 'En Proceso'), ('espera', 'En Espera'), ('concluido', 'Concluido')], db_index=True, default='creado', max_length=15, verbose_name='Estado')),
                ('motivo_espera', models.TextField(blank=True, help_text='Especificar qué se espera: piezas, proveedor, equipo de reemplazo, etc.', verbose_name='Motivo de Espera')),
                ('solucion', models.TextField(blank=True, verbose_name='Descripción de la Solución')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('fecha_resolucion', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Resolución')),
                ('asignado_a', models.ForeignKey(blank=True, limit_choices_to={'groups__name': 'IT'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets_asignados', to='auth.user', verbose_name='Asignado a (IT)')),
                ('empleado', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tickets', to='empleados.empleado', verbose_name='Empleado que Reporta')),
                ('equipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets', to='it_tickets.equipocomputo', verbose_name='Equipo Relacionado')),
            ],
            options={
                'verbose_name': 'Ticket de Soporte IT',
                'verbose_name_plural': 'Tickets de Soporte IT',
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['estado', 'prioridad'], name='idx_ticket_estado_prioridad'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['empleado', 'estado'], name='idx_ticket_empleado_estado'),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['fecha_creacion'], name='idx_ticket_fecha_creacion'),
        ),

        # --- HistorialTicket ---
        migrations.CreateModel(
            name='HistorialTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado_anterior', models.CharField(choices=[('creado', 'Creado'), ('pendiente', 'Pendiente'), ('proceso', 'En Proceso'), ('espera', 'En Espera'), ('concluido', 'Concluido')], max_length=15, verbose_name='Estado Anterior')),
                ('estado_nuevo', models.CharField(choices=[('creado', 'Creado'), ('pendiente', 'Pendiente'), ('proceso', 'En Proceso'), ('espera', 'En Espera'), ('concluido', 'Concluido')], max_length=15, verbose_name='Estado Nuevo')),
                ('comentario', models.TextField(blank=True, verbose_name='Comentario')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historial', to='it_tickets.ticket', verbose_name='Ticket')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user', verbose_name='Usuario que Cambió el Estado')),
            ],
            options={
                'verbose_name': 'Historial de Ticket',
                'verbose_name_plural': 'Historial de Tickets',
                'ordering': ['-fecha'],
            },
        ),

        # --- MantenimientoEquipo ---
        migrations.CreateModel(
            name='MantenimientoEquipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_mantenimiento', models.CharField(choices=[('preventivo', 'Preventivo'), ('correctivo', 'Correctivo')], default='preventivo', max_length=15, verbose_name='Tipo de Mantenimiento')),
                ('descripcion', models.TextField(verbose_name='Descripción del Mantenimiento')),
                ('fecha_realizado', models.DateField(verbose_name='Fecha Realizado')),
                ('fecha_proximo', models.DateField(blank=True, null=True, verbose_name='Fecha del Próximo Mantenimiento')),
                ('tecnico', models.CharField(max_length=150, verbose_name='Técnico Responsable')),
                ('costo', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Costo (MXN)')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mantenimientos', to='it_tickets.equipocomputo', verbose_name='Equipo')),
                ('registrado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user', verbose_name='Registrado Por')),
            ],
            options={
                'verbose_name': 'Mantenimiento de Equipo',
                'verbose_name_plural': 'Mantenimientos de Equipo',
                'ordering': ['-fecha_realizado'],
            },
        ),

        # --- Data migration: crear grupo IT ---
        migrations.RunPython(
            crear_grupo_it,
            migrations.RunPython.noop,
        ),
    ]
