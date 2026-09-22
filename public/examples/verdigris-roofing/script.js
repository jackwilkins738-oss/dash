// Verdigris Roofing — no framework, no build step: a mobile nav toggle and a
// scroll-reveal, exactly the amount of JS a real small-business site needs.
(function () {
  var toggle = document.getElementById('navToggle');
  var mobile = document.getElementById('navMobile');
  if (toggle && mobile) {
    toggle.addEventListener('click', function () {
      var open = mobile.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    mobile.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        mobile.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var targets = document.querySelectorAll('.reveal');
  if (reduced || !('IntersectionObserver' in window)) {
    targets.forEach(function (el) {
      el.classList.add('in');
    });
  } else {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('in');
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: '0px 0px -10% 0px', threshold: 0.1 },
    );
    targets.forEach(function (el) {
      io.observe(el);
    });
  }

  // Work gallery filter (work.html only - harmless no-op elsewhere, since
  // querySelectorAll just returns an empty list on pages with no .filter-tab).
  var tabs = document.querySelectorAll('.filter-tab');
  var jobs = document.querySelectorAll('.job[data-category]');
  var noJobs = document.getElementById('noJobs');
  if (tabs.length) {
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) {
          t.setAttribute('aria-pressed', String(t === tab));
        });
        var filter = tab.getAttribute('data-filter');
        var visibleCount = 0;
        jobs.forEach(function (job) {
          var show = filter === 'all' || job.getAttribute('data-category') === filter;
          job.hidden = !show;
          if (show) visibleCount++;
        });
        if (noJobs) noJobs.style.display = visibleCount === 0 ? 'block' : 'none';
      });
    });
  }

  // Instant estimate configurator (estimate.html only). Vanilla JS state
  // machine: a plain object holds the selection, one render() call keeps
  // the roof colour, the price and the button states all in sync with it -
  // rather than each click handler reaching into the DOM by hand.
  var roofFace = document.getElementById('roofFace');
  if (roofFace) {
    var MATERIALS = {
      slate: { label: 'Slate', fill: '#3f4c56', multiplier: 1.08 },
      concrete: { label: 'Concrete tile', fill: '#7c5443', multiplier: 1.0 },
      clay: { label: 'Clay tile', fill: '#b3592f', multiplier: 1.15 },
    };
    var SIZES = [
      { label: 'Small terrace', base: 5800 },
      { label: 'Average semi', base: 7400 },
      { label: 'Large detached', base: 9500 },
    ];

    var state = { material: 'concrete', size: 1 };
    var priceEl = document.getElementById('priceValue');
    var displayedPrice = 0;
    var priceAnimId = null;

    function estimate() {
      var m = MATERIALS[state.material];
      var s = SIZES[state.size];
      return Math.round((s.base * m.multiplier) / 50) * 50;
    }

    function animatePrice(target) {
      if (priceAnimId) cancelAnimationFrame(priceAnimId);
      var start = displayedPrice;
      var startTime = null;
      var duration = 500;
      function tick(now) {
        if (!startTime) startTime = now;
        var t = Math.min(1, (now - startTime) / duration);
        // Ease-out cubic - starts fast, settles gently, like a real counter.
        var eased = 1 - Math.pow(1 - t, 3);
        displayedPrice = Math.round(start + (target - start) * eased);
        if (priceEl) priceEl.textContent = '£' + displayedPrice.toLocaleString('en-GB');
        if (t < 1) {
          priceAnimId = requestAnimationFrame(tick);
        } else {
          priceAnimId = null;
        }
      }
      priceAnimId = requestAnimationFrame(tick);
    }

    function render() {
      var m = MATERIALS[state.material];
      document.querySelectorAll('[data-material]').forEach(function (btn) {
        btn.setAttribute('aria-pressed', String(btn.getAttribute('data-material') === state.material));
      });
      if (roofFace) roofFace.style.fill = m.fill;

      var sizeLabels = document.querySelectorAll('.size-labels span');
      sizeLabels.forEach(function (span, i) {
        span.setAttribute('data-active', String(i === state.size));
      });

      var total = estimate();
      animatePrice(total);

      var ctaLine = document.getElementById('configSummary');
      if (ctaLine) {
        ctaLine.textContent = SIZES[state.size].label + ' re-roof in ' + m.label.toLowerCase();
      }
      var cta = document.getElementById('configCta');
      if (cta) {
        var msg = 'Hi, I used the instant estimate on your site: ' + SIZES[state.size].label.toLowerCase() +
          ' re-roof in ' + m.label.toLowerCase() + ', estimated around £' + total.toLocaleString('en-GB') +
          '. Can I get a proper written price?';
        cta.href = 'https://wa.me/447700900123?text=' + encodeURIComponent(msg);
      }
    }

    document.querySelectorAll('[data-material]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.material = btn.getAttribute('data-material');
        render();
      });
    });

    var slider = document.getElementById('sizeSlider');
    if (slider) {
      slider.addEventListener('input', function () {
        state.size = Number(slider.value);
        render();
      });
    }

    render();
  }
})();
