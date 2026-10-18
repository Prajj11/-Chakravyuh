import { z } from "zod";
import definitions from "@/types/schema.json";

type Schema = Record<string, unknown>;
const defs: Record<string, unknown> = definitions.$defs;
const object = (value: unknown): Schema => {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("Invalid runtime schema");
  return value as Schema;
};
const cache = new Map<string, z.ZodType>();
function compile(value: unknown): z.ZodType {
  if (value === true) return z.unknown();
  if (value === false) return z.never();
  const schema = object(value);
  if (typeof schema.$ref === "string")
    return named(schema.$ref.split("/").at(-1) ?? "");
  if ("const" in schema) return z.custom((v) => v === schema.const);
  if (Array.isArray(schema.enum))
    return z.custom((v) => (schema.enum as unknown[]).includes(v));
  if (Array.isArray(schema.anyOf)) {
    const members = schema.anyOf.map(compile);
    return z.custom((v) =>
      members.some((member) => member.safeParse(v).success),
    );
  }
  if (schema.type === "null") return z.null();
  if (schema.type === "boolean") return z.boolean();
  if (schema.type === "number" || schema.type === "integer") {
    let result = z.number().finite();
    if (schema.type === "integer") result = result.int();
    if (typeof schema.minimum === "number") result = result.min(schema.minimum);
    if (typeof schema.maximum === "number") result = result.max(schema.maximum);
    return result;
  }
  if (schema.type === "string") {
    let result = z.string();
    if (typeof schema.minLength === "number")
      result = result.min(schema.minLength);
    if (typeof schema.maxLength === "number")
      result = result.max(schema.maxLength);
    if (typeof schema.pattern === "string")
      result = result.regex(new RegExp(schema.pattern));
    if (schema.format === "date-time")
      result = result.refine((v) => Number.isFinite(Date.parse(v)));
    return result;
  }
  if (schema.type === "array") {
    let result = z.array(compile(schema.items ?? {}));
    if (typeof schema.minItems === "number")
      result = result.min(schema.minItems);
    return result;
  }
  if (schema.type === "object") {
    if (schema.properties) {
      const shape: Record<string, z.ZodType> = {};
      for (const [key, field] of Object.entries(object(schema.properties)))
        shape[key] = compile(field);
      return z.object(shape).strict();
    }
    return z.record(z.string(), compile(schema.additionalProperties ?? {}));
  }
  return z.unknown();
}
function named(name: string): z.ZodType {
  const previous = cache.get(name);
  if (previous) return previous;
  const lazy = z.lazy(() => compile(defs[name]));
  cache.set(name, lazy);
  return lazy;
}
export function contract<T>(name: string): z.ZodType<T> {
  // JSON schemas and TypeScript mirrors are generated from the same Python models.
  return named(name) as z.ZodType<T>;
}
