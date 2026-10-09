// /analyze isteğinin doğrulama şeması.
import { z } from "zod";

const MAX_VIDEOS = 5;
const MAX_TRANSCRIPT_CHARS = 120_000;
const MAX_IMAGE_B64 = 2_000_000; // ~1.5 MB görsel

const ImageSchema = z.object({
  media_type: z.enum(["image/jpeg", "image/png", "image/webp", "image/gif"]),
  data: z.string().max(MAX_IMAGE_B64),
});

export const RequestSchema = z.object({
  code: z.string().max(200),
  concept: z.string().max(4000).default(""),
  channel: z.object({
    name: z.string().max(200).default(""),
    url: z.string().max(500).default(""),
    language: z.string().max(60).default(""),
    notes: z.string().max(4000).default(""),
    otherTitles: z.string().max(10000).default(""),
  }),
  videos: z
    .array(
      z.object({
        title: z.string().min(1).max(300),
        views: z.string().max(40).default(""),
        duration: z.string().max(20).default(""),
        metrics: z.string().max(1000).default(""),
        description: z.string().max(6000).default(""),
        first30: z.string().max(4000).default(""),
        first30Estimated: z.boolean().default(false),
        transcript: z.string().min(1).max(MAX_TRANSCRIPT_CHARS),
        thumbnail: ImageSchema.nullable().default(null),
      }),
    )
    .min(1)
    .max(MAX_VIDEOS),
});

export type AnalyzeRequest = z.infer<typeof RequestSchema>;
