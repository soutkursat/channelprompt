// Çalıştırma: node --test
const test = require("node:test");
const assert = require("node:assert");
const T = require("../assets/transcript.js");
const { buildPrompt } = require("../assets/prompt.js");

test("SRT ayrıştırma", () => {
  const r = T.parseTranscript("1\n00:00:01,000 --> 00:00:04,000\nHello there\n\n2\n00:00:31,500 --> 00:00:35,000\nLater <i>line</i>\n");
  assert.strictEqual(r.timed, true);
  assert.deepStrictEqual(r.segments, [{ start: 1, text: "Hello there" }, { start: 31.5, text: "Later line" }]);
});

test("VTT ayrıştırma", () => {
  const r = T.parseTranscript("WEBVTT\n\n00:00.000 --> 00:02.000\nFirst\n\n00:40.000 --> 00:42.000\nSecond\n");
  assert.deepStrictEqual(r.segments.map((s) => s.start), [0, 40]);
});

test("YouTube transkript kopyası", () => {
  const raw = "0:00\nIn 1945 something happened that nobody expected\n0:05\nand the whole world changed forever after\n0:32\nthen things got even stranger for everyone\n1:10 and more text here too";
  const r = T.parseTranscript(raw);
  assert.strictEqual(r.timed, true);
  assert.deepStrictEqual(r.segments.map((s) => s.start), [0, 5, 32, 70]);
});

test("düz metin: ilk 30 sn tahmini", () => {
  const a = T.analyzeVideo({ transcript: "word ".repeat(300), durationSeconds: 120 });
  assert.strictEqual(a.timed, false);
  assert.strictEqual(a.wpm, 150);
  assert.strictEqual(a.first30.split(" ").length, 75);
  assert.strictEqual(a.first30Estimated, true);
});

test("izlenme ve süre", () => {
  assert.strictEqual(T.parseViews("2.4M"), 2400000);
  assert.strictEqual(T.parseViews("850K"), 850000);
  assert.strictEqual(T.parseViews("12 bin"), 12000);
  assert.strictEqual(T.parseViews("1.234.567"), 1234567);
  assert.strictEqual(T.parseDuration("18:42"), 1122);
  assert.strictEqual(T.parseDuration("1:02:03"), 3723);
});

test("prompt tüm verileri ve adımları içerir", () => {
  const p = buildPrompt({
    channelName: "Test Kanal", channelUrl: "https://youtube.com/@test", language: "İngilizce",
    notes: "tarih", otherTitles: "Diğer A\nDiğer B",
    videos: [
      { title: "Video Bir", transcript: "0:00 Hook line here now\n0:10 second line of it\n0:40 third part text more words " + "x ".repeat(60),
        views: 1200000, durationSeconds: 600, description: "açıklama", thumbnailName: "thumb1.jpg" },
      { title: "Video İki", transcript: "plain ".repeat(80), views: 0, durationSeconds: 0, description: "", thumbnailName: "" },
    ],
  });
  for (const s of ["# Test Kanal", "Video Bir", "Video İki", '"thumb1.jpg" → VİDEO 1', "Diğer B", "<transkript_2>",
                   'tahmini="evet"', "AŞAMA 0", "KANAL DNA RAPORU", "ADIM 1", "ADIM 6", "/seo", "İngilizce", "1.200.000"]) {
    assert.ok(p.includes(s), "eksik: " + s);
  }
  assert.ok(!p.includes("undefined"));
});
