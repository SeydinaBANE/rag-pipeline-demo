"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";

import { submitFeedback } from "@/lib/api";

interface FeedbackItem {
  id: string;
  query: string;
  answer: string;
  rating: 1 | -1 | null;
}

const DEMO_ITEMS: FeedbackItem[] = [
  {
    id: "1",
    query: "What is Retrieval-Augmented Generation?",
    answer:
      "RAG combines information retrieval with text generation. A retriever fetches relevant documents from a knowledge base, and a language model generates an answer conditioned on those documents.",
    rating: null,
  },
  {
    id: "2",
    query: "How does BM25 work?",
    answer:
      "BM25 is a ranking function based on term frequency and inverse document frequency. It handles exact keyword matching and complements dense vector retrieval in hybrid search.",
    rating: null,
  },
  {
    id: "3",
    query: "What is LangChain used for?",
    answer:
      "LangChain is a framework for developing applications powered by language models. It provides tools for chaining calls to LLMs, managing memory, and building agents.",
    rating: null,
  },
];

export default function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>(DEMO_ITEMS);
  const [submitting, setSubmitting] = useState<string | null>(null);

  const vote = async (item: FeedbackItem, rating: 1 | -1) => {
    setSubmitting(item.id);
    try {
      await submitFeedback({ query: item.query, answer: item.answer, rating });
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, rating } : i)),
      );
    } catch {
      // silent fail — demo mode without auth
    } finally {
      setSubmitting(null);
    }
  };

  const positive = items.filter((i) => i.rating === 1).length;
  const total = items.filter((i) => i.rating !== null).length;

  return (
    <div className="flex flex-col h-screen">
      <div className="border-b bg-white px-6 py-3.5">
        <h1 className="font-semibold text-gray-900">Feedback</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Rate answers to improve the pipeline · stored per-tenant in JSONL
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 max-w-2xl">
        {total > 0 && (
          <div className="bg-green-50 border border-green-100 rounded-xl px-4 py-3 mb-5 text-sm text-green-700">
            {positive}/{total} answers rated helpful (
            {Math.round((positive / total) * 100)}% positive)
          </div>
        )}

        <div className="space-y-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-white border border-gray-200 rounded-xl p-5"
            >
              <p className="text-xs font-medium text-blue-600 mb-1.5">
                Q: {item.query}
              </p>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">
                {item.answer}
              </p>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400 mr-1">Was this helpful?</span>
                <button
                  onClick={() => void vote(item, 1)}
                  disabled={item.rating !== null || submitting === item.id}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    item.rating === 1
                      ? "bg-green-50 border-green-200 text-green-700"
                      : "border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-700"
                  } disabled:opacity-50`}
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  Yes
                </button>
                <button
                  onClick={() => void vote(item, -1)}
                  disabled={item.rating !== null || submitting === item.id}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    item.rating === -1
                      ? "bg-red-50 border-red-200 text-red-700"
                      : "border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-700"
                  } disabled:opacity-50`}
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                  No
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
