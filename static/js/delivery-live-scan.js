/**
 * Live-скан поставки: парсинг штрих-коду (логіка supplies/tasks.py) + пошук у попередньо завантажених GeneralSupply.
 */
(function (global) {
  'use strict';

  const GS_SEP = '\x1d';

  function buildGeneralSupplyIndex(items) {
    const bySmn = new Map();
    const byRef = new Map();
    for (const gs of items) {
      if (gs.SMN_code) {
        bySmn.set(gs.SMN_code, gs);
      }
      if (gs.ref) {
        byRef.set(gs.ref, gs);
      }
    }
    return { bySmn, byRef };
  }

  function findGeneralSupplyBySmn(smn, index) {
    const candidates = [];
    const seen = new Set();

    function add(value) {
      if (value && !seen.has(value)) {
        seen.add(value);
        candidates.push(value);
      }
    }

    add(smn);
    if (smn.startsWith('01') && smn.length > 2) {
      add(smn.slice(2));
    } else {
      add('01' + smn);
    }

    for (const candidate of candidates) {
      const gs = index.bySmn.get(candidate);
      if (gs) {
        return gs;
      }
    }
    return null;
  }

  function parseExpiryYyMmDd(dateStr) {
    if (!dateStr || dateStr.length !== 6) {
      return null;
    }
    const yy = parseInt(dateStr.slice(0, 2), 10);
    const mm = parseInt(dateStr.slice(2, 4), 10);
    const dd = parseInt(dateStr.slice(4, 6), 10);
    if (Number.isNaN(yy) || Number.isNaN(mm) || Number.isNaN(dd)) {
      return null;
    }
    const year = 2000 + yy;
    const d = new Date(year, mm - 1, dd);
    if (d.getFullYear() !== year || d.getMonth() !== mm - 1 || d.getDate() !== dd) {
      return null;
    }
    return d;
  }

  function formatDateDisplay(date) {
    if (!date) {
      return '—';
    }
    const dd = String(date.getDate()).padStart(2, '0');
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const yyyy = date.getFullYear();
    return `${dd}.${mm}.${yyyy}`;
  }

  function formatDateIso(date) {
    if (!date) {
      return '';
    }
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${date.getFullYear()}-${mm}-${dd}`;
  }

  function parseDataMatrix(barcodeStr) {
    let workStr = barcodeStr;
    let gtin = '';
    let dateExpired = '';
    let lot = '';
    let smn = '';

    if (workStr.startsWith('01')) {
      gtin = workStr.slice(2, 16);
      workStr = workStr.slice(16);
    } else {
      const match01 = workStr.match(new RegExp('(?:^|' + GS_SEP + ')01(\\d{14})'));
      if (match01) {
        gtin = match01[1];
        workStr = workStr.replace(match01[0], '|', 1);
      }
    }

    const match11 = workStr.match(/11(\d{6})/);
    if (match11) {
      workStr = workStr.replace(match11[0], '|', 1);
    }

    const match17 = workStr.match(/17(\d{6})/);
    if (match17) {
      dateExpired = match17[1];
      workStr = workStr.replace(match17[0], '|', 1);
    }

    const match240 = workStr.match(/240([A-Za-z0-9]+?)(?:\x1d|\||422|$)/);
    let smnFound = '';
    if (match240) {
      smnFound = match240[1];
      workStr = workStr.replace(match240[0], '|', 1);
    }

    const match10 = workStr.match(/10([A-Za-z0-9]+?)(?:\x1d|\||$)/);
    if (match10) {
      lot = match10[1];
    }

    smn = smnFound || gtin;
    return { smn, lot, dateExpired, searchByRef: false };
  }

  function parseSiemens(barcodeStr) {
    const arrItem = barcodeStr.split(',');
    if (arrItem.length === 1) {
      const barcode = arrItem[0];
      const smn = barcode.slice(32, -6).slice(-8);
      const lot = barcode.slice(18, -25);
      let dateExpired = barcode.slice(23, -17);
      dateExpired = dateExpired.slice(-6);
      return { smn, lot, dateExpired, searchByRef: false };
    }
    if (arrItem.length === 3) {
      return {
        smn: arrItem[0],
        lot: arrItem[1],
        dateExpired: arrItem[2],
        searchByRef: true,
      };
    }
    return null;
  }

  function parseBarcode(raw, barcodeType) {
    const trimmed = (raw || '').trim();
    if (!trimmed) {
      return null;
    }
    if (barcodeType === 'Siemens') {
      return parseSiemens(trimmed);
    }
    if (barcodeType === 'Data Matrix') {
      return parseDataMatrix(trimmed);
    }
    return null;
  }

  function lookupGeneralSupply(parsed, raw, index) {
    if (!parsed) {
      return { recognized: false, raw };
    }
    let gs = null;
    if (parsed.searchByRef) {
      gs = index.byRef.get(parsed.smn) || null;
    } else {
      gs = findGeneralSupplyBySmn(parsed.smn, index);
    }
    const expiry = parseExpiryYyMmDd(parsed.dateExpired);
    if (gs) {
      return {
        recognized: true,
        raw,
        generalSupply: gs,
        smn: parsed.smn,
        lot: parsed.lot || '',
        expiry,
        expiryLabel: expiry ? formatDateDisplay(expiry) : (parsed.dateExpired || '—'),
        expiryIso: expiry ? formatDateIso(expiry) : '',
      };
    }
    return {
      recognized: false,
      raw,
      smn: parsed.smn,
      lot: parsed.lot || '',
      expiryLabel: parsed.dateExpired || '—',
    };
  }

  let audioContext = null;

  function getAudioContext() {
    if (!audioContext) {
      const Ctx = global.AudioContext || global.webkitAudioContext;
      if (!Ctx) {
        return null;
      }
      audioContext = new Ctx();
    }
    return audioContext;
  }

  function resumeAudioContext() {
    const ctx = getAudioContext();
    if (ctx && ctx.state === 'suspended') {
      return ctx.resume();
    }
    return Promise.resolve();
  }

  function playTone(ctx, frequency, startAt, duration, type, gainPeak) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type || 'sine';
    osc.frequency.setValueAtTime(frequency, startAt);
    gain.gain.setValueAtTime(0.0001, startAt);
    gain.gain.exponentialRampToValueAtTime(gainPeak, startAt + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(startAt);
    osc.stop(startAt + duration + 0.02);
  }

  /** kind: 'ok' (знайдено) | 'err' (не знайдено) */
  function playFeedback(kind) {
    const ctx = getAudioContext();
    if (!ctx) {
      return Promise.resolve();
    }
    return resumeAudioContext().then(function () {
      const t0 = ctx.currentTime + 0.01;
      if (kind === 'ok') {
        playTone(ctx, 1046.5, t0, 0.1, 'sine', 0.22);
        playTone(ctx, 1318.5, t0 + 0.11, 0.14, 'sine', 0.2);
      } else {
        playTone(ctx, 220, t0, 0.16, 'square', 0.12);
        playTone(ctx, 185, t0 + 0.22, 0.2, 'square', 0.1);
      }
    }).catch(function () { /* autoplay blocked */ });
  }

  function bindAudioUnlock(element) {
    if (!element || element.dataset.liveScanAudioBound === '1') {
      return;
    }
    element.dataset.liveScanAudioBound = '1';
    function unlock() {
      resumeAudioContext();
    }
    element.addEventListener('focus', unlock, { passive: true });
    element.addEventListener('click', unlock, { passive: true });
  }

  global.DeliveryLiveScan = {
    buildGeneralSupplyIndex,
    parseBarcode,
    lookupGeneralSupply,
    formatDateDisplay,
    formatDateIso,
    playFeedback,
    bindAudioUnlock,
  };
})(typeof window !== 'undefined' ? window : global);
