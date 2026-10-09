import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { BlueprintSchema } from "../src/schema.ts";

test("örnek blueprint şemaya uyar", () => {
  const raw = JSON.parse(readFileSync(new URL("../../tests/fixtures/blueprint.json", import.meta.url), "utf8"));
  assert.doesNotThrow(() => BlueprintSchema.parse(raw));
});
