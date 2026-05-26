import type { SourceDocument } from "@/lib/types";

interface Props {
  source: SourceDocument;
  index: number;
}

export function SourceCard({ source, index }: Props) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-blue-600 font-medium text-xs truncate max-w-[200px]">
          [{index + 1}] {source.source}
        </span>
        {source.score != null && (
          <span className="text-gray-400 text-xs ml-2 shrink-0">
            score {source.score.toFixed(3)}
          </span>
        )}
      </div>
      <p className="text-gray-600 text-xs leading-relaxed line-clamp-3">
        {source.content}
      </p>
    </div>
  );
}
