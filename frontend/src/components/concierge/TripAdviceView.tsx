import type { TripAdviceResponse } from "@/lib/concierge/types";

interface TripAdviceViewProps {
  response: TripAdviceResponse;
}

type MarkdownBlock =
  | { kind: "heading"; depth: number; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "table"; headers: string[]; rows: string[][] };

function parseTable(lines: string[]): { headers: string[]; rows: string[][] } | null {
  if (lines.length < 2) return null;
  const header = lines[0];
  const divider = lines[1];
  if (!/^\|.*\|$/.test(header) || !/^\|[\s:-|]+\|$/.test(divider)) return null;
  const headers = header.split("|").map((c) => c.trim()).filter(Boolean);
  const rows = lines.slice(2)
    .filter((line) => /^\|.*\|$/.test(line))
    .map((line) => line.split("|").map((c) => c.trim()).filter(Boolean));
  return { headers, rows };
}

function parseMarkdown(markdown: string): MarkdownBlock[] {
  const chunks = markdown.split(/\n\s*\n/g).map((c) => c.trim()).filter(Boolean);
  const blocks: MarkdownBlock[] = [];

  for (const chunk of chunks) {
    const lines = chunk.split("\n").map((line) => line.trim()).filter(Boolean);
    if (lines.length === 0) continue;

    const table = parseTable(lines);
    if (table) {
      blocks.push({ kind: "table", headers: table.headers, rows: table.rows });
      continue;
    }

    if (lines.every((line) => /^[-*]\s+/.test(line))) {
      blocks.push({ kind: "list", items: lines.map((line) => line.replace(/^[-*]\s+/, "")) });
      continue;
    }

    if (lines.every((line) => /^\d+\.\s+/.test(line))) {
      blocks.push({ kind: "list", items: lines.map((line) => line.replace(/^\d+\.\s+/, "")) });
      continue;
    }

    if (lines.length === 1 && /^#{1,6}\s+/.test(lines[0])) {
      const line = lines[0];
      const depth = Math.min(6, line.match(/^#+/)?.[0].length ?? 1);
      blocks.push({ kind: "heading", depth, text: line.replace(/^#{1,6}\s+/, "") });
      continue;
    }

    blocks.push({ kind: "paragraph", text: lines.join(" ") });
  }

  return blocks;
}

export function TripAdviceView({ response }: TripAdviceViewProps) {
  return (
    <section aria-label="trip advice" className="space-y-4">
      <p className="text-sm leading-relaxed text-slate-700">{response.response}</p>

      {response.adviceSections.map((section) => (
        <article key={section.heading} className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-slate-900">{section.heading}</h3>
          <div className="space-y-2 text-sm text-slate-700">
            {parseMarkdown(section.bodyMarkdown).map((block, idx) => {
              if (block.kind === "heading") {
                return (
                  <p key={idx} className="font-semibold text-slate-900">
                    {block.text}
                  </p>
                );
              }
              if (block.kind === "list") {
                return (
                  <ul key={idx} className="list-disc space-y-1 pl-5">
                    {block.items.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                );
              }
              if (block.kind === "table") {
                return (
                  <div key={idx} className="overflow-x-auto">
                    <table className="min-w-full border-collapse border border-slate-300 text-left text-xs">
                      <thead className="bg-slate-100 text-slate-800">
                        <tr>
                          {block.headers.map((header) => (
                            <th key={header} className="border border-slate-300 px-2 py-1 font-semibold">{header}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {block.rows.map((row, rowIdx) => (
                          <tr key={`${rowIdx}-${row.join("-")}`} className="bg-white">
                            {row.map((cell, cellIdx) => (
                              <td key={`${cellIdx}-${cell}`} className="border border-slate-300 px-2 py-1">{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              }
              return <p key={idx}>{block.text}</p>;
            })}
          </div>
        </article>
      ))}

      {response.citations.length > 0 ? (
        <footer className="space-y-1 border-t border-slate-200 pt-2 text-xs text-slate-600">
          <p className="font-semibold">Sources</p>
          <ul className="space-y-1">
            {response.citations.map((citation) => (
              <li key={citation.url}>
                <a href={citation.url} target="_blank" rel="noreferrer" className="text-blue-700 hover:underline">
                  {citation.label}
                </a>
              </li>
            ))}
          </ul>
        </footer>
      ) : null}
    </section>
  );
}
