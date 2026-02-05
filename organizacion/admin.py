from django.contrib import admin
from .models import Departamento, RelacionSupervision


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'departamento_padre', 'responsable', 'activo')
    list_filter = ('activo', 'departamento_padre')
    search_fields = ('codigo', 'nombre', 'descripcion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    autocomplete_fields = ['responsable', 'departamento_padre']

    fieldsets = (
        ('Informacion General', {
            'fields': ('codigo', 'nombre', 'descripcion')
        }),
        ('Jerarquia', {
            'fields': ('departamento_padre', 'responsable')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )


@admin.register(RelacionSupervision)
class RelacionSupervisionAdmin(admin.ModelAdmin):
    list_display = ('supervisor', 'subordinado', 'tipo_relacion', 'puede_autorizar_permisos', 'activo', 'esta_vigente')
    list_filter = ('tipo_relacion', 'puede_autorizar_permisos', 'activo')
    search_fields = ('supervisor__user__username', 'subordinado__user__username')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    autocomplete_fields = ['supervisor', 'subordinado']

    fieldsets = (
        ('Relacion', {
            'fields': ('supervisor', 'subordinado', 'tipo_relacion')
        }),
        ('Permisos', {
            'fields': ('puede_autorizar_permisos',)
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio', 'fecha_fin', 'activo')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        }),
    )

    def esta_vigente(self, obj):
        return obj.esta_vigente()
    esta_vigente.boolean = True
    esta_vigente.short_description = 'Vigente'
