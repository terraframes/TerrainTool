// search.js — geocoding search with autocomplete suggestions
// Exposes: window.initSearch(map, token, zoomFor65Pct, onFlyStart, onFlyEnd)
//   onFlyStart() — called just before map.flyTo (sets isProgrammaticMove=true)
//   onFlyEnd()   — registered as map.once('moveend') handler

(function () {
  'use strict';

  var TYPES = 'country,region,place,locality,neighborhood,address,poi';

  window.initSearch = function (map, token, zoomFor65Pct, onFlyStart, onFlyEnd) {
    var input          = document.getElementById('search-input');
    var suggestionsDiv = document.getElementById('search-suggestions');
    var debounceTimer  = null;
    var currentSuggestions = [];

    if (!input || !suggestionsDiv) {
      console.error('Search: #search-input or #search-suggestions not found — check DOM order');
      return;
    }
    function flyTo(lng, lat, placeName) {
      var z = zoomFor65Pct(lat);
      onFlyStart();
      map.flyTo({ center: [lng, lat], zoom: z });
      map.once('moveend', onFlyEnd);
      input.value = placeName;
      hideSuggestions();
    }

    function hideSuggestions() {
      suggestionsDiv.style.display = 'none';
      currentSuggestions = [];
    }

    function showSuggestions(features) {
      currentSuggestions = features;
      suggestionsDiv.innerHTML = '';
      if (!features.length) { hideSuggestions(); return; }
      features.forEach(function (f) {
        var item = document.createElement('div');
        item.className = 'suggestion-item';
        item.textContent = f.place_name;
        item.addEventListener('mousedown', function (e) {
          e.preventDefault(); // prevent input blur firing before mouseup
          flyTo(f.center[0], f.center[1], f.place_name);
        });
        suggestionsDiv.appendChild(item);
      });
      suggestionsDiv.style.display = 'block';
    }

    async function fetchSuggestions(query) {
      if (!query) { hideSuggestions(); return; }

      var mapboxFetch = fetch(
        'https://api.mapbox.com/geocoding/v5/mapbox.places/' +
        encodeURIComponent(query) + '.json' +
        '?access_token=' + token + '&limit=3&types=' + TYPES
      ).then(function (res) {
        if (!res.ok) throw new Error('Mapbox geocoding HTTP error: ' + res.status);
        return res.json().then(function (data) { return data.features || []; });
      });

      var nominatimFetch = fetch(
        'https://nominatim.openstreetmap.org/search' +
        '?q=' + encodeURIComponent(query) +
        '&format=json&limit=3&addressdetails=0&accept-language=en',
        { headers: { 'User-Agent': 'TerrainPrintTool/1.0' } }
      ).then(function (res) {
        if (!res.ok) throw new Error('Nominatim HTTP error: ' + res.status);
        return res.json().then(function (results) {
          return results.map(function (r) {
            return {
              place_name: r.display_name,
              center: [parseFloat(r.lon), parseFloat(r.lat)]
            };
          });
        });
      });

      var results = await Promise.allSettled([mapboxFetch, nominatimFetch]);

      var mapboxFeatures = [];
      if (results[0].status === 'fulfilled') {
        mapboxFeatures = results[0].value;
      } else {
        console.error('Search: Mapbox suggestions failed —', results[0].reason.message);
      }

      var nominatimFeatures = [];
      if (results[1].status === 'fulfilled') {
        nominatimFeatures = results[1].value;
      } else {
        console.error('Search: Nominatim suggestions failed —', results[1].reason.message);
      }

      // Merge Mapbox first, then Nominatim; deduplicate by coords rounded to 2 dp.
      var seen = {};
      var merged = [];
      mapboxFeatures.concat(nominatimFeatures).forEach(function (f) {
        var key = f.center[0].toFixed(2) + ',' + f.center[1].toFixed(2);
        if (!seen[key]) { seen[key] = true; merged.push(f); }
      });

      showSuggestions(merged.slice(0, 5));
    }

    async function doSearch() {
      var query = input.value.trim();
      if (!query) return;
      // Use first open suggestion if the dropdown is visible
      if (suggestionsDiv.style.display !== 'none' && currentSuggestions.length) {
        var f0 = currentSuggestions[0];
        flyTo(f0.center[0], f0.center[1], f0.place_name);
        return;
      }
      // Otherwise hit the API directly
      try {
        var url = 'https://api.mapbox.com/geocoding/v5/mapbox.places/' +
                  encodeURIComponent(query) + '.json' +
                  '?access_token=' + token + '&limit=1&types=' + TYPES;
        var res = await fetch(url);
        if (!res.ok) throw new Error('Geocoding HTTP error: ' + res.status);
        var data = await res.json();
        if (!data.features || !data.features.length) {
          console.error('Address search: no results found for "' + query + '"');
          return;
        }
        var f = data.features[0];
        flyTo(f.center[0], f.center[1], f.place_name);
      } catch (e) {
        console.error('Address search failed:', e.message);
      }
    }

    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        fetchSuggestions(input.value.trim());
      }, 300);
    });

    input.addEventListener('blur', function () {
      setTimeout(hideSuggestions, 150);
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') doSearch();
      if (e.key === 'Escape') hideSuggestions();
    });

    document.getElementById('search-btn').addEventListener('click', doSearch);
  };

}());
