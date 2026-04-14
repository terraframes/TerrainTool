// coverage.js — Coverage polygon system for high-resolution datasets
// Exposes:
//   window.initCoverage(map, highResKmSizes)  — call once after map loads
//   window.getDatasetForCurrentSelection()    — returns dataset string for current selection

(function () {
  'use strict';

  window._currentDataset = 'GLO-30';
  window._selectionInvalid = false;
  window._coveragePolygons = [];

  var SNAP_LIST = [
    2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
    3.0, 3.2, 3.4, 3.6, 3.8,
    4.0, 4.2, 4.4, 4.6, 4.8,
    5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    22, 24, 25, 26, 28, 30, 32, 34, 36, 38, 40,
    45, 50, 55, 60, 65, 70, 75, 80, 90,
    100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200
  ];
  var HIGH_RES_THRESHOLD_KM = 25;
  var LEFT_SEGMENT_END_PCT = 25;
  var thresholdIndex = SNAP_LIST.indexOf(HIGH_RES_THRESHOLD_KM);
  var lastIndex = SNAP_LIST.length - 1;
  if (thresholdIndex === -1) console.error('ASSERTION FAILED: 25 not in SNAP_LIST');
  window._currentAreaKm = HIGH_RES_THRESHOLD_KM;
  var _currentSnapIndex = thresholdIndex;
  var _isDragging = false;
  var _insideCoverage = false;
  var _map = null;
  var sliderEl = null;

  window.getDatasetForCurrentSelection = function () {
    return window._currentDataset || 'GLO-30';
  };

  function snapIndexToTrackPct(idx) {
    if (idx <= thresholdIndex) {
      return (idx / thresholdIndex) * LEFT_SEGMENT_END_PCT;
    } else {
      return LEFT_SEGMENT_END_PCT + ((idx - thresholdIndex) / (lastIndex - thresholdIndex)) * (100 - LEFT_SEGMENT_END_PCT);
    }
  }

  function trackPctToSnapIndex(pct) {
    var frac;
    if (pct <= LEFT_SEGMENT_END_PCT) {
      frac = (pct / LEFT_SEGMENT_END_PCT) * thresholdIndex;
    } else {
      frac = thresholdIndex + ((pct - LEFT_SEGMENT_END_PCT) / (100 - LEFT_SEGMENT_END_PCT)) * (lastIndex - thresholdIndex);
    }
    return Math.round(Math.min(Math.max(frac, 0), lastIndex));
  }

  function updateSegmentColours() {
    var locked  = document.getElementById('seg-locked');
    var avail   = document.getElementById('seg-available');
    var userPct = snapIndexToTrackPct(_currentSnapIndex);
    if (!locked || !avail) return;
    if (_insideCoverage) {
      locked.style.width = '0%';
      avail.style.left   = '0%';
      avail.style.width  = userPct + '%';
      avail.style.borderRadius = '999px';
    } else {
      var lockPct = LEFT_SEGMENT_END_PCT;
      locked.style.width = lockPct + '%';
      if (userPct > lockPct) {
        avail.style.left   = lockPct + '%';
        avail.style.width  = (userPct - lockPct) + '%';
        avail.style.borderRadius = '0 999px 999px 0';
      } else {
        avail.style.left  = userPct + '%';
        avail.style.width = (lockPct - userPct) + '%';
        avail.style.borderRadius = '0 999px 999px 0';
      }
    }
  }

  function updateGreyOverlay() {
    updateSegmentColours();
  }

  function buildTicks() {
    var tickRow = document.getElementById('slider-ticks');
    if (!tickRow) return;
    tickRow.innerHTML = '';
    [{km: 2, label: '2 km', cls: ''}, {km: 25, label: '25 km', cls: 'threshold'},
     {km: 100, label: '100 km', cls: ''}, {km: 200, label: '200 km', cls: ''}]
    .forEach(function (t) {
      var pct = snapIndexToTrackPct(SNAP_LIST.indexOf(t.km));
      var div = document.createElement('div');
      div.className = 'tick ' + t.cls;
      div.style.left = pct + '%';
      div.innerHTML = '<div class="tick-mark"></div><div class="tick-label">' + t.label + '</div>';
      tickRow.appendChild(div);
    });
  }

  function initSlider() {
    sliderEl = document.getElementById('area-slider');
    if (!sliderEl) return;
    noUiSlider.create(sliderEl, {
      start: LEFT_SEGMENT_END_PCT,
      step: 0.01,
      range: { min: 0, max: 100 },
      connect: [false, true]
    });
    var segLocked = document.createElement('div');
    segLocked.id = 'seg-locked';
    segLocked.style.cssText = 'position:absolute;top:0;left:0;height:100%;' +
      'background:#555;border-radius:999px 0 0 999px;pointer-events:none;' +
      'z-index:1;transition:width 0.15s;';
    var segAvailable = document.createElement('div');
    segAvailable.id = 'seg-available';
    segAvailable.style.cssText = 'position:absolute;top:0;height:100%;' +
      'background:#ccc;pointer-events:none;z-index:1;';
    sliderEl.insertBefore(segLocked, sliderEl.firstChild);
    sliderEl.insertBefore(segAvailable, sliderEl.firstChild);
    var sliderLabel = document.createElement('div');
    sliderLabel.id = 'slider-km-label';
    sliderLabel.style.cssText = 'position:absolute;top:-28px;transform:translateX(-50%);font-size:14px;font-weight:600;color:#1a1a1a;white-space:nowrap;pointer-events:none;font-family:sans-serif;letter-spacing:0.01em;';
    sliderEl.style.position = 'relative';
    sliderEl.appendChild(sliderLabel);
    sliderEl.noUiSlider.on('start', function () { _isDragging = true; });
    sliderEl.noUiSlider.on('update', function (values) {
      var pct = parseFloat(values[0]);

      if (!_insideCoverage) {
        if (!window._selectionInvalid) {
          // Hard lock — user is in GLO-30 only area, never allow below threshold
          if (pct < LEFT_SEGMENT_END_PCT - 0.05) {
            pct = LEFT_SEGMENT_END_PCT;
            if (_isDragging) sliderEl.noUiSlider.set(LEFT_SEGMENT_END_PCT);
          }
        } else {
          // Red state — user is already below threshold, allow movement
          // but re-engage hard lock the moment they reach 25km
          if (pct >= LEFT_SEGMENT_END_PCT - 0.05) {
            pct = LEFT_SEGMENT_END_PCT;
            sliderEl.noUiSlider.set(LEFT_SEGMENT_END_PCT);
            _currentSnapIndex = thresholdIndex;
            window._currentAreaKm = HIGH_RES_THRESHOLD_KM;
            _applyClearState();
            updateGreyOverlay();
            if (window._triggerOverlayUpdate) window._triggerOverlayUpdate();
            if (window._triggerClipUpdate) window._triggerClipUpdate();
            return;
          }
        }
      }

      _currentSnapIndex = trackPctToSnapIndex(pct);
      window._currentAreaKm = SNAP_LIST[_currentSnapIndex];
      var pctForLabel = snapIndexToTrackPct(_currentSnapIndex);
      var lbl = document.getElementById('slider-km-label');
      if (lbl) {
        lbl.style.left = pctForLabel + '%';
        lbl.textContent = window._currentAreaKm < 10
          ? window._currentAreaKm.toFixed(1) + ' km'
          : window._currentAreaKm + ' km';
      }
      updateGreyOverlay();
      _runCoverageCheck();
      if (window._triggerOverlayUpdate) window._triggerOverlayUpdate();
      if (window._triggerClipUpdate) window._triggerClipUpdate();
    });
    sliderEl.noUiSlider.on('change', function () {
      _isDragging = false;
      sliderEl.noUiSlider.set(snapIndexToTrackPct(_currentSnapIndex));
      if (window._triggerAutoZoom) window._triggerAutoZoom();
    });
    setTimeout(buildTicks, 0);
    updateGreyOverlay();
  }

  function _runCoverageCheck() {
    if (!_map) return;
    var center = _map.getCenter();
    var centrePoint = turf.point([center.lng, center.lat]);
    var matchedDataset = null;
    window._coveragePolygons.forEach(function (entry) {
      if (!matchedDataset && turf.booleanPointInPolygon(centrePoint, entry.geojson)) {
        matchedDataset = entry.dataset;
      }
    });

    if (matchedDataset) {
      _insideCoverage = true;
      window._currentDataset = matchedDataset;
      _applyClearState();
    } else {
      _insideCoverage = false;
      window._currentDataset = 'GLO-30';
      if (window._currentAreaKm < HIGH_RES_THRESHOLD_KM) {
        _applyInvalidState();
      } else {
        _applyClearState();
      }
    }
    updateGreyOverlay();
    updateSegmentColours();
  }

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
  }

  function _applyClearState() {
    window._selectionInvalid = false;
    var overlay = document.getElementById('overlay');
    if (overlay) overlay.classList.remove('overlay-invalid');
    var confirmBtn = document.getElementById('confirm-btn');
    if (confirmBtn) confirmBtn.disabled = false;
    var msg = document.getElementById('coverage-message');
    if (msg) msg.style.display = 'none';
  }

  window.initCoverage = function (map) {
    _map = map;

    fetch('faroe_islands_coverage.geojson')
      .then(function (res) {
        if (!res.ok) {
          throw new Error('HTTP ' + res.status + ' fetching faroe_islands_coverage.geojson');
        }
        return res.json();
      })
      .then(function (geojson) {
        var features = [];
        if (geojson.type === 'FeatureCollection') {
          features = geojson.features;
        } else if (geojson.type === 'Feature') {
          features = [geojson];
        } else {
          features = [{ type: 'Feature', geometry: geojson, properties: {} }];
        }
        features.forEach(function (feature) {
          window._coveragePolygons.push({ dataset: 'FO-DEM', geojson: feature });
        });
        console.log('Coverage: loaded ' + window._coveragePolygons.length +
                    ' polygon(s) for FO-DEM');
        initSlider();
        _runCoverageCheck();
      })
      .catch(function (err) {
        console.error('Coverage: failed to load faroe_islands_coverage.geojson —', err.message);
        console.error('Coverage: sizes below 25 km will be blocked outside coverage.');
        initSlider();
        _applyClearState();
      });

    map.on('move', function () {
      _runCoverageCheck();
    });
  };

}());
