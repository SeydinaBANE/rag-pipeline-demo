"use client";

import { ThumbsDown, ThumbsUp, Zap } from "lucide-react";
import { useState } from "react";

import { SourceCard } from "@/components/chat/SourceCard";
import type { ChatMessage } from "@/lib/types";

interface Props {
  message: ChatMessage;
  onFeedback?: (rating: 1 | -1) => void;
}

export function MessageBubble({ message, onFeedback }: Props) {
  const [voted, setVoted] = useState<1 | -1 | null>(null);

  const handleVote = (rating: 1 | -1) => {
    setVoted(rating);
    onFeedback?.(rating);
  };

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 max-w-[85%]">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 shadow-sm">
        {message.error ? (
          <p className="text-red-500">{message.error}</p>
        ) : message.content ? (
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
        )}

        {message.content && !message.error && (
          <div className="flex items-center gap-3 mt-3 pt-2.5 border-t border-gray-100">
            {message.cached != null && (
              <span
                className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded ${
                  message.cached
                    ? "bg-green-50 text-green-600"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                <Zap className="w-3 h-3" />
                {message.cached ? "cached" : "live"}
              </span>
            )}
            {message.latency_ms != null && (
              <span className="text-xs text-gray-400">
                {message.latency_ms.toFixed(0)} ms
              </span>
            )}
            <div className="ml-auto flex gap-1">
              <button
                onClick={() => handleVote(1)}
                disabled={voted !== null}
                className={`p-1 rounded transition-colors ${
                  voted === 1
                    ? "text-green-600"
                    : "text-gray-400 hover:text-green-600"
                }`}
                aria-label="Helpful"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleVote(-1)}
                disabled={voted !== null}
                className={`p-1 rounded transition-colors ${
                  voted === -1
                    ? "text-red-500"
                    : "text-gray-400 hover:text-red-500"
                }`}
                aria-label="Not helpful"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {message.sources && message.sources.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {message.sources.map((s, i) => (
            <SourceCard key={`${s.source}-${i}`} source={s} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
