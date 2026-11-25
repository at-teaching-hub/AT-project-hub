/**
 * Robot Competition Result - Google Apps Script
 *
 * Recommended card sheet layout:
 *   A1: ROUTE
 *   B1: CARD NUMBER
 *   A2+: route letter
 *   B2+: card UID
 *
 * The script also detects the reversed A=CARD NUMBER / B=ROUTE layout.
 *
 * cards response:
 *   UID|ROUTE
 *   UID|ROUTE
 */

const CONFIG = {
  API_TOKEN: 'CHANGE_ME_RANDOM_TOKEN',
  CARD_SHEET_NAME: 'CARD',
  RESULT_SHEET_NAME: 'result',
  CARD_NUMBER_HEADER: 'CARD NUMBER',
  ROUTE_HEADER: 'ROUTE'
};

function doGet(e) {
  const params = e && e.parameter ? e.parameter : {};

  if (String(params.token || '') !== CONFIG.API_TOKEN) {
    return text_('ERROR_BAD_TOKEN');
  }

  const action = String(params.action || '');

  if (action === 'cards') return getCards_();

  if (action === 'log') {
    return logResult_(
      String(params.uid || ''),
      String(params.result || ''),
      String(params.note || '')
    );
  }

  return text_('ERROR_UNKNOWN_ACTION');
}

function getCards_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.CARD_SHEET_NAME);

  if (!sheet) return text_('ERROR_CARD_SHEET_NOT_FOUND');

  const lastRow = sheet.getLastRow();
  if (lastRow < 1) return text_('');

  const values = sheet.getRange(1, 1, lastRow, 2).getValues();
  const headerA = String(values[0][0] || '').trim().toUpperCase();
  const headerB = String(values[0][1] || '').trim().toUpperCase();

  // Default layout: A = ROUTE, B = CARD NUMBER.
  let routeColumn = 0;
  let cardColumn = 1;

  if (headerA.indexOf('CARD') >= 0 && headerB.indexOf('ROUTE') >= 0) {
    routeColumn = 1;
    cardColumn = 0;
  }

  const cards = [];
  const seen = {};

  for (let i = 1; i < values.length; i++) {
    const route = normalizeRoute_(values[i][routeColumn]);
    const uid = normalizeUid_(values[i][cardColumn]);
    if (!route || !uid || seen[uid]) continue;
    seen[uid] = true;
    cards.push(uid + '|' + route);
  }

  return text_(cards.join('\n'));
}

function logResult_(uid, result, note) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(CONFIG.RESULT_SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(CONFIG.RESULT_SHEET_NAME);

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['TIMESTAMP', 'CARD NUMBER', 'RESULT', 'NOTE']);
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    sheet.appendRow([
      new Date(),
      normalizeUid_(uid) || String(uid).trim(),
      String(result).trim(),
      String(note).trim()
    ]);
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }

  return text_('OK');
}

function normalizeRoute_(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9_-]/g, '')
    .slice(0, 7);
}

function normalizeUid_(value) {
  const raw = String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[^0-9A-F]/g, '');

  if (!raw || (raw.length !== 8 && raw.length !== 14)) return '';
  return raw.match(/.{2}/g).join(':');
}

function text_(value) {
  return ContentService
    .createTextOutput(String(value))
    .setMimeType(ContentService.MimeType.TEXT);
}
