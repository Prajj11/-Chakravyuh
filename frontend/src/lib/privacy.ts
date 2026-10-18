import type { GraphNode, NarrativeCampaignDetail } from "@/types/chakravyuh";
export const restricted = (node: GraphNode) =>
  node.role === "ORGANIC_USER" || node.role === "UNCLASSIFIED";
export const alias = (node: GraphNode) =>
  `Participant ${Array.from(node.id)
    .reduce(
      (hash, char) => Math.imul(hash ^ char.charCodeAt(0), 16777619),
      2166136261,
    )
    .toString(16)
    .replace("-", "")}`;
export const label = (node: GraphNode, privacy: boolean) =>
  privacy && restricted(node) ? alias(node) : node.handle;
export function privateText(
  text: string,
  detail: NarrativeCampaignDetail,
  privacy: boolean,
): string {
  if (!privacy) return text;
  let result = text;
  for (const node of detail.nodes.filter(restricted)) {
    for (const value of [
      node.handle,
      node.handle.replace(/^@/, ""),
      node.id,
    ].sort((a, b) => b.length - a.length)) {
      if (value)
        result = result.replace(
          new RegExp(
            `(?<!\\w)${value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?!\\w)`,
            "gi",
          ),
          alias(node),
        );
    }
  }
  return result;
}
export const roleLabel = (role: string) =>
  ({
    EARLIEST_OBSERVED_SEED: "Earliest observed seed",
    BOT_AMPLIFIER: "Bot amplifier indicator",
    BRIDGE_INFLUENCER: "Bridge influencer",
    ORGANIC_USER: "Low observed indicators",
    UNCLASSIFIED: "Unclassified",
  })[role] ?? role;
export const score = (value: number | null | undefined, digits = 1) =>
  value == null ? "Insufficient data" : value.toFixed(digits);
