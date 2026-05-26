import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// Mock next/navigation used by Sidebar
vi.mock("next/navigation", () => ({
  usePathname: () => "/chat",
}));

import { Sidebar } from "@/components/Sidebar";

describe("Sidebar", () => {
  it("renders the brand name", () => {
    render(<Sidebar />);
    expect(screen.getByText("RAG Pipeline")).toBeInTheDocument();
  });

  it("renders all navigation links", () => {
    render(<Sidebar />);
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("Analytics")).toBeInTheDocument();
    expect(screen.getByText("Feedback")).toBeInTheDocument();
  });

  it("highlights the active link", () => {
    render(<Sidebar />);
    const chatLink = screen.getByText("Chat").closest("a");
    expect(chatLink?.className).toContain("bg-blue-600");
  });

  it("renders the JWT token input", () => {
    render(<Sidebar />);
    expect(screen.getByPlaceholderText("Paste your JWT…")).toBeInTheDocument();
  });
});
