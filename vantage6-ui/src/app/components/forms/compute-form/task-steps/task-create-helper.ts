/**
 * Compares two IDs for selection in mat-select components.
 * Handles different data types (number, string, array) and converts them to strings for comparison.
 *
 * @param id1 - First ID to compare (number or string)
 * @param id2 - Second ID to compare (number, string, or array of strings)
 * @returns boolean - True if the IDs match after conversion to strings
 */
export function compareIDsForSelection(id1: number | string, id2: number | string | string[]): boolean {
  // The mat-select object set from typescript only has an ID set. Compare that with the ID of the
  // organization object from the collaboration
  if (Array.isArray(id2)) {
    id2 = id2[0];
  }
  if (typeof id1 === 'number') {
    id1 = id1.toString();
  }
  if (typeof id2 === 'number') {
    id2 = id2.toString();
  }
  return id1 === id2;
}

/**
 * Gets the display name for an object, preferring display_name over name.
 *
 * @param obj - Object with display_name and name properties
 * @returns string - The display name or fallback to name
 */
export function getDisplayName(obj: { display_name?: string; name: string }): string {
  return obj.display_name && obj.display_name != '' ? obj.display_name : obj.name;
}
