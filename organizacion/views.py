from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import models

from .models import Departamento, RelacionSupervision
from .serializers import (
    DepartamentoListSerializer,
    DepartamentoDetailSerializer,
    DepartamentoCreateUpdateSerializer,
    DepartamentoOrganigramaSerializer,
    RelacionSupervisionListSerializer,
    RelacionSupervisionDetailSerializer,
    RelacionSupervisionCreateUpdateSerializer,
)


class DepartamentoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de departamentos.
    """
    queryset = Departamento.objects.all().select_related('responsable', 'departamento_padre')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return DepartamentoListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DepartamentoCreateUpdateSerializer
        elif self.action == 'organigrama':
            return DepartamentoOrganigramaSerializer
        return DepartamentoDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtrar por activo
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)

        # Filtrar solo raices (sin padre)
        solo_raiz = self.request.query_params.get('solo_raiz', None)
        if solo_raiz is not None and solo_raiz.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(departamento_padre__isnull=True)

        # Buscar
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(codigo__icontains=search) |
                models.Q(nombre__icontains=search)
            )

        return queryset

    @action(detail=False, methods=['get'])
    def organigrama(self, request):
        """Retorna la estructura del organigrama"""
        raices = Departamento.objects.filter(
            departamento_padre__isnull=True,
            activo=True
        ).select_related('responsable')
        serializer = DepartamentoOrganigramaSerializer(raices, many=True)
        return Response(serializer.data)


class RelacionSupervisionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de relaciones de supervision.
    """
    queryset = RelacionSupervision.objects.all().select_related('supervisor', 'subordinado')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return RelacionSupervisionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RelacionSupervisionCreateUpdateSerializer
        return RelacionSupervisionDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtrar por supervisor
        supervisor = self.request.query_params.get('supervisor', None)
        if supervisor:
            queryset = queryset.filter(supervisor_id=supervisor)

        # Filtrar por subordinado
        subordinado = self.request.query_params.get('subordinado', None)
        if subordinado:
            queryset = queryset.filter(subordinado_id=subordinado)

        # Filtrar por tipo
        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo_relacion=tipo)

        # Filtrar solo activos
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)

        return queryset


# ===== VISTAS WEB =====

@login_required
def organigrama_view(request):
    """Vista para el organigrama organizacional"""
    departamentos_raiz = Departamento.objects.filter(
        departamento_padre__isnull=True,
        activo=True
    ).select_related('responsable').prefetch_related('subdepartamentos')

    return render(request, 'organizacion/organigrama.html', {
        'departamentos': departamentos_raiz
    })
