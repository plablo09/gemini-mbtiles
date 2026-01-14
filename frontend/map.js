// Version control for tile caching. Bump this when backend data schema changes.
const TILE_VERSION = 'v1.2';

// --- Color Palettes (ColorBrewer Safe) ---

// Land Use: Using ColorBrewer 'Set2' (Qualitative, Color-blind safe)
const LAND_USE_COLORS = [
    'match',
    ['get', 'uso_suelo'],
    'Habitacional', '#66c2a5',
    'Comercio', '#fc8d62',
    'Industrial', '#8da0cb',
    'Otros Usos', '#e78ac3',
    /* fallback (S/N) */ '#b3b3b3'
];

// Alcaldia: Using ColorBrewer 'Paired' (12 colors) extended with 'Dark2' (4 colors)
// to cover all 16 boroughs safely.
const ALCALDIA_COLORS = [
    'match',
    ['get', 'alcaldia'],
    'ALVARO OBREGON', '#a6cee3',
    'AZCAPOTZALCO', '#1f78b4',
    'BENITO JUAREZ', '#b2df8a',
    'COYOACAN', '#33a02c',
    'CUAJIMALPA DE MORELOS', '#fb9a99',
    'CUAUHTEMOC', '#e31a1c',
    'GUSTAVO A. MADERO', '#fdbf6f',
    'IZTACALCO', '#ff7f00',
    'IZTAPALAPA', '#cab2d6',
    'MAGDALENA CONTRERAS', '#6a3d9a',
    'MIGUEL HIDALGO', '#ffff99',
    'MILPA ALTA', '#b15928',
    'TLAHUAC', '#1b9e77', // Extended from Dark2
    'TLALPAN', '#d95f02', // Extended from Dark2
    'VENUSTIANO CARRANZA', '#7570b3', // Extended from Dark2
    'XOCHIMILCO', '#e7298a', // Extended from Dark2
    /* fallback */ '#cccccc'
];

// Legend Data Definition
const LEGENDS = {
    'uso_suelo': {
        title: 'Land Use',
        items: [
            { label: 'Habitacional', color: '#66c2a5' },
            { label: 'Comercio', color: '#fc8d62' },
            { label: 'Industrial', color: '#8da0cb' },
            { label: 'Otros Usos', color: '#e78ac3' },
            { label: 'S/N', color: '#b3b3b3' }
        ]
    },
    'alcaldia': {
        title: 'Borough',
        items: [
            { label: 'Alvaro Obregon', color: '#a6cee3' },
            { label: 'Azcapotzalco', color: '#1f78b4' },
            { label: 'Benito Juarez', color: '#b2df8a' },
            { label: 'Coyoacan', color: '#33a02c' },
            { label: 'Cuajimalpa', color: '#fb9a99' },
            { label: 'Cuauhtemoc', color: '#e31a1c' },
            { label: 'Gustavo A. Madero', color: '#fdbf6f' },
            { label: 'Iztacalco', color: '#ff7f00' },
            { label: 'Iztapalapa', color: '#cab2d6' },
            { label: 'Magdalena Contreras', color: '#6a3d9a' },
            { label: 'Miguel Hidalgo', color: '#ffff99' },
            { label: 'Milpa Alta', color: '#b15928' },
            { label: 'Tlahuac', color: '#1b9e77' },
            { label: 'Tlalpan', color: '#d95f02' },
            { label: 'Venustiano Carranza', color: '#7570b3' },
            { label: 'Xochimilco', color: '#e7298a' }
        ]
    }
};

// --- Map Initialization ---

const map = new maplibregl.Map({
    container: 'map',
    style: {
        'version': 8,
        'sources': {
            'osm': {
                'type': 'raster',
                'tiles': [
                    'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
                    'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
                    'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png'
                ],
                'tileSize': 256,
                'attribution': '&copy; OpenStreetMap Contributors',
                'maxzoom': 19
            },
            'cadastre': {
                'type': 'vector',
                'tiles': [window.location.origin + `/tiles/{z}/{x}/{y}.pbf?v=${TILE_VERSION}`],
                'minzoom': 14,
                'maxzoom': 18
            }
        },
        'layers': [
            {
                'id': 'osm',
                'type': 'raster',
                'source': 'osm',
                'paint': {}
            },
            {
                'id': 'cadastre-lots-fill',
                'type': 'fill',
                'source': 'cadastre',
                'source-layer': 'cadastre_layer',
                'layout': {},
                'paint': {
                    'fill-color': LAND_USE_COLORS, // Default
                    'fill-opacity': 0.6
                }
            },
            {
                'id': 'cadastre-lots-outline',
                'type': 'line',
                'source': 'cadastre',
                'source-layer': 'cadastre_layer',
                'layout': {},
                'paint': {
                    'line-color': '#003',
                    'line-width': 0.5,
                    'line-opacity': 0.3
                }
            },
            {
                'id': 'cadastre-lots-extrusion',
                'type': 'fill-extrusion',
                'source': 'cadastre',
                'source-layer': 'cadastre_layer',
                'paint': {
                    'fill-extrusion-color': LAND_USE_COLORS, // Default
                    'fill-extrusion-height': ['*', ['coalesce', ['get', 'no_niveles'], 1], 3.5],
                    'fill-extrusion-base': 0,
                    'fill-extrusion-opacity': 0.8
                },
                'layout': {
                    'visibility': 'none'
                }
            }
        ]
    },
    center: [-99.1332, 19.4326],
    zoom: 14
});

map.addControl(new maplibregl.NavigationControl());

// --- UI Logic ---

const zoomDisplay = document.getElementById('zoom-value');
function updateZoom() {
    zoomDisplay.innerText = map.getZoom().toFixed(2);
}

// Legend Updater
function updateLegend(mode) {
    const legendContainer = document.getElementById('legend');
    const data = LEGENDS[mode];
    
    let html = `<h4>${data.title}</h4>`;
    data.items.forEach(item => {
        html += `<div><span style="background-color: ${item.color}"></span>${item.label}</div>`;
    });
    
    legendContainer.innerHTML = html;
}

// Initialize Legend
updateLegend('uso_suelo');

map.on('load', updateZoom);
map.on('move', updateZoom);

// View Toggle (2D/3D)
let is3D = false;
const toggleBtn = document.getElementById('view-toggle');

toggleBtn.addEventListener('click', () => {
    is3D = !is3D;
    
    if (is3D) {
        map.easeTo({ pitch: 60, bearing: -20, duration: 1000 });
        map.setLayoutProperty('cadastre-lots-extrusion', 'visibility', 'visible');
        map.setLayoutProperty('cadastre-lots-fill', 'visibility', 'none');
        map.setLayoutProperty('cadastre-lots-outline', 'visibility', 'none');
        toggleBtn.innerText = 'Switch to 2D';
    } else {
        map.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
        map.setLayoutProperty('cadastre-lots-extrusion', 'visibility', 'none');
        map.setLayoutProperty('cadastre-lots-fill', 'visibility', 'visible');
        map.setLayoutProperty('cadastre-lots-outline', 'visibility', 'visible');
        toggleBtn.innerText = 'Switch to 3D';
    }
});

// Coloring Mode Selector
const coloringSelect = document.getElementById('coloring-mode');

coloringSelect.addEventListener('change', (e) => {
    const mode = e.target.value;
    let colorExpression;
    
    if (mode === 'uso_suelo') {
        colorExpression = LAND_USE_COLORS;
    } else if (mode === 'alcaldia') {
        colorExpression = ALCALDIA_COLORS;
    }
    
    // Update both 2D and 3D layers
    map.setPaintProperty('cadastre-lots-fill', 'fill-color', colorExpression);
    map.setPaintProperty('cadastre-lots-extrusion', 'fill-extrusion-color', colorExpression);
    
    // Update Legend
    updateLegend(mode);
});
