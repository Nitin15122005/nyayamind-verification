/** Small word-level LCS diff -- no new npm dependency. Used only to render
 * the correction visualization: strikethrough the removed span, highlight
 * the added span, leave everything else (the vast majority of a
 * correction, by construction) untouched. Tokenizes on whitespace while
 * keeping the whitespace itself as part of the following token, so the
 * rendered text reflows exactly like the original. */

function tokenize(text) {
  return text.match(/\S+\s*|\s+/g) || [];
}

export function wordDiff(before, after) {
  const a = tokenize(before || "");
  const b = tokenize(after || "");
  const n = a.length;
  const m = b.length;

  // Preserve the unchanged paragraph edges without putting them through the
  // quadratic LCS table. Correction edits are local, so this keeps full-
  // paragraph previews efficient even when the surrounding text is long.
  let prefix = 0;
  while (prefix < n && prefix < m && a[prefix] === b[prefix]) prefix++;

  let suffix = 0;
  while (
    suffix < n - prefix &&
    suffix < m - prefix &&
    a[n - suffix - 1] === b[m - suffix - 1]
  ) suffix++;

  const aMiddle = a.slice(prefix, n - suffix);
  const bMiddle = b.slice(prefix, m - suffix);
  const middleOps = [];
  const middleN = aMiddle.length;
  const middleM = bMiddle.length;

  // Bound memory for pathological inputs with multiple distant edits. If
  // the unmatched middle is too large, show it as one replacement region
  // rather than allocating an unbounded quadratic matrix.
  if (middleN * middleM > 1_000_000) {
    if (middleN) middleOps.push({ type: "removed", text: aMiddle.join("") });
    if (middleM) middleOps.push({ type: "added", text: bMiddle.join("") });
  } else {
    const lcs = Array.from({ length: middleN + 1 }, () => new Array(middleM + 1).fill(0));
    for (let i = middleN - 1; i >= 0; i--) {
      for (let j = middleM - 1; j >= 0; j--) {
        lcs[i][j] = aMiddle[i] === bMiddle[j]
          ? lcs[i + 1][j + 1] + 1
          : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
      }
    }

    let i = 0;
    let j = 0;
    while (i < middleN && j < middleM) {
      if (aMiddle[i] === bMiddle[j]) {
        middleOps.push({ type: "equal", text: aMiddle[i] });
        i++;
        j++;
      } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
        middleOps.push({ type: "removed", text: aMiddle[i++] });
      } else {
        middleOps.push({ type: "added", text: bMiddle[j++] });
      }
    }
    while (i < middleN) middleOps.push({ type: "removed", text: aMiddle[i++] });
    while (j < middleM) middleOps.push({ type: "added", text: bMiddle[j++] });
  }

  const ops = [];
  if (prefix) ops.push({ type: "equal", text: a.slice(0, prefix).join("") });
  ops.push(...middleOps);
  if (suffix) ops.push({ type: "equal", text: a.slice(n - suffix).join("") });

  // Merge consecutive same-type runs so rendering isn't one <span> per word.
  const merged = [];
  for (const op of ops) {
    const last = merged[merged.length - 1];
    if (last && last.type === op.type) {
      last.text += op.text;
    } else {
      merged.push({ ...op });
    }
  }
  return merged;
}
