// Version control for tile caching. Bump this when backend data schema changes.
const TILE_VERSION = 'v1.1';

// Land use color palette
const LAND_USE_COLORS = [
    'match',
    ['get', 'uso_suelo'],
    'Habitacional', '#f39c12',
    'Comercio', '#c0392b',
    'Industrial', '#a020f0',
    'Otros Usos', '#3bb2d0',
    /* fallback */ '#cccccc'
];

// Initialize the map
const map = new maplibregl.Map({
    container: 'map', // The ID of the div in index.html
    // A minimal, self-contained style object. This removes the need for an external API key.
    style: {
        'version': 8,
        'sources': {
            // OpenStreetMap Raster Tiles
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
            // Our vector tile source from the local backend
            'cadastre': {
                'type': 'vector',
                'tiles': [window.location.origin + `/tiles/{z}/{x}/{y}.pbf?v=${TILE_VERSION}`],
                'minzoom': 14, // Only show parcels from Z14 onwards
                'maxzoom': 18
            }
        },
        'layers': [
            // OSM Background
            {
                'id': 'osm',
                'type': 'raster',
                'source': 'osm',
                'paint': {}
            },
            // Our layer to display the cadastral lots fill
            {
                'id': 'cadastre-lots-fill',
                'type': 'fill',
                'source': 'cadastre',
                'source-layer': 'cadastre_layer', // Must match the name in the backend
                'layout': {},
                'paint': {
                    'fill-color': LAND_USE_COLORS,
                    'fill-opacity': 0.6
                }
            },
            // A separate layer for the outline
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
            // 3D Extrusion layer (initially hidden/invisible)
            {
                'id': 'cadastre-lots-extrusion',
                'type': 'fill-extrusion',
                'source': 'cadastre',
                'source-layer': 'cadastre_layer',
                'paint': {
                    'fill-extrusion-color': LAND_USE_COLORS,
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
    center: [-99.1332, 19.4326], // Starting position [lng, lat] for Mexico City
    zoom: 14 // Starting zoom level (closer in)
});

// Add zoom and rotation controls to the map.
map.addControl(new maplibregl.NavigationControl());

// Update zoom level display
const zoomDisplay = document.getElementById('zoom-value');
function updateZoom() {
    zoomDisplay.innerText = map.getZoom().toFixed(2);
}

map.on('load', updateZoom);
map.on('move', updateZoom);

// View Toggle Logic
let is3D = false;
const toggleBtn = document.getElementById('view-toggle');

toggleBtn.addEventListener('click', () => {
    is3D = !is3D;
    
    if (is3D) {
        // Switch to 3D
        map.easeTo({
            pitch: 60,
            bearing: -20,
            duration: 1000
        });
        
        map.setLayoutProperty('cadastre-lots-extrusion', 'visibility', 'visible');
        map.setLayoutProperty('cadastre-lots-fill', 'visibility', 'none');
        map.setLayoutProperty('cadastre-lots-outline', 'visibility', 'none');
        
        toggleBtn.innerText = 'Switch to 2D';
    } else {
        // Switch to 2D
        map.easeTo({
            pitch: 0,
            bearing: 0,
            duration: 1000
        });
        
        map.setLayoutProperty('cadastre-lots-extrusion', 'visibility', 'none');
        map.setLayoutProperty('cadastre-lots-fill', 'visibility', 'visible');
        map.setLayoutProperty('cadastre-lots-outline', 'visibility', 'visible');
        
        toggleBtn.innerText = 'Switch to 3D';
    }
});
