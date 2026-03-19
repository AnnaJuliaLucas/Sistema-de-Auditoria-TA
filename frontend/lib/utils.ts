/**
 * Cleans a title by removing leading numbers, dots, and dashes often found in audit item names.
 * Example: "5.1 - Alimentação" -> "Alimentação"
 *          "5 - GESTÃO" -> "GESTÃO"
 */
export function cleanTitle(title: string | undefined): string {
    if (!title) return "";
    // Remove leading numbers, dots, dashes, and spaces.
    // Includes en-dash (–) and em-dash (—)
    const cleaned = title.replace(/^[\d\.\-\s–—]+/, "");
    return cleaned.trim() || title.trim();
}
