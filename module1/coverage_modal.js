// coverage_modal.js — ? button and high-res coverage info modal

(function () {
  'use strict';

  var _coverageInfo = [];

  function fetchCoverageInfo() {
    fetch('coverage_info.json')
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) { _coverageInfo = data; })
      .catch(function (err) {
        console.error('coverage_modal: failed to load coverage_info.json —', err.message);
      });
  }

  function buildModal() {
    var overlay = document.createElement('div');
    overlay.id = 'info-modal-overlay';

    var card = document.createElement('div');
    card.id = 'info-modal-card';

    var header = document.createElement('div');
    header.id = 'info-modal-header';

    var title = document.createElement('p');
    title.id = 'info-modal-title';
    title.textContent = 'High-resolution data (below 25 km) is only available in covered regions';

    var closeBtn = document.createElement('button');
    closeBtn.id = 'info-modal-close';
    closeBtn.textContent = '×';
    closeBtn.setAttribute('aria-label', 'Close');

    header.appendChild(title);
    header.appendChild(closeBtn);
    card.appendChild(header);

    var list = document.createElement('ul');
    list.id = 'info-modal-list';

    _coverageInfo.forEach(function (entry) {
      var li = document.createElement('li');
      li.className = 'info-modal-row';

      var main = document.createElement('span');
      main.className = 'info-modal-main';
      main.textContent = entry.emoji + ' ' + entry.region + ' — ' + entry.status;

      var sources = document.createElement('span');
      sources.className = 'info-modal-sources';
      sources.textContent = entry.source.join(' · ');

      li.appendChild(main);
      li.appendChild(sources);
      list.appendChild(li);
    });

    card.appendChild(list);
    overlay.appendChild(card);
    return overlay;
  }

  function openModal() {
    if (document.getElementById('info-modal-overlay')) return;
    var overlay = buildModal();
    document.body.appendChild(overlay);

    // Trigger reflow so CSS transition plays
    overlay.getBoundingClientRect();
    overlay.classList.add('info-modal-visible');

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeModal();
    });

    document.addEventListener('keydown', onKeyDown);
    document.getElementById('info-modal-close').addEventListener('click', closeModal);
  }

  function closeModal() {
    var overlay = document.getElementById('info-modal-overlay');
    if (!overlay) return;
    overlay.classList.remove('info-modal-visible');
    overlay.addEventListener('transitionend', function () {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, { once: true });
    document.removeEventListener('keydown', onKeyDown);
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') closeModal();
  }

  function init() {
    fetchCoverageInfo();
    var btn = document.getElementById('info-btn');
    if (btn) btn.addEventListener('click', openModal);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
