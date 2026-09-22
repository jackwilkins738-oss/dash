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
})();
