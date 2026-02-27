# Design System - ChecadorLogincoV2

## Stack confirmado
- Tailwind CSS via CDN (cdn.tailwindcss.com)
- Alpine.js 3.x via CDN (defer)
- Font Awesome 6.4.0 via CDN
- NO framework CSS adicional (no Bootstrap)

## Paleta de colores principal
- Primario: blue-600 (#2563EB), hover: blue-700
- Fondo body: bg-gray-100
- Fondo cards/modales: bg-white
- Bordes: border-gray-200 (separadores), border-gray-300 (inputs)
- Texto principal: text-gray-900
- Texto secundario: text-gray-500, text-gray-400
- Error: text-red-500, border-red-400, bg-red-50, border-red-200
- Exito: text-green-700, bg-green-50, border-green-200
- Warning: bg-yellow-50, border-yellow-200, text-yellow-800
- Navbar: bg-blue-600 con hover bg-blue-700

## Tipografia
- Tamanos de headings: text-2xl font-bold (h1), text-xl font-bold (h1 dentro de card), text-lg font-semibold (modal header), text-base font-semibold (section header)
- Labels de form: text-sm font-medium text-gray-700
- Inputs: text-sm
- Texto de apoyo: text-xs text-gray-400 / text-gray-500

## Clases de inputs (patron estandar)
```
border border-gray-300 rounded-md px-3 py-2 text-sm
focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none
```
Con error: añadir `border-red-400`

## Clases de botones
- Primario: `bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition`
- Secundario: `bg-white hover:bg-gray-100 text-gray-700 border border-gray-300 px-4 py-2 rounded-md text-sm font-medium transition`
- Peligro: `bg-red-500 hover:bg-red-600 text-white`
- Disabled: añadir `disabled:bg-blue-400`

## Modales (patron estandar)
- Overlay: `fixed inset-0 bg-gray-600 bg-opacity-50 z-50 flex items-center justify-center p-4`
- Contenedor: `bg-white rounded-lg shadow-xl w-full max-w-lg`
- Header: `flex items-center justify-between px-6 py-4 border-b border-gray-200`
- Body: `px-6 py-5 space-y-4`
- Footer: `px-6 py-4 bg-gray-50 rounded-b-lg flex justify-end gap-3`
- Transicion entrada: `x-transition:enter="transition ease-out duration-200"` con scale-95->scale-100 + opacity-0->opacity-100
- Transicion salida: `x-transition:leave="transition ease-in duration-150"`
- Cerrar con Escape: `@keydown.escape.window="cerrarModal()"`
- Cerrar al click fuera: `@click.outside="cerrarModal()"`

## Iconografia Font Awesome 6 (categorias IT)
- Hardware: fas fa-microchip
- Software: fas fa-code
- Red: fas fa-network-wired
- Otro: fas fa-question-circle
- Laptop: fas fa-laptop
- Ticket: fas fa-ticket-alt
- Spinner loading: SVG animate-spin (no FA spinner)

## Locale y formatos
- Idioma: es-mx
- Fechas: d/m/Y (DD/MM/YYYY)
- Hora: H:i (24 horas en tablas), usar contexto para 12h
- Timezone: America/Mexico_City
