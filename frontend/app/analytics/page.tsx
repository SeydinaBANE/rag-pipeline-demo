"use client";

import { Activity, Clock, Database, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { checkHealth } from "@/lib/api";

interface StatCard {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

export default function AnalyticsPage() {
  const [version, setVersion] = useState("–");
  const [apiStatus, setApiStatus] = useState<"unknown" | "ok" | "error">(
    "unknown",
  );

  useEffect(() => {
    checkHealth()
      .then((h) => {
        setVersion(h.version);
        setApiStatus("ok");
      })
      .catch(() => setApiStatus("error"));
  }, []);

  const cards: StatCard[] = [
    {
      label: "API Status",
      value: apiStatus === "ok" ? "Healthy" : apiStatus === "error" ? "Down" : "Checking…",
      icon: Activity,
      color: apiStatus === "ok" ? "text-green-500" : "text-red-500",
    },
    {
      label: "API Version",
      value: version,
      icon: Database,
      color: "text-blue-500",
    },
    {
      label: "Cache",
      value: "Redis · local",
      icon: Zap,
      color: "text-yellow-500",
    },
    {
      label: "Latency target",
      value: "< 2 s p95",
      icon: Clock,
      color: "text-purple-500",
    },
  ];

  return (
    <div className="flex flex-col h-screen">
      <div className="border-b bg-white px-6 py-3.5">
        <h1 className="font-semibold text-gray-900">Analytics</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Pipeline health · Prometheus metrics at{" "}
          <code className="bg-gray-100 px-1 rounded">:8000/metrics</code>
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="grid grid-cols-2 gap-4 max-w-2xl">
          {cards.map(({ label, value, icon: Icon, color }) => (
            <div
              key={label}
              className="bg-white border border-gray-200 rounded-xl p-5 flex items-start gap-4"
            >
              <div className={`mt-0.5 ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">
                  {label}
                </p>
                <p className="text-lg font-semibold text-gray-900 mt-0.5">
                  {value}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Prometheus Metrics
          </h2>
          <div className="bg-gray-900 rounded-xl p-4 font-mono text-xs text-green-400 space-y-1">
            <p># HELP rag_query_total Total RAG queries processed</p>
            <p>rag_query_total{"{"} tenant_id=&quot;acme&quot; {"}"} …</p>
            <p># HELP rag_query_latency_seconds RAG query end-to-end latency</p>
            <p>rag_query_latency_seconds_bucket{"{"} le=&quot;1.0&quot; {"}"} …</p>
            <p className="text-gray-600">
              → open{" "}
              <a
                href="http://localhost:8000/metrics"
                target="_blank"
                rel="noreferrer"
                className="underline text-green-500"
              >
                localhost:8000/metrics
              </a>{" "}
              to view live data
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
