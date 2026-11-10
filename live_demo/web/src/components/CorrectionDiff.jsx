import { wordDiff } from "../lib/diff.js";

/** Renders only the changed span with emphasis (strikethrough for removed,
 * highlighted accent for added) -- everything else in the paragraph is
 * plain text, matching the "only the changed phrase, not the whole
 * paragraph" requirement. */
export default function CorrectionDiff({ before, after }) {
  const ops = wordDiff(before, after);
  return (
    <p className="text-lg font-medium leading-[1.65] text-ink-primary">
      {ops.map((op, idx) => {
        if (op.type === "equal") return <span key={idx}>{op.text}</span>;
        if (op.type === "removed") {
          return (
            <span key={idx} className="text-contra/90 line-through decoration-contra/70">
              {op.text}
            </span>
          );
        }
        return (
          <span
            key={idx}
            className="rounded-[3px] bg-entail/20 px-0.5 font-medium text-entail underline decoration-entail/40"
          >
            {op.text}
          </span>
        );
      })}
    </p>
  );
}
