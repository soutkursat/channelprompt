# Kanal Klonlayıcı: başarılı kanal verisi → Claude Projesi talimatı

Öğrenci, formülünü çıkarmak istediği faceless YouTube kanalının en çok izlenen 5 videosunu girer:

- başlık,
- transkript,
- thumbnail.

Site bu verilerden tek bir **prompt** üretir. Öğrenci bu promptu Claude'da bir projenin *Instructions* alanına yapıştırır ve thumbnail'ları projeye yükler. Kanal analizini ve sonraki tüm üretimi Claude Projesi öğrencinin kendi hesabında yapar.

- API anahtarı gerekmez, sunucu gerekmez.
- Her şey tarayıcıda çalışır. Transkriptler ve görseller hiçbir yere gönderilmez.

## Kullanıcı ne girer?

| Alan | Zorunlu mu? |
|---|---|
| Kanal linki, kanal adı, içerik dili | İsteğe bağlı |
| 5 video için **başlık** ve **transkript** (yapıştırma veya `.txt` / `.srt` / `.vtt`) | Evet (en az 1 video) |
| 5 video için **thumbnail** | Önerilir (prompt dosya adlarıyla eşleştirir) |
| İzlenme, süre, açıklama | İsteğe bağlı |
| Kanalın diğer başlıkları, notlar | İsteğe bağlı |

Transkriptte zaman damgası varsa ilk 30 saniye birebir çıkarılır. Zaman damgası olan kaynaklar:

- YouTube'un "Transkripti göster" kopyası,
- SRT,
- VTT.

Zaman damgası yoksa ilk 30 saniye anlatım hızına göre tahmin edilir.

## Üretilen prompt neleri içerir?

1. **Rol ve kurallar:** Kullanıcıyla Türkçe konuşur, içeriği seçilen dilde üretir. Formül kopyalanır, cümleler kopyalanmaz.
2. **Proje dosyaları:** Hangi thumbnail'ın hangi videoya ait olduğu.
3. **Referans kanal verileri:** Başlıklar, izlenmeler, süreler, script metrikleri, ilk 30 saniye ve tam transkriptler.
4. **AŞAMA 0, kanal analizi** (ilk sohbette bir kez):
   - Video analizleri: hook anatomisi, beat sheet, retention araçları, ton, kurgu, başlık, thumbnail, SEO ve başarı formülü.
   - Kanal DNA raporu: fikir filtresi, başlık sistemi, thumbnail sistemi, script blueprint'i, prodüksiyon reçetesi ve SEO.
   - Kullanıcıya bu raporları projeye dosya olarak kaydetmesi söylenir.
5. **İş akışı:**
   - `ADIM 1` 5 fikir
   - `ADIM 2` script
   - `ADIM 3` 10 başlık
   - `ADIM 4` 10 thumbnail hook
   - `ADIM 5` kapak tasarımı
   - `ADIM 6` SEO
   - `ADIM 7` prodüksiyon paketi
6. **Komutlar:** `/analiz`, `/fikir`, `/script`, `/baslik`, `/thumbnail`, `/kapak`, `/seo`, `/paket`, `/revize`.
7. **Kalite kontrol listesi.**

## Pro sürüm (AI analiz)

Pro sürümde analiz Claude projesine bırakılmaz. Sunucu tarafında Claude ile önceden yapılır ve sonuçlar prompta gömülür:

- hook formülü,
- saniye saniye ilk 30 saniye yapısı,
- yüzdeli beat sheet,
- başlık ve thumbnail formülleri,
- ton kuralları,
- fikir filtresi.

Kullanıcı kendi kanal konseptini de yazabilir. Formül bu konsepte uyarlanır: neyin aynen taşındığı ve neyin değiştiği ayrılır, uyarlanmış hook ve başlık şablonları ve 10 fikirlik bir havuz da prompta eklenir.

```
Tarayıcı ──(başlık, transkript, küçültülmüş thumbnail, konsept, Pro kodu)──▶ Cloudflare Worker ──▶ Claude API
        ◀──────────── Kanal Blueprint'i (JSON) ◀──────────────────────────
Tarayıcı: blueprint + transkriptlerden Pro promptu üretir (assets/premium.js)
```

- **Tek Claude çağrısı, yapılandırılmış çıktı:** Worker, Claude'dan JSON şemasına uyan bir blueprint ister (`worker/src/schema.ts`). Prompt metni tarayıcıda şablondan üretildiği için çıktı tokenı azdır ve sonuç her seferinde aynı düzende gelir.
- **Erişim:** `PRO_CODES` içindeki kodlardan biri olmadan analiz yapılmaz.
- **Gizlilik:** Veriler yalnızca analiz isteğinde Claude'a gider, hiçbir yerde saklanmaz.

### Pro kurulumu (bir kez)

1. **Cloudflare hesabı aç** (ücretsiz plan yeterli). *My Profile → API Tokens* altında "Edit Cloudflare Workers" şablonuyla bir token oluştur. Hesap kimliğini (Account ID) panelin sağ tarafından kopyala.
2. GitHub'da **Settings → Secrets and variables → Actions** sayfasına şu dört gizli değeri ekle:

   | Gizli değer | Açıklama |
   |---|---|
   | `CLOUDFLARE_API_TOKEN` | 1. adımdaki token |
   | `CLOUDFLARE_ACCOUNT_ID` | Cloudflare hesap kimliği |
   | `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
   | `PRO_CODES` | Öğrencilere vereceğin kodlar, virgülle ayrılmış (ör. `KOD-AHMET-01,KOD-AYSE-02`) |

3. **Actions → "Deploy Pro API" → Run workflow.** Worker yayınlanır; adresi iş akışı çıktısında görünür (ör. `https://channelprompt-pro.<hesap>.workers.dev`).
4. Bu adresi `assets/config.js` içindeki `apiUrl` alanına yaz ve `main`'e gönder. Pro sekmesi aktifleşir.

Model ve analiz derinliği `worker/wrangler.toml` içindeki `CLAUDE_MODEL` ve `CLAUDE_EFFORT` değişkenleriyle değiştirilir.

### Yerel test (API'ye para harcamadan)

```bash
cd worker && npm ci
npm run typecheck && npm test
# Sahte bir Claude sunucusuyla uçtan uca deneme için .dev.vars dosyasına ANTHROPIC_BASE_URL=http://127.0.0.1:9999 yaz
npx wrangler dev
```

## Yayınlama

Statik bir sitedir. Depo kökünü olduğu gibi GitHub Pages, Netlify, Vercel ya da herhangi bir statik barındırmaya yükleyin.

Yerelde denemek için:

```bash
python3 -m http.server 8000   # http://localhost:8000
```

## Geliştirme

```
index.html
assets/
  style.css        # kırmızı-siyah glassmorphism tasarım
  transcript.js    # transkript ayrıştırma ve metrikler
  prompt.js        # prompt şablonu (metodolojini burada düzenleyebilirsin)
  premium.js       # Pro prompt şablonu (Claude'un blueprint'inden)
  config.js        # Pro API adresi
  app.js           # form etkileşimleri
worker/            # Pro analiz API'si (Cloudflare Worker + Claude)
  src/schema.ts    # Kanal Blueprint şeması
  src/prompt.ts    # Claude'a giden analiz talimatı
  src/index.ts     # /analyze uç noktası
tests/
```

Testler: `node --test "tests/*.test.js"` (ön yüz) ve `cd worker && npm test` (Pro API)
