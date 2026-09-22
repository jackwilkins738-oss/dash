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

    var state = { material: 'concrete', size: 1, extras: 0 };
    var priceEl = document.getElementById('priceValue');
    var displayedPrice = 0;
    var priceAnimId = null;

    function estimate() {
      var m = MATERIALS[state.material];
      var s = SIZES[state.size];
      return Math.round((s.base * m.multiplier) / 50) * 50 + state.extras;
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

    document.addEventListener('extras-changed', function (e) {
      state.extras = e.detail.total;
      render();
    });

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

  // ---------------------------------------------------------------------
  // Hero visual (index.html) - a cursor-tilt house illustration that
  // cycles through the three roof materials on its own, so the "watch it
  // change" moment from the estimate page is visible before a visitor has
  // clicked anything. Same MATERIALS figures as the configurator (small
  // terrace base, since the hero already says "From £X").
  // ---------------------------------------------------------------------
  var heroCard = document.getElementById('heroRoofCard');
  var heroRoofFace = document.getElementById('heroRoofFace');
  if (heroCard && heroRoofFace) {
    var HERO_MATERIALS = [
      { label: 'Concrete tile', fill: '#7c5443', price: 6500 },
      { label: 'Clay tile', fill: '#b3592f', price: 9100 },
      { label: 'Slate', fill: '#3f4c56', price: 10400 },
    ];
    var heroMaterialEl = document.getElementById('heroMaterialLabel');
    var heroPriceEl = document.getElementById('heroPriceLabel');
    var heroIndex = 0;
    var heroTimer = null;

    var showHeroMaterial = function (i) {
      var m = HERO_MATERIALS[i];
      heroRoofFace.style.fill = m.fill;
      if (heroMaterialEl) {
        heroMaterialEl.style.opacity = '0';
        heroPriceEl.style.opacity = '0';
        setTimeout(function () {
          heroMaterialEl.textContent = m.label;
          heroPriceEl.textContent = '£' + m.price.toLocaleString('en-GB');
          heroMaterialEl.style.opacity = '1';
          heroPriceEl.style.opacity = '1';
        }, 250);
      }
    };
    showHeroMaterial(0);

    var startHeroCycle = function () {
      if (heroTimer || reduced) return;
      heroTimer = window.setInterval(function () {
        heroIndex = (heroIndex + 1) % HERO_MATERIALS.length;
        showHeroMaterial(heroIndex);
      }, 3200);
    };
    var stopHeroCycle = function () {
      window.clearInterval(heroTimer);
      heroTimer = null;
    };

    if ('IntersectionObserver' in window) {
      var heroIo = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) startHeroCycle();
            else stopHeroCycle();
          });
        },
        { threshold: 0.4 },
      );
      heroIo.observe(heroCard);
    } else {
      startHeroCycle();
    }

    // Cursor tilt - fine pointers only, same reasoning as the magnetic
    // buttons above.
    if (fine && !reduced) {
      heroCard.addEventListener('mousemove', function (e) {
        var r = heroCard.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        heroCard.style.transform = 'rotateY(' + px * 10 + 'deg) rotateX(' + py * -10 + 'deg)';
      });
      heroCard.addEventListener('mouseleave', function () {
        heroCard.style.transform = 'rotateY(0deg) rotateX(0deg)';
      });
    }
  }

  // =======================================================================
  // Wow-factor pass 2. Every block below is guarded by the element it
  // needs existing, so this is a safe no-op on any page that doesn't have
  // the relevant markup - same pattern as everything above.
  // =======================================================================

  // --- Preloader ---------------------------------------------------------
  // A real percentage count (not a fake instant flash), with a slight
  // overshoot on the last tick so it settles rather than just stopping -
  // same overshoot curve philosophy as the parent Scalar site's JumpStat.
  var preloader = document.getElementById('preloader');
  if (preloader) {
    var plCount = document.getElementById('preloaderCount');
    var plBar = document.getElementById('preloaderBarFill');
    document.body.classList.add('pl-active');
    if (reduced) {
      preloader.remove();
      document.body.classList.remove('pl-active');
    } else {
      var plStart = null;
      var plDuration = 1400;
      var plTick = function (now) {
        if (!plStart) plStart = now;
        var t = Math.min(1, (now - plStart) / plDuration);
        var eased = 1 - Math.pow(1 - t, 2);
        var pct = Math.round(eased * 100);
        if (plCount) plCount.textContent = pct;
        if (plBar) plBar.style.width = pct + '%';
        if (t < 1) {
          requestAnimationFrame(plTick);
        } else {
          setTimeout(function () {
            preloader.classList.add('pl-exit');
            document.body.classList.remove('pl-active');
            setTimeout(function () {
              preloader.remove();
            }, 750);
          }, 250);
        }
      };
      requestAnimationFrame(plTick);
    }
  }

  // --- Custom two-part cursor ---------------------------------------------
  // A dot that tracks the pointer exactly, and a ring that lags gently
  // behind it (lerped each frame) and expands over anything clickable.
  // Fine pointers only - there's no cursor on a phone to replace.
  if (fine && !reduced) {
    var cDot = document.createElement('div');
    cDot.className = 'cursor-dot';
    var cRing = document.createElement('div');
    cRing.className = 'cursor-ring';
    document.body.appendChild(cDot);
    document.body.appendChild(cRing);
    document.documentElement.classList.add('has-custom-cursor');

    var mx = -100,
      my = -100,
      rx = -100,
      ry = -100;
    document.addEventListener('mousemove', function (e) {
      mx = e.clientX;
      my = e.clientY;
      cDot.style.transform = 'translate(' + mx + 'px, ' + my + 'px) translate(-50%, -50%)';
      var target = e.target.closest && e.target.closest('a, button, [role="button"], input, select, textarea');
      cRing.classList.toggle('is-hover', !!target);
    });
    var cursorLoop = function () {
      rx += (mx - rx) * 0.16;
      ry += (my - ry) * 0.16;
      cRing.style.transform = 'translate(' + rx + 'px, ' + ry + 'px) translate(-50%, -50%)';
      requestAnimationFrame(cursorLoop);
    };
    requestAnimationFrame(cursorLoop);
    document.addEventListener('mouseleave', function () {
      cDot.style.opacity = '0';
      cRing.style.opacity = '0';
    });
    document.addEventListener('mouseenter', function () {
      cDot.style.opacity = '1';
      cRing.style.opacity = '1';
    });
  }

  // --- Condensing glass navbar --------------------------------------------
  var navEl = document.getElementById('top');
  if (navEl) {
    var syncNavCondense = function () {
      navEl.classList.toggle('is-condensed', window.scrollY > 40);
    };
    window.addEventListener('scroll', syncNavCondense, { passive: true });
    syncNavCondense();
  }

  // --- Animated stat dial (78% response-rate figure) ----------------------
  var dialFill = document.querySelector('.stat-dial-fill');
  if (dialFill) {
    var dialNumberEl = document.querySelector('.stat-dial-number');
    var dialPercent = Number(dialFill.getAttribute('data-percent')) || 0;
    var dialCircumference = 2 * Math.PI * 55; // r=55, matches the SVG below
    var runDial = function () {
      var start = null;
      var dur = 1400;
      var tick = function (now) {
        if (!start) start = now;
        var t = Math.min(1, (now - start) / dur);
        var eased = 1 - Math.pow(1 - t, 3);
        var current = Math.round(eased * dialPercent);
        if (dialNumberEl) dialNumberEl.textContent = current + '%';
        dialFill.style.strokeDashoffset = String(dialCircumference * (1 - (eased * dialPercent) / 100));
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    if (reduced || !('IntersectionObserver' in window)) {
      dialFill.style.strokeDashoffset = String(dialCircumference * (1 - dialPercent / 100));
      if (dialNumberEl) dialNumberEl.textContent = dialPercent + '%';
    } else {
      var dialIo = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            dialIo.unobserve(entry.target);
            runDial();
          });
        },
        { threshold: 0.5 },
      );
      dialIo.observe(dialFill);
    }
  }

  // --- Footer word reveal ---------------------------------------------------
  // Sits at the very bottom of the page, so the shared .reveal observer's
  // -10% bottom rootMargin can never be satisfied once the page hits max
  // scroll. A dedicated, more lenient observer (no bottom shrink) instead.
  var footerWord = document.getElementById('footerWord');
  if (footerWord) {
    if (reduced || !('IntersectionObserver' in window)) {
      footerWord.classList.add('in');
    } else {
      var footerIo = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              footerWord.classList.add('in');
              footerIo.unobserve(entry.target);
            }
          });
        },
        { threshold: 0 },
      );
      footerIo.observe(footerWord);
    }
  }

  // --- Services accordion --------------------------------------------------
  var accordionItems = document.querySelectorAll('.accordion-item');
  if (accordionItems.length) {
    var firstPanel = accordionItems[0].querySelector('.accordion-panel');
    accordionItems[0].classList.add('is-open');
    firstPanel.style.maxHeight = 'none';
    accordionItems.forEach(function (item) {
      var trigger = item.querySelector('.accordion-trigger');
      var panel = item.querySelector('.accordion-panel');
      trigger.addEventListener('click', function () {
        var willOpen = !item.classList.contains('is-open');
        accordionItems.forEach(function (other) {
          var otherPanel = other.querySelector('.accordion-panel');
          if (otherPanel.style.maxHeight === 'none') {
            otherPanel.style.maxHeight = otherPanel.scrollHeight + 'px';
            otherPanel.getBoundingClientRect();
          }
          other.classList.remove('is-open');
          other.querySelector('.accordion-trigger').setAttribute('aria-expanded', 'false');
          otherPanel.style.maxHeight = '0px';
        });
        if (willOpen) {
          item.classList.add('is-open');
          trigger.setAttribute('aria-expanded', 'true');
          panel.style.maxHeight = panel.scrollHeight + 'px';
        }
      });
    });
  }

  // --- Estimate calculator polish: glowing slider track + extras toggles --
  var sizeSliderEl = document.getElementById('sizeSlider');
  var sizeTrackFill = document.getElementById('sizeTrackFill');
  if (sizeSliderEl && sizeTrackFill) {
    var syncSliderFill = function () {
      var pct = (Number(sizeSliderEl.value) / Number(sizeSliderEl.max)) * 100;
      sizeTrackFill.style.width = pct + '%';
    };
    sizeSliderEl.addEventListener('input', syncSliderFill);
    syncSliderFill();
  }

  var EXTRAS = {
    guttering: 450,
    chimney: 280,
    skip: 320,
  };
  var extraToggles = document.querySelectorAll('.switch[data-extra]');
  if (extraToggles.length) {
    var updateExtrasTotal = function () {
      var total = 0;
      extraToggles.forEach(function (sw) {
        if (sw.getAttribute('aria-checked') === 'true') total += EXTRAS[sw.getAttribute('data-extra')] || 0;
      });
      var evt = new CustomEvent('extras-changed', { detail: { total: total } });
      document.dispatchEvent(evt);
    };
    extraToggles.forEach(function (sw) {
      sw.addEventListener('click', function () {
        var checked = sw.getAttribute('aria-checked') === 'true';
        sw.setAttribute('aria-checked', String(!checked));
        updateExtrasTotal();
      });
    });
  }

  // --- Hero ambient scene: hand-rolled Canvas2D rain + stars + fog --------
  // Deliberately not WebGL/Three.js: it would need either a third-party CDN
  // script (blocked by this site's own CSP, and not worth widening it for
  // a cosmetic effect) or a vendored library file. A hand-written Canvas2D
  // scene needs neither - zero dependencies, and still genuinely animated.
  // Desktop + fine pointer only, same reasoning as the tilt effect above.
  var ambientCanvas = document.getElementById('heroAmbient');
  if (ambientCanvas && fine && !reduced) {
    var actx = ambientCanvas.getContext('2d');
    var stars = [];
    var drops = [];
    var acWidth = 0,
      acHeight = 0,
      acDpr = Math.min(window.devicePixelRatio || 1, 2);

    var resizeCanvas = function () {
      var rect = ambientCanvas.getBoundingClientRect();
      acWidth = rect.width;
      acHeight = rect.height;
      ambientCanvas.width = acWidth * acDpr;
      ambientCanvas.height = acHeight * acDpr;
      actx.setTransform(acDpr, 0, 0, acDpr, 0, 0);
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    for (var si = 0; si < 60; si++) {
      stars.push({
        x: Math.random(),
        y: Math.random() * 0.6,
        r: Math.random() * 1.2 + 0.3,
        phase: Math.random() * Math.PI * 2,
      });
    }
    for (var di = 0; di < 70; di++) {
      drops.push({
        x: Math.random(),
        y: Math.random(),
        len: Math.random() * 14 + 8,
        speed: Math.random() * 0.012 + 0.01,
      });
    }

    var ambientRunning = false;
    var ambientLoop = function (now) {
      if (!ambientRunning) return;
      actx.clearRect(0, 0, acWidth, acHeight);

      // Stars - a slow twinkle
      actx.fillStyle = 'rgba(200, 230, 220, 0.8)';
      stars.forEach(function (s) {
        var tw = 0.4 + 0.6 * Math.abs(Math.sin(now * 0.001 + s.phase));
        actx.globalAlpha = tw;
        actx.beginPath();
        actx.arc(s.x * acWidth, s.y * acHeight, s.r, 0, Math.PI * 2);
        actx.fill();
      });
      actx.globalAlpha = 1;

      // Rain - falling lines, wrapping to the top
      actx.strokeStyle = 'rgba(143, 214, 180, 0.35)';
      actx.lineWidth = 1;
      drops.forEach(function (d) {
        d.y += d.speed;
        if (d.y > 1.1) d.y = -0.1;
        var px = d.x * acWidth;
        var py = d.y * acHeight;
        actx.beginPath();
        actx.moveTo(px, py);
        actx.lineTo(px - 2, py + d.len);
        actx.stroke();
      });

      requestAnimationFrame(ambientLoop);
    };

    var startAmbient = function () {
      if (ambientRunning) return;
      ambientRunning = true;
      requestAnimationFrame(ambientLoop);
    };
    var stopAmbient = function () {
      ambientRunning = false;
    };
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stopAmbient();
      else if (heroCard) startAmbient();
    });

    if ('IntersectionObserver' in window) {
      var ambientIo = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              startAmbient();
              ambientCanvas.parentElement.classList.add('is-ready');
            } else {
              stopAmbient();
            }
          });
        },
        { threshold: 0.2 },
      );
      ambientIo.observe(ambientCanvas);
    } else {
      startAmbient();
      ambientCanvas.parentElement.classList.add('is-ready');
    }
  }

  // --- Giant footer word: scroll-linked reveal, and glowing window pulse --
  // (Footer word reuses the site-wide .reveal system - just needs the
  // 'reveal' class added in the HTML, see index.html.)
})();
