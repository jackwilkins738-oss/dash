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
    // Multipliers and bases checked against real published 2026 UK re-roof
    // price guides for a 3-bed semi (concrete £6,500-£11,500, clay
    // £9,500-£15,500, slate £11,000-£18,500 - MyBuilder, BookABuilderUK,
    // FixMyRoof, BestBuilders) rather than picked to look plausible.
    var MATERIALS = {
      slate: { label: 'Slate', fill: '#3f4c56', multiplier: 1.6, life: '80-150 years' },
      concrete: { label: 'Concrete tile', fill: '#7c5443', multiplier: 1.0, life: '40-60 years' },
      clay: { label: 'Clay tile', fill: '#b3592f', multiplier: 1.4, life: '60-100 years' },
    };
    var SIZES = [
      { label: 'Small terrace', base: 6500 },
      { label: 'Average semi', base: 8500 },
      { label: 'Large detached', base: 11500 },
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
      var lifeEl = document.getElementById('materialLife');
      if (lifeEl) lifeEl.textContent = m.life + ' typical lifespan';
      document.querySelectorAll('.lifespan-bar').forEach(function (bar) {
        bar.classList.toggle('is-selected', bar.getAttribute('data-material') === state.material);
      });
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

  // ---------------------------------------------------------------------
  // Scroll progress bar - a thin line across the top that fills as you
  // scroll, same idea as the parent Scalar site's own progress indicator.
  // ---------------------------------------------------------------------
  var progressBar = document.getElementById('scrollProgress');
  if (progressBar && !reduced) {
    var updateProgress = function () {
      var h = document.documentElement;
      var scrolled = h.scrollTop;
      var max = h.scrollHeight - h.clientHeight;
      var pct = max > 0 ? (scrolled / max) * 100 : 0;
      progressBar.style.width = pct + '%';
    };
    window.addEventListener('scroll', updateProgress, { passive: true });
    window.addEventListener('resize', updateProgress);
    updateProgress();
  }

  // ---------------------------------------------------------------------
  // Magnetic buttons - a CTA very gently follows the cursor within its own
  // bounds, then springs back on leave. Fine pointers only: there's no
  // cursor on a phone to follow, and reduced-motion asks for none of it.
  // ---------------------------------------------------------------------
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (fine && !reduced) {
    document.querySelectorAll('[data-magnetic]').forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect();
        var x = e.clientX - r.left - r.width / 2;
        var y = e.clientY - r.top - r.height / 2;
        el.style.transform = 'translate(' + x * 0.18 + 'px, ' + y * 0.28 + 'px)';
      });
      el.addEventListener('mouseleave', function () {
        el.style.transform = '';
      });
    });

    // Cursor-lit cards - a soft glow that tracks the pointer across the
    // card's own surface, via two CSS custom properties the stylesheet
    // reads for a radial-gradient position. Applied to the existing card
    // classes directly rather than a data attribute, so it works on every
    // card site-wide without hand-tagging each one across 7 HTML files.
    document.querySelectorAll('[data-spotlight], .card, .job, .option-card, .area-card').forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect();
        el.style.setProperty('--mx', ((e.clientX - r.left) / r.width) * 100 + '%');
        el.style.setProperty('--my', ((e.clientY - r.top) / r.height) * 100 + '%');
      });
    });
  }

  // ---------------------------------------------------------------------
  // Animated number entrance - a real overshoot-and-settle jump for the
  // handful of numbers that matter most (hero stats, guarantee lengths),
  // same technique the parent Scalar site's own JumpStat uses: the Web
  // Animations API plus an IntersectionObserver, not a library.
  // ---------------------------------------------------------------------
  if (!reduced && 'IntersectionObserver' in window) {
    var jumpIo = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return
          jumpIo.unobserve(entry.target);
          entry.target.animate(
            [
              { opacity: 0, transform: 'translateY(18px) scale(0.4) rotate(-4deg)' },
              { opacity: 1, transform: 'translateY(0) scale(1) rotate(0deg)' },
            ],
            { duration: 700, easing: 'cubic-bezier(0.3, 1.9, 0.5, 1)', fill: 'forwards' },
          );
        });
      },
      { rootMargin: '0px 0px -10% 0px' },
    );
    document.querySelectorAll('[data-jump]').forEach(function (el) {
      jumpIo.observe(el);
    });
  } else {
    document.querySelectorAll('[data-jump]').forEach(function (el) {
      el.style.opacity = '1';
    });
  }

  // ---------------------------------------------------------------------
  // Animated lifespan comparison bars (materials.html, and the smaller
  // copy of the same chart on estimate.html) - each bar grows to a width
  // proportional to a real, sourced lifespan figure the first time it
  // scrolls into view. Data lives on the element itself (data-years),
  // not duplicated in JS, so the number on screen and the number driving
  // the animation can never drift apart.
  // ---------------------------------------------------------------------
  var lifespanBars = document.querySelectorAll('.lifespan-bar');
  if (lifespanBars.length) {
    var maxYears = Math.max.apply(
      null,
      Array.from(lifespanBars).map(function (b) {
        return Number(b.getAttribute('data-max-years'));
      }),
    );
    var growBar = function (bar) {
      var fill = bar.querySelector('.lifespan-fill');
      var max = Number(bar.getAttribute('data-max-years'));
      var pct = Math.min(100, (max / maxYears) * 100);
      if (reduced) {
        fill.style.width = pct + '%';
        return;
      }
      fill.animate([{ width: '0%' }, { width: pct + '%' }], {
        duration: 1100,
        easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        fill: 'forwards',
      });
    };
    if ('IntersectionObserver' in window) {
      var barIo = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            barIo.unobserve(entry.target);
            growBar(entry.target);
          });
        },
        { threshold: 0.4 },
      );
      lifespanBars.forEach(function (bar) {
        barIo.observe(bar);
      });
    } else {
      lifespanBars.forEach(growBar);
    }
  }

  // ---------------------------------------------------------------------
  // "How it works" handoff animation (index.html) - a dot travels from
  // "you message us" to "same-day quote" to "job booked", exactly the
  // pattern used for the site+dashboard handoff on the parent Scalar site:
  // a small setTimeout-driven state machine, not a JS animation library.
  // ---------------------------------------------------------------------
  var flowRoot = document.getElementById('howItWorksFlow');
  if (flowRoot) {
    var flowNodes = flowRoot.querySelectorAll('.flow-node');
    var flowDots = flowRoot.querySelectorAll('.flow-dot');
    var flowTimers = [];
    var runFlow = function () {
      flowTimers.forEach(function (t) {
        clearTimeout(t);
      });
      flowTimers = [];
      flowNodes.forEach(function (n) {
        n.classList.remove('is-active');
      });
      flowDots.forEach(function (d) {
        d.style.left = '0%';
        d.style.opacity = '0';
      });
      if (reduced) {
        flowNodes.forEach(function (n) {
          n.classList.add('is-active');
        });
        return;
      }
      var STEP = 1500;
      flowNodes.forEach(function (node, i) {
        flowTimers.push(
          window.setTimeout(function () {
            node.classList.add('is-active');
            if (flowDots[i]) {
              flowDots[i].style.opacity = '1';
              flowDots[i].style.left = '100%';
            }
          }, i * STEP + 300),
        );
      });
      flowTimers.push(window.setTimeout(runFlow, flowNodes.length * STEP + 1800));
    };
    if ('IntersectionObserver' in window) {
      var flowIo = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              if (flowTimers.length === 0) runFlow();
            } else {
              flowTimers.forEach(function (t) {
                clearTimeout(t);
              });
              flowTimers = [];
            }
          });
        },
        { threshold: 0.5 },
      );
      flowIo.observe(flowRoot);
    } else {
      runFlow();
    }
  }
})();
