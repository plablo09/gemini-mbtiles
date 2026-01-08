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
                'tiles': ['/tiles/{z}/{x}/{y}.pbf'],
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
                    'fill-color': '#088',
                    'fill-opacity': 0.4
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
                    'line-width': 0.5
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
