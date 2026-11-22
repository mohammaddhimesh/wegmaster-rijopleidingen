/**
 * Klikss — Apps Script voor de Google Sheet "Klikss"
 * ---------------------------------------------------------------
 * Wat doet dit?
 *  1. setup()  : maakt de tabbladen Bezoeken, Ads kliks, Overzicht en Per keyword
 *                (1x uitvoeren, daarna nooit meer nodig).
 *  2. doPost() : ontvangt elk advertentiebezoek van de website en schrijft/werkt
 *                één regel per bezoek bij in "Bezoeken".
 *
 * Installeren (in het account wegmasterrijopleidingen@gmail.com):
 *  - Maak een lege Google Sheet met de naam "Klikss".
 *  - Extensies > Apps Script > plak deze hele code > Opslaan.
 *  - Kies bovenin de functie "setup" > Uitvoeren > toegang toestaan.
 *  - Implementeren > Nieuwe implementatie > Type: Web-app
 *      Uitvoeren als: Ik   |   Wie heeft toegang: Iedereen
 *    > Implementeren > kopieer de Web-app-URL (eindigt op /exec) en stuur die naar Claude.
 */

var TAB_BEZOEKEN = 'Bezoeken';
var TAB_ADS = 'Ads kliks';
var TAB_OVERZICHT = 'Overzicht';
var TAB_KEYWORD = 'Per keyword';

var KOP_BEZOEKEN = ['Bezoek-ID', 'Tijd', 'GCLID', 'Pagina', 'Seconden', 'Kliks op site',
  'Scroll %', 'Prijzen gezien', 'Actie', 'Naam', 'Telefoon', 'Bericht', 'Apparaat'];
var KOP_ADS = ['GCLID', 'Datum', 'Campagne', 'Advertentiegroep', 'Keyword', 'Match',
  'Stad', 'Apparaat', 'CPC (gem. keyword die dag)', 'Zoekterm'];

function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.setSpreadsheetTimeZone('Europe/Amsterdam');

  var b = maakTab_(ss, TAB_BEZOEKEN, KOP_BEZOEKEN);
  b.getRange('B:B').setNumberFormat('dd-mm-yyyy hh:mm');
  var a = maakTab_(ss, TAB_ADS, KOP_ADS);
  a.getRange('B:B').setNumberFormat('dd-mm-yyyy');
  a.getRange('I:I').setNumberFormat('€ 0.00');

  // ---------- Overzicht: één regel per bezoek, met de Ads-gegevens erbij, filter op datum ----------
  var o = ss.getSheetByName(TAB_OVERZICHT) || ss.insertSheet(TAB_OVERZICHT);
  o.clear();
  o.getRange('A1:F1').setValues([['Van:', '', '', 'Tot en met:', '', '']]);
  o.getRange('B1').setFormula('=TODAY()-7');
  o.getRange('E1').setFormula('=TODAY()');
  o.getRange('B1').setNumberFormat('dd-mm-yyyy');
  o.getRange('E1').setNumberFormat('dd-mm-yyyy');
  o.getRange('G1').setValue('← pas de datums aan om te filteren');
  o.getRange('A1:G1').setFontWeight('bold');
  o.getRange('B1').setBackground('#fff3e0');
  o.getRange('E1').setBackground('#fff3e0');

  var kop = ['Tijd', 'Pagina', 'Keyword', 'Zoekterm', 'Stad', 'Apparaat', 'CPC', 'Seconden',
    'Kliks op site', 'Scroll %', 'Prijzen gezien', 'Actie', 'Naam', 'Telefoon', 'Bericht', 'GCLID',
    'Kort (<10 s)', 'Aangemeld'];
  o.getRange(3, 1, 1, kop.length).setValues([kop]).setFontWeight('bold')
    .setBackground('#17354d').setFontColor('#ffffff');
  var L = function (col) { return 'IFERROR(VLOOKUP(Bezoeken!C2:C,\'Ads kliks\'!A2:J,' + col + ',FALSE),"")'; };
  var f = '=IFERROR(SORT(FILTER({' +
    'Bezoeken!B2:B, Bezoeken!D2:D, ' + L(5) + ', ' + L(10) + ', ' + L(7) + ', ' +
    'IF(' + L(8) + '="",Bezoeken!M2:M,' + L(8) + '), ' + L(9) + ', ' +
    'Bezoeken!E2:E, Bezoeken!F2:F, Bezoeken!G2:G, Bezoeken!H2:H, Bezoeken!I2:I, ' +
    'Bezoeken!J2:J, Bezoeken!K2:K, Bezoeken!L2:L, Bezoeken!C2:C, ' +
    'IF(Bezoeken!E2:E<10,1,0), IF(Bezoeken!I2:I="Formulier",1,0)' +
    '}, Bezoeken!B2:B>=B1, Bezoeken!B2:B<E1+1), 1, FALSE), "Nog geen bezoeken in deze periode")';
  o.getRange('A4').setFormula('=ARRAYFORMULA(' + f.substring(1) + ')');
  o.getRange('A4:A').setNumberFormat('dd-mm-yyyy hh:mm');
  o.getRange('G4:G').setNumberFormat('€ 0.00');
  o.setFrozenRows(3);

  // ---------- Per keyword: welke keyword levert serieuze bezoekers / aanmeldingen ----------
  var k = ss.getSheetByName(TAB_KEYWORD) || ss.insertSheet(TAB_KEYWORD);
  k.clear();
  k.getRange('A1').setValue('Zelfde periode als het tabblad Overzicht (Van / Tot en met)').setFontStyle('italic');
  k.getRange('A3').setFormula(
    '=IFERROR(QUERY(Overzicht!A4:R, "select C, count(A), avg(H), sum(Q), sum(R), avg(G) ' +
    'where A is not null group by C order by count(A) desc ' +
    'label C \'Keyword\', count(A) \'Bezoeken\', avg(H) \'Gem. seconden\', sum(Q) \'Kort (<10 s)\', ' +
    'sum(R) \'Aanmeldingen\', avg(G) \'Gem. CPC\'", 0), "Nog geen gegevens")');
  k.getRange('A3:F3').setFontWeight('bold');
  k.getRange('C:C').setNumberFormat('0');
  k.getRange('F:F').setNumberFormat('€ 0.00');

  // volgorde van de tabbladen
  ss.setActiveSheet(o); ss.moveActiveSheet(1);
  ss.setActiveSheet(k); ss.moveActiveSheet(2);
  var leeg = ss.getSheetByName('Sheet1') || ss.getSheetByName('Blad1');
  if (leeg && ss.getSheets().length > 1) ss.deleteSheet(leeg);
  SpreadsheetApp.flush();
}

function maakTab_(ss, naam, kop) {
  var sh = ss.getSheetByName(naam) || ss.insertSheet(naam);
  if (sh.getLastRow() === 0) {
    sh.getRange(1, 1, 1, kop.length).setValues([kop]).setFontWeight('bold')
      .setBackground('#17354d').setFontColor('#ffffff');
    sh.setFrozenRows(1);
  }
  return sh;
}

// ---------- Ontvangen van de website (één bezoek = één regel, wordt bijgewerkt) ----------
function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    var v = JSON.parse(e.postData.contents);
    if (!v || !v.vid) return ok_();
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TAB_BEZOEKEN);
    var rij = [
      String(v.vid).slice(0, 40),
      new Date(Number(v.t0) || Date.now()),
      String(v.g || '').slice(0, 200),
      String(v.page || '').slice(0, 120),
      Number(v.secs) || 0,
      Number(v.kl) || 0,
      Number(v.sc) || 0,
      v.pr ? 'ja' : 'nee',
      String(v.act || '').slice(0, 20),
      String(v.naam || '').slice(0, 80),
      String(v.tel || '').slice(0, 30),
      String(v.msg || '').slice(0, 500),
      String(v.dev || '').slice(0, 20)
    ];
    var gevonden = sh.getRange('A:A').createTextFinder(rij[0]).matchEntireCell(true).findNext();
    if (gevonden) {
      sh.getRange(gevonden.getRow(), 1, 1, rij.length).setValues([rij]);
    } else {
      sh.appendRow(rij);
    }
  } catch (err) {
    // niets: de website mag hier nooit last van hebben
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
  return ok_();
}

function doGet() { return ok_(); }

function ok_() {
  return ContentService.createTextOutput('ok');
}
