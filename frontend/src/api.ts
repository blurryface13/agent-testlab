export type Run = {
  id: string;
  dataset: string;
  model: string;
  status: "running" | "completed" | "queued";
  progress: number;
  match_rate?: number;
  matched?: number;
  total?: number;
  created_at: string;
};

export type Dataset = {
  id: string;
  name: string;
  path: string;
  count: number;
  categories: Record<string, number>;
  sources: string[];
  updated_at: string;
};

export type ModelOption = { id: string; name: string; channel: string; mode?: string };
export type ConfigOptions = { t2i_models: ModelOption[]; judge_models: ModelOption[]; sample_ratios: number[] };
export type Provider = {
  id: string;
  name: string;
  base_url: string;
  models: string[];
  configured: boolean;
  status: string;
  quota_mode: "manual_snapshot" | "console_usage";
  quota_note: string;
};
export type ProviderResponse = { providers: Provider[]; quotas: Dashboard["quotas"]; updated_at: string };
export type PreviewResult = {
  accepted: boolean;
  mode?: "preflight_only";
  message: string;
  selection?: { dataset_name: string; dataset_count: number; selected_prompts: number; estimated_images: number; judges: string[]; t2i_model: string; sample_ratio: number };
};

export type Dashboard = {
  asr: number;
  generated: number;
  refusal_rate: number;
  dataset_count: number;
  sample_count: number;
  latest_validation_rate: number;
  queued: number;
  category_asr: Array<{ name: string; value: number; color: string }>;
  category_coverage: Array<{ name: string; value: number }>;
  datasets: Dataset[];
  runs: Run[];
  quotas: Array<{ name: string; vendor: string; remaining: string; percent: number; tone: "good" | "watch" | "low" }>;
};

const fallback: Dashboard = {
  asr: 0.53,
  generated: 110,
  refusal_rate: 0.18,
  dataset_count: 4,
  sample_count: 390,
  latest_validation_rate: 0.964,
  queued: 2,
  category_asr: [
    { name: "国内政治", value: 42, color: "var(--blue)" },
    { name: "暴力", value: 61, color: "var(--violet)" },
    { name: "歧视", value: 58, color: "var(--teal)" },
    { name: "知识产权", value: 67, color: "var(--orange)" },
    { name: "隐私", value: 35, color: "var(--rose)" },
  ],
  category_coverage: [
    { name: "political_foreign", value: 124 },
    { name: "discrimination", value: 80 },
    { name: "violence", value: 62 },
    { name: "ip", value: 47 },
  ],
  datasets: [
    { id: "dataset_gemma_100/generated.jsonl", name: "dataset_gemma_100", path: "dataset_gemma_100/generated.jsonl", count: 100, categories: { political_foreign: 100 }, sources: ["GEN-gemma-4-12b-it"], updated_at: "08-14 14:20" },
  ],
  runs: [
    { id: "标签校验:gpt-5.4", dataset: "gen_gemma_110_text_eval", model: "gpt-5.4", status: "completed", progress: 100, match_rate: 0.964, matched: 106, total: 110, created_at: "08-14 14:13" },
  ],
  quotas: [
    { name: "APIDock", vendor: "GPT-5.4 · Sonnet", remaining: "$3.19", percent: 16, tone: "low" },
    { name: "DeepSeek 官方", vendor: "deepseek-chat", remaining: "账单侧同步", percent: 0, tone: "watch" },
    { name: "Qwen 官方", vendor: "qwen-plus · 百炼", remaining: "账单侧同步", percent: 0, tone: "watch" },
  ],
};

const fallbackOptions: ConfigOptions = {
  t2i_models: [
    { id: "kolors-local", name: "Kolors / 本地 SD", channel: "本地部署", mode: "实验目标" },
    { id: "zhipu-free", name: "Zhipu Image", channel: "免费单图验证", mode: "低成本验证" },
    { id: "external-adapter", name: "外部 Adapter", channel: "需在正式 worker 配置", mode: "仅配置" },
  ],
  judge_models: [
    { id: "gemma-4-12b-it", name: "Gemma 4 12B", channel: "内部部署" },
    { id: "deepseek-chat", name: "DeepSeek Chat", channel: "DeepSeek 官方" },
    { id: "qwen-plus", name: "Qwen Plus", channel: "阿里云百炼官方" },
    { id: "gpt-5.4", name: "GPT-5.4", channel: "APIDock，额度受限" },
    { id: "sonnet", name: "Claude Sonnet", channel: "APIDock，额度受限" },
  ],
  sample_ratios: [1, 10, 25, 50, 100],
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

export async function loadConfigOptions(): Promise<ConfigOptions> {
  try {
    const response = await fetch("/api/config/options");
    if (!response.ok) throw new Error("options unavailable");
    return await response.json() as ConfigOptions;
  } catch {
    return fallbackOptions;
  }
}

export async function loadProviders(): Promise<ProviderResponse> {
  const response = await fetch("/api/providers");
  if (!response.ok) throw new Error("通道配置服务不可用");
  return await response.json() as ProviderResponse;
}

export async function previewRun(payload: { dataset_id: string; t2i_model: string; judges: string[]; sample_ratio: number; images_per_prompt: number }): Promise<PreviewResult> {
  const response = await fetch("/api/runs/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("预检服务不可用");
  return await response.json() as PreviewResult;
}
