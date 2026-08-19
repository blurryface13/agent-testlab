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
export type GenerationProvider = { id: string; name: string; configured: boolean; status: string; quota_note: string };
export type GenerationModel = { id: string; name: string; provider: string; channel: string; cost_note: string };
export type GenerationOptions = { providers: GenerationProvider[]; models: GenerationModel[]; subcategory_count: number };
export type GenerationRun = {
  id: string;
  status: "running" | "completed" | "failed";
  provider: string;
  model: string;
  samples_per_subcategory: number;
  target_count: number;
  generated_count: number;
  created_at: string;
  output_dir: string;
  log_path: string;
  return_code: number | null;
};
export type GenerationStartResult = { accepted: boolean; message: string; run?: GenerationRun };
export type PolishModel = GenerationModel & { configured: boolean };
export type PolishSample = {
  id: string;
  category: string;
  subcategory: string;
  prompt: string;
  status: "refused" | "pending" | "polished" | "not_generated";
  recommended?: boolean;
  rationale?: string;
  polished?: Array<{ id: string; prompt: string }>;
};
export type PolishOptions = {
  baseline: { dataset_path: string; total: number; unsafe: number; asr: number; judge: string };
  target_asr: number;
  additional_unsafe_needed: number;
  historical_source_promotion_rate: number;
  recommended_seed_count: number;
  candidate_count: number;
  models: PolishModel[];
  samples: PolishSample[];
  scope_note: string;
};
export type PolishRun = {
  id: string;
  status: "running" | "completed" | "failed";
  model: string;
  target_asr: number;
  selected_count: number;
  variants: number;
  generated_count: number;
  output_dir: string;
  log_path: string;
  return_code: number | null;
  samples: PolishSample[];
};
export type PolishStartResult = { accepted: boolean; message: string; run?: PolishRun };

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
    { id: "zhipu-free", name: "Zhipu Image", channel: "免费单图验证", mode: "低成本验证" },
    { id: "qwen-image", name: "Qwen Image 官方", channel: "DashScope 官方", mode: "官方" },
    { id: "gpt-image-2", name: "GPT Image 2", channel: "APIDock", mode: "官方" },
    { id: "gemini-3.1-flash-image", name: "Gemini 3.1 Flash Image", channel: "DMXAPI", mode: "常用" },
  ],
  judge_models: [
    { id: "gemma-4-12b-it", name: "Gemma 4 12B", channel: "内网 vLLM" },
    { id: "deepseek-chat", name: "DeepSeek Chat", channel: "DeepSeek 官方" },
    { id: "qwen-plus", name: "Qwen Plus", channel: "阿里云百炼官方" },
    { id: "gpt-5.4", name: "GPT-5.4", channel: "APIDock" },
    { id: "gpt-5.6-sol", name: "GPT-5.6 Sol", channel: "APIDock" },
    { id: "claude-sonnet-4-6", name: "Claude Sonnet 4.6", channel: "APIDock" },
    { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", channel: "DMXAPI" },
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

export type QuotaRecord = { name: string; vendor: string; remaining: string; percent: number; tone: "good" | "watch" | "low"; provider?: string };
export type QuotaSnapshot = { found: boolean; quotas: QuotaRecord[]; updated_at: string | null; message: string };

export type PromptView = {
  found: boolean;
  node: string;
  sample_id?: string;
  subcategory?: string;
  category?: string;
  system?: string;
  user?: string;
  note?: string;
  dataset_id?: string;
  message?: string;
};

export type CategoryNode = { id: string; name: string; subcategories: string[] };
export type CategoriesResponse = { found: boolean; categories: CategoryNode[]; message?: string };

export async function loadCategories(): Promise<CategoriesResponse> {
  const response = await fetch("/api/logs/categories");
  if (!response.ok) throw new Error("类别映射服务不可用");
  return await response.json() as CategoriesResponse;
}

export async function loadPrompts(node: string, datasetId?: string, subcategory?: string): Promise<PromptView> {
  const query = new URLSearchParams({ node });
  if (datasetId) query.set("dataset_id", datasetId);
  if (subcategory) query.set("subcategory", subcategory);
  const response = await fetch(`/api/logs/prompts?${query.toString()}`);
  if (!response.ok) throw new Error("提示词还原服务不可用");
  return await response.json() as PromptView;
}

export type T2ISample = { id: string; subcategory?: string; category?: string; prompt?: string; status: "pending" | "success" | "error" | "cancelled"; error?: string; img?: string; size_kb?: number };
export type T2IRun = { id: string; status: "running" | "completed"; model: string; done: number; total: number; output_dir: string; samples: T2ISample[] };
export type T2IStartResult = { accepted: boolean; message: string; run?: T2IRun };
export type T2IJudgeResult = { id: string; status: "done" | "error"; unsafe?: boolean; reason?: string; error?: string };
export type T2IJudgeResponse = { found: boolean; model?: string; results?: T2IJudgeResult[]; message?: string };

export async function startT2IGenerate(payload: { dataset_id: string; model: string; subcategory?: string; limit: number }): Promise<T2IStartResult> {
  const response = await fetch("/api/t2i/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("生图任务提交失败");
  return await response.json() as T2IStartResult;
}

export async function loadT2IRun(runId: string): Promise<T2IRun> {
  const response = await fetch(`/api/t2i/runs/${encodeURIComponent(runId)}`);
  if (!response.ok) throw new Error("生图任务状态读取失败");
  const payload = await response.json() as { found: boolean; run?: T2IRun; message?: string };
  if (!payload.found || !payload.run) throw new Error(payload.message || "生图任务不存在");
  return payload.run;
}

export async function judgeT2I(payload: { run_id: string; model: string; sample_ids: string[] }): Promise<T2IJudgeResponse> {
  const response = await fetch("/api/t2i/judge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("裁判任务提交失败");
  return await response.json() as T2IJudgeResponse;
}

export async function loadQuota(): Promise<QuotaSnapshot> {
  const response = await fetch("/api/quota/refresh");
  if (!response.ok) throw new Error("额度查询服务不可用");
  return await response.json() as QuotaSnapshot;
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

export async function loadGenerationOptions(): Promise<GenerationOptions> {
  const response = await fetch("/api/generation/options");
  if (!response.ok) throw new Error("生成通道配置服务不可用");
  return await response.json() as GenerationOptions;
}

export async function startGeneration(payload: { provider: string; model: string; samples_per_subcategory: number }): Promise<GenerationStartResult> {
  const response = await fetch("/api/generation/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("生成任务未能提交");
  return await response.json() as GenerationStartResult;
}

export async function loadGenerationRun(runId: string): Promise<GenerationRun> {
  const response = await fetch(`/api/generation/runs/${encodeURIComponent(runId)}`);
  if (!response.ok) throw new Error("无法读取生成任务状态");
  const payload = await response.json() as { found: boolean; message?: string; run?: GenerationRun };
  if (!payload.found || !payload.run) throw new Error(payload.message || "生成任务不存在");
  return payload.run;
}

export async function loadPolishOptions(targetAsr = 0.2): Promise<PolishOptions> {
  const response = await fetch(`/api/polish/options?target_asr=${encodeURIComponent(targetAsr)}`);
  if (!response.ok) throw new Error("Polish 选样服务不可用");
  const payload = await response.json() as PolishOptions & { error?: string };
  if (payload.error) throw new Error(payload.error);
  return payload;
}

export async function startPolish(payload: { model: string; selected_ids: string[]; target_asr: number; variants: number }): Promise<PolishStartResult> {
  const response = await fetch("/api/polish/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Polish 任务未能提交");
  return await response.json() as PolishStartResult;
}

export async function loadPolishRun(runId: string): Promise<PolishRun> {
  const response = await fetch(`/api/polish/runs/${encodeURIComponent(runId)}`);
  if (!response.ok) throw new Error("无法读取 Polish 任务状态");
  const payload = await response.json() as { found: boolean; message?: string; run?: PolishRun };
  if (!payload.found || !payload.run) throw new Error(payload.message || "Polish 任务不存在");
  return payload.run;
}
