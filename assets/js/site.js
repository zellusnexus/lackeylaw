/* The Lackey Law Firm — site script (replaces jQuery + Elementor runtime).
   Mobile menu, nav dropdowns, tabs, accordions, sticky-header shadow, reveal-on-scroll,
   lazy JotForm embed and deferred chat widget. No dependencies. */
(function () {
  var doc = document.documentElement;
  doc.classList.add('js');

  // Mobile menu
  var toggle = document.querySelector('.nav-toggle');
  var nav = toggle && document.getElementById(toggle.getAttribute('aria-controls'));
  if (toggle && nav) {
    var setOpen = function (open) {
      toggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    };
    toggle.addEventListener('click', function () { setOpen(toggle.getAttribute('aria-expanded') !== 'true'); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
  }

  // Dropdown menus in the main navigation. aria-expanded on the trigger is the
  // one state the CSS reads to show a menu and flip its arrow, so hover (mouse,
  // desktop layout only), click, tap and keyboard all open and close it the
  // same way and the arrow always matches the menu.
  var triggers = document.querySelectorAll('.nav__trigger');
  var desktop = matchMedia('(min-width: 1025px)');
  var isOpen = function (t) { return t.getAttribute('aria-expanded') === 'true'; };
  var closeMenus = function (except) {
    triggers.forEach(function (t) { if (t !== except) t.setAttribute('aria-expanded', 'false'); });
  };
  var openMenu = function (t) { closeMenus(t); t.setAttribute('aria-expanded', 'true'); };
  triggers.forEach(function (t) {
    var item = t.closest('.nav__item');
    var hoveredAt = 0;
    t.addEventListener('click', function (e) {
      e.stopPropagation();
      if (!isOpen(t)) openMenu(t);
      // A click that lands just after hovering opened the menu was meant to
      // open it, so it doesn't snap shut again.
      else if (Date.now() - hoveredAt > 500) t.setAttribute('aria-expanded', 'false');
    });
    if (!item) return;
    // Mouse only: touch taps also fire pointerenter, and the tap's own click
    // should be what opens the menu.
    item.addEventListener('pointerenter', function (e) {
      if (e.pointerType !== 'mouse' || !desktop.matches || isOpen(t)) return;
      hoveredAt = Date.now();
      openMenu(t);
    });
    item.addEventListener('pointerleave', function (e) {
      if (e.pointerType === 'mouse' && desktop.matches) t.setAttribute('aria-expanded', 'false');
    });
    // Tabbing out of a desktop menu closes it. (Not in the mobile menu, where
    // the open list pushes the items below it down: closing it on the press
    // would move the item being tapped out from under the finger.)
    item.addEventListener('focusout', function (e) {
      if (desktop.matches && e.relatedTarget && !item.contains(e.relatedTarget)) t.setAttribute('aria-expanded', 'false');
    });
  });
  document.addEventListener('click', function (e) { if (!e.target.closest('.nav__item')) closeMenus(); });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var item = document.activeElement && document.activeElement.closest && document.activeElement.closest('.nav__item');
    closeMenus();
    if (item) item.querySelector('.nav__trigger').focus();
  });

  // Tabs: panels stack without JS; with JS only the selected one shows
  document.querySelectorAll('.tabs').forEach(function (box) {
    var tabs = box.querySelectorAll('[role="tab"]');
    var select = function (tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab, panel = document.getElementById(t.getAttribute('aria-controls'));
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        if (panel) panel.hidden = !on;
      });
      if (focus) tab.focus();
    };
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(t); });
      t.addEventListener('keydown', function (e) {
        var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (d) select(tabs[(i + d + tabs.length) % tabs.length], true);
      });
    });
    var first = box.querySelector('[role="tab"][aria-selected="true"]') || tabs[0];
    if (first) select(first);
  });

  // Header shadow once the page has scrolled
  var header = document.querySelector('.site-header');
  if (header) {
    var onScroll = function () { header.classList.toggle('is-scrolled', window.scrollY > 8); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Auto-scrolling strip (awards): items are cloned once so the loop is
  // seamless; it pauses on hover, focus and touch, and stays a normal
  // swipeable scroller for visitors who prefer reduced motion.
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('.scroller[data-autoscroll]').forEach(function (track) {
      var originals = Array.prototype.slice.call(track.children);
      originals.forEach(function (el) {
        var c = el.cloneNode(true);
        c.setAttribute('aria-hidden', 'true');
        c.querySelectorAll('a, button').forEach(function (f) { f.tabIndex = -1; });
        track.appendChild(c);
      });
      track.classList.add('is-auto');
      var n = originals.length;
      // Measure the loop length once (and again when the strip resizes),
      // not on every animation frame, to avoid forced layout.
      var half = 0;
      var measure = function () { half = track.children[n].offsetLeft - track.children[0].offsetLeft; };
      measure();
      if ('ResizeObserver' in window) new ResizeObserver(measure).observe(track);
      else window.addEventListener('resize', measure);
      var pos = track.scrollLeft, paused = false, resumeT, last = null, speed = 40; // px per second
      var pause = function () { paused = true; clearTimeout(resumeT); };
      var resume = function (delay) {
        clearTimeout(resumeT);
        resumeT = setTimeout(function () { pos = track.scrollLeft; last = null; paused = false; }, delay || 0);
      };
      track.addEventListener('mouseenter', pause);
      track.addEventListener('mouseleave', function () { resume(); });
      track.addEventListener('focusin', pause);
      track.addEventListener('focusout', function () { resume(); });
      track.addEventListener('touchstart', pause, { passive: true });
      track.addEventListener('touchend', function () { resume(2500); }, { passive: true });
      track.addEventListener('wheel', function () { pause(); resume(2500); }, { passive: true });
      var step = function (t) {
        if (!paused && !document.hidden) {
          if (last !== null && half > 0) {
            pos += speed * Math.min(t - last, 100) / 1000;
            if (pos >= half) pos -= half;
            track.scrollLeft = pos;
          }
          last = t;
        } else {
          last = null;
          if (half > 0 && track.scrollLeft >= half) track.scrollLeft -= half;
        }
        requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  // JotForm contact form: built only when it nears the screen. The form brings
  // reCAPTCHA and ~2 MB of third-party script, so loading it up front was the
  // main cause of slow load and blocked main thread on the home page.
  var loadScript = function (src, onload) {
    var sc = document.createElement('script');
    sc.src = src; sc.async = true;
    if (onload) sc.onload = onload;
    document.head.appendChild(sc);
  };
  var forms = document.querySelectorAll('[data-jotform]');
  var buildForm = function (box) {
    if (box.dataset.loaded) return;
    box.dataset.loaded = '1';
    var id = box.getAttribute('data-jotform');
    var f = document.createElement('iframe');
    f.id = 'JotFormIFrame-' + id;
    f.title = 'Contact form';
    f.src = 'https://form.jotform.com/' + id;
    f.allow = 'geolocation; microphone; camera; fullscreen';
    f.setAttribute('allowtransparency', 'true');
    box.appendChild(f);
    loadScript('https://cdn.jotfor.ms/s/umd/latest/for-form-embed-handler.js', function () {
      if (window.jotformEmbedHandler) window.jotformEmbedHandler("iframe[id='" + f.id + "']", 'https://form.jotform.com/');
    });
  };
  if (forms.length) {
    if ('IntersectionObserver' in window) {
      var fio = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { fio.unobserve(en.target); buildForm(en.target); } });
      }, { rootMargin: '400px 0px' });
      forms.forEach(function (box) { fio.observe(box); });
    } else {
      forms.forEach(buildForm);
    }
  }

  // Collect.chat widget: loaded on the visitor's first scroll, tap, click or
  // key press instead of during page load.
  var chatEvents = ['scroll', 'pointerdown', 'keydown', 'touchstart'];
  var loadChat = function () {
    chatEvents.forEach(function (ev) { window.removeEventListener(ev, loadChat, { passive: true }); });
    if (window.CollectId) return;
    window.CollectId = '5db1efdece96ee05323484e9';
    loadScript('https://collectcdn.com/launcher.js');
  };
  chatEvents.forEach(function (ev) { window.addEventListener(ev, loadChat, { passive: true }); });

  // Accordions: one item open at a time within each .accordion, with a smooth
  // open/close. Without JS they still work as plain <details>.
  var reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  var animate = function (d, opening) {
    var summary = d.querySelector('summary');
    if (d._anim) d._anim.cancel();
    if (reduceMotion.matches || !d.animate) {
      d.classList.remove('is-closing');
      d.open = opening;
      return;
    }
    var start = d.offsetHeight;
    var edges = d.offsetHeight - d.clientHeight;
    if (opening) d.open = true;
    var end = opening ? d.offsetHeight : summary.offsetHeight + edges;
    d.classList.toggle('is-closing', !opening);
    d.style.overflow = 'hidden';
    d._anim = d.animate({ height: [start + 'px', end + 'px'] }, { duration: 320, easing: 'cubic-bezier(.2,.7,.2,1)' });
    d._anim.onfinish = function () {
      if (!opening) d.open = false;
      d.classList.remove('is-closing');
      d.style.overflow = '';
      d._anim = null;
    };
    d._anim.oncancel = function () { d.style.overflow = ''; };
  };
  document.querySelectorAll('.accordion').forEach(function (acc) {
    var items = acc.querySelectorAll('details');
    items.forEach(function (d) {
      var summary = d.querySelector('summary');
      if (!summary) return;
      summary.addEventListener('click', function (e) {
        e.preventDefault();
        var opening = !d.open || d.classList.contains('is-closing');
        if (opening) {
          items.forEach(function (o) { if (o !== d && o.open && !o.classList.contains('is-closing')) animate(o, false); });
        }
        animate(d, opening);
      });
    });
  });

  // In-page links (e.g. Service Areas > Huntsville -> #hsvpi). Content above the target that
  // loads late (the reviews widget, images) changes the page height mid-scroll, so a normal
  // smooth scroll stops short and then has to correct. Instead, glide to the target while
  // re-reading its position every frame, then hold it in place for a few seconds if anything
  // still moves. Any scrolling by the visitor stops both.
  var reduceScroll = matchMedia('(prefers-reduced-motion: reduce)');
  var glide = { el: null, raf: 0, ro: null, until: 0 };
  var targetY = function (el) {
    var pad = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    var max = document.documentElement.scrollHeight - window.innerHeight;
    return Math.max(0, Math.min(max, el.getBoundingClientRect().top + window.pageYOffset - pad));
  };
  // Instant scroll that works the same everywhere: the page sets scroll-behavior: smooth in CSS,
  // which would turn every step of the glide into its own little smooth scroll, so switch it off
  // for the duration and use the plain two-argument scrollTo.
  var rootStyle = document.documentElement.style;
  var jumpTo = function (y) { rootStyle.scrollBehavior = 'auto'; window.scrollTo(0, y); };
  var stopGlide = function () {
    glide.el = null;
    rootStyle.scrollBehavior = '';
    if (glide.raf) { cancelAnimationFrame(glide.raf); glide.raf = 0; }
    if (glide.ro) { glide.ro.disconnect(); glide.ro = null; }
    ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) { window.removeEventListener(ev, stopGlide); });
  };
  var holdTarget = function (el) {
    setTimeout(function () { if (glide.el === el) stopGlide(); }, 4000);
    if (!('ResizeObserver' in window)) return;
    glide.until = Date.now() + 4000;
    glide.ro = new ResizeObserver(function () {
      if (glide.el !== el || Date.now() > glide.until) { stopGlide(); return; }
      jumpTo(targetY(el));
    });
    glide.ro.observe(document.body);
  };
  var glideTo = function (el) {
    stopGlide();
    glide.el = el;
    // Start any embedded form in the target's section now, so it has loaded and settled by the time
    // the glide arrives instead of popping in (and resizing its section) as the visitor gets there.
    var sect = el.closest('section') || el.parentNode;
    if (sect && typeof buildForm === 'function') sect.querySelectorAll('[data-jotform]').forEach(buildForm);
    ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) { window.addEventListener(ev, stopGlide, { passive: true }); });
    if (reduceScroll.matches) { jumpTo(targetY(el)); holdTarget(el); return; }
    var from = window.pageYOffset;
    var dist = Math.abs(targetY(el) - from);
    var dur = Math.min(1000, Math.max(400, dist / 6));
    var t0 = performance.now();
    var step = function (now) {
      if (glide.el !== el) return;
      var t = Math.min(1, (now - t0) / dur);
      var e = t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;  // ease in-out
      jumpTo(from + (targetY(el) - from) * e);                            // target re-read every frame
      if (t < 1) glide.raf = requestAnimationFrame(step);
      else { glide.raf = 0; holdTarget(el); }
    };
    glide.raf = requestAnimationFrame(step);
  };
  var hashTarget = function (hash) {
    if (!hash || hash.length < 2) return null;
    try { return document.getElementById(decodeURIComponent(hash.slice(1))); } catch (err) { return null; }
  };
  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest && e.target.closest('a[href*="#"]');
    if (!a || !a.hash || a.pathname !== location.pathname || a.host !== location.host) return;
    var el = hashTarget(a.hash);
    if (!el) return;
    e.preventDefault();
    if (location.hash !== a.hash) history.pushState(null, '', a.hash);
    glideTo(el);
  });
  // Arriving from another page with a #hash: take over from wherever the browser's own jump got to.
  var arrive = hashTarget(location.hash);
  if (arrive) requestAnimationFrame(function () { glideTo(arrive); });
  window.addEventListener('popstate', function () { var el = hashTarget(location.hash); if (el) glideTo(el); });

  // Reveal on scroll (skipped when the visitor prefers reduced motion)
  var items = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    items.forEach(function (el) { el.classList.add('is-visible'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('is-visible'); io.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (el) { io.observe(el); });
  }
})();
