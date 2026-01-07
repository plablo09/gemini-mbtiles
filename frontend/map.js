// Initialize the map
const map = new maplibregl.Map({
    container: 'map', // The ID of the div in index.html
    // A minimal, self-contained style object. This removes the need for an external API key.
    style: {
        'version': 8,
        'sources': {
            // Our vector tile source from the local backend
            'cadastre': {
                'type': 'vector',
                'tiles': ['http://localhost:8000/tiles/{z}/{x}/{y}.pbf'],
                'minzoom': 8,
                'maxzoom': 18
            }
        },
        'layers': [
            // A simple background layer
            {
                'id': 'background',
                'type': 'background',
                'paint': {
                    'background-color': '#f0f2f5' // A light grey background
                }
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
    zoom: 10 // Starting zoom level
});

// Add zoom and rotation controls to the map.
map.addControl(new maplibregl.NavigationControl());
