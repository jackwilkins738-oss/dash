// Verdigris Roofing - the show-piece interaction layer.
//
// Loaded on every page alongside script.js. Each block is guarded by the
// markup it needs, so it's a no-op anywhere that markup isn't present - the
// same pattern script.js uses. No dependencies, no build step.
//
//   1. Mobile action bar      (every page)  Call / WhatsApp / Estimate
//   2. Page-header word rise  (inner pages) the homepage headline treatment
//   3. Live "open now" status (contact)     real UK time vs stated hours
//   4. Before / after slider  (home)        drag to re-roof
//   5. Roof explorer          (home)        tap a part, turn the weather up
//   6. Exploded roof          (home)        five layers, pulled apart by scroll
(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var SVGNS = 'http://www.w3.org/2000/svg';
  var BASE = '/examples/verdigris-roofing/';

  function svg(tag, attrs, parent) {
    var el = document.createElementNS(SVGNS, tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  }

  // Deterministic "random", so the illustrations look hand-placed and the
  // same on every load rather than reshuffling.
  function rng(seed) {
    return function () {
      seed = (seed * 16807) % 2147483647;
      return (seed - 1) / 2147483646;
    };
  }

  function onceInView(el, fn, threshold) {
    if (!('IntersectionObserver' in window)) return fn();
    var io = new IntersectionObserver(
      function (entries) {
        if (entries[0].isIntersecting) {
          io.disconnect();
          fn();
        }
      },
      { threshold: threshold || 0.35 }
    );
    io.observe(el);
  }

  // =======================================================================
  // 1. Mobile action bar. Phones only (CSS hides it from 760px up). Slides
  // in once the hero's own buttons have scrolled away, and steps aside over
  // the closing call-to-action and the footer so the same ask is never on
  // screen twice. Replaces the floating WhatsApp bubble on phones.
  // =======================================================================
  (function () {
    var bar = document.createElement('div');
    bar.className = 'mab';
    bar.setAttribute('aria-label', 'Quick contact');
    bar.innerHTML =
      '<a class="mab-btn mab-call" href="tel:01892000000" aria-label="Call Verdigris Roofing">' +
      '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>' +
      '<span>Call</span></a>' +
      '<a class="mab-btn mab-wa" href="https://wa.me/447700900123" target="_blank" rel="noopener noreferrer" aria-label="Message on WhatsApp">' +
      '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M12 2C6.5 2 2 6.5 2 12c0 2 .6 3.8 1.6 5.4L2 22l4.7-1.6A10 10 0 0 0 12 22c5.5 0 10-4.5 10-10S17.5 2 12 2zm0 18.2c-1.6 0-3.1-.5-4.4-1.3l-.3-.2-3 1 1-3-.2-.3A8.2 8.2 0 1 1 12 20.2z"/></svg>' +
      '<span>WhatsApp</span></a>' +
      '<a class="mab-btn mab-primary" href="' + BASE + 'estimate.html">Estimate &rarr;</a>';
    document.body.appendChild(bar);
    document.documentElement.classList.add('has-mab');

    var pastHero = false;
    var ctaInView = false;
    var sync = function () {
      bar.classList.toggle('is-in', pastHero && !ctaInView);
    };
    var onScroll = function () {
      var next = window.scrollY > window.innerHeight * 0.7;
      if (next !== pastHero) {
        pastHero = next;
        sync();
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    if ('IntersectionObserver' in window) {
      var seen = new Set();
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) seen.add(e.target);
          else seen.delete(e.target);
        });
        ctaInView = seen.size > 0;
        sync();
      });
      document.querySelectorAll('.cta-band, .site-footer').forEach(function (el) {
        io.observe(el);
      });
    }
  })();

  // =======================================================================
  // 2. Inner-page headlines rise word by word, the same way the homepage
  // hero does. Split in JS so the seven pages' HTML stays as it is; the
  // full sentence stays on the h1 as its accessible name.
  // =======================================================================
  document.querySelectorAll('.page-header h1').forEach(function (h1) {
    if (h1.children.length) return; // only plain-text headlines
    var text = h1.textContent.trim();
    h1.setAttribute('aria-label', text);
    h1.textContent = '';
    h1.classList.add('split-h1');
    text.split(/\s+/).forEach(function (w, i) {
      var word = document.createElement('span');
      word.className = 'word';
      word.setAttribute('aria-hidden', 'true');
      word.style.setProperty('--w-i', i);
      var inner = document.createElement('span');
      inner.textContent = w;
      word.appendChild(inner);
      h1.appendChild(word);
      h1.appendChild(document.createTextNode(' '));
    });
  });

  // =======================================================================
  // 3. Live "open now" status, from the real UK time against the hours the
  // contact page states (Mon-Fri, 7.30am-5pm). Never a fake "online".
  // =======================================================================
  document.querySelectorAll('[data-open-status]').forEach(function (el) {
    var render = function () {
      var parts = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Europe/London',
        weekday: 'short',
        hour: '2-digit',
        minute: '2-digit',
        hourCycle: 'h23',
      }).formatToParts(new Date());
      var get = function (t) {
        var p = parts.find(function (x) {
          return x.type === t;
        });
        return p ? p.value : '';
      };
      var day = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(get('weekday'));
      var mins = Number(get('hour')) * 60 + Number(get('minute'));
      var clock = get('hour') + ':' + get('minute');
      var weekday = day >= 1 && day <= 5;
      var open = weekday && mins >= 450 && mins < 1020;
      var next;
      if (weekday && mins < 450) next = '7.30am today';
      else if (day === 5 || day === 6) next = '7.30am Monday';
      else next = '7.30am tomorrow'; // Mon-Thu evenings, and any time Sunday
      el.classList.toggle('is-open', open);
      el.innerHTML = open
        ? '<span class="os-dot"></span><strong>Office open now</strong> &middot; ' + clock + ' UK &middot; written price back today'
        : '<span class="os-dot"></span><strong>' + clock + ' in the UK</strong> &middot; WhatsApp now and it&rsquo;s first in the queue at ' + next;
    };
    render();
    window.setInterval(render, 30000);
  });

  // =======================================================================
  // 4. Before / after: drag to re-roof. Both halves are drawn here as real
  // tile courses - the "before" one worn (slipped, cracked and missing
  // tiles, moss, a sagging ridge), the "after" one new. The after half is
  // revealed by a clip that follows the handle.
  // =======================================================================
  (function () {
    var stage = document.getElementById('baStage');
    if (!stage) return;
    var before = document.getElementById('baBefore');
    var after = document.getElementById('baAfter');
    var range = stage.querySelector('.ba-range');
    var W = 800;
    var H = 380;

    function drawRoof(root, worn) {
      var r = rng(worn ? 11 : 29);
      // Sky, then the slope.
      var sky = svg('linearGradient', { id: worn ? 'baSkyB' : 'baSkyA', x1: 0, y1: 0, x2: 0, y2: 1 }, svg('defs', {}, root));
      svg('stop', { offset: 0, 'stop-color': worn ? '#2a302d' : '#1d3a4a' }, sky);
      svg('stop', { offset: 1, 'stop-color': worn ? '#3b403c' : '#4d7f8f' }, sky);
      svg('rect', { x: 0, y: 0, width: W, height: H, fill: 'url(#' + (worn ? 'baSkyB' : 'baSkyA') + ')' }, root);
      // Felt under the tiles - it's what shows through a gap.
      svg('rect', { x: 0, y: 70, width: W, height: H - 70, fill: worn ? '#191b1a' : '#233029' }, root);

      // Each tile carries a light-to-shadow gradient so it reads as a
      // curved, overlapping tile rather than a flat brick.
      var defs = root.querySelector('defs');
      var shadeId = worn ? 'baShadeB' : 'baShadeA';
      var shade = svg('linearGradient', { id: shadeId, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
      svg('stop', { offset: 0, 'stop-color': '#000', 'stop-opacity': 0.28 }, shade);
      svg('stop', { offset: 0.35, 'stop-color': '#fff', 'stop-opacity': worn ? 0.02 : 0.1 }, shade);
      svg('stop', { offset: 1, 'stop-color': '#000', 'stop-opacity': 0.22 }, shade);

      var tileW = 58;
      var tileH = 40;
      var gauge = 24; // exposed height of each course
      var rows = Math.ceil((H - 70) / gauge) + 1;
      // Bottom course first: on a real roof each course laps OVER the one
      // below it, so the higher row has to be drawn on top.
      for (var row = rows - 1; row >= 0; row--) {
        var y = 70 + row * gauge;
        var offset = row % 2 ? tileW / 2 : 0;
        for (var x = -tileW + offset; x < W + tileW; x += tileW) {
          var base = worn ? 38 + r() * 26 : 57 + r() * 7;
          var sat = worn ? 14 + r() * 10 : 38 + r() * 6;
          var hue = worn ? 16 + r() * 14 : 13 + r() * 3;
          if (worn && r() < 0.06) continue; // missing tile: felt shows
          var slip = worn && r() < 0.09 ? 6 + r() * 10 : 0;
          var rot = worn ? (r() - 0.5) * 5 : 0;
          var g = svg('g', { transform: 'translate(' + x + ' ' + (y + slip) + ') rotate(' + rot.toFixed(2) + ' ' + tileW / 2 + ' 0)' }, root);
          var shape = 'M1 0 H' + (tileW - 1) + ' V' + (tileH - 8) + ' Q' + (tileW - 1) + ' ' + tileH + ' ' + (tileW - 9) + ' ' + tileH + ' H9 Q1 ' + tileH + ' 1 ' + (tileH - 8) + ' Z';
          // Shadow the tail casts on the course below.
          svg('path', { d: shape, fill: 'rgba(0,0,0,0.45)', transform: 'translate(0 3)' }, g);
          svg('path', { d: shape, fill: 'hsl(' + hue + ' ' + sat + '% ' + base / 1.9 + '%)' }, g);
          svg('path', { d: shape, fill: 'url(#' + shadeId + ')' }, g);
          if (!worn) svg('path', { d: 'M5 ' + (tileH - 3) + ' H' + (tileW - 5), stroke: 'rgba(255,255,255,0.14)', 'stroke-width': 1 }, g);
          if (worn && r() < 0.12) {
            svg('path', { d: 'M' + (10 + r() * 30) + ' 18 l' + (4 + r() * 8) + ' 10 l-5 9', stroke: 'rgba(0,0,0,0.55)', 'stroke-width': 1.3, fill: 'none' }, g);
          }
          if (worn && r() < 0.22) {
            svg('ellipse', { cx: 8 + r() * 40, cy: tileH - 8 + r() * 6, rx: 8 + r() * 14, ry: 3 + r() * 5, fill: 'hsl(' + (80 + r() * 25) + ' 35% ' + (22 + r() * 10) + '%)', opacity: 0.9 }, g);
          }
        }
      }
      // Ridge: sagging and patched before, a straight run of caps after.
      var ridge = svg('g', {}, root);
      for (var i = 0; i < W / 70 + 1; i++) {
        var sag = worn ? Math.sin((i / (W / 70)) * Math.PI) * 9 + (r() - 0.5) * 4 : 0;
        svg('path', {
          d: 'M' + (i * 70 - 4) + ' ' + (60 + sag) + ' Q' + (i * 70 + 33) + ' ' + (38 + sag) + ' ' + (i * 70 + 70) + ' ' + (60 + sag) + ' V' + (80 + sag) + ' H' + (i * 70 - 4) + ' Z',
          fill: worn ? 'hsl(20 16% ' + (22 + r() * 8) + '%)' : 'hsl(14 34% 30%)',
          stroke: 'rgba(0,0,0,0.35)',
          'stroke-width': 1.5,
        }, ridge);
        if (worn && r() < 0.5) svg('rect', { x: i * 70 + 8 + r() * 30, y: 74 + sag, width: 14 + r() * 16, height: 5, fill: '#8b8578', opacity: 0.8 }, ridge);
      }
      if (!worn) {
        // A low sun glint that sweeps across the new tiles.
        var sheen = svg('linearGradient', { id: 'baSheen', x1: 0, y1: 0, x2: 1, y2: 0 }, root.querySelector('defs'));
        svg('stop', { offset: 0, 'stop-color': '#fff', 'stop-opacity': 0 }, sheen);
        svg('stop', { offset: 0.5, 'stop-color': '#fff', 'stop-opacity': 0.14 }, sheen);
        svg('stop', { offset: 1, 'stop-color': '#fff', 'stop-opacity': 0 }, sheen);
        svg('rect', { class: 'ba-sheen', x: -300, y: 60, width: 260, height: H, fill: 'url(#baSheen)' }, root);
      }
    }
    drawRoof(before, true);
    drawRoof(after, false);

    var set = function (v) {
      v = Math.max(0, Math.min(100, v));
      stage.style.setProperty('--x', v + '%');
      range.value = v;
    };
    range.addEventListener('input', function () {
      stage.classList.add('is-touched');
      set(Number(range.value));
    });
    var dragging = false;
    var fromPointer = function (e) {
      var rect = stage.getBoundingClientRect();
      set(((e.clientX - rect.left) / rect.width) * 100);
    };
    stage.addEventListener('pointerdown', function (e) {
      dragging = true;
      stage.classList.add('is-touched', 'is-dragging');
      stage.setPointerCapture(e.pointerId);
      fromPointer(e);
    });
    stage.addEventListener('pointermove', function (e) {
      if (dragging) fromPointer(e);
    });
    var end = function () {
      dragging = false;
      stage.classList.remove('is-dragging');
    };
    stage.addEventListener('pointerup', end);
    stage.addEventListener('pointercancel', end);

    set(50);
    // Unprompted, it sweeps once when it first arrives, so nobody has to
    // guess that it's draggable.
    if (!reduced) {
      onceInView(stage, function () {
        var t0 = performance.now();
        var tick = function (now) {
          if (stage.classList.contains('is-touched')) return;
          var t = Math.min(1, (now - t0) / 2600);
          set(50 + Math.sin(t * Math.PI * 2) * 32 * (1 - t * 0.4));
          if (t < 1) requestAnimationFrame(tick);
          else set(50);
        };
        requestAnimationFrame(tick);
      }, 0.5);
    }
  })();

  // =======================================================================
  // 5. Roof explorer. Six hotspots on the house; each opens what goes
  // wrong there, the sign to look for from the ground, and the typical
  // price to fix it - the same ranges services.html and estimate.html use.
  // The weather control drives rain across the scene; in a storm, water
  // visibly finds every weak point at once.
  // =======================================================================
  (function () {
    var stage = document.getElementById('explorerStage');
    if (!stage) return;
    var panel = document.getElementById('explorerPanel');
    var rainLayer = document.getElementById('explorerRain');

    var PARTS = {
      ridge: {
        n: '01',
        title: 'Ridge & hip tiles',
        wrong: 'The mortar they sit in cracks and washes out over the years, until the tiles loosen and lift in a high wind.',
        look: 'Gaps along the top line of the roof, or crumbs of mortar collecting in the gutter.',
        fix: 'Re-bed, or dry-fix so there’s no mortar left to fail',
        price: '£220 – £900',
      },
      tiles: {
        n: '02',
        title: 'Tiles & slates',
        wrong: 'One slipped or cracked tile lets water straight onto the felt beneath - and old felt gives up quickly once it’s wet.',
        look: 'A tile sitting lower than its neighbours, or a lighter patch where one is missing.',
        fix: 'Replace like-for-like; a full re-roof only when patching stops being worth it',
        price: '£220 – £900 repair · re-roof £6,500+',
      },
      valley: {
        n: '03',
        title: 'Valleys',
        wrong: 'Where two slopes meet, all the water from both runs down one channel. Worn lead or cracked mortar there lets it in.',
        look: 'Staining on the ceiling directly below where two roofs join.',
        fix: 'Re-line the valley in lead or a GRP liner',
        price: '£650 – £2,200',
      },
      chimney: {
        n: '04',
        title: 'Chimney flashing',
        wrong: 'The lead that seals the chimney to the roof lifts, splits or was only ever sealed with mastic - one of the most common places a leak starts.',
        look: 'Damp on the chimney breast inside, or lead that’s lifted away from the brickwork.',
        fix: 'New Code 4 lead flashing, dressed and pointed in',
        price: 'From £280',
      },
      gutter: {
        n: '05',
        title: 'Gutters & fascias',
        wrong: 'A blocked or sagging gutter overflows straight down the wall - and, in heavy rain, back up under the bottom row of tiles.',
        look: 'Water spilling over the edge when it rains, or green streaks down the brickwork.',
        fix: 'Clear and re-align, or replace the run and fascia',
        price: 'Clear from £450 · new run £650+',
      },
      flat: {
        n: '06',
        title: 'Flat roof',
        wrong: 'Old felt cracks and blisters in the sun, and water ponds where it should drain.',
        look: 'Standing water a day after rain, or blisters and splits on the surface.',
        fix: 'GRP fibreglass or single-ply, laid with a proper fall',
        price: '£2,400 – £4,800',
      },
    };

    var spots = stage.querySelectorAll('.hs');
    var show = function (key) {
      var p = PARTS[key];
      if (!p) return;
      spots.forEach(function (s) {
        var on = s.getAttribute('data-part') === key;
        s.classList.toggle('is-active', on);
        s.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      panel.classList.remove('is-swap');
      void panel.offsetWidth; // restart the swap animation
      panel.classList.add('is-swap');
      panel.innerHTML =
        '<p class="xp-num">' + p.n + ' / 06</p>' +
        '<h3 class="xp-title">' + p.title + '</h3>' +
        '<dl class="xp-facts">' +
        '<div><dt>What goes wrong</dt><dd>' + p.wrong + '</dd></div>' +
        '<div><dt>What to look for</dt><dd>' + p.look + '</dd></div>' +
        '<div><dt>How we fix it</dt><dd>' + p.fix + '</dd></div>' +
        '</dl>' +
        '<div class="xp-price"><span>Typical price</span><strong>' + p.price + '</strong></div>' +
        '<a class="btn btn-primary xp-cta" href="https://wa.me/447700900123?text=' +
        encodeURIComponent('Hi Verdigris - I think I have a problem with my ' + p.title.toLowerCase() + '. Could you take a look? Postcode: ') +
        '" target="_blank" rel="noopener noreferrer">Send us a photo of yours &rarr;</a>';
    };
    spots.forEach(function (s) {
      s.addEventListener('click', function () {
        stage.classList.add('is-touched');
        show(s.getAttribute('data-part'));
      });
      s.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          stage.classList.add('is-touched');
          show(s.getAttribute('data-part'));
        }
      });
    });
    show('chimney');

    // Rain: a fixed pool of drops whose count and speed the weather sets.
    var r = rng(7);
    for (var i = 0; i < 70; i++) {
      var x = r() * 540 - 10;
      svg('line', {
        class: 'rain-drop' + (i >= 34 ? ' rain-heavy' : ''),
        x1: x,
        y1: -20,
        x2: x - 4,
        y2: -4,
        style: '--rd:' + (0.55 + r() * 0.5).toFixed(2) + 's;--rdl:' + (-r() * 1.2).toFixed(2) + 's',
      }, rainLayer);
    }

    var weatherBtns = stage.querySelectorAll('[data-weather-btn]');
    var lightningTimer = 0;
    var setWeather = function (w) {
      stage.setAttribute('data-weather', w);
      weatherBtns.forEach(function (b) {
        b.setAttribute('aria-checked', b.getAttribute('data-weather-btn') === w ? 'true' : 'false');
      });
      window.clearInterval(lightningTimer);
      if (w === 'storm' && !reduced) {
        var strike = function () {
          stage.classList.remove('is-flash');
          void stage.offsetWidth;
          stage.classList.add('is-flash');
        };
        strike();
        lightningTimer = window.setInterval(strike, 4200);
      }
    };
    weatherBtns.forEach(function (b) {
      b.addEventListener('click', function () {
        stage.classList.add('is-touched');
        setWeather(b.getAttribute('data-weather-btn'));
      });
    });
    setWeather('clear');

    // Unprompted demo once it's in view: rain comes in, then the storm, and
    // the panel walks two weak points - then hands control to the visitor.
    if (!reduced) {
      onceInView(stage, function () {
        var steps = [
          [900, function () { setWeather('rain'); }],
          [2600, function () { show('valley'); }],
          [4400, function () { setWeather('storm'); show('ridge'); }],
          [8200, function () { setWeather('rain'); }],
        ];
        steps.forEach(function (s) {
          window.setTimeout(function () {
            if (!stage.classList.contains('is-touched')) s[1]();
          }, s[0]);
        });
      }, 0.45);
    }
    // Stop the lightning timer while the section is off-screen.
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        stage.classList.toggle('is-offscreen', !entries[0].isIntersecting);
      }).observe(stage);
    }
  })();

  // =======================================================================
  // 6. Exploded roof. A pinned section: scrolling through it pulls a roof
  // apart into its five layers, then walks each one. The layers are drawn
  // here in isometric from one plane definition, so they line up exactly.
  // Scroll position -> --p (0..1) on the section; CSS does the moving.
  // =======================================================================
  (function () {
    var section = document.getElementById('anatomy');
    if (!section) return;
    var root = document.getElementById('anatomySvg');
    var items = section.querySelectorAll('.anatomy-list li');

    // The roof plane in isometric: O is the eaves' left corner, U runs
    // along the eaves, V runs up the slope to the ridge.
    var O = [30, 210];
    var U = [250, 105];
    var V = [160, -110];
    var pt = function (a, b) {
      return [O[0] + U[0] * a + V[0] * b, O[1] + U[1] * a + V[1] * b];
    };
    var quad = function (a0, b0, a1, b1) {
      var p = [pt(a0, b0), pt(a1, b0), pt(a1, b1), pt(a0, b1)];
      return 'M' + p.map(function (q) { return q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join(' L') + ' Z';
    };
    var layer = function (i, name) {
      var g = svg('g', { class: 'layer', 'data-layer': i, style: '--i:' + i }, root);
      svg('title', {}, g).textContent = name;
      return g;
    };

    // 0 rafters
    var g0 = layer(0, 'Rafters');
    for (var k = 0; k <= 7; k++) {
      var a = k / 7;
      svg('path', { d: quad(a - 0.012, -0.02, a + 0.012, 1.02), fill: '#8a6a4a', stroke: '#5b4431', 'stroke-width': 0.8 }, g0);
    }
    // 1 membrane
    var g1 = layer(1, 'Breathable membrane');
    svg('path', { d: quad(0, 0, 1, 1), fill: 'rgba(143, 214, 180, 0.28)', stroke: '#8fd6b4', 'stroke-width': 1.2 }, g1);
    for (var m = 1; m < 4; m++) {
      svg('path', { d: quad(0, m / 4 - 0.002, 1, m / 4 + 0.002), fill: 'rgba(143, 214, 180, 0.5)' }, g1);
    }
    // 2 battens
    var g2 = layer(2, 'Battens');
    for (var b = 0; b <= 11; b++) {
      var y = b / 11;
      svg('path', { d: quad(-0.01, y - 0.012, 1.01, y + 0.012), fill: '#b98b58', stroke: '#7b5a36', 'stroke-width': 0.6 }, g2);
    }
    // 3 tiles
    var g3 = layer(3, 'Tiles');
    var tr = rng(3);
    for (var row = 0; row < 11; row++) {
      var off = row % 2 ? 0.5 / 9 : 0;
      for (var col = -1; col < 9; col++) {
        var a0 = Math.max(0, col / 9 + off);
        var a1 = Math.min(1, (col + 1) / 9 + off - 0.004);
        if (a1 <= a0) continue;
        var l = 30 + tr() * 6;
        svg('path', {
          d: quad(a0, row / 11, a1, (row + 1) / 11 + 0.02),
          fill: 'hsl(16 38% ' + l + '%)',
          stroke: 'rgba(0,0,0,0.35)',
          'stroke-width': 0.7,
        }, g3);
      }
    }
    // 4 ridge
    var g4 = layer(4, 'Ridge');
    for (var c = 0; c < 8; c++) {
      svg('path', { d: quad(c / 8, 0.96, (c + 1) / 8 - 0.004, 1.06), fill: 'hsl(14 30% 26%)', stroke: '#8fd6b4', 'stroke-width': 0.8 }, g4);
    }

    var active = -1;
    var setActive = function (i) {
      if (i === active) return;
      active = i;
      section.setAttribute('data-active', i);
      items.forEach(function (li, j) {
        li.classList.toggle('is-active', j === i);
      });
    };

    if (reduced) {
      section.style.setProperty('--p', 1);
      section.classList.add('is-static');
      setActive(-1);
      return;
    }

    var raf = 0;
    var update = function () {
      raf = 0;
      var rect = section.getBoundingClientRect();
      var span = section.offsetHeight - window.innerHeight;
      var p = span > 0 ? Math.min(1, Math.max(0, -rect.top / span)) : 0;
      // First 30%: the roof comes apart. Then each layer takes a turn.
      var explode = Math.min(1, p / 0.3);
      section.style.setProperty('--e', explode.toFixed(3));
      setActive(p < 0.3 ? -1 : Math.min(4, Math.floor(((p - 0.3) / 0.7) * 5)));
    };
    var onScroll = function () {
      if (!raf) raf = requestAnimationFrame(update);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();
  })();
})();
