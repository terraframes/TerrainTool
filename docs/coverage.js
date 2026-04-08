// coverage.js — Coverage polygon system for high-resolution datasets
// Exposes:
//   window.initCoverage(map, highResKmSizes)      — call once after map loads
//   window.getDatasetForCurrentSelection()         — returns dataset string for current selection
//   window.onSizeChanged(map, highResKmSizes)      — call from size button click handler

(function () {
  'use strict';

  // The currently active dataset, updated on every map move.
  // Defaults to GLO-30 until coverage polygons are loaded and a match is found.
  window._currentDataset = 'GLO-30';

  // True when the active size requires high-res coverage that isn't available here.
  // selection.js reads this; the confirm button is disabled by _applyInvalidState().
  window._selectionInvalid = false;

  // Array of { dataset: string, geojson: GeoJSON Feature } objects.
  // Populated once faroe_islands_coverage.geojson (and any future files) are loaded.
  window._coveragePolygons = [];

  var _highResKmSizes = [];

  // Returns the dataset string appropriate for the current map center + selected size.
  window.getDatasetForCurrentSelection = function () {
    return window._currentDataset || 'GLO-30';
  };

  // onSizeChanged — call from widget.html size button click handler.
  // Size button clicks don't trigger a map move event, so we need a separate hook.
  window.onSizeChanged = function (map, highResKmSizes) {
    _updateSizeButtons(map, highResKmSizes);
  };

  // initCoverage — call once on page load.
  //   map            — the Mapbox GL map instance
  //   highResKmSizes — array of size strings that require coverage, e.g. ['5', '10']
  window.initCoverage = function (map, highResKmSizes) {
    _highResKmSizes = highResKmSizes;
  // Grey out high-res buttons immediately on load — they stay grey until
  // coverage polygons confirm the centre point is inside a covered area.
    highResKmSizes.forEach(function(km) {
    var btn = document.querySelector('.size-btn[data-km="' + km + '"]');
    if (btn) btn.disabled = true;
});

    // Fetch the Faroe Islands coverage GeoJSON relative to this page.
    fetch('faroe_islands_coverage.geojson')
      .then(function (res) {
        if (!res.ok) {
          throw new Error('HTTP ' + res.status + ' fetching faroe_islands_coverage.geojson');
        }
        return res.json();
      })
      .then(function (geojson) {
        // Store the loaded feature. The GeoJSON may be a FeatureCollection or a single Feature.
        // Turf works with individual Features, so unwrap FeatureCollections.
        var features = [];
        if (geojson.type === 'FeatureCollection') {
          features = geojson.features;
        } else if (geojson.type === 'Feature') {
          features = [geojson];
        } else {
          // Plain geometry — wrap it
          features = [{ type: 'Feature', geometry: geojson, properties: {} }];
        }

        features.forEach(function (feature) {
          window._coveragePolygons.push({ dataset: 'FO-DEM', geojson: feature });
        });

        console.log('Coverage: loaded ' + window._coveragePolygons.length +
                    ' polygon(s) for FO-DEM');

        // Run an immediate check so the UI reflects the starting position.
        _updateSizeButtons(map, highResKmSizes);
      })
      .catch(function (err) {
        // GeoJSON failed to load — high-res sizes are permanently unavailable.
        console.error('Coverage: failed to load faroe_islands_coverage.geojson —', err.message);
        console.error('Coverage: 5 km and 10 km will be marked invalid if selected.');

        // If the user already has a high-res size active, show the invalid state.
        // Otherwise clear it so non-high-res sizes work normally.
        var activeBtn = document.querySelector('.size-btn.active');
        var activeKm = activeBtn ? activeBtn.dataset.km : null;
        var highResKmSizesStr = highResKmSizes.map(String);
        if (activeKm && highResKmSizesStr.indexOf(activeKm) !== -1) {
          _applyInvalidState();
        } else {
          _applyClearState();
        }
      });

    // Re-check coverage on every map move so the UI stays in sync as the user pans.
    map.on('move', function () {
      _updateSizeButtons(map, highResKmSizes);
    });
  };

  // _applyInvalidState — the active size requires coverage that isn't available here.
  // Turns the overlay red, disables Confirm, shows the coverage message.
  function _applyInvalidState() {
    window._selectionInvalid = true;

    var overlay = document.getElementById('overlay');
    if (overlay) overlay.classList.add('overlay-invalid');

    var confirmBtn = document.getElementById('confirm-btn');
    if (confirmBtn) confirmBtn.disabled = true;

    var msg = document.getElementById('coverage-message');
    
    if (msg) {
      msg.textContent = 'Chosen resolution not available in this region';
      msg.style.display = 'block';
    }
    // Grey out high-res buttons that aren't currently active
    _highResKmSizes.forEach(function(km) {
      var btn = document.querySelector('.size-btn[data-km="' + km + '"]');
      if (btn && !btn.classList.contains('active')) btn.disabled = true;
    });
  }

  // _applyClearState — the active size is valid for this location.
  // Restores green overlay, enables Confirm, hides the coverage message.
  function _applyClearState() {
    window._selectionInvalid = false;

    var overlay = document.getElementById('overlay');
    if (overlay) overlay.classList.remove('overlay-invalid');

    var confirmBtn = document.getElementById('confirm-btn');
    if (confirmBtn) confirmBtn.disabled = false;

    var msg = document.getElementById('coverage-message');
    if (msg) msg.style.display = 'none';
    // Re-enable all high-res buttons now that coverage is available
    
  }

  // _updateSizeButtons — core logic, called on every map move and every size button click.
  // Checks whether the map centre falls inside a coverage polygon, then updates
  // window._currentDataset and applies the appropriate valid/invalid UI state.
  function _updateSizeButtons(map, highResKmSizes) {
    // Skip update while the select/confirm flow is active — selection.js has locked
    // the UI and we must not interfere with its button states.
    var confirmBtn = document.getElementById('confirm-btn');
    if (confirmBtn && confirmBtn.disabled && !window._selectionInvalid) return;

    var center = map.getCenter();
    var lat = center.lat;
    var lon = center.lng;

    // Get the currently active area size from the active button.
    var activeBtn = document.querySelector('.size-btn.active');
    var activeKm = activeBtn ? activeBtn.dataset.km : null;
    var highResKmSizesStr = highResKmSizes.map(String);
    var activeIsHighRes = activeKm && highResKmSizesStr.indexOf(activeKm) !== -1;

    // Check whether the map centre point falls inside any coverage polygon.
    // Using centre-point rather than full bbox so that the dataset only activates
    // when the customer is genuinely centred on the covered area.
    var centrePoint = turf.point([lon, lat]);
    var matchedDataset = null;
    window._coveragePolygons.forEach(function (entry) {
      if (!matchedDataset && turf.booleanPointInPolygon(centrePoint, entry.geojson)) {
        matchedDataset = entry.dataset;
      }
    });

    if (matchedDataset) {
      // Centre is inside a high-res coverage area — the dataset is available.
      window._currentDataset = matchedDataset;
      // Re-enable high-res buttons — we have coverage here
      _highResKmSizes.forEach(function(km) {
        var btn = document.querySelector('.size-btn[data-km="' + km + '"]');
        if (btn) btn.disabled = false;
      });
      _applyClearState();
    } else {
      // No coverage match at this location — fall back to GLO-30.
      window._currentDataset = 'GLO-30';

      if (activeIsHighRes) {
        // The currently active size requires coverage we don't have here.
        _applyInvalidState();
      } else {
        // A non-high-res size is active — GLO-30 is fine, no invalid state.
        // But still grey out high-res buttons since we're outside coverage.
        _highResKmSizes.forEach(function(km) {
          var btn = document.querySelector('.size-btn[data-km="' + km + '"]');
          if (btn) btn.disabled = true;
        });
        _applyClearState();
      }
    }
  }

}());
