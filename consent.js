/* WegMaster — tracking-instellingen (laden vóór gtag.js)
   - Google Ads / GA4: altijd aan (consent standaard 'granted'), geen cookiebanner.
   - Microsoft Clarity: laadt altijd, met cookies.
   - Eigenaar-schakelaar: open 1x  /?owner=1  op je eigen telefoon/pc
     -> Clarity laadt daar nooit meer en GA4 telt je niet mee.
     Ongedaan maken: /?owner=0                                               */
(function () {
  var OWNER_KEY = 'wm_owner';
  var CLARITY_ID = 'yxaoh4p5b0';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { dataLayer.push(arguments); };

  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function write(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function del(k) { try { localStorage.removeItem(k); } catch (e) {} }

  // Oude keuze uit de vroegere cookiebanner opruimen (anders blijft 'denied' hangen)
  del('wm_consent');

  // ---- Eigenaar-schakelaar (?owner=1 / ?owner=0) ----
  try {
    var qs = new URLSearchParams(location.search);
    if (qs.get('owner') === '1') write(OWNER_KEY, '1');
    if (qs.get('owner') === '0') del(OWNER_KEY);
  } catch (e) {}
  var isOwner = read(OWNER_KEY) === '1';

  // Eigenaar telt ook niet mee in Google Analytics 4 (Google Ads-conversies blijven gewoon werken)
  if (isOwner) { window['ga-disable-G-RQ52QDSQX7'] = true; }

  // ---- Google Consent Mode v2: alles toegestaan ----
  gtag('consent', 'default', {
    ad_storage: 'granted',
    ad_user_data: 'granted',
    ad_personalization: 'granted',
    analytics_storage: 'granted'
  });
  gtag('set', 'ads_data_redaction', false);
  gtag('set', 'url_passthrough', true);

  // ---- Herkomst onthouden: Meta-advertentie (utm_source=meta of fbclid) ----
  try {
    var q2 = new URLSearchParams(location.search);
    if (q2.get('utm_source') === 'meta' || q2.get('fbclid')) {
      write('wm_meta_ts', String(Date.now()));
      write('wm_meta_ad', q2.get('utm_content') || '');
    }
  } catch (e) {}
  // Bron voor e-mail en WhatsApp: de laatste advertentie-klik wint
  window.wmBron = function () {
    var mts = Number(read('wm_meta_ts') || 0), gts = Number(read('wm_gclid_ts') || 0);
    var hasG = !!read('wm_gclid');
    if (mts && mts >= gts) { var ad = read('wm_meta_ad'); return 'Meta advertentie' + (ad ? ' (' + ad + ')' : ''); }
    return hasG ? 'Google advertentie' : 'Website (geen advertentie)';
  };

  // ---- Meta Pixel (niet voor de eigenaar). Leeg ID = uit. ----
  var META_PIXEL_ID = '';
  window.wmMeta = function () {};
  if (META_PIXEL_ID && !isOwner) {
    var n = window.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
    if (!window._fbq) window._fbq = n;
    n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
    fbq('init', META_PIXEL_ID);
    fbq('track', 'PageView');
    window.wmMeta = function (ev, params) { try { fbq('track', ev, params || {}); } catch (e) {} };
    // Script pas laden na de pagina, zodat het de laadsnelheid niet raakt
    var loadFb = function () {
      var t = document.createElement('script'); t.async = true;
      t.src = 'https://connect.facebook.net/en_US/fbevents.js';
      document.head.appendChild(t);
    };
    if (document.readyState === 'complete') setTimeout(loadFb, 1500);
    else window.addEventListener('load', function () { setTimeout(loadFb, 1500); });
    // ViewContent: 1x per pagina zodra een pakketkaart in beeld komt
    var seen = false, tries = 0;
    var watchCards = function () {
      if (seen || !('IntersectionObserver' in window)) return;
      var cards = document.querySelectorAll('.auto-package-card, .pkg-card');
      if (cards.length) {
        var io = new IntersectionObserver(function (es) {
          es.forEach(function (x) { if (x.isIntersecting && !seen) { seen = true; window.wmMeta('ViewContent', { content_name: 'Lespakketten' }); io.disconnect(); } });
        }, { threshold: 0.5 });
        cards.forEach(function (c) { io.observe(c); });
      } else if (++tries < 10) { setTimeout(watchCards, 1500); }
    };
    window.addEventListener('load', watchCards);
  }

  // ---- Microsoft Clarity (niet voor de eigenaar) ----
  if (!isOwner) {
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', CLARITY_ID);
    window.clarity('consentv2', { ad_Storage: 'granted', analytics_Storage: 'granted' });
  }
})();
