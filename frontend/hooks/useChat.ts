"use client";

import { useCallback, useState } from "react";

import { queryRAG, submitFeedback } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (query: string) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", timestamp: new Date() },
    ]);

    try {
      const response = await queryRAG(query);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: response.answer,
                sources: response.sources,
                cached: response.cached,
                latency_ms: response.latency_ms,
              }
            : m,
        ),
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: "", error: msg } : m,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendFeedback = useCallback(
    async (message: ChatMessage, rating: 1 | -1) => {
      const userQuery =
        messages[messages.findIndex((m) => m.id === message.id) - 1]?.content ??
        "";
      await submitFeedback({
        query: userQuery,
        answer: message.content,
        rating,
      });
    },
    [messages],
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, isLoading, sendMessage, sendFeedback, clearMessages };
}
