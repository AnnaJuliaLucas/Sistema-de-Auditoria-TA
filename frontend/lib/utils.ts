/**
 * Cleans a title by removing leading numbers, dots, and dashes often found in audit item names.
 * Example: "5.1 - Alimentação" -> "Alimentação"
 *          "5 - GESTÃO" -> "GESTÃO"
 */
export function cleanTitle(title: string | undefined): string {
    if (!title) return "";
    // Remove leading numbers, dots, dashes, and spaces if followed by a letter
    // This regex looks for digits/dots/dashes/spaces at the start and replaces them
    // only if there's actual text following (to avoid erasing number-only titles if they exist)
    const cleaned = title.replace(/^[\d\.\-\b\s]+(?=[a-zA-ZáéíóúÁÉÍÓÚçÇ])/, "");
    return cleaned.trim() || title.trim();
}
