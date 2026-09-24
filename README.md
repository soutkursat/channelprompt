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
  app.js           # form etkileşimleri
tests/prompt.test.js
```

Testler: `node --test`
