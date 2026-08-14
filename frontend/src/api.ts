export type Run = {
  id: string;
  dataset: string;
  model: string;
  status: "running" | "completed" | "queued";
  progress: number;
  asr?: number;
  created_at: string;
};

export type Dashboard = {
  asr: number;
  generated: number;
  refusal_rate: number;
  queued: number;
  category_asr: Array<{ name: string; value: number; color: string }>;
  runs: Run[];
  quotas: Array<{ name: string; vendor: string; remaining: string; percent: number; tone: "good" | "watch" | "low" }>;
};

const fallback: Dashboard = {
  asr: 0.53,
  generated: 110,
  refusal_rate: 0.18,
  queued: 2,
  category_asr: [
    { name: "国内政治", value: 42, color: "var(--blue)" },
    { name: "暴力", value: 61, color: "var(--violet)" },
    { name: "歧视", value: 58, color: "var(--teal)" },
    { name: "知识产权", value: 67, color: "var(--orange)" },
    { name: "隐私", value: 35, color: "var(--rose)" },
  ],
  runs: [
    { id: "run-20260814-03", dataset: "Gemma Stage 1 · 110", model: "Kolors / local", status: "running", progress: 68, created_at: "今天 14:20" },
    { id: "run-20260814-02", dataset: "国内政治 · 100", model: "Zhipu Image", status: "completed", progress: 100, asr: 0.42, created_at: "今天 10:12" },
    { id: "run-20260813-01", dataset: "GPT-5.4 · 110", model: "Kolors / local", status: "completed", progress: 100, asr: 0.53, created_at: "昨天 18:46" },
  ],
  quotas: [
    { name: "APIDock", vendor: "GPT-5.4 · Sonnet", remaining: "$3.19", percent: 16, tone: "low" },
    { name: "Gemma local", vendor: "内部部署", remaining: "可用", percent: 96, tone: "good" },
    { name: "Zhipu free", vendor: "单图验证", remaining: "可用", percent: 72, tone: "watch" },
  ],
};

export async function loadDashboard(): Promise<{ data: Dashboard; source: "api" | "demo" }> {
  try {
    const response = await fetch("/api/dashboard");
    if (!response.ok) throw new Error("dashboard unavailable");
    return { data: await response.json() as Dashboard, source: "api" };
  } catch {
    return { data: fallback, source: "demo" };
  }
}
