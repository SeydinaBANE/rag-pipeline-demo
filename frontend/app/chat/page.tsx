"use client";

import { Bot, Trash2 } from "lucide-react";
import { useEffect, useRef } from "react";

import { MessageBubble } from "@/components/chat/MessageBubble";
import { QueryInput } from "@/components/chat/QueryInput";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const { messages, isLoading, sendMessage, sendFeedback, clearMessages } =
    useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-white px-6 py-3.5">
        <div>
          <h1 className="font-semibold text-gray-900">Chat</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Hybrid retrieval · BM25 + vector · cross-encoder reranking
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center">
              <Bot className="w-7 h-7 text-blue-500" />
            </div>
            <div>
              <p className="font-medium text-gray-700">Ready to answer</p>
              <p className="text-sm text-gray-400 mt-1 max-w-xs">
                Ask anything about your indexed documents or RAG concepts.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              {[
                "What is RAG?",
                "How does BM25 work?",
                "Explain hybrid search",
              ].map((hint) => (
                <button
                  key={hint}
                  onClick={() => sendMessage(hint)}
                  className="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onFeedback={
              msg.role === "assistant"
                ? (rating) => void sendFeedback(msg, rating)
                : undefined
            }
          />
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <QueryInput onSend={(q) => void sendMessage(q)} isLoading={isLoading} />
    </div>
  );
}
