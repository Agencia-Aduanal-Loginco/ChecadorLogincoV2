# Patrones Alpine.js + Tailwind confirmados en el proyecto

## Patron: componente Alpine en pagina
```html
<div x-data="nombreComponente()" x-init="init()">
  ...
</div>
```
Con funcion JS al final en `{% block extra_js %}`.

## Patron: mostrar/ocultar con transicion
```html
<div x-show="condicion"
     x-transition:enter="transition ease-out duration-200"
     x-transition:enter-start="opacity-0"
     x-transition:enter-end="opacity-100"
     x-transition:leave="transition ease-in duration-150"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0">
```

## Patron: binding de clases condicionales
```html
:class="{ 'border-red-400': errores.campo }"
```

## Patron: spinner de carga
```html
<svg x-show="cargando" class="animate-spin h-4 w-4" ...>
  <circle class="opacity-25" ...></circle>
  <path class="opacity-75" fill="currentColor" ...></path>
</svg>
<span x-text="cargando ? 'Enviando...' : 'Crear Ticket'"></span>
```

## Patron: fetch con CSRF
```js
const csrfToken = this.getCookie('csrftoken');
await fetch('/api/.../', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
  body: JSON.stringify(payload),
});
```

## Patron: manejo de errores del serializer DRF
```js
if (data.campo) this.errores.campo = Array.isArray(data.campo) ? data.campo[0] : data.campo;
if (data.detail || data.non_field_errors) { this.errorGeneral = ... }
```

## Patron: formularios dinamicos con JS vanilla (template permisos)
- El proyecto usa tanto Alpine.js (tickets) como JS vanilla (permisos)
- Para nuevos componentes interactivos: preferir Alpine.js por consistencia con tickets

## Notas de accesibilidad sistemicas
- Los labels de form usan `for` correctamente en la mayoria de vistas
- Faltan `aria-describedby` en campos con mensajes de error
- Faltan `role="alert"` en mensajes de error inline
- El boton cerrar modal no tiene `aria-label` descriptivo
- Falta `aria-live` en zonas que cambian dinamicamente (errores, exito)
