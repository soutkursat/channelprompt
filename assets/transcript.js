// Transkript ayrıştırma ve metrikler. Tamamen tarayıcıda çalışır; hiçbir veri sunucuya gönderilmez.
(function (root) {
  const DEFAULT_WPM = 150;
  const TS = "(?:(\\d{1,2}):)?(\\d{1,2}):(\\d{2})(?:[.,](\\d{1,3}))?";
  const CUE_RE = new RegExp(`^\\s*${TS}\\s*-->\\s*${TS}`);
  const LINE_TS_RE = new RegExp(`^\\s*[\\[(]?${TS}[\\])]?\\s*[-–:]?\\s*(.*)$`);

  const toSeconds = (h, m, s, ms) =>
    (+h || 0) * 3600 + +m * 60 + +s + (ms ? +ms.padEnd(3, "0") / 1000 : 0);

  function formatSeconds(total) {
    total = Math.floor(total);
    const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), s = total % 60;
    const pad = (n) => String(n).padStart(2, "0");
    return h ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
  }

  // "12:34", "1:02:03" veya "754" → saniye
  function parseDuration(value) {
    value = (value || "").trim();
    if (/^\d+$/.test(value)) return +value;
    const m = value.match(/^(?:(\d+):)?(\d{1,2}):(\d{2})$/);
    return m ? toSeconds(m[1], m[2], m[3]) : 0;
  }

  // "2.4M", "850K", "12 bin", "1.234.567" → sayı
  function parseViews(value) {
    value = (value || "").trim().toLowerCase().replace(/\s/g, "");
    const m = value.match(/^([\d.,]+)(k|b|bin|m|mn|milyon)?$/);
    if (!m) return 0;
    if (m[2]) return Math.round(parseFloat(m[1].replace(",", ".")) * (["k", "b", "bin"].includes(m[2]) ? 1e3 : 1e6));
    return +m[1].replace(/[.,]/g, "") || 0;
  }

  // SRT / VTT / YouTube "Transkripti göster" kopyası / düz metin → { segments: [{start, text}], timed }
  function parseTranscript(raw) {
    raw = (raw || "").replace(/\r\n/g, "\n").replace(/﻿/g, "").trim();
    if (!raw) return { segments: [], timed: false };
    const lines = raw.split("\n");

    if (lines.slice(0, 50).some((l) => CUE_RE.test(l))) {
      const segments = [];
      let current = [], start = null;
      for (const line of [...lines, ""]) {
        const cue = line.match(CUE_RE);
        if (cue) { start = toSeconds(cue[1], cue[2], cue[3], cue[4]); current = []; }
        else if (!line.trim()) {
          if (start !== null && current.length) segments.push({ start, text: current.join(" ") });
          start = null; current = [];
        } else if (start !== null) {
          const text = line.replace(/<[^>]+>/g, "").trim();
          if (text && current[current.length - 1] !== text) current.push(text);
        }
      }
      return { segments: segments.filter((s, i) => !i || s.text !== segments[i - 1].text), timed: true };
    }

    const timed = [];
    let pending = null;
    for (const line of lines) {
      if (!line.trim()) continue;
      const m = line.match(LINE_TS_RE);
      if (m) {
        const start = toSeconds(m[1], m[2], m[3], m[4]), text = m[5].trim();
        if (text) { timed.push({ start, text }); pending = null; } else pending = start;
      } else if (pending !== null) { timed.push({ start: pending, text: line.trim() }); pending = null; }
      else if (timed.length) timed[timed.length - 1].text += " " + line.trim();
    }
    const words = timed.reduce((n, s) => n + s.text.split(/\s+/).length, 0);
    if (timed.length >= 3 && words > 20) return { segments: timed, timed: true };

    return { segments: [{ start: 0, text: lines.map((l) => l.trim()).filter(Boolean).join(" ") }], timed: false };
  }

  // Bir videonun transkriptinden promptta kullanılacak bilgiler.
  function analyzeVideo({ transcript, durationSeconds }) {
    const { segments, timed } = parseTranscript(transcript);
    const text = segments.map((s) => s.text).join(" ");
    const words = text.split(/\s+/).filter(Boolean);
    const wpm = durationSeconds ? Math.round(words.length / (durationSeconds / 60)) : 0;
    const first30 = timed
      ? segments.filter((s) => s.start < 30).map((s) => s.text).join(" ")
      : words.slice(0, Math.round((wpm || DEFAULT_WPM) / 2)).join(" ");
    const sentences = text.split(/(?<=[.!?])\s+/).filter((s) => s.trim());
    const avgSentence = sentences.length ? words.length / sentences.length : 0;
    const body = timed ? segments.map((s) => `[${formatSeconds(s.start)}] ${s.text}`).join("\n") : text;
    return {
      timed, text, body, first30, first30Estimated: !timed,
      wordCount: words.length, wpm,
      estimatedMinutes: words.length ? +(words.length / (wpm || DEFAULT_WPM)).toFixed(1) : 0,
      sentenceCount: sentences.length, avgSentence: +avgSentence.toFixed(1),
      questionCount: (text.match(/\?/g) || []).length,
    };
  }

  const api = { parseTranscript, parseDuration, parseViews, formatSeconds, analyzeVideo, DEFAULT_WPM };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Transcript = api;
})(typeof window !== "undefined" ? window : globalThis);
