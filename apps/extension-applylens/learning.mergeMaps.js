/**
 * ES Module version of selector map merge logic
 * Integrates with existing extension learning system
 */

/**
 * Merge canonical server map with local FormMemory.
 * Local overrides win on conflicts.
 *
 * @param {Object} serverMap - Canonical mappings from aggregated server events
 * @param {Object} localMap - Local FormMemory mappings (user overrides)
 * @returns {Object} Combined SelectorMap with local preferences taking precedence
 */
function mergeSelectorMaps(serverMap, localMap) {
  return {
    ...serverMap,
    ...localMap, // local wins on conflicts
  };
}

// ES module export
export { mergeSelectorMaps };
