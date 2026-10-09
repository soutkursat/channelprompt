// Pro analiz API'si (Cloudflare Worker).
// POST /analyze: kanal verilerini Claude ile analiz eder ve Kanal Blueprint'ini NDJSON akışıyla döndürür.
// Gönderilen transkript ve görseller hiçbir yerde saklanmaz.
import Anthropic from "@anthropic-ai/sdk";
import { betaZodOutputFormat } from "@anthropic-ai/sdk/helpers/beta/zod";
import { BlueprintSchema } from "./schema.ts";
import { SYSTEM_PROMPT, buildUserText } from "./prompt.ts";
import { RequestSchema, type AnalyzeRequest } from "./request.ts";

export interface Env {
  ANTHROPIC_API_KEY: string;
  PRO_CODES: string; // virgülle ayrılmış erişim kodları
  ALLOWED_ORIGINS?: string; // virgülle ayrılmış; boşsa her origin
  CLAUDE_MODEL?: string;
  CLAUDE_EFFORT?: "low" | "medium" | "high" | "xhigh" | "max";
  ANTHROPIC_BASE_URL?: string; // yalnızca yerel testler için
}

function corsHeaders(request: Request, env: Env): Record<string, string> {
  const origin = request.headers.get("Origin") ?? "";
  const allowed = (env.ALLOWED_ORIGINS ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  const allow = allowed.length === 0 ? "*" : allowed.includes(origin) ? origin : allowed[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}

function json(body: unknown, status: number, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...headers, "Content-Type": "application/json" } });
}

function isValidCode(code: string, env: Env): boolean {
  const codes = (env.PRO_CODES ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  return codes.length > 0 && codes.includes(code.trim());
}

function userFacingError(err: unknown): string {
  if (err instanceof Anthropic.RateLimitError) return "Şu an yoğunluk var, lütfen birkaç dakika sonra tekrar dene.";
  if (err instanceof Anthropic.AuthenticationError) return "Sunucu yapılandırma hatası (API anahtarı).";
  if (err instanceof Anthropic.BadRequestError) return "Gönderilen veriler işlenemedi. Transkriptleri ve görselleri kontrol et.";
  if (err instanceof Anthropic.APIConnectionError) return "Analiz servisine bağlanılamadı, tekrar dene.";
  if (err instanceof Anthropic.APIError) return "Analiz servisi geçici bir hata verdi, tekrar dene.";
  if (err instanceof Error) return err.message;
  return "Beklenmeyen hata.";
}

async function runAnalysis(data: AnalyzeRequest, env: Env) {
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY, maxRetries: 3, baseURL: env.ANTHROPIC_BASE_URL || undefined });

  const content: Anthropic.Beta.BetaContentBlockParam[] = [];
  data.videos.forEach((v, i) => {
    if (v.thumbnail) {
      content.push({ type: "text", text: `VİDEO ${i + 1} thumbnail'ı: "${v.title}"` });
      content.push({ type: "image", source: { type: "base64", media_type: v.thumbnail.media_type, data: v.thumbnail.data } });
    }
  });
  content.push({ type: "text", text: buildUserText(data) });

  const stream = client.beta.messages.stream({
    model: env.CLAUDE_MODEL || "claude-opus-5-5",
    max_tokens: 64000,
    system: SYSTEM_PROMPT,
    thinking: { type: "adaptive" },
    output_config: { effort: env.CLAUDE_EFFORT || "high", format: betaZodOutputFormat(BlueprintSchema) },
    // Güvenlik sınıflandırıcısı isteği reddederse sunucu tarafında önerilen modele düşer.
    betas: ["server-side-fallback-2026-07-01"],
    fallbacks: "default",
    messages: [{ role: "user", content }],
  });
  const message = await stream.finalMessage();

  if (message.stop_reason === "refusal") throw new Error("Claude bu içeriği analiz etmeyi reddetti.");
  if (message.stop_reason === "max_tokens") throw new Error("Analiz çok uzun sürdü ve yarıda kesildi. Daha kısa transkriptlerle tekrar dene.");
  const text = message.content.flatMap((b) => (b.type === "text" ? [b.text] : [])).join("");
  const blueprint = BlueprintSchema.parse(JSON.parse(text));
  return { blueprint, usage: message.usage, model: message.model };
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const cors = corsHeaders(request, env);
    const url = new URL(request.url);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname === "/health") return json({ ok: true, model: env.CLAUDE_MODEL || "claude-opus-5-5" }, 200, cors);
    if (url.pathname !== "/analyze" || request.method !== "POST") return json({ error: "Bulunamadı." }, 404, cors);

    let data: AnalyzeRequest;
    try {
      data = RequestSchema.parse(await request.json());
    } catch {
      return json({ error: "Geçersiz istek. Alanları kontrol et." }, 400, cors);
    }
    if (!isValidCode(data.code, env)) return json({ error: "Pro erişim kodu geçersiz." }, 403, cors);

    // Analiz birkaç dakika sürebilir: bağlantının kopmaması için NDJSON akışıyla düzenli sinyal gönderiyoruz.
    const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
    const writer = writable.getWriter();
    const enc = new TextEncoder();
    const send = (obj: unknown) => writer.write(enc.encode(JSON.stringify(obj) + "\n"));
    const started = Date.now();

    const work = (async () => {
      const beat = setInterval(() => send({ type: "progress", elapsed: Math.round((Date.now() - started) / 1000) }), 8000);
      try {
        await send({ type: "progress", elapsed: 0 });
        const result = await runAnalysis(data, env);
        await send({ type: "result", ...result });
      } catch (err) {
        console.error(err);
        await send({ type: "error", error: userFacingError(err) });
      } finally {
        clearInterval(beat);
        await writer.close();
      }
    })();
    ctx.waitUntil(work);

    return new Response(readable, {
      headers: { ...cors, "Content-Type": "application/x-ndjson; charset=utf-8", "Cache-Control": "no-store" },
    });
  },
};
