/**
 * Klikss — Google Ads-script
 * ---------------------------------------------------------------
 * Schrijft elke advertentieklik (GCLID) met keyword, stad, apparaat,
 * gemiddelde CPC van dat keyword die dag en (indien bekend) de zoekterm
 * in het tabblad "Ads kliks" van de Google Sheet "Klikss".
 *
 * Installeren:
 *  - Google Ads > Tools > Bulkacties > Scripts > + Nieuw script
 *  - Plak deze code, vul hieronder SHEET_URL in (de link van de Sheet "Klikss").
 *  - Autoriseren > Voorbeeld (test) > Uitvoeren.
 *  - Frequentie: Dagelijks, 07:00.
 *  Bij de eerste keer worden de laatste 30 dagen ingelezen; daarna elke dag gisteren en eergisteren.
 */

var SHEET_URL = 'PLAK_HIER_DE_LINK_VAN_DE_SHEET_KLIKSS';
var TAB = 'Ads kliks';
var EERSTE_KEER_DAGEN = 30;

function main() {
  var sh = SpreadsheetApp.openByUrl(SHEET_URL).getSheetByName(TAB);
  if (!sh) throw new Error('Tabblad "' + TAB + '" niet gevonden. Voer eerst setup() uit in de Sheet.');

  // al opgeslagen GCLID's (geen dubbele regels)
  var bekend = {};
  if (sh.getLastRow() > 1) {
    sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues().forEach(function (r) { bekend[r[0]] = true; });
  }
  var dagen = sh.getLastRow() > 1 ? 2 : EERSTE_KEER_DAGEN;
  var tz = AdsApp.currentAccount().getTimeZone();
  var geoCache = {};
  var nieuw = [];

  for (var i = dagen; i >= 1; i--) {
    var d = Utilities.formatDate(new Date(Date.now() - i * 86400000), tz, 'yyyy-MM-dd');

    // gemiddelde CPC per keyword op die dag
    var cpc = {};
    var it = AdsApp.search(
      'SELECT ad_group_criterion.resource_name, metrics.average_cpc FROM keyword_view ' +
      "WHERE segments.date = '" + d + "' AND metrics.clicks > 0");
    while (it.hasNext()) {
      var r = it.next();
      cpc[r.adGroupCriterion.resourceName] = (Number(r.metrics.averageCpc) || 0) / 1e6;
    }

    // zoektermen per keyword op die dag
    var termen = {};
    it = AdsApp.search(
      'SELECT segments.keyword.ad_group_criterion, search_term_view.search_term, metrics.clicks ' +
      "FROM search_term_view WHERE segments.date = '" + d + "' AND metrics.clicks > 0");
    while (it.hasNext()) {
      var s = it.next();
      var kw = s.segments.keyword.adGroupCriterion;
      (termen[kw] = termen[kw] || []).push(s.searchTermView.searchTerm);
    }

    // de kliks zelf
    it = AdsApp.search(
      'SELECT click_view.gclid, click_view.keyword, click_view.keyword_info.text, ' +
      'click_view.keyword_info.match_type, click_view.location_of_presence.city, ' +
      'click_view.area_of_interest.city, campaign.name, ad_group.name, segments.device ' +
      "FROM click_view WHERE segments.date = '" + d + "'");
    while (it.hasNext()) {
      var c = it.next();
      var g = c.clickView.gclid;
      if (!g || bekend[g]) continue;
      bekend[g] = true;
      var kwRes = c.clickView.keyword || '';
      var info = c.clickView.keywordInfo || {};
      var stadRes = (c.clickView.locationOfPresence && c.clickView.locationOfPresence.city) ||
        (c.clickView.areaOfInterest && c.clickView.areaOfInterest.city) || '';
      var t = termen[kwRes] || [];
      var zoekterm = t.length === 1 ? t[0] : (t.length > 1 ? 'één van: ' + t.join(' | ') : '');
      nieuw.push([g, d, c.campaign.name, c.adGroup.name, info.text || '', info.matchType || '',
        stadRes, c.segments.device || '', kwRes && cpc[kwRes] ? cpc[kwRes] : '', zoekterm]);
      if (stadRes) geoCache[stadRes] = '';
    }
  }

  // stadsnamen ophalen
  var ids = Object.keys(geoCache);
  for (var j = 0; j < ids.length; j += 100) {
    var stuk = ids.slice(j, j + 100).map(function (x) { return "'" + x + "'"; }).join(',');
    var gi = AdsApp.search('SELECT geo_target_constant.resource_name, geo_target_constant.name ' +
      'FROM geo_target_constant WHERE geo_target_constant.resource_name IN (' + stuk + ')');
    while (gi.hasNext()) {
      var gg = gi.next();
      geoCache[gg.geoTargetConstant.resourceName] = gg.geoTargetConstant.name;
    }
  }
  nieuw.forEach(function (r) { r[6] = geoCache[r[6]] || r[6]; });

  if (nieuw.length) {
    sh.getRange(sh.getLastRow() + 1, 1, nieuw.length, nieuw[0].length).setValues(nieuw);
  }
  Logger.log(nieuw.length + ' nieuwe kliks toegevoegd.');
}
