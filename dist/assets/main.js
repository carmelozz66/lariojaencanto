(function () {
  'use strict';
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* Menú móvil */
  var toggle = $('.nav-toggle'), nav = $('#nav');
  if (toggle) toggle.addEventListener('click', function () {
    var open = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open);
  });

  /* Mapa base: OpenTopoMap (por defecto) y satélite, igual en todos los mapas de la web */
  function baseMap(el, opts) {
    var map = L.map(el, opts);
    var otm = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      subdomains: 'abc', maxZoom: 17,
      attribution: 'Datos &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>, SRTM &middot; Estilo &copy; <a href="https://opentopomap.org" target="_blank" rel="noopener">OpenTopoMap</a> (CC-BY-SA)'
    }).addTo(map);
    var sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 17, attribution: 'Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics'
    });
    L.control.layers({ 'Topográfico (OpenTopoMap)': otm, 'Satélite': sat }, null, { collapsed: true }).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
    return map;
  }
  function drawTrack(map, pts) {
    L.polyline(pts, { color: '#fff', weight: 8, opacity: .9, lineJoin: 'round' }).addTo(map);
    var line = L.polyline(pts, { color: '#d6204f', weight: 4, opacity: 1, lineJoin: 'round' }).addTo(map);
    var a = pts[0], b = pts[pts.length - 1];
    var far = map.distance(a, b) > 150;
    var dot = function (ll, col, txt) {
      return L.circleMarker(ll, { radius: 8, color: '#fff', weight: 3, fillColor: col, fillOpacity: 1 }).addTo(map).bindTooltip(txt);
    };
    dot(a, '#2d5f3a', far ? 'Salida' : 'Salida y llegada');
    if (far) dot(b, '#1b1b1b', 'Llegada');
    return line;
  }
  var pin = L.divIcon({ className: '', html: '<div class="pin"></div>', iconSize: [18, 18], iconAnchor: [9, 9], popupAnchor: [0, -10] });

  /* Mapa de inicio */
  var big = $('#map');
  if (big && window.RUTAS) {
    var map = baseMap(big, { scrollWheelZoom: false });
    var pts = [];
    window.RUTAS.forEach(function (r) {
      if (r.lat == null) return;
      pts.push([r.lat, r.lng]);
      var pop = '<b>' + r.titulo + '</b><br>' + r.km + ' km · ' + r.dificultad + '<br><a href="rutas/' + r.slug + '.html">Ver ruta →</a>';
      L.marker([r.lat, r.lng], { icon: pin, title: r.titulo }).addTo(map).bindPopup(pop);
    });
    var fit = function () { map.invalidateSize(); if (pts.length) map.fitBounds(pts, { padding: [30, 30], maxZoom: 11 }); };
    fit();
    window.addEventListener('load', fit);
    map.on('focus', function () { map.scrollWheelZoom.enable(); });
    map.on('blur', function () { map.scrollWheelZoom.disable(); });
    var openAll = function () { window.open($('#open-map').dataset.url, '_blank'); };
    $('#open-map').addEventListener('click', openAll);
    map.on('click', openAll);
  }

  /* Mapa general a pantalla completa (página propia) */
  var gen = $('#mapfull-map');
  if (gen && gen.dataset.general && window.RUTAS_MAPA) {
    var gm = baseMap(gen, { scrollWheelZoom: true });
    var all = [];
    window.RUTAS_MAPA.forEach(function (r) {
      var pop = '<b>' + r.titulo + '</b><br>' + r.km + ' km · ' + r.dificultad + '<br><a href="rutas/' + r.slug + '.html">Ver ruta →</a>';
      if (r.puntos.length > 1) {
        L.polyline(r.puntos, { color: '#fff', weight: 6, opacity: .8, lineJoin: 'round' }).addTo(gm);
        L.polyline(r.puntos, { color: '#d6204f', weight: 3, opacity: 1, lineJoin: 'round' }).addTo(gm).bindPopup(pop);
        r.puntos.forEach(function (p) { all.push(p); });
      }
      if (r.lat != null) {
        L.marker([r.lat, r.lng], { icon: pin, title: r.titulo }).addTo(gm).bindPopup(pop);
        all.push([r.lat, r.lng]);
      }
    });
    if (all.length) gm.fitBounds(all, { padding: [40, 40] });
    var closeGen = function () {
      window.close();
      setTimeout(function () { window.location.href = $('#mapfull-ficha').href; }, 200);
    };
    $('.v-close').addEventListener('click', closeGen);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeGen(); });
  }

  /* Mini mapa de la ruta */
  /* Mapa a pantalla completa (página propia, se abre en otra pestaña) */
  var fullPage = $('#mapfull-map');
  if (fullPage && fullPage.dataset.page) {
    var fpts = [];
    try { fpts = JSON.parse($('#track-data').textContent); } catch (e) {}
    if (fpts.length > 1) {
      var fm = baseMap(fullPage, { scrollWheelZoom: true });
      var fl = drawTrack(fm, fpts);
      fm.fitBounds(fl.getBounds(), { padding: [40, 40] });
    }
    var closeTab = function () {
      window.close();
      setTimeout(function () { window.location.href = $('#mapfull-ficha').href; }, 200);
    };
    $('.v-close').addEventListener('click', closeTab);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeTab(); });
  }

  var mini = $('#mini-map');
  if (mini && mini.dataset.rich) {
    var tdr = $('#track-data'), tpts = [];
    try { tpts = JSON.parse(tdr.textContent); } catch (e) {}
    if (tpts.length > 1) {
      // en ficha "móvil nuevo" el mapa pequeño es una vista previa: un dedo sobre él no bloquea el desplazamiento de la página
      var vista = !!mini.closest('.m2') && L.Browser.mobile;
      var mm = baseMap(mini, { scrollWheelZoom: false, dragging: !vista, touchZoom: !vista, doubleClickZoom: !vista });
      var ln = drawTrack(mm, tpts);
      mm.fitBounds(ln.getBounds(), { padding: [20, 20] });
      var openFull = function () { window.open(mini.dataset.url, '_blank'); };
      var ob = $('#open-map');
      if (ob) ob.addEventListener('click', openFull);
      mm.on('click', openFull);
    }
  } else if (mini) {
    var lat = parseFloat(mini.dataset.lat), lng = parseFloat(mini.dataset.lng);
    if (!isNaN(lat)) {
      var m = baseMap(mini, { scrollWheelZoom: false, zoomControl: true }).setView([lat, lng], 11);
      L.marker([lat, lng], { icon: pin, title: mini.dataset.titulo }).addTo(m);
      var td = $('#track-data');
      if (td) {
        try {
          var line = L.polyline(JSON.parse(td.textContent), { color: '#8a2f3f', weight: 4, opacity: .9 }).addTo(m);
          m.fitBounds(line.getBounds(), { padding: [20, 20], maxZoom: 15 });
        } catch (e) {}
      }
    }
  }

  /* Filtros del catálogo */
  var grid = $('#grid');
  if (grid) {
    var cards = $$('.ruta-card', grid), count = $('#count'), empty = $('#empty');
    var state = { q: '', zona: '', dif: '', km: '' };
    var groups = { zona: $('#f-zona'), dif: $('#f-dif'), km: $('#f-km') };

    function inRange(v, spec) {
      if (!spec) return true;
      var p = spec.split('-').map(Number);
      return v >= p[0] && v <= (p[1] === undefined ? p[0] : p[1]);
    }
    function apply() {
      var n = 0;
      cards.forEach(function (c) {
        var ok = (!state.q || c.dataset.texto.indexOf(state.q) > -1) &&
          (!state.zona || c.dataset.zona === state.zona) &&
          inRange(+c.dataset.nivel, state.dif) &&
          (!state.km || (+c.dataset.km >= +state.km.split('-')[0] && +c.dataset.km < +state.km.split('-')[1]));
        c.hidden = !ok; if (ok) n++;
      });
      count.textContent = n + (n === 1 ? ' ruta' : ' rutas');
      empty.hidden = n > 0;
      Object.keys(groups).forEach(function (k) {
        $$('.pill', groups[k]).forEach(function (b) { b.classList.toggle('on', b.dataset.v === state[k]); });
      });
      try { history.replaceState(null, '', state.zona ? '#zona=' + encodeURIComponent(state.zona) : location.pathname); } catch (e) {}
    }
    Object.keys(groups).forEach(function (k) {
      groups[k].addEventListener('click', function (e) {
        var b = e.target.closest('.pill'); if (!b) return;
        state[k] = b.dataset.v; apply();
      });
    });
    $('#f-q').addEventListener('input', function (e) {
      state.q = e.target.value.trim().toLowerCase(); apply();
    });
    $('#reset').addEventListener('click', function () {
      state = { q: '', zona: '', dif: '', km: '' }; $('#f-q').value = ''; apply();
    });
    var h = location.hash.match(/zona=([^&]+)/);
    if (h) state.zona = decodeURIComponent(h[1]);
    apply();
  }

  /* Lightbox */
  var lb = $('#lightbox');
  if (lb) {
    var img = $('img', lb), cap = $('figcaption', lb);
    function close() { lb.hidden = true; document.body.style.overflow = ''; }
    document.addEventListener('click', function (e) {
      var a = e.target.closest('[data-lightbox]');
      if (a) {
        e.preventDefault();
        img.src = a.href; img.alt = a.dataset.lightbox; cap.textContent = a.dataset.lightbox;
        lb.hidden = false; document.body.style.overflow = 'hidden'; $('.lb-close', lb).focus();
      } else if (e.target === lb || e.target.closest('.lb-close')) close();
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !lb.hidden) close(); });
  }

  /* ---------- Tracks: descarga (GPX / KML) ---------- */
  var ASSETS = (document.currentScript && document.currentScript.src || '').replace(/main\.js.*$/, '');

  // Carga el GPX como script (.gpx.js) para que funcione también abriendo la web como archivo local.
  function loadGpx(file, ok, fail) {
    var s = document.createElement('script');
    window.__gpxLoaded = function (txt) { ok(txt); };
    s.onerror = fail;
    s.src = ASSETS.replace(/assets\/$/, '') + 'tracks/' + file + '.js';
    document.head.appendChild(s);
  }
  function saveText(text, name, type) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type: type }));
    a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  }
  function gpxToKml(txt, nombre) {
    var doc = new DOMParser().parseFromString(txt, 'application/xml');
    var pts = $$('trkpt,rtept', doc);
    var c = pts.map(function (p) {
      var e = p.getElementsByTagName('ele')[0];
      return p.getAttribute('lon') + ',' + p.getAttribute('lat') + ',' + (e ? e.textContent : 0);
    }).join(' ');
    var esc = nombre.replace(/&/g, '&amp;').replace(/</g, '&lt;');
    return '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>' + esc + '</name>' +
      '<Style id="t"><LineStyle><color>ff3f2f8a</color><width>4</width></LineStyle></Style>' +
      '<Placemark><name>' + esc + '</name><styleUrl>#t</styleUrl><LineString><tessellate>1</tessellate>' +
      '<altitudeMode>clampToGround</altitudeMode><coordinates>' + c + '</coordinates></LineString></Placemark></Document></kml>';
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('[data-track]');
    if (!a) return;
    e.preventDefault();
    var file = a.dataset.file, kml = a.dataset.track === 'kml';
    loadGpx(file, function (txt) {
      if (kml) saveText(gpxToKml(txt, file.replace(/\.gpx$/, '')), file.replace(/\.gpx$/, '.kml'), 'application/vnd.google-earth.kml+xml');
      else saveText(txt, file, 'application/gpx+xml');
    }, function () { window.location.href = a.href; });
  });
})();
