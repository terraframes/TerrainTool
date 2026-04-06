// selection.js — Select / Confirm / Cancel panel logic, for Terrain Print Tool
// Exposes: window.initSelection(map, getAreaKm, haversineDest, summary)

(function () {
  'use strict';

  window.initSelection = function (map, getAreaKm, haversineDest, summary) {
    var lastPayload = null;

    function lockMap() {
      try {
        map.dragPan.disable();
        map.scrollZoom.disable();
        map.touchZoomRotate.disable();
        map.doubleClickZoom.disable();
      } catch (e) {
        console.error('Select: could not lock map interactions —', e.message);
      }
      document.querySelectorAll('.size-btn').forEach(function (b) { b.disabled = true; });
      document.getElementById('search-input').disabled = true;
      document.getElementById('search-btn').disabled = true;
    }

    function unlockMap() {
      try {
        map.dragPan.enable();
        map.scrollZoom.enable();
        map.touchZoomRotate.enable();
        map.doubleClickZoom.enable();
      } catch (e) {
        console.error('Cancel: could not re-enable map interactions —', e.message);
      }
      document.querySelectorAll('.size-btn').forEach(function (b) { b.disabled = false; });
      document.getElementById('search-input').disabled = false;
      document.getElementById('search-btn').disabled = false;
    }

    document.getElementById('confirm-btn').addEventListener('click', function () {
      var center = map.getCenter();
      var half   = getAreaKm() / 2;
      var north  = haversineDest(center.lat, center.lng,   0, half);
      var south  = haversineDest(center.lat, center.lng, 180, half);
      var east   = haversineDest(center.lat, center.lng,  90, half);
      var west   = haversineDest(center.lat, center.lng, 270, half);

      lastPayload = {
        bbox: {
          min_lat: +south.lat.toFixed(6),
          max_lat: +north.lat.toFixed(6),
          min_lon: +west.lon.toFixed(6),
          max_lon: +east.lon.toFixed(6)
        },
        center_lat:    +center.lat.toFixed(6),
        center_lon:    +center.lng.toFixed(6),
        area_km:       getAreaKm(),
        dataset:       'GLO-30',
        print_size_mm: 200
      };

      console.log(JSON.stringify(lastPayload, null, 2));

      summary.style.display = 'block';
      summary.innerHTML =
        '<strong>Current selection</strong><br>' +
        'Center: ' + lastPayload.center_lat + ', ' + lastPayload.center_lon + '<br>' +
        'N ' + lastPayload.bbox.max_lat + ' / S ' + lastPayload.bbox.min_lat + ' / ' +
        'E ' + lastPayload.bbox.max_lon + ' / W ' + lastPayload.bbox.min_lon + '<br>' +
        'Area: ' + getAreaKm() + ' km &nbsp;|&nbsp; Dataset: GLO-30' +
        '<div id="summary-actions">' +
        '<button id="summary-confirm-btn">Confirm</button>' +
        '<button id="summary-cancel-btn">Cancel</button>' +
        '</div>';

      lockMap();

      ddocument.getElementById('summary-confirm-btn').addEventListener('click', function () {
  // Build a Shopify-shaped payload matching what webhook.py expects
  var shopifyPayload = {
    order_number: 'TEST-' + Date.now(),
    line_items: [{
      properties: [
        { name: 'min_lat', value: String(lastPayload.bbox.min_lat) },
        { name: 'max_lat', value: String(lastPayload.bbox.max_lat) },
        { name: 'min_lon', value: String(lastPayload.bbox.min_lon) },
        { name: 'max_lon', value: String(lastPayload.bbox.max_lon) },
        { name: 'area_km', value: String(lastPayload.area_km) }
      ]
    }]
  };

  fetch('https://terraintool-production.up.railway.app/webhook', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(shopifyPayload)
  })
  .then(function (res) {
    if (res.ok) {
      summary.innerHTML = '<strong>Order submitted successfully.</strong>';
    } else {
      summary.innerHTML = '<strong>Error — server returned ' + res.status + '</strong>';
    }
  })
  .catch(function (err) {
    summary.innerHTML = '<strong>Error — could not reach server: ' + err.message + '</strong>';
  });
});

      document.getElementById('summary-cancel-btn').addEventListener('click', function () {
        summary.style.display = 'none';
        unlockMap();
      });
    });
  };

}());
