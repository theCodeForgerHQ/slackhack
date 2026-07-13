/**
 * Evidence sanitization for prompt-injection hardening.
 *
 * Inspired by Consensus (BitTriad) and standard prompt-injection defenses:
 * 1. Unicode NFKC normalization collapses homoglyphs and compatibility chars.
 * 2. Wrapping each untrusted snippet in unambiguous XML-like delimiters makes
 *    it structurally harder for attacker-controlled content to break out of
 *    the evidence context and be interpreted as instructions.
 * 3. A short allowlist removes zero-width and directional characters that are
 *    invisible to reviewers but visible to LLM tokenizers.
 */

/** Characters we strip entirely: zero-width joiners, directional marks, etc. */
const STRIP_REGEX = /[\u200B-\u200F\u2060-\u206F\uFEFF\u202A-\u202E]/gu;

/**
 * Normalize a single evidence snippet before it reaches the drafting LLM.
 * The original snippet is preserved in the citation for the user; this is the
 * *model-input* version only.
 */
export function sanitizeEvidenceSnippet(snippet: string): string {
  return (
    snippet
      // Strip invisible control characters.
      .replace(STRIP_REGEX, '')
      // NFKC normalization: collapses homoglyphs, fullwidth, etc.
      .normalize('NFKC')
      // Remove any attempts to close the evidence delimiter early.
      .replace(/<\/evidence>/gi, '\\u003C/evidence\\u003E')
  );
}

/**
 * Wrap a sanitized snippet in an unambiguous delimiter.
 * This makes the boundary between system context and attacker text explicit
 * to both the tokenizer and any downstream guard.
 */
export function wrapEvidenceSnippet(snippet: string, index: number): string {
  const safe = sanitizeEvidenceSnippet(snippet);
  return `<evidence index="${index}">\n${safe}\n</evidence>`;
}

/** Sanitize an entire array of hits in place (model-input side only). */
export function sanitizeHits<T extends { snippet: string }>(hits: T[]): T[] {
  return hits.map((h) => ({ ...h, snippet: sanitizeEvidenceSnippet(h.snippet) }));
}
