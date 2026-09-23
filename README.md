# Kanal Klonlayıcı: başarılı kanal analizi → Claude Projesi paketi

Öğrenci, analiz etmek istediği faceless YouTube kanalının en çok izlenen 5 videosunu (başlık, transkript,
thumbnail) sisteme yükler. Sistem bunları Claude ile derinlemesine analiz eder ve öğrenciye bu kanalı
**Claude Projects** üzerinden birebir aynı formülle kurup yönetmesini sağlayan hazır bir paket verir.

YouTube API kullanılmaz. Tek gereken anahtar **Anthropic API anahtarıdır**.

## Kullanıcı ne yükler?

| Alan | Zorunlu mu? |
|---|---|
| Kanal linki, kanal adı, içerik dili | İsteğe bağlı (referans) |
| 5 video için **başlık** | Evet |
| 5 video için **transkript**: yapıştırma veya `.txt` / `.srt` / `.vtt` dosyası | Evet (en az 1 video) |
| 5 video için **thumbnail** görseli | Önerilir |
| İzlenme, süre, video açıklaması | İsteğe bağlı |
| Kanalın diğer başlıkları, notlar | İsteğe bağlı |

Transkriptte zaman damgası varsa (YouTube'un "Transkripti göster" kopyası, SRT, VTT) ilk 30 saniye birebir
çıkarılır. Zaman damgası yoksa anlatım hızına göre tahmin edilir.

**Gizlilik:** Yüklenen transkriptler, görseller ve sonuçlar veritabanına ya da diske kaydedilmez. Hepsi
yalnızca bellekte tutulur ve `RESULT_TTL_MINUTES` (varsayılan 120 dk) sonunda silinir.

## Ne üretir?

1. **Video analizi** (her video için, paralel): ilk 30 saniye hook anatomisi, beat sheet, açık döngüler, retention
   araçları, anlatım tonu, kurgu çıkarımı, başlık formülü, thumbnail analizi, SEO, başarı formülü.
2. **Kanal DNA raporu**: konsept, fikir filtresi, başlık sistemi, thumbnail sistemi ve hook formülleri, script
   blueprint'i, kurgu ve prodüksiyon reçetesi, SEO stratejisi.
3. **Proje talimatı**: Claude Projesi'nin *Instructions* alanına yapıştırılacak adım adım sistem promptu.

**ZIP paketi:** `00_KURULUM_REHBERI.md`, `01_PROJE_TALIMATI.md`, `KANAL_DNA_RAPORU.md`, `VIDEO_ANALIZLERI.md`,
`ORNEK_SCRIPTLER.md`, `BASLIK_KUTUPHANESI.md`, `THUMBNAIL_REFERANS.md` ve `thumbnails/`.

### Claude Projesi içindeki akış

`ADIM 0` tanıtım → `ADIM 1` konsepte özel 5 içerik fikri → `ADIM 2` script → `ADIM 3` 10 başlık →
`ADIM 4` 10 thumbnail hook → `ADIM 5` (isteğe bağlı) kapak tasarımı ve AI görsel promptları →
`ADIM 6` SEO açıklaması ve anahtar kelimeler → `ADIM 7` prodüksiyon paketi.
Kısa komutlar: `/fikir`, `/script`, `/baslik`, `/thumbnail`, `/kapak`, `/seo`, `/paket`, `/revize`.

## Kurulum

```bash
cp .env.example .env        # ANTHROPIC_API_KEY'i gir
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docker:

```bash
docker build -t kanal-klonlayici .
docker run -p 8000:8000 --env-file .env kanal-klonlayici
```

İşler bellekte tutulduğu için uygulamayı **tek süreçle** çalıştırın (birden fazla uvicorn worker kullanmayın).
Sunucu yeniden başlarsa devam eden analizler kaybolur.

### Ortam değişkenleri

| Değişken | Açıklama |
|---|---|
| `ANTHROPIC_API_KEY` | **Zorunlu.** https://console.anthropic.com → API Keys |
| `ACCESS_CODE` | Öğrencilere verilecek erişim kodu. API maliyetini korumak için önerilir. |
| `CLAUDE_MODEL` / `CLAUDE_EFFORT` | Varsayılan `claude-opus-5` / `high`. Maliyeti düşürmek için `medium`. |
| `RESULT_TTL_MINUTES` | Sonuçların bellekte tutulma süresi (varsayılan 120). |
| `MAX_CONCURRENT_JOBS` | Aynı anda çalışan analiz sayısı (varsayılan 3). |

## Proje yapısı

```
app/
  main.py       # FastAPI: form, bellek içi iş kuyruğu, sonuç ve ZIP indirme
  inputs.py     # Transkript ayrıştırma (düz metin, YouTube kopyası, SRT, VTT) ve metrikler
  analyzer.py   # Analiz hattı ve Claude çağrıları
  prompts.py    # Analiz ve talimat promptları (kendi metodolojini buraya ekleyebilirsin)
  bundle.py     # ZIP paketi
  static/index.html
```
