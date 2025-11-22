import type { SelectorMap } from "./types";

/**
 * Merge canonical server map with local FormMemory.
 * Local overrides win on conflicts.
 *
 * @param serverMap - Canonical mappings from aggregated server events
 * @param localMap - Local FormMemory mappings (user overrides)
 * @returns Combined SelectorMap with local preferences taking precedence
 */
export function mergeSelectorMaps(
  serverMap: SelectorMap,
  localMap: SelectorMap
): SelectorMap {
  return {
    ...serverMap,
    ...localMap, // local wins
  };
}
