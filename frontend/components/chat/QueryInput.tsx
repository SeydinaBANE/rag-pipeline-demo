"use client";

import { ArrowUp } from "lucide-react";
import { type KeyboardEvent, useRef, useState } from "react";

interface Props {
  onSend: (query: string) => void;
  isLoading: boolean;
}

export function QueryInput({ onSend, isLoading }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const query = value.trim();
    if (!query || isLoading) return;
    setValue("");
    onSend(query);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="border-t bg-white px-4 py-3">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
          rows={1}
          className="flex-1 resize-none rounded-xl border border-gray-300 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder:text-gray-400"
          disabled={isLoading}
        />
        <button
          onClick={submit}
          disabled={!value.trim() || isLoading}
          className="shrink-0 w-9 h-9 flex items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          aria-label="Send"
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      </div>
      <p className="text-center text-gray-400 text-xs mt-2">
        Answers may be inaccurate. Always verify with primary sources.
      </p>
    </div>
  );
}
