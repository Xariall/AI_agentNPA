"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line, Legend, CartesianGrid,
} from "recharts";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { fetchEvalMetrics, fetchEvalHistory } from "../lib/api";

interface MetricCardProps {
  label: string;
  value: string;
  hint: string;
  color?: string;
}

function MetricCard({ label, value, hint, color = "#1D4ED8" }: MetricCardProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-sm transition-shadow">
      <div className="text-2xl font-bold mb-1" style={{ color }}>{value}</div>
      <div className="text-sm font-medium text-slate-700 mb-1">{label}</div>
      <div className="text-xs text-slate-400">{hint}</div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [metrics, hist] = await Promise.all([fetchEvalMetrics(), fetchEvalHistory()]);
      setData(metrics);
      setHistory(hist);
    } catch {
      setError("Не удалось загрузить данные. Убедитесь, что backend запущен.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-500 text-sm">Загрузка метрик...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <div className="text-slate-600 text-sm">{error}</div>
        <button onClick={load} className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50">
          Повторить
        </button>
      </div>
    );
  }

  const metrics = data.metrics as Record<string, Record<string, number>>;
  const retrieval = metrics?.retrieval ?? {};
  const generation = metrics?.generation ?? {};
  const performance = metrics?.performance ?? {};
  const byCategory = (metrics?.by_category as unknown as Record<string, Record<string, number>>) ?? {};

  const hitRateData = [
    { k: "@1", value: Math.round((retrieval["hit_rate@1"] ?? 0) * 100) },
    { k: "@3", value: Math.round((retrieval["hit_rate@3"] ?? 0) * 100) },
    { k: "@5", value: Math.round((retrieval["hit_rate@5"] ?? 0) * 100) },
  ];

  const radarData = [
    { metric: "Hit Rate @5", value: Math.round((retrieval["hit_rate@5"] ?? 0) * 100) },
    { metric: "MRR×100", value: Math.round((retrieval["mrr"] ?? 0) * 100) },
    { metric: "Keyword Cov.", value: Math.round((generation["keyword_coverage"] ?? 0) * 100) },
    { metric: "Refusal OK", value: Math.round((generation["refusal_correctness"] ?? 0) * 100) },
    { metric: "Citation OK", value: Math.round((1 - (generation["verification_failure_rate"] ?? 0)) * 100) },
  ];

  const categoryData = Object.entries(byCategory).map(([cat, stats]) => ({
    category: cat.replace("_", " "),
    keyword_cov: Math.round((stats["keyword_coverage"] ?? 0) * 100),
    refusal: Math.round((stats["refusal_correctness"] ?? 0) * 100),
    count: stats["count"] ?? 0,
  }));

  const historyData = (history as Array<Record<string, unknown>>).map((h) => ({
    tag: String(h.tag).replace(/_20\d{6}_\d{6}$/, ""),
    hit_rate_5: Math.round(((h.hit_rate_5 as number) ?? 0) * 100),
    keyword_coverage: Math.round(((h.keyword_coverage as number) ?? 0) * 100),
    refusal_correctness: Math.round(((h.refusal_correctness as number) ?? 0) * 100),
  }));

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/" className="text-slate-400 hover:text-slate-700 transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-slate-800">Метрики качества</h1>
            <p className="text-xs text-slate-400">
              Eval-набор: {data.eval_set_size as number} вопросов · {data.timestamp as string} · {data.filename as string}
            </p>
          </div>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
          Обновить
        </button>
      </header>

      <div className="flex-1 p-6 space-y-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="Hit Rate @ 5"
            value={`${Math.round((retrieval["hit_rate@5"] ?? 0) * 100)}%`}
            hint="Правильный документ найден в топ-5"
            color="#1D4ED8"
          />
          <MetricCard
            label="Keyword Coverage"
            value={`${Math.round((generation["keyword_coverage"] ?? 0) * 100)}%`}
            hint="Ключевые слова ответа совпали"
            color="#16a34a"
          />
          <MetricCard
            label="Refusal Correctness"
            value={`${Math.round((generation["refusal_correctness"] ?? 0) * 100)}%`}
            hint="Правильные отказы вне домена"
            color="#9333ea"
          />
          <MetricCard
            label="Citation Integrity"
            value={`${Math.round((1 - (generation["verification_failure_rate"] ?? 0)) * 100)}%`}
            hint="Ответы без галлюцинированных ссылок"
            color="#dc2626"
          />
        </div>

        {/* Secondary metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <MetricCard
            label="MRR"
            value={(retrieval["mrr"] ?? 0).toFixed(3)}
            hint="Mean Reciprocal Rank"
            color="#0891b2"
          />
          <MetricCard
            label="Latency p50"
            value={`${Math.round((performance["latency_p50"] ?? 0) / 1000)}s`}
            hint="Медианное время ответа"
            color="#f59e0b"
          />
          <MetricCard
            label="Latency p95"
            value={`${Math.round((performance["latency_p95"] ?? 0) / 1000)}s`}
            hint="95-й перцентиль времени ответа"
            color="#f59e0b"
          />
        </div>

        {/* Charts grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Hit Rate @ k bar chart */}
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-700 mb-4">Hit Rate @ k</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={hitRateData} barSize={40}>
                <XAxis dataKey="k" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
                <Tooltip formatter={(v) => [`${v}%`, "Hit Rate"]} />
                <Bar dataKey="value" fill="#1D4ED8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Radar chart */}
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-700 mb-4">Общий профиль качества</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} />
                <Radar name="v1" dataKey="value" stroke="#1D4ED8" fill="#1D4ED8" fillOpacity={0.2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Category breakdown */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 md:col-span-2">
            <h3 className="text-sm font-semibold text-slate-700 mb-4">По категориям вопросов</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={categoryData} barSize={16} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="category" tick={{ fontSize: 11 }} width={130} />
                <Tooltip formatter={(v) => [`${v}%`]} />
                <Legend />
                <Bar dataKey="keyword_cov" name="Keyword Coverage" fill="#1D4ED8" radius={[0, 3, 3, 0]} />
                <Bar dataKey="refusal" name="Refusal Correctness" fill="#16a34a" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Iteration history */}
          {historyData.length > 1 && (
            <div className="bg-white border border-slate-200 rounded-xl p-4 md:col-span-2">
              <h3 className="text-sm font-semibold text-slate-700 mb-4">История итераций</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={historyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tag" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => [`${v}%`]} />
                  <Legend />
                  <Line type="monotone" dataKey="hit_rate_5" name="Hit Rate @5" stroke="#1D4ED8" strokeWidth={2} dot />
                  <Line type="monotone" dataKey="keyword_coverage" name="Keyword Coverage" stroke="#16a34a" strokeWidth={2} dot />
                  <Line type="monotone" dataKey="refusal_correctness" name="Refusal Correctness" stroke="#9333ea" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
