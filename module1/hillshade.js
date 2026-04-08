// hillshade.js — dual-map hillshade overlay clipped to selection box
// Exposes: window.initHillshade(map, overlay)
//   map     — the bottom Mapbox map instance
//   overlay — the #overlay div element, used to compute clip-path pixel bounds

(function () {
  'use strict';

  window.initHillshade = function (map, overlay) {
    var hsDiv = document.getElementById('map-hillshade');
    if (!hsDiv) {
      console.error('Hillshade: #map-hillshade element not found in the DOM.');
      return;
    }
    // White background blocks the basemap beneath the clipped region completely.
    hsDiv.style.backgroundColor = '#ebe0d5';

    // Second map instance — camera-synced, fully non-interactive.
    // interactive:false prevents Mapbox attaching any pointer/keyboard handlers.
    // pointer-events:none on the container div handles CSS-level passthrough.
    var hillshadeMap;
    try {
      hillshadeMap = new mapboxgl.Map({
        container:        'map-hillshade',
        style: {
          version: 8,
          sources: {},
          layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#ffffff' } }]
        },
        center:           map.getCenter(),
        zoom:             map.getZoom(),
        bearing:          map.getBearing(),
        pitch:            map.getPitch(),
        interactive:      false,
        attributionControl: false
      });
    } catch (e) {
      console.error('Hillshade: could not create hillshade map instance —', e.message);
      return;
    }

    hillshadeMap.on('load', function () {
      // Inline style has only a white background — nothing to remove.
      try {
        hillshadeMap.addSource('dem', {
          type:     'raster-dem',
          url:      'mapbox://mapbox.mapbox-terrain-dem-v1',
          tileSize: 512,
          maxzoom:  14
        });
      } catch (e) {
        console.error('Hillshade: could not add DEM source —', e.message);
        return;
      }
      try {
        hillshadeMap.addLayer({
          id:     'hillshading',
          type:   'hillshade',
          source: 'dem',
          paint: {
            'hillshade-shadow-color':           '#000000',
            'hillshade-highlight-color':        '#ffffff',
            'hillshade-accent-color':           '#808080',
            'hillshade-illumination-direction': 315,
            'hillshade-exaggeration':           0.9
          }
        });
      } catch (e) {
        console.error('Hillshade: could not add hillshade layer —', e.message);
      }
    });

    // Compute CSS clip-path inset values from the overlay div's current pixel size.
    // #overlay is always centered on screen, so:
    //   left inset  = (viewportWidth  - size) / 2
    //   top  inset  = (viewportHeight - size) / 2
    //   right inset = viewportWidth  - left - size
    //   bottom inset= viewportHeight - top  - size
    function updateClip() {
      var size   = parseFloat(overlay.style.width) || 0;
      var left   = (window.innerWidth  - size) / 2;
      var top    = (window.innerHeight - size) / 2;
      var right  = window.innerWidth  - left - size;
      var bottom = window.innerHeight - top  - size;
      hsDiv.style.clipPath =
        'inset(' + top + 'px ' + right + 'px ' + bottom + 'px ' + left + 'px)';
    }

    // Sync the hillshade map camera to the bottom map instantly (no animation).
    // This is the only thing that drives the hillshade map camera.
    function syncCamera() {
      try {
        hillshadeMap.jumpTo({
          center:  map.getCenter(),
          zoom:    map.getZoom(),
          bearing: map.getBearing(),
          pitch:   map.getPitch()
        });
      } catch (e) {
        console.error('Hillshade: camera sync failed —', e.message);
      }
      updateClip();
    }

    // Drive both camera sync and clip-path entirely from bottom map move events.
    map.on('move', syncCamera);

    // Set initial clip-path once the bottom map has loaded and updateOverlay()
    // has set overlay.style.width for the first time.
    map.on('load', updateClip);

    // In explore mode a size-button click calls updateOverlay() but does not
    // trigger a map move, so the clip-path needs an explicit nudge.
    document.querySelectorAll('.size-btn').forEach(function (btn) {
      btn.addEventListener('click', updateClip);
    });

    // Pure greyscale — no CSS filter applied.

    console.log('Hillshade: dual-map hillshade initialised.');
  };

}());
