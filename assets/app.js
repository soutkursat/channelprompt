// Form etkileşimleri ve prompt oluşturma. Hiçbir veri sunucuya gönderilmez.
(function () {
  const VIDEO_COUNT = 5;
  const MIN_WORDS = 50;
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => new Intl.NumberFormat("tr-TR").format(n);
  let promptText = "";
  const q = (el, f) => el.querySelector(`[data-f="${f}"]`);
  const wordsOf = (s) => (s.trim() ? s.trim().split(/\s+/).length : 0);

  const imgIcon = '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/></svg>';

  for (let i = 1; i <= VIDEO_COUNT; i++) {
    const el = document.createElement("div");
    el.className = "glass video";
    el.dataset.i = i;
    el.innerHTML = `
      <div class="video-head">
        <div class="num">${i}</div>
        <h3>${i}. en çok izlenen video</h3>
        <span class="status">Eksik</span>
      </div>
      <div class="video-body">
        <div class="stack">
          <div>
            <label>Thumbnail</label>
            <div class="drop">
              <input type="file" data-f="thumb" accept="image/jpeg,image/png,image/webp,image/gif" aria-label="Thumbnail ${i}">
              <div class="ph">${imgIcon}Sürükle bırak ya da tıkla<br><small>JPG, PNG, WEBP</small></div>
              <button class="clear" type="button" aria-label="Görseli kaldır">×</button>
            </div>
            <div class="fname"></div>
          </div>
          <div class="mini">
            <div><label>İzlenme</label><input data-f="views" placeholder="2.4M"></div>
            <div><label>Süre</label><input data-f="duration" placeholder="18:42"></div>
          </div>
        </div>
        <div class="stack">
          <div><label>Video başlığı *</label><input data-f="title" placeholder="Videonun tam başlığı" maxlength="300"></div>
          <div>
            <label>Transkript *</label>
            <textarea data-f="transcript" placeholder="Transkripti buraya yapıştır ya da dosya yükle…"></textarea>
            <div class="transcript-bar">
              <label class="file-btn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 16V4m0 0L7 9m5-5 5 5M5 20h14"/></svg>
                Dosya yükle (.txt, .srt, .vtt)
                <input type="file" data-f="tfile" accept=".txt,.srt,.vtt,.sbv,text/plain">
              </label>
              <span class="count">0 kelime</span>
            </div>
          </div>
          <details>
            <summary>Video açıklaması (isteğe bağlı, SEO için)</summary>
            <textarea data-f="description" style="min-height:90px" placeholder="Videonun YouTube açıklamasını yapıştır"></textarea>
          </details>
        </div>
      </div>`;
    $("videos").append(el);
    $("dots").append(document.createElement("i"));
    wire(el);
  }

  function wire(el) {
    const drop = el.querySelector(".drop"), thumb = q(el, "thumb"), ta = q(el, "transcript");

    const setPreview = () => {
      drop.querySelector("img")?.remove();
      const f = thumb.files[0];
      el.querySelector(".fname").textContent = f ? f.name : "";
      if (!f) { drop.classList.remove("has"); return refresh(); }
      if (!f.type.startsWith("image/")) { toast("Lütfen bir görsel dosyası seç."); thumb.value = ""; return setPreview(); }
      const img = document.createElement("img");
      img.src = URL.createObjectURL(f); img.alt = "";
      drop.prepend(img); drop.classList.add("has"); refresh();
    };
    thumb.addEventListener("change", setPreview);
    drop.querySelector(".clear").addEventListener("click", (e) => { e.preventDefault(); thumb.value = ""; setPreview(); });
    ["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((t) => drop.addEventListener(t, () => drop.classList.remove("over")));
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) { thumb.files = e.dataTransfer.files; setPreview(); }
    });

    const tfile = q(el, "tfile");
    tfile.addEventListener("change", async () => {
      const f = tfile.files[0]; if (!f) return;
      if (f.size > 2 * 1024 * 1024) { toast("Transkript dosyası 2 MB'tan büyük olamaz."); tfile.value = ""; return; }
      ta.value = await f.text(); tfile.value = ""; refresh();
    });
    ta.addEventListener("input", refresh);
    q(el, "title").addEventListener("input", refresh);

    function refresh() {
      const words = wordsOf(ta.value);
      el.querySelector(".count").textContent = fmt(words) + " kelime";
      const ready = q(el, "title").value.trim() && words >= MIN_WORDS;
      el.classList.toggle("ready", !!ready);
      el.querySelector(".status").textContent = ready ? (thumb.files[0] ? "Hazır" : "Hazır · thumbnail yok") : "Eksik";
      updateDock();
    }
  }

  const cards = () => [...document.querySelectorAll(".video")];

  function updateDock() {
    const ready = cards().filter((c) => c.classList.contains("ready")).length;
    [...$("dots").children].forEach((d, i) => d.classList.toggle("on", i < ready));
    $("readyText").textContent = `${ready}/${VIDEO_COUNT} video hazır`;
    $("submit").disabled = ready === 0;
  }

  function show(id) {
    for (const s of ["form", "result"]) $(s).classList.toggle("hidden", s !== id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function toast(msg) {
    $("toast").textContent = msg; $("toast").classList.add("show");
    clearTimeout(toast.t); toast.t = setTimeout(() => $("toast").classList.remove("show"), 3200);
  }

  $("form").addEventListener("submit", (e) => {
    e.preventDefault();
    const partial = cards().find((c) => (q(c, "title").value.trim() || q(c, "transcript").value.trim()) && !c.classList.contains("ready"));
    if (partial) {
      partial.scrollIntoView({ behavior: "smooth", block: "center" });
      return toast(`Video ${partial.dataset.i}: başlık ve en az ${MIN_WORDS} kelimelik transkript gerekli.`);
    }
    const videos = cards().filter((c) => c.classList.contains("ready")).map((c) => ({
      title: q(c, "title").value.trim(),
      transcript: q(c, "transcript").value,
      views: Transcript.parseViews(q(c, "views").value),
      durationSeconds: Transcript.parseDuration(q(c, "duration").value),
      description: q(c, "description").value.trim(),
      thumbnailName: q(c, "thumb").files[0]?.name || "",
    }));
    const data = {
      channelUrl: $("channel_url").value.trim(),
      channelName: $("channel_name").value.trim(),
      language: $("language").value,
      notes: $("notes").value.trim(),
      otherTitles: $("other_titles").value,
      videos,
    };
    promptText = PromptBuilder.buildPrompt(data);
    renderResult(data);
  });

  function renderResult(data) {
    $("resTitle").textContent = data.channelName || data.channelUrl || "Referans kanal";
    const thumbs = data.videos.filter((v) => v.thumbnailName).length;
    const chips = [
      `${data.videos.length} video`,
      `${thumbs} thumbnail`,
      `${fmt(promptText.length)} karakter`,
      `~${fmt(wordsOf(promptText))} kelime`,
    ];
    $("resChips").replaceChildren(...chips.map((t) => Object.assign(document.createElement("span"), { className: "chip", textContent: t })));
    $("thumbStep").innerHTML = thumbs
      ? `${thumbs} thumbnail görselini <b>aynı dosya adlarıyla</b> projenin <b>Project knowledge</b> alanına yükle.`
      : `Thumbnail yüklemedin. İstersen referans thumbnail'ları <b>Project knowledge</b> alanına ekleyebilirsin.`;
    $("promptOut").textContent = promptText;
    show("result");
  }

  $("copyBtn").onclick = async () => {
    try { await navigator.clipboard.writeText(promptText); toast("Prompt kopyalandı ✓"); }
    catch (e) {
      const r = document.createRange(); r.selectNodeContents($("promptOut"));
      const s = getSelection(); s.removeAllRanges(); s.addRange(r);
      toast("Metin seçildi, Ctrl+C / Cmd+C ile kopyala.");
    }
  };

  $("downloadBtn").onclick = () => {
    const name = ($("channel_name").value.trim() || "kanal").replace(/[^\p{L}\p{N}-]+/gu, "-").replace(/^-|-$/g, "");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([promptText], { type: "text/markdown;charset=utf-8" }));
    a.download = `${name}-claude-proje-talimati.md`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };

  $("editBtn").onclick = () => show("form");
})();
