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

  // Standard LCS table (fine for the short, sentence-length fields this
  // demo diffs -- never a full document).
  const lcs = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }

  const ops = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      ops.push({ type: "equal", text: a[i] });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      ops.push({ type: "removed", text: a[i] });
      i++;
    } else {
      ops.push({ type: "added", text: b[j] });
      j++;
    }
  }
  while (i < n) {
    ops.push({ type: "removed", text: a[i] });
    i++;
  }
  while (j < m) {
    ops.push({ type: "added", text: b[j] });
    j++;
  }

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
