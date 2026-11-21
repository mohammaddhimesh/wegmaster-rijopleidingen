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
