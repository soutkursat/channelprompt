"""Claude'a gönderilen analiz ve prompt-üretim talimatları."""

ANALYST_SYSTEM = """Sen dünyanın en iyi faceless YouTube stratejistlerinden birisin. Yüzlerce faceless kanalı sıfırdan büyüttün; \
script yazımı, retention mühendisliği, başlık/thumbnail paketleme, kurgu ritmi ve YouTube SEO konusunda uzmansın.

Görevin: Sana verilen gerçek kanal verilerini (metadata, izlenme sayıları, tam transkriptler, thumbnail görselleri) \
tersine mühendislikle çözümlemek ve bir öğrencinin bu kanalı BİREBİR aynı formülle yeniden üretebilmesi için gereken \
her şeyi ortaya çıkarmak.

Çalışma kuralları:
- Tüm analizi TÜRKÇE yaz. Kanalın dilinden alıntı yaparken orijinal dili koru ve gerekiyorsa yanına Türkçe açıklama ekle.
- Genel geçer tavsiye verme. Her tespiti verilerden somut bir kanıtla (alıntı, zaman damgası, sayı, thumbnail öğesi) destekle.
- Transkriptten çıkarılamayan şeyleri (ör. görsel kurgu) çıkarım olarak işaretle: "(çıkarım)" yaz ve neden öyle düşündüğünü belirt.
- Kopyalanabilir formüller, şablonlar ve kurallar üret. "Güzel bir hook yaz" değil, "Hook = [şok edici iddia] + [zaman baskısı] + [izleyiciye doğrudan soru], 45-60 kelime" gibi.
- Markdown formatında, net başlıklarla yaz. Tablo kullanmak anlaşılırlığı artırıyorsa kullan.
"""


def video_analysis_prompt(ctx: dict) -> str:
    return f"""Aşağıda "{ctx['channel_title']}" kanalının en çok izlenen videolarından biri var (kanal sıralaması: #{ctx['rank']}).
Thumbnail görseli bu mesajın başında ekli.

## Video verileri
- Başlık: {ctx['title']}
- URL: {ctx['url']}
- İzlenme: {ctx['views']:,} | Beğeni: {ctx['likes']:,} | Yorum: {ctx['comments']:,}
- Süre: {ctx['duration']} | Yayın tarihi: {ctx['published_at']}
- Etiketler: {ctx['tags'] or '(yok)'}
- Script metrikleri (otomatik hesaplandı): {ctx['metrics']}
- Transkript kaynağı / dili: {ctx['transcript_source'] or 'YOK'} / {ctx['transcript_language'] or '-'}

## Açıklama
<description>
{ctx['description'] or '(boş)'}
</description>

## İlk 30 saniye (birebir transkript)
<first_30s>
{ctx['first_30s'] or '(transkript alınamadı)'}
</first_30s>

## Tam transkript (zaman damgalı)
<transcript>
{ctx['transcript'] or '(transkript alınamadı — analizi başlık, açıklama, thumbnail ve süreye dayanarak yap ve bunu açıkça belirt)'}
</transcript>

---

Bu videoyu aşağıdaki başlıklarla ÇOK DETAYLI analiz et:

### 1. Video Özeti ve Konsept
- Video tek cümlede neyi vaat ediyor, izleyiciye ne veriyor?
- Konu kategorisi, hedef izleyici profili, izleyicinin tıklama motivasyonu (merak, korku, hayranlık, öğrenme, nostalji vb.)

### 2. İlk 30 Saniye — Hook Anatomisi (en kritik bölüm)
- İlk 30 saniyenin birebir metnini cümle cümle parçala; her cümlenin işlevini yaz (pattern interrupt, iddia, bağlam, vaat, açık döngü, sosyal kanıt, tehdit/risk vb.).
- Hook hangi formülü kullanıyor? Formülü değişkenli bir şablon olarak yaz.
- Thumbnail + başlık + ilk cümle arasındaki vaat tutarlılığı nasıl sağlanmış?
- Bu hook'u taklit etmek için yeniden kullanılabilir 3 farklı hook şablonu üret (kanalın dilinde).

### 3. Script Yapısı ve Akış (Beat Sheet)
- Videoyu zaman damgalarıyla bölümlere ayır: her bölümün süresi, toplam içindeki yüzdesi, işlevi.
- Anlatı iskeleti (ör. kronolojik hikâye, geri sayım listesi, problem-çözüm, gizem-ifşa, karşılaştırma).
- Açık döngüler (open loop): nerede açılıyor, nerede kapanıyor? Alıntıyla göster.
- Retention araçları: yeniden hook'lar, "ama asıl önemli olan…" geçişleri, cliffhanger'lar, sayılar, kontrast, merak boşlukları. Her birini zaman damgasıyla listele.
- Kapanış ve CTA yapısı: abone/izleme çağrısı nerede ve nasıl yapılmış, sonraki videoya yönlendirme var mı?

### 4. Anlatım Dili ve Ses Tonu
- Anlatıcı bakış açısı (1. tekil, 2. tekil/izleyiciye hitap, 3. şahıs belgesel vb.), resmiyet seviyesi, duygu tonu.
- Cümle uzunluğu ve ritim (metriklerle destekle), kelime seçimi, tekrar eden ifadeler ve imza kalıplar (birebir alıntı).
- Konuşma hızı (dakika başı kelime) ve bunun seslendirme (AI voice / insan sesi) için anlamı.

### 5. Kurgu ve Görsel Anlatım (çıkarım)
- Transkript ritmi, cümle geçişleri ve konuya göre muhtemel görsel yapı: stok video, AI görsel, animasyon, harita, arşiv görüntüsü, metin üstü, zoom/ken burns vb.
- Tahmini sahne değişim sıklığı ve kurgu temposu.
- Müzik/ses efekti kullanımına dair ipuçları.
- Bu videoyu faceless olarak birebir üretmek için adım adım prodüksiyon reçetesi.

### 6. Başlık Analizi
- Başlığın formülü (değişkenli şablon), uzunluğu, güç kelimeleri, merak boşluğu, sayı/yıl kullanımı, büyük harf kullanımı.
- Bu başlığın neden tıklattığına dair psikolojik açıklama.

### 7. Thumbnail Analizi (ekteki görsele bak)
- Kompozisyon (ana obje konumu, yerleşim ızgarası), renk paleti (baskın renkler, kontrast), yüz/obje/karakter kullanımı, duygu.
- Thumbnail üzerindeki metin (varsa birebir yaz): kelime sayısı, font stili, renk, konum. Thumbnail metninin başlıkla ilişkisi (tekrar mı, tamamlayıcı mı?).
- Oklar, daireler, bulanıklık, kırmızı vurgular gibi dikkat unsurları.
- Bu thumbnail'ın AI görsel aracında yeniden üretilebilmesi için detaylı bir tasarım brifingi (İngilizce görsel prompt dahil).

### 8. SEO ve Paketleme
- Açıklama yapısı (ilk 2 satır, zaman damgaları, linkler, hashtag), etiket stratejisi, anahtar kelime yerleşimi.

### 9. Bu Videonun Başarı Formülü
- Videonun bu kadar izlenmesinin en olası 5 nedeni (önem sırasına göre).
- Öğrencinin bu videodan alması gereken 10 maddelik "kopyala-uygula" kural listesi.
"""


def channel_dna_prompt(ctx: dict) -> str:
    return f"""Aşağıda "{ctx['channel_title']}" kanalının tüm verileri ve en çok izlenen {ctx['top_count']} videosunun detaylı analizleri var.
Mesajın başında kanalın en çok izlenen videolarından {ctx['thumb_count']} tanesinin thumbnail'ları, izlenme sırasına göre ekli \
(her görselden önce hangi videoya ait olduğu yazıyor).

## Kanal bilgileri
{ctx['channel_info']}

## Yayın takvimi (son yüklemelerden hesaplandı)
{ctx['cadence']}

## En çok izlenen videolar (başlık | izlenme | süre | yayın tarihi)
{ctx['top_titles']}

## Son yüklenen videolar (başlık | izlenme | süre | yayın tarihi)
{ctx['recent_titles']}

## En çok izlenen {ctx['top_count']} videonun detaylı analizleri
{ctx['video_analyses']}

---

Tüm bu verileri sentezleyerek bir **KANAL DNA RAPORU** yaz. Bu rapor, öğrencinin kanalı birebir aynı formülle kurması için \
Claude Projesi'ne bilgi dosyası olarak yüklenecek. Bu yüzden eksiksiz, somut ve şablon odaklı olmalı. Başlıklar:

### 1. Kanal Kimliği
- Niş, alt niş, konsept tek cümle ("Bu kanal ___ için ___ yapar").
- Hedef izleyici (yaş, ilgi alanı, bölge, izleme motivasyonu), izleyicinin kanaldan beklediği duygu.
- Kanalın konumlanması ve rakiplerden ayrıştığı nokta. İçerik sütunları (tekrar eden konu kategorileri) ve her sütunun performansı.
- Kanalın içerik dili ve lehçesi.

### 2. Konu / Fikir Seçim Formülü
- En çok izlenen konuların ortak özellikleri. Hangi konu tipleri patlıyor, hangileri zayıf kalıyor (son yüklemeler vs. en iyiler karşılaştırması).
- Yeni fikir üretirken kullanılacak 5-7 maddelik fikir filtresi (bir fikrin bu kanala uygun olup olmadığını test eden sorular).
- Bu kanal için 10 örnek yeni video fikri (kanalın dilinde başlık taslağıyla).

### 3. Başlık Sistemi
- Kanalda tekrar eden 5-8 başlık formülü; her biri değişkenli şablon + kanaldan 2 gerçek örnek.
- Ortalama başlık uzunluğu (karakter), büyük harf, sayı, yıl, parantez, emoji, soru kullanımı; güç kelimeleri listesi.
- Başlık yazım kuralları (yap / yapma listesi).

### 4. Thumbnail Sistemi (ekli görsellere dayanarak)
- Tekrar eden görsel şablon(lar): kompozisyon, ana obje, arka plan, renk paleti (HEX tahmini ile), kontrast, ışık.
- Thumbnail metni (hook) kuralları: kelime sayısı, font tipi/kalınlığı, renk, kontur/gölge, konum; metnin başlıkla ilişkisi.
- Thumbnail hook formülleri: kanaldaki gerçek thumbnail metinlerinden çıkarılmış 5+ şablon ve örnek.
- Dikkat unsurları (ok, daire, kırmızı vurgu, bulanıklık, önce/sonra, ölçek karşılaştırması vb.).
- Yeni thumbnail'lar için AI görsel üretim prompt şablonu (İngilizce, değişkenli) + Canva/Photoshop için katman katman tasarım talimatı.

### 5. Script Blueprint'i (Ana Şablon)
- Hedef video süresi ve hedef kelime sayısı (dakika başı kelime hızına göre hesapla).
- İlk 30 saniye hook formülü: saniye saniye yapı + kelime aralığı + 3 örnek şablon.
- Bölüm bölüm yapı (beat sheet): her bölümün işlevi, yüzdelik süresi, kelime aralığı.
- Retention cihazları listesi ve script içinde ne sıklıkla kullanılacağı (ör. "her 60-90 saniyede bir yeniden hook").
- Anlatıcı sesi, ton, bakış açısı, cümle uzunluğu, imza ifadeler, yasaklı ifadeler.
- CTA yerleşimi ve kapanış formülü.

### 6. Kurgu ve Prodüksiyon Reçetesi (faceless)
- Görsel tipi ve kaynakları, sahne değişim temposu, metin/altyazı kullanımı, müzik ve SFX tarzı.
- Seslendirme profili (ses tipi, cinsiyet, yaş, hız, duygu) ve önerilen AI ses araçları.
- Adım adım üretim akışı (script → ses → görsel → kurgu → thumbnail → yükleme) ve her adım için önerilen araçlar.
- Kurgucuya verilecek standart brif şablonu.

### 7. SEO ve Yayın Stratejisi
- Açıklama şablonu (kanalın mevcut açıklama yapısına göre), etiket stratejisi, anahtar kelime kümeleri.
- Yayın sıklığı, gün/saat önerisi, ideal video süresi.

### 8. Başarı Formülü ve Kopyalama Kuralları
- Kanalın başarısının 7 temel sütunu.
- "Asla yapma" listesi (formülü bozan hatalar).
- İlk 10 video için yol haritası önerisi.
"""


def instructions_prompt(ctx: dict) -> str:
    return f"""Aşağıda "{ctx['channel_title']}" kanalı için hazırlanmış KANAL DNA RAPORU ve video analizlerinin özeti var.

<kanal_dna_raporu>
{ctx['dna_report']}
</kanal_dna_raporu>

<video_analizleri>
{ctx['video_analyses']}
</video_analizleri>

---

GÖREV: Öğrencinin Claude'da oluşturacağı bir **Claude Projesi**'nin "Instructions" (Proje Talimatları) alanına yapıştıracağı \
SİSTEM PROMPTUNU yaz. Bu prompt ile Claude, öğrencinin kişisel "kanal yönetim asistanı" olacak ve bu kanalı birebir aynı \
formülle yeniden üretmesini adım adım yönetecek.

Projeye ayrıca şu bilgi dosyaları yüklenecek (prompt içinde bu dosya adlarıyla referans ver):
{ctx['knowledge_files']}

Yazacağın promptun gereksinimleri:

1. **Rol ve bağlam**: Claude'un rolünü, kanalın konseptini, nişini, hedef izleyicisini ve üretim dilini ({ctx['content_language']}) \
net tanımla. Kullanıcıyla iletişim dili Türkçe; üretilen script, başlık, thumbnail metni, açıklama ve etiketler ise \
{ctx['content_language']} olacak.

2. **Bilgi dosyalarının kullanımı**: Her adımda hangi dosyaya bakılacağını açıkça söyle (ör. "Başlık üretmeden önce \
KANAL_DNA_RAPORU.md içindeki Başlık Sistemi bölümünü ve BASLIK_VE_METRIK_KUTUPHANESI.md'deki en çok izlenen başlıkları incele"). \
Thumbnail önerilerinde projeye yüklenmiş referans thumbnail görsellerini (THUMBNAIL_REFERANS.md'de hangi görselin hangi videoya ait olduğu yazıyor) dikkate almasını söyle.

3. **Adım adım iş akışı** (her adımın sonunda kullanıcıdan onay/seçim beklenmeli, adımlar atlanmamalı):
   - ADIM 0 — Başlangıç: Kullanıcı ilk mesajı attığında kendini kısaca tanıt, kanal konseptini 3-4 cümlede özetle ve menüyü göster.
   - ADIM 1 — Fikir üretimi: Kanalın konseptine ve fikir filtresine %100 uygun 5 içerik fikri. Her fikir için: çalışma başlığı, \
tek cümlelik vaat, neden bu kanalda tutacağı (hangi başarılı videoya benzediği), hook açısı, tahmini süre. Kullanıcı bir fikir \
seçene kadar bekle. Kullanıcı kendi fikrini de getirebilir; o zaman fikri filtreden geçirip güçlendir.
   - ADIM 2 — Script: Seçilen fikir için tam script. Script blueprint'indeki süre/kelime hedefi, ilk 30 saniye hook formülü, bölüm \
yapısı, retention cihazları, anlatıcı tonu ve CTA yerleşimine birebir uy. Scriptten önce kısa bir bölüm planı (beat sheet) göster. \
Scripti bölüm başlıkları ve [GÖRSEL: ...] kurgu notlarıyla ver ki kurgucu doğrudan kullanabilsin. Script sonunda kelime sayısı ve \
tahmini süreyi yaz. Kullanıcıdan revizyon ya da onay iste. Uzun scriptlerde bölümler halinde üretip devam için onay al.
   - ADIM 3 — Başlık önerileri: Kanalın başlık formüllerine dayalı 10 başlık; her birinin hangi formülü kullandığını belirt, en \
güçlü 3'ünü gerekçesiyle öner.
   - ADIM 4 — Thumbnail hook önerileri: Kanalın thumbnail metin kurallarına uygun 10 thumbnail metni; seçilen başlıkla uyumlu \
(tekrar etmeyen, tamamlayan) olmalı. En iyi 3 başlık + thumbnail metni kombinasyonunu öner.
   - ADIM 5 — Kapak (thumbnail) tasarımı (isteğe bağlı, kullanıcı isterse): 3 farklı konsept; her biri için kompozisyon, renk \
paleti (HEX), obje/karakter, metin yerleşimi, font; Midjourney/DALL-E/Ideogram/Flux için İngilizce hazır prompt ve Canva'da \
katman katman uygulama talimatı. Referans thumbnail'lara sadık kal.
   - ADIM 6 — SEO: Videonun anahtar kelime araştırması (ana anahtar kelime, 10-15 ikincil / uzun kuyruk anahtar kelime), kanalın \
açıklama şablonuna uygun SEO açıklaması (ilk 2 satırda ana anahtar kelime + hook, zaman damgaları, CTA, hashtag'ler) ve \
virgülle ayrılmış 15-25 etiket (toplam 500 karakteri aşmayacak şekilde).
   - ADIM 7 — Prodüksiyon paketi (isteğe bağlı): Seslendirme ayarları, kurgucu brifi, müzik/SFX önerisi, yayın günü/saati.
   - Tüm adımlar bittiğinde, bütün çıktıları tek bir "Video Paketi" özetinde topla ve yeni video için ADIM 1'e dönmeyi teklif et.

4. **Komutlar**: Kullanıcının hızlı kullanabileceği kısa komutlar tanımla (ör. /fikir, /script, /baslik, /thumbnail, /kapak, \
/seo, /paket, /revize) ve her komutun ne yaptığını yaz.

5. **Kanal formülü özeti**: Promptun içine, dosyalara bakmadan da uygulanabilecek şekilde en kritik kuralları göm: hook formülü, \
script yapısı (yüzdelerle), başlık formülleri, thumbnail kuralları, ton kuralları, hedef süre/kelime sayısı, yasaklar. \
(Bu bölüm kısa ama kesin olmalı; detaylar bilgi dosyalarında.)

6. **Kalite kontrol**: Her çıktıdan önce Claude'un kendi kendine uygulayacağı bir kontrol listesi (ör. "Hook ilk 5 saniyede \
başlıktaki vaadi karşılıyor mu?", "Script hedef kelime aralığında mı?", "Başlık kanalın formüllerinden birine uyuyor mu?"). \
Özgünlük kuralı: kanalın formülünü kopyala ama rakip videoların cümlelerini birebir kopyalama.

7. **Biçim**: Promptu Markdown ile, net başlıklar ve numaralı adımlarla yaz. Türkçe yaz. Kanalın dilinden örnekleri orijinal \
dilde bırak. Promptu doğrudan yapıştırılabilir halde ver; önüne ya da arkasına açıklama ekleme. İlk satır "# " ile başlayan \
bir başlık olsun.
"""
