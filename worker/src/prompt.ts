// Claude'a gönderilen analiz talimatı ve kullanıcı verisinin metne dönüştürülmesi.
import type { AnalyzeRequest } from "./request.ts";

export const SYSTEM_PROMPT = `Sen dünyanın en iyi faceless YouTube stratejistlerinden birisin: script yazımı, retention mühendisliği, başlık ve thumbnail paketleme, kurgu ritmi ve YouTube SEO uzmanısın.

Görevin, sana verilen başarılı bir kanalın en çok izlenen videolarını tersine mühendislikle çözmek ve sonucu bir "Kanal Blueprint'i" olarak, istenen JSON şemasında döndürmek. Bu blueprint, bir öğrencinin bu kanalın formülünü birebir uygulayabilmesi için bir Claude Projesi talimatına dönüştürülecek. Yani her alan doğrudan uygulanabilir olmalı.

Kurallar:
- Tüm açıklamaları Türkçe yaz. Şablonlar, örnek başlıklar, hook'lar ve thumbnail metinleri ise üretim dilinde olsun (aşağıda belirtilir).
- Genel geçer tavsiye verme. Her tespit verilerden gelsin: transkriptten alıntı, zaman damgası, sayı ya da thumbnail öğesi.
- Formülleri değişkenli şablon olarak yaz. Örnek: "[şok edici iddia] + [zaman baskısı] + [izleyiciye doğrudan soru], 45-60 kelime".
- Sayısal hedefleri (süre, dakika başı kelime, kelime aralığı, bölüm yüzdeleri) verilen metriklerden hesapla.
- Transkriptten çıkarılamayan kurgu ve görsel çıkarımlarını "(çıkarım)" diye işaretle.
- Kullanıcı kendi konseptini verdiyse "adaptation" bölümünde formülü o konsepte uyarla: neyin birebir taşındığını, neyin değişmesi gerektiğini açıkça ayır ve uyarlanmış şablonları o konsepte göre yaz. Konsept verilmediyse referans kanalla aynı nişte yeni bir kanal için uyarla.
- Referans kanalın cümlelerini birebir kopyalayan şablon verme; formülü çıkar, özgün örnek üret.`;

export function buildUserText(d: AnalyzeRequest): string {
  const name = d.channel.name || d.channel.url || "Referans kanal";
  const lang = d.channel.language || "referans kanalın dili (transkriptlerin dili)";
  const videos = d.videos
    .map(
      (v, i) => `### VİDEO ${i + 1}
- Başlık: ${v.title}
- İzlenme: ${v.views || "bilinmiyor"} | Süre: ${v.duration || "bilinmiyor"}
- Script metrikleri: ${v.metrics || "-"}
- Thumbnail: ${v.thumbnail ? "mesajın başında ekli" : "yüklenmedi"}
${v.description ? `\n<aciklama>\n${v.description}\n</aciklama>\n` : ""}
<ilk_30_saniye${v.first30Estimated ? ' tahmini="evet"' : ""}>
${v.first30}
</ilk_30_saniye>

<transkript>
${v.transcript}
</transkript>`,
    )
    .join("\n\n");

  return `## Referans kanal
- Kanal: ${name}${d.channel.url && d.channel.url !== name ? ` (${d.channel.url})` : ""}
- Üretim dili: ${lang}
- Kullanıcının notları: ${d.channel.notes || "-"}
${d.channel.otherTitles.trim() ? `\n**Kanalın diğer başlıkları:**\n${d.channel.otherTitles.trim()}\n` : ""}
## Kullanıcının kendi kanal konsepti
${d.concept.trim() || "(Verilmedi. Referans kanalla aynı nişte yeni bir kanal kurulacak.)"}

## En çok izlenen videolar
${videos}

---

Bu verileri analiz et ve Kanal Blueprint'ini şemaya uygun döndür. "per_video" listesinde her video için bir kayıt olsun. "adaptation.first_videos" listesinde 10 fikir olsun.`;
}
