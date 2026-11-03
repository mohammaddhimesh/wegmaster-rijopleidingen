/* WegMaster — cookietoestemming + Google Consent Mode v2 + Clarity Consent v2
   Laden vóór gtag.js.
   - Google Ads: zonder keuze/weigeren -> geen advertentiecookies (zoals voorheen).
   - Microsoft Clarity: laadt ALTIJD, maar cookieless tot "Accepteren".
     Na "Accepteren" mag Clarity cookies gebruiken.
   - Eigenaar-schakelaar: open 1x  /?owner=1  op je eigen telefoon/pc
     -> Clarity laadt daar nooit meer (jij wordt niet opgenomen).
     Ongedaan maken: /?owner=0                                               */
(function () {
  var KEY = 'wm_consent';
  var OWNER_KEY = 'wm_owner';
  var CLARITY_ID = 'yxaoh4p5b0';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { dataLayer.push(arguments); };

  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function write(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function del(k) { try { localStorage.removeItem(k); } catch (e) {} }

  // ---- Eigenaar-schakelaar (?owner=1 / ?owner=0) ----
  try {
    var qs = new URLSearchParams(location.search);
    if (qs.get('owner') === '1') write(OWNER_KEY, '1');
    if (qs.get('owner') === '0') del(OWNER_KEY);
  } catch (e) {}
  var isOwner = read(OWNER_KEY) === '1';

  // ---- Google Consent Mode v2 ----
  var DENIED = { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'denied' };
  var GRANTED = { ad_storage: 'granted', ad_user_data: 'granted', ad_personalization: 'granted', analytics_storage: 'granted' };

  gtag('consent', 'default', Object.assign({ wait_for_update: 500 }, DENIED));
  gtag('set', 'ads_data_redaction', true);
  gtag('set', 'url_passthrough', true);

  // ---- Microsoft Clarity: altijd laden (behalve eigenaar), standaard cookieless ----
  function clarityConsent(granted) {
    if (isOwner || typeof window.clarity !== 'function') return;
    window.clarity('consentv2', {
      ad_Storage: granted ? 'granted' : 'denied',
      analytics_Storage: granted ? 'granted' : 'denied'
    });
  }

  if (!isOwner) {
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', CLARITY_ID);
    clarityConsent(false); // start cookieless
  }

  function apply(choice) {
    if (choice === 'granted') {
      gtag('consent', 'update', GRANTED);
      gtag('set', 'ads_data_redaction', false);
      clarityConsent(true);
    } else {
      gtag('consent', 'update', DENIED);
      clarityConsent(false);
    }
  }

  var stored = read(KEY);
  if (stored) apply(stored);

  function banner() {
    if (document.getElementById('wm-consent')) return;
    var css = document.createElement('style');
    css.textContent =
      '#wm-consent{position:fixed;left:12px;right:12px;bottom:12px;z-index:2147483000;max-width:560px;margin:0 auto;' +
      'background:#0B1B2E;color:#E7EEF5;border-radius:16px;padding:16px 18px;box-shadow:0 18px 40px -12px rgba(0,0,0,.45);' +
      'font:14px/1.45 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}' +
      '#wm-consent p{margin:0 0 12px}#wm-consent b{color:#fff}' +
      '#wm-consent .wm-c-row{display:flex;gap:10px;flex-wrap:wrap}' +
      '#wm-consent button{flex:1 1 140px;border:0;border-radius:999px;padding:11px 16px;font:inherit;font-weight:700;cursor:pointer}' +
      '#wm-consent .wm-c-yes{background:#F3801E;color:#fff}#wm-consent .wm-c-no{background:transparent;color:#E7EEF5;border:1px solid #3A5068}' +
      '#wm-consent button:focus-visible{outline:3px solid #F3801E;outline-offset:2px}' +
      '@media(max-width:879px){#wm-consent{bottom:calc(72px + env(safe-area-inset-bottom))}}';
    document.head.appendChild(css);
    var en = (document.documentElement.lang || 'nl').indexOf('en') === 0;
    var el = document.createElement('div');
    el.id = 'wm-consent'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'Cookies');
    el.innerHTML = en
      ? '<p><b>Cookies</b><br>We use cookies for statistics (Microsoft Clarity) and advertising (Google Ads). Is that OK? Without consent we only measure anonymously, without cookies.</p><div class="wm-c-row"><button type="button" class="wm-c-yes">Accept</button><button type="button" class="wm-c-no">Decline</button></div>'
      : '<p><b>Cookies</b><br>We gebruiken cookies voor statistieken (Microsoft Clarity) en advertenties (Google Ads). Vind je dat goed? Zonder toestemming meten we alleen anoniem, zonder cookies.</p><div class="wm-c-row"><button type="button" class="wm-c-yes">Accepteren</button><button type="button" class="wm-c-no">Weigeren</button></div>';
    document.body.appendChild(el);
    el.querySelector('.wm-c-yes').addEventListener('click', function () { write(KEY, 'granted'); apply('granted'); el.remove(); });
    el.querySelector('.wm-c-no').addEventListener('click', function () { write(KEY, 'denied'); apply('denied'); el.remove(); });
  }

  // Keuze later wijzigen: elk element met data-cookie-settings opent de banner opnieuw
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-cookie-settings]');
    if (t) { e.preventDefault(); banner(); }
  });

  if (!stored) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', banner);
    else banner();
  }
})();
