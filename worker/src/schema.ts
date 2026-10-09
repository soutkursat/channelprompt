// Kanal Blueprint'i: Claude'un analiz sonucunu döndürdüğü yapı. Ön yüz bu yapıdan Pro promptu üretir.
import { z } from "zod";

const str = z.string();
const list = z.array(z.string());

export const BlueprintSchema = z.object({
  channel: z.object({
    niche: str.describe("Ana niş"),
    sub_niche: str,
    concept_sentence: str.describe("'Bu kanal ___ için ___ yapar' formatında tek cümle"),
    target_audience: str,
    viewer_emotion: str.describe("İzleyicinin kanaldan beklediği duygu"),
    content_pillars: list,
    positioning: str,
    content_language: str,
  }),
  per_video: z.array(
    z.object({
      title: str,
      core_promise: str,
      why_it_worked: list.describe("En olası 3-5 neden, önem sırasıyla"),
      hook_breakdown: z.array(z.object({ quote: str, function: str })).describe("İlk 30 saniye cümle cümle"),
      title_formula: str,
      thumbnail_notes: str,
    }),
  ),
  hook: z.object({
    formula: str.describe("Değişkenli şablon, örn. [şok iddia] + [zaman baskısı] + [soru]"),
    second_by_second: z.array(z.object({ range: str, purpose: str, example: str })),
    word_range: str,
    rules: list,
    templates: list.describe("Kanal dilinde, boşluklu yeniden kullanılabilir hook şablonları"),
  }),
  script: z.object({
    target_duration_minutes: str,
    words_per_minute: str,
    target_word_range: str,
    narrative_skeleton: str,
    beats: z.array(z.object({ name: str, purpose: str, percent: str, word_range: str })),
    retention_devices: z.array(z.object({ device: str, frequency: str, example: str })),
    open_loop_pattern: str,
    tone: z.object({
      point_of_view: str,
      formality: str,
      sentence_style: str,
      signature_phrases: list,
      banned: list,
    }),
    cta: z.object({ placement: str, formula: str }),
  }),
  titles: z.object({
    formulas: z.array(z.object({ template: str, examples: list, why_it_works: str })),
    avg_length_chars: str,
    power_words: list,
    do: list,
    dont: list,
  }),
  thumbnails: z.object({
    visual_template: str,
    composition: str,
    palette: z.array(z.object({ hex: str, usage: str })),
    text_rules: str,
    hook_formulas: z.array(z.object({ template: str, example: str })),
    attention_devices: list,
    ai_image_prompt_template: str.describe("İngilizce, değişkenli görsel üretim promptu"),
    canva_steps: list,
  }),
  production: z.object({
    visual_style: str,
    scene_pace: str,
    voice_profile: str,
    music_sfx: str,
    workflow_steps: list,
    editor_brief_template: str,
  }),
  seo: z.object({
    description_template: str,
    tag_strategy: str,
    keyword_clusters: list,
  }),
  idea_filter: list.describe("Bir fikrin bu formüle uyup uymadığını test eden 5-7 soru"),
  success_pillars: list,
  never_do: list,
  adaptation: z.object({
    user_concept: str.describe("Kullanıcının konsepti; verilmediyse referans kanalla aynı niş"),
    fit_assessment: str.describe("Formül bu konsepte ne kadar taşınır, riskler"),
    what_transfers: list,
    what_changes: list,
    adapted_concept_sentence: str,
    adapted_hook_templates: list,
    adapted_title_formulas: z.array(z.object({ template: str, example: str })),
    adapted_thumbnail_hooks: list,
    first_videos: z.array(z.object({ title: str, promise: str, hook_angle: str })).describe("İlk 10 video fikri"),
  }),
});

export type Blueprint = z.infer<typeof BlueprintSchema>;
