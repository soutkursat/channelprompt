# Kanal Klonlayıcı: YouTube kanal analizi → Claude Projesi paketi

Öğrenci başarılı bir faceless YouTube kanalının linkini girer. Sistem kanalı baştan sona analiz eder ve öğrenciye,
o kanalı **Claude Projects** üzerinden birebir aynı formülle kurup yönetmesini sağlayan hazır bir paket verir.

## Ne yapar?

1. **Veri toplama (YouTube Data API)**
   - Linki çözer: `@handle`, `/channel/UC…`, `/c/…`, `/user/…`, video veya shorts linki.
   - Kanal bilgileri: abone, toplam izlenme, açıklama, anahtar kelimeler, dil.
   - **En çok izlenen 5 video** (uzun video / shorts / hepsi seçilebilir) ve desen analizi için en çok izlenen 30 video.
   - Son 20 yükleme: yayın sıklığı, gün ve saat dağılımı.
   - En çok izlenen videoların **tam transkriptleri** (zaman damgalı) ve **thumbnail görselleri**.
   - Otomatik script metrikleri: kelime sayısı, dakika başı kelime, cümle uzunluğu, ilk 30 saniyedeki kelime sayısı.

2. **Claude ile 3 aşamalı analiz**
   - **Video analizi** (5 video, paralel): ilk 30 saniye hook anatomisi, beat sheet, açık döngüler, retention araçları,
     anlatım tonu, kurgu çıkarımı, başlık formülü, thumbnail analizi (görsel okunur), SEO, başarı formülü.
   - **Kanal DNA raporu**: konsept, fikir filtresi, başlık sistemi, thumbnail sistemi (12 thumbnail birlikte incelenir),
     thumbnail hook formülleri, script blueprint'i, kurgu ve prodüksiyon reçetesi, SEO ve yayın stratejisi.
   - **Proje talimatı**: Claude Projesi'nin *Instructions* alanına yapıştırılacak, adım adım ilerleyen sistem promptu.

3. **Çıktı: ZIP paketi**

   | Dosya | Nereye? |
   |---|---|
   | `00_KURULUM_REHBERI.md` | Öğrencinin okuyacağı kurulum adımları |
   | `01_PROJE_TALIMATI.md` | Proje → **Instructions** |
   | `KANAL_DNA_RAPORU.md` | Proje → **Knowledge** |
   | `VIDEO_ANALIZLERI.md` | Proje → **Knowledge** |
   | `ORNEK_SCRIPTLER.md` (tam transkriptler) | Proje → **Knowledge** |
   | `BASLIK_VE_METRIK_KUTUPHANESI.md` | Proje → **Knowledge** |
   | `THUMBNAIL_REFERANS.md` + `thumbnails/*.jpg` | Proje → **Knowledge** |

## Claude Projesi içindeki akış (talimatın yönettiği)

`ADIM 0` tanıtım ve kanal konsepti → `ADIM 1` konsepte özel 5 içerik fikri (kullanıcı seçer) →
`ADIM 2` beat sheet ve tam script (kurgu notlarıyla) → `ADIM 3` 10 başlık önerisi →
`ADIM 4` 10 thumbnail hook önerisi → `ADIM 5` (isteğe bağlı) kapak tasarım konseptleri ve AI görsel promptları →
`ADIM 6` SEO: anahtar kelimeler, açıklama, etiketler → `ADIM 7` prodüksiyon paketi.
Kısa komutlar: `/fikir`, `/script`, `/baslik`, `/thumbnail`, `/kapak`, `/seo`, `/paket`, `/revize`.

## Kurulum

```bash
cp .env.example .env        # anahtarları doldur
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Tarayıcıda `http://localhost:8000` adresini aç.

Docker ile:

```bash
docker build -t kanal-klonlayici .
docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/data kanal-klonlayici
```

Render, Railway, Fly.io gibi Docker destekleyen her platformda çalışır. `PORT` ortam değişkeni desteklenir.

### Gerekli anahtarlar

| Değişken | Açıklama |
|---|---|
| `YOUTUBE_API_KEY` | Google Cloud Console → *YouTube Data API v3*'ü etkinleştir → API anahtarı oluştur. |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys. |
| `ACCESS_CODE` | (İsteğe bağlı) Öğrencilere vereceğin erişim kodu. API maliyetini korumak için önerilir. |
| `CLAUDE_MODEL` / `CLAUDE_EFFORT` | Varsayılan `claude-opus-5` / `high`. |
| `YT_PROXY_URL` | (İsteğe bağlı) YouTube, bulut sunucu IP'lerinden altyazı çekmeyi sık sık engeller. Sunucuda transkriptler gelmiyorsa bir residential proxy tanımla. |
| `SUPADATA_API_KEY` | (İsteğe bağlı) Transkript alınamazsa kullanılan yedek servis. |

### Maliyet ve süre (yaklaşık)

- **YouTube kotası:** Analiz başına yaklaşık 210 birim (arama isteği 100 birim). Günlük ücretsiz kota 10.000 birim,
  yani günde yaklaşık 45 analiz. Daha fazlası için Google'dan kota artışı iste.
- **Claude:** Analiz başına 7 istek (5 video, 1 DNA, 1 talimat). Uzun transkriptli kanallarda toplam birkaç yüz bin token
  eder. Maliyeti düşürmek için `CLAUDE_EFFORT=medium` kullanılabilir.
- **Süre:** Genelde 5-15 dakika. Analiz arka planda çalışır. Öğrenci sayfayı kapatsa bile `?job=…` linkiyle sonuca döner.

## Proje yapısı

```
app/
  main.py       # FastAPI: form, iş kuyruğu, sonuç ve ZIP indirme
  youtube.py    # YouTube Data API, transkript, thumbnail, yayın takvimi
  analyzer.py   # Analiz hattı ve Claude çağrıları
  prompts.py    # Analiz ve talimat üretim promptları (burayı düzenleyerek metodolojini ekleyebilirsin)
  bundle.py     # ZIP paketi ve bilgi dosyaları
  static/index.html
```

Kendi eğitim metodolojini (hook tipleri, script şablonların vb.) `app/prompts.py` içindeki analiz ve talimat
promptlarına ekleyerek çıktıları kendi sistemine göre özelleştirebilirsin.
