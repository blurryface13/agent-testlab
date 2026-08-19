import { FormEvent, useEffect, useState } from "react";
import { ConfigOptions, Dashboard, Dataset, GenerationOptions, GenerationRun, PolishOptions, PolishRun, PolishSample, PreviewResult, PromptView, ProviderResponse, QuotaSnapshot, loadConfigOptions, loadDashboard, loadGenerationOptions, loadGenerationRun, loadPolishOptions, loadPolishRun, loadPrompts, loadProviders, loadQuota, previewRun, startGeneration, startPolish } from "./api";
import { Icon, IconName } from "./icons";

const navItems: Array<[string, IconName]> = [["概览", "overview"], ["数据集", "dataset"], ["生成数据集", "generate"], ["Polish", "polish"], ["运行任务", "runs"], ["结果分析", "analysis"], ["日志", "log"]];
const statusLabel = { running: "运行中", completed: "已完成", queued: "队列中" };

export function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [options, setOptions] = useState<ConfigOptions | null>(null);
  const [providers, setProviders] = useState<ProviderResponse | null>(null);
  const [source, setSource] = useState<"api" | "demo">("demo");
  const [active, setActive] = useState("概览");
  const [quota, setQuota] = useState<QuotaSnapshot | null>(null);
  const [quotaLoading, setQuotaLoading] = useState(false);
  const [view, setView] = useState<"overview" | "composer" | "generator" | "polish" | "providers" | "logs">("overview");

  const refresh = () => {
    Promise.all([loadDashboard(), loadConfigOptions(), loadProviders().catch(() => null)]).then(([nextDashboard, nextOptions, nextProviders]) => {
      setDashboard(nextDashboard.data);
      setSource(nextDashboard.source);
      setOptions(nextOptions);
      setProviders(nextProviders);
    });
  };

  useEffect(refresh, []);

  const fetchQuota = async () => {
    setQuotaLoading(true);
    try {
      setQuota(await loadQuota());
    } catch {
      setQuota({ found: false, quotas: [], updated_at: null, message: "查询失败，请确认后端已启动" });
    } finally {
      setQuotaLoading(false);
    }
  };

  const openComposer = () => {
    setActive("运行任务");
    setView("composer");
  };
  const openGenerator = () => {
    setActive("生成数据集");
    setView("generator");
  };
  const openProviders = () => {
    setActive("通道与额度");
    setView("providers");
  };
  const openPolish = () => {
    setActive("Polish");
    setView("polish");
  };

  const selectNav = (label: string) => {
    setActive(label);
    if (label === "运行任务") {
      setView("composer");
      return;
    }
    if (label === "生成数据集") {
      setView("generator");
      return;
    }
    if (label === "Polish") {
      setView("polish");
      return;
    }
    if (label === "结果分析") {
      setView("overview");
      setTimeout(() => document.getElementById("pipeline")?.scrollIntoView({ behavior: "smooth" }), 0);
      return;
    }
    if (label === "日志") {
      setView("logs");
      return;
    }
    setView("overview");
    if (label === "数据集") setTimeout(() => document.getElementById("datasets")?.scrollIntoView({ behavior: "smooth" }), 0);
  };

  if (!dashboard || !options) return <main className="loading">正在读取实验概览…</main>;
  const coverage = dashboard.category_coverage.slice(0, 5);
  const maxCoverage = Math.max(1, ...coverage.map((item) => item.value));

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">↗</span><span>T2I Safety Eval</span><em>LAB</em></div>
        <div className="top-actions"><span className={`source-badge ${source}`}><i />{source === "api" ? "已连接本地服务" : "演示数据"}</span><button className="avatar" aria-label="当前用户">D</button></div>
      </header>

      <aside className="sidebar">
        <p className="nav-caption">评测工作台</p>
        {navItems.map(([label, icon]) => <button key={label} className={active === label ? "nav-item selected" : "nav-item"} onClick={() => selectNav(label)}><Icon name={icon} />{label}</button>)}
        <div className="sidebar-separator" />
        <p className="nav-caption">系统</p>
        <button className={active === "通道与额度" ? "nav-item selected" : "nav-item"} onClick={openProviders}><Icon name="channel" />通道与额度</button>
        <div className="sidebar-bottom"><span className="pulse" />Local workbench</div>
      </aside>

      <main className="content" id="workspace">
        {view === "composer" ? (
          <RunComposer datasets={dashboard.datasets} options={options} onBack={() => { setView("overview"); setActive("概览"); }} />
        ) : view === "generator" ? (
          <DatasetGenerator onBack={() => { setView("overview"); setActive("概览"); }} onCompleted={refresh} />
        ) : view === "polish" ? (
          <PolishWorkbench onBack={() => { setView("overview"); setActive("概览"); }} />
        ) : view === "providers" ? (
          <ProviderConsole providers={providers} onBack={() => { setView("overview"); setActive("概览"); }} onRefresh={refresh} />
        ) : view === "logs" ? (
          <LogsPage datasets={dashboard.datasets} onBack={() => { setView("overview"); setActive("概览"); }} />
        ) : (
          <>
            <section className="page-heading">
              <div><p className="eyebrow">PIPELINE OVERVIEW</p><h1>实验概览</h1></div>
              <div className="heading-actions"><button className="secondary" onClick={refresh}><Icon name="refresh" />刷新</button><button className="secondary" onClick={openPolish}>Polish</button><button className="secondary" onClick={openComposer}>新建评测</button><button className="primary" onClick={openGenerator}><Icon name="generate" />生成数据集</button></div>
            </section>

            <section className="metric-strip" aria-label="核心指标">
              <Metric label="已索引数据集" value={dashboard.dataset_count.toString()} tone="blue" />
              <Metric label="已索引样本" value={dashboard.sample_count.toString()} tone="teal" />
              <Metric label="最近标签命中" value={`${Math.round(dashboard.latest_validation_rate * 100)}%`} tone="violet" />
            </section>

            <section className="dashboard-grid">
              <section className="panel category-panel">
                <div className="panel-heading"><h2>小类样本覆盖</h2><button className="text-button" onClick={() => document.getElementById("datasets")?.scrollIntoView({ behavior: "smooth" })}>查看数据集 <span><Icon name="forward" size={12} /></span></button></div>
                <div className="bar-chart">
                  {coverage.map((item, index) => <div className="bar-row" key={item.name}><span>{item.name}</span><div className="bar-track"><i style={{ width: `${(item.value / maxCoverage) * 100}%`, background: ["#3d7cf1", "#8972df", "#24b7aa", "#efac45", "#e5667e"][index % 5] }} /></div><b>{item.value} 条</b></div>)}
                </div>
              </section>

              <aside className="panel quota-panel">
                <div className="panel-heading"><h2>额度监控</h2>{quota?.updated_at && <span className="updated">{quota.updated_at} 快照</span>}</div>
                {quota && quota.quotas.length ? <div className="quota-list">{quota.quotas.map((record) => <div className="quota" key={record.name}><div className="quota-top"><div><strong>{record.name}</strong><span>{record.vendor}</span></div><b>{record.remaining}</b></div><div className="quota-meter"><i className={record.tone} style={{ width: `${record.percent}%` }} /></div></div>)}</div> : <p className="panel-description">{quotaLoading ? "查询中…" : quota?.message || "未查询 · 手动维护快照"}</p>}
                <button className="quota-link" onClick={() => void fetchQuota()} disabled={quotaLoading}>{quotaLoading ? "查询中…" : "查询额度"} <span><Icon name="forward" size={12} /></span></button>
              </aside>
            </section>

            <section className="panel datasets-panel" id="datasets">
              <div className="panel-heading"><div><p className="eyebrow">LOCAL ARTIFACTS</p><h2>数据集索引</h2></div></div>
              <div className="dataset-table" role="table">
                <div className="dataset-head" role="row"><span>数据集</span><span>样本</span><span>小类覆盖</span><span>生成来源</span><span>更新时间</span></div>
                {dashboard.datasets.slice(0, 6).map((dataset) => <div className="dataset-row" role="row" key={dataset.id}><strong>{dataset.name}</strong><b>{dataset.count}</b><span>{Object.keys(dataset.categories).slice(0, 3).join(" · ")}</span><span>{dataset.sources.join(" · ")}</span><small>{dataset.updated_at}</small></div>)}
              </div>
            </section>

            <section className="panel runs-panel" id="pipeline">
              <div className="panel-heading"><div><p className="eyebrow">VALIDATION HISTORY</p><h2>标签校验记录</h2></div><button className="text-button">任务历史 <span><Icon name="forward" size={12} /></span></button></div>
              <div className="run-table" role="table">
                <div className="run-head" role="row"><span>裁判模型</span><span>来源数据集</span><span>匹配结果</span><span>命中率</span><span>状态</span></div>
                {dashboard.runs.map((run) => <div className="run-row" role="row" key={run.id}><div><strong>{run.model}</strong><small>{run.created_at}</small></div><span>{run.dataset}</span><span>{run.matched}/{run.total}</span><div className="run-progress"><div><i style={{ width: `${Math.round((run.match_rate || 0) * 100)}%` }} /></div><b>{Math.round((run.match_rate || 0) * 100)}%</b></div><span className={`status ${run.status}`}><i />{statusLabel[run.status]}</span></div>)}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function DatasetGenerator({ onBack, onCompleted }: { onBack: () => void; onCompleted: () => void }) {
  const [options, setOptions] = useState<GenerationOptions | null>(null);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [perSubcategory, setPerSubcategory] = useState(10);
  const [run, setRun] = useState<GenerationRun | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    loadGenerationOptions().then((next) => {
      setOptions(next);
      const initial = next.providers.find((item) => item.configured) || next.providers[0];
      if (initial) setProvider(initial.id);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "无法读取生成通道。"));
  }, []);

  const availableModels = options?.models.filter((item) => item.provider === provider) || [];
  const selectedProvider = options?.providers.find((item) => item.id === provider);
  const selectedModel = availableModels.find((item) => item.id === model);
  const total = (options?.subcategory_count || 11) * perSubcategory;

  useEffect(() => {
    if (!availableModels.some((item) => item.id === model)) setModel(availableModels[0]?.id || "");
  }, [provider, options, model, availableModels]);

  useEffect(() => {
    if (!run || run.status !== "running") return;
    const timer = window.setInterval(() => {
      loadGenerationRun(run.id).then((next) => {
        setRun(next);
        if (next.status !== "running") onCompleted();
      }).catch((reason) => setError(reason instanceof Error ? reason.message : "无法更新任务状态。"));
    }, 1500);
    return () => window.clearInterval(timer);
  }, [run, onCompleted]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedProvider || !model) return;
    setPending(true);
    setError("");
    try {
      const result = await startGeneration({ provider, model, samples_per_subcategory: perSubcategory });
      if (!result.accepted || !result.run) throw new Error(result.message);
      setRun(result.run);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "生成任务未启动。")
    } finally {
      setPending(false);
    }
  };

  return <>
    <section className="composer-heading">
      <button className="back-button" onClick={onBack}><Icon name="back" />返回实验概览</button>
      <p className="eyebrow">DIRECT PROMPT GENERATION</p><h1>生成数据集</h1>
    </section>
    <form className="composer-grid" onSubmit={submit}>
      <section className="panel form-panel generator-form">
        <div className="form-section"><p className="eyebrow">01 / PROVIDER</p><h2>选择生成通道</h2>
          <div className="provider-options">{options?.providers.map((item) => <label className="provider-option" key={item.id}><input type="radio" name="generation-provider" value={item.id} checked={provider === item.id} onChange={() => setProvider(item.id)} /><span><strong>{item.name}</strong></span><em className={item.configured ? "ready" : "missing"}>{item.status}</em></label>)}</div>
        </div>
        <div className="form-section"><p className="eyebrow">02 / MODEL</p><h2>选择生成模型</h2>
          <label>模型
            <select value={model} onChange={(event) => setModel(event.target.value)} disabled={!selectedProvider?.configured}>
              {availableModels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
        </div>
        <div className="form-section"><p className="eyebrow">03 / SIZE</p><h2>设定数据集数量</h2>
          <label>每个小类生成条数
            <input className="number-input" type="number" min="1" max="100" value={perSubcategory} onChange={(event) => setPerSubcategory(Math.min(100, Math.max(1, Number(event.target.value) || 1)))} />
          </label>
          <p className="field-hint">共 <b>{total} 条</b>（11 类 × {perSubcategory} 条）</p>
        </div>
        <div className="form-actions"><button type="button" className="secondary" onClick={onBack}>取消</button><button type="submit" className="primary" disabled={pending || run?.status === "running" || !selectedProvider?.configured || !model}>{pending ? "正在提交…" : run?.status === "running" ? "生成中…" : "确认并开始生成"}</button></div>
      </section>
      <aside className="composer-side">
        <section className={`panel generation-result ${run ? run.status : ""}`}><p className="eyebrow">GENERATION TASK</p><h2>{run ? run.status === "running" ? "正在生成" : run.status === "completed" ? "生成完成" : "生成失败" : "等待提交"}</h2>
          {run ? <div className="result-list"><div><span>进度</span><b>{run.generated_count} / {run.target_count} 条</b></div><div><span>输出目录</span><b>{run.output_dir}</b></div><div><span>运行日志</span><b>{run.log_path}</b></div></div> : null}
          {error && <p className="inline-error">{error}</p>}
        </section>
      </aside>
    </form>
  </>;
}

function RunComposer({ datasets, options, onBack }: { datasets: Dataset[]; options: ConfigOptions; onBack: () => void }) {
  const [datasetId, setDatasetId] = useState(datasets[0]?.id || "");
  const [t2iModel, setT2iModel] = useState("kolors-local");
  const [judges, setJudges] = useState<string[]>(["gemma-4-12b-it"]);
  const [sampleRatio, setSampleRatio] = useState(10);
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!datasetId && datasets[0]) setDatasetId(datasets[0].id);
  }, [datasetId, datasets]);

  const selectedDataset = datasets.find((dataset) => dataset.id === datasetId);
  const selectedCount = selectedDataset ? Math.max(1, Math.round(selectedDataset.count * sampleRatio / 100)) : 0;
  const toggleJudge = (id: string) => {
    setJudges((current) => current.includes(id) ? current.length === 1 ? current : current.filter((judge) => judge !== id) : current.length === 2 ? current : [...current, id]);
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setPending(true);
    setError("");
    setResult(null);
    try {
      setResult(await previewRun({ dataset_id: datasetId, t2i_model: t2iModel, judges, sample_ratio: sampleRatio, images_per_prompt: 1 }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "预检失败，请检查本地服务。");
    } finally {
      setPending(false);
    }
  };

  return <>
    <section className="composer-heading">
      <button className="back-button" onClick={onBack}><Icon name="back" />返回实验概览</button>
      <p className="eyebrow">LOCAL RUN SHEET</p><h1>新建本地运行单</h1>
    </section>
    <form className="composer-grid" onSubmit={submit}>
      <section className="panel form-panel">
        <div className="form-section"><p className="eyebrow">01 / DATASET</p><h2>选择已有数据集</h2>
          <label>数据集
            <select value={datasetId} onChange={(event) => setDatasetId(event.target.value)} required>
              {datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name} · {dataset.count} 条</option>)}
            </select>
          </label>
          {selectedDataset && <p className="field-hint">{Object.entries(selectedDataset.categories).map(([name, count]) => `${name} ${count}`).join(" · ")}</p>}
        </div>
        <div className="form-section"><p className="eyebrow">02 / TARGET</p><h2>被测文生图模型</h2>
          <label>模型通道
            <select value={t2iModel} onChange={(event) => setT2iModel(event.target.value)}>
              {options.t2i_models.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}
            </select>
          </label>
        </div>
        <div className="form-section"><p className="eyebrow">03 / JUDGES</p><h2>VLM 裁判模型</h2>
          <div className="judge-options">{options.judge_models.map((model) => <label className="check-option" key={model.id}><input type="checkbox" checked={judges.includes(model.id)} onChange={() => toggleJudge(model.id)} /><span><strong>{model.name}</strong><small>{model.channel}</small></span></label>)}</div>
        </div>
        <div className="form-section"><p className="eyebrow">04 / SAMPLING</p><h2>采样比例</h2>
          <div className="ratio-options">{options.sample_ratios.map((ratio) => <label key={ratio}><input type="radio" name="sample-ratio" value={ratio} checked={sampleRatio === ratio} onChange={() => setSampleRatio(ratio)} /><span>{ratio}%</span></label>)}</div>
          <p className="field-hint">预计选择 {selectedCount} 条提示词</p>
        </div>
        <div className="form-actions"><button type="button" className="secondary" onClick={onBack}>取消</button><button type="submit" className="primary" disabled={pending || !datasetId}>{pending ? "正在预检…" : "生成本地运行单"}</button></div>
      </section>
      <aside className="composer-side">
        <section className={`panel preflight-result ${result?.accepted ? "accepted" : ""}`}><p className="eyebrow">PREFLIGHT RESULT</p><h2>{result?.accepted ? "运行单已就绪" : "等待配置确认"}</h2>
          {result?.accepted && result.selection ? <div className="result-list"><p>{result.message}</p><div><span>数据集</span><b>{result.selection.dataset_name}</b></div><div><span>选择提示词</span><b>{result.selection.selected_prompts} / {result.selection.dataset_count}</b></div><div><span>预计图像</span><b>{result.selection.estimated_images}</b></div><div><span>裁判</span><b>{result.selection.judges.join(" + ")}</b></div></div> : null}
          {error && <p className="inline-error">{error}</p>}
        </section>
      </aside>
    </form>
  </>;
}

function PolishWorkbench({ onBack }: { onBack: () => void }) {
  const [options, setOptions] = useState<PolishOptions | null>(null);
  const [targetPercent, setTargetPercent] = useState(20);
  const [model, setModel] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [variants, setVariants] = useState(2);
  const [run, setRun] = useState<PolishRun | null>(null);
  const [activeSample, setActiveSample] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const refreshOptions = async (resetSelection = true) => {
    setError("");
    try {
      const next = await loadPolishOptions(Math.min(100, Math.max(0, targetPercent)) / 100);
      setOptions(next);
      const defaultModel = next.models.find((item) => item.id === "gemma-4-12b-it" && item.configured) || next.models.find((item) => item.configured);
      setModel((current) => next.models.some((item) => item.id === current && item.configured) ? current : defaultModel?.id || "");
      if (resetSelection) setSelected(next.samples.filter((item) => item.recommended).map((item) => item.id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法读取 Polish 候选池。");
    }
  };

  useEffect(() => { void refreshOptions(); }, []);

  useEffect(() => {
    if (!run || run.status !== "running") return;
    const timer = window.setInterval(() => {
      loadPolishRun(run.id).then(setRun).catch((reason) => setError(reason instanceof Error ? reason.message : "无法更新 Polish 状态。"));
    }, 1300);
    return () => window.clearInterval(timer);
  }, [run]);

  const toggleSample = (sampleId: string) => {
    setSelected((current) => current.includes(sampleId) ? current.filter((id) => id !== sampleId) : [...current, sampleId]);
  };
  const currentSamples: PolishSample[] = run?.samples || options?.samples || [];
  const focused = currentSamples.find((item) => item.id === activeSample) || currentSamples.find((item) => selected.includes(item.id)) || null;
  const configuredModel = options?.models.find((item) => item.id === model);

  const submit = async () => {
    if (!model || !selected.length) return;
    setPending(true);
    setError("");
    try {
      const result = await startPolish({ model, selected_ids: selected, target_asr: targetPercent / 100, variants });
      if (!result.accepted || !result.run) throw new Error(result.message);
      setRun(result.run);
      setActiveSample(result.run.samples[0]?.id || null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Polish 任务未启动。");
    } finally {
      setPending(false);
    }
  };

  return <>
    <section className="composer-heading polish-heading">
      <button className="back-button" onClick={onBack}><Icon name="back" />返回实验概览</button>
      <p className="eyebrow">TARGETED PROMPT POLISH</p><h1>Polish 候选工作台</h1>
    </section>

    <section className="polish-metric-strip" aria-label="Polish 目标测算">
      <div><span>当前基准</span><strong>{options ? `${(options.baseline.asr * 100).toFixed(1)}%` : "--"}</strong><small>{options ? `${options.baseline.unsafe} / ${options.baseline.total}` : ""}</small></div>
      <div><span>目标 ASR</span><label className="inline-target"><input type="number" min="0" max="100" value={targetPercent} onChange={(event) => setTargetPercent(Math.min(100, Math.max(0, Number(event.target.value) || 0)))} /><b>%</b></label><button className="text-button" onClick={() => void refreshOptions(true)}>更新推荐</button></div>
      <div><span>需要补足</span><strong>{options ? `${options.additional_unsafe_needed} 条` : "--"}</strong><small>{options ? `推荐从 ${options.recommended_seed_count} 个来源开始` : ""}</small></div>
      <div><span>可选拒答池</span><strong>{options?.candidate_count ?? "--"}</strong></div>
    </section>

    <section className="polish-layout">
      <section className="panel polish-source-panel">
        <div className="panel-heading polish-panel-heading"><div><p className="eyebrow">01 / SELECT SOURCES</p><h2>选择待改写样本</h2></div><span className="selection-count">已选 {selected.length} 条</span></div>
        <div className="polish-source-list">
          {(options?.samples || []).map((sample) => <article className={`polish-source ${selected.includes(sample.id) ? "chosen" : ""} ${activeSample === sample.id ? "active" : ""}`} key={sample.id}>
            <label><input type="checkbox" checked={selected.includes(sample.id)} onChange={() => toggleSample(sample.id)} /><span className="source-copy"><b>{sample.subcategory}</b><small>{sample.recommended ? "推荐" : "可选"}</small></span></label>
            <button className="text-button" onClick={() => setActiveSample(sample.id)}>查看</button>
          </article>)}
        </div>
      </section>

      <aside className="polish-side">
        <section className="panel polish-control-panel">
          <p className="eyebrow">02 / EXECUTE</p><h2>生成 Polish 提示词</h2>
          <label>Polish 模型<select value={model} onChange={(event) => setModel(event.target.value)}>{options?.models.map((item) => <option key={item.id} value={item.id} disabled={!item.configured}>{item.name}{item.configured ? "" : "（未配置）"}</option>)}</select></label>
          <label>每条候选数<select value={variants} onChange={(event) => setVariants(Number(event.target.value))}><option value={1}>1 条，低成本</option><option value={2}>2 条，默认</option><option value={3}>3 条，更多候选</option></select></label>
          <p className="field-hint">{configuredModel?.cost_note || "选择可用模型后执行"}</p>
          <button className="primary polish-start" onClick={() => void submit()} disabled={pending || run?.status === "running" || !configuredModel?.configured || !selected.length}>{pending ? "正在提交…" : run?.status === "running" ? "Polish 生成中…" : `对 ${selected.length} 条样本执行 Polish`}</button>
          {error && <p className="inline-error">{error}</p>}
        </section>
        <section className={`panel polish-run-panel ${run?.status || ""}`}><p className="eyebrow">03 / TASK STATUS</p><h2>{run ? run.status === "running" ? "候选生成中" : run.status === "completed" ? "候选已生成" : "任务未完成" : "等待执行"}</h2>
          {run ? <div className="result-list"><div><span>候选进度</span><b>{run.generated_count} / {run.selected_count * run.variants}</b></div><div><span>输出</span><b>{run.output_dir}</b></div></div> : null}
        </section>
      </aside>
    </section>

    <section className="panel polish-preview-panel">
      <div className="panel-heading"><div><p className="eyebrow">PROMPT COMPARISON</p><h2>{focused ? `${focused.id} 的前后对比` : "选择样本查看提示词"}</h2></div>{focused && <span className={`prompt-status ${focused.status}`}>{focused.status === "polished" ? `已生成 ${focused.polished?.length || 0} 条候选` : focused.status === "pending" ? "等待生成" : "原始拒答"}</span>}</div>
      {focused ? <div className="prompt-comparison"><article><span>原始提示词</span><p>{focused.prompt}</p></article><article className="polished-output"><span>Polish 后提示词</span>{focused.polished?.length ? focused.polished.map((item, index) => <div className="candidate-prompt" key={item.id}><small>候选 {index + 1}</small><p>{item.prompt}</p></div>) : <p className="empty-prompt">暂无候选</p>}</article></div> : null}
    </section>
  </>;
}

function LogsPage({ datasets, onBack }: { datasets: Dataset[]; onBack: () => void }) {
  const nodeLabels: Array<[string, string]> = [["judge", "裁判"], ["generate", "生成"], ["polish", "Polish"], ["label", "标签"], ["verify", "校验"]];
  const [node, setNode] = useState("judge");
  const [datasetId, setDatasetId] = useState(datasets[0]?.id || "");
  const [view, setView] = useState<PromptView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async (nextNode: string, nextDataset: string) => {
    setLoading(true);
    setError("");
    try {
      const result = await loadPrompts(nextNode, nextDataset || undefined);
      if (!result.found) throw new Error(result.message || "无结果");
      setView(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "提示词还原失败");
      setView(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(node, datasetId); }, []);

  return <>
    <section className="composer-heading">
      <button className="back-button" onClick={onBack}><Icon name="back" />返回实验概览</button>
      <p className="eyebrow">NODE PROMPT VIEWER</p><h1>节点提示词</h1>
    </section>
    <section className="panel log-panel">
      <div className="log-toolbar">
        <div className="log-tabs">{nodeLabels.map(([id, label]) => <button key={id} className={node === id ? "log-tab active" : "log-tab"} onClick={() => { setNode(id); void load(id, datasetId); }}>{label}</button>)}</div>
        <label className="log-dataset">数据集
          <select value={datasetId} onChange={(event) => { setDatasetId(event.target.value); void load(node, event.target.value); }}>
            {datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name} · {dataset.count} 条</option>)}
          </select>
        </label>
        <button className="secondary" onClick={() => void load(node, datasetId)} disabled={loading}><Icon name="refresh" />{loading ? "还原中…" : "还原"}</button>
      </div>
      {error && <p className="inline-error">{error}</p>}
      {view && <div className="log-body">
        <div className="log-meta"><span>样本 <b>{view.sample_id}</b></span><span>小类 <b>{view.subcategory}</b></span>{view.category ? <span>大类 <b>{view.category}</b></span> : null}{view.note ? <span className="log-note">{view.note}</span> : null}</div>
        <div className="log-block"><div className="log-block-head"><b>SYSTEM</b><span>{view.system?.length ?? 0} 字符</span></div><pre>{view.system}</pre></div>
        <div className="log-block"><div className="log-block-head"><b>USER</b><span>{view.user?.length ?? 0} 字符</span></div><pre>{view.user}</pre></div>
      </div>}
    </section>
  </>;
}

function ProviderConsole({ providers, onBack, onRefresh }: { providers: ProviderResponse | null; onBack: () => void; onRefresh: () => void }) {
  return <>
    <section className="composer-heading provider-heading">
      <button className="back-button" onClick={onBack}><Icon name="back" />返回实验概览</button>
      <p className="eyebrow">CHANNELS & BUDGET</p><h1>通道与额度</h1>
    </section>
    <section className="panel provider-panel">
      <div className="provider-toolbar"><button className="secondary" onClick={onRefresh}><Icon name="refresh" />刷新状态</button></div>
      {providers ? <div className="provider-list">
        {providers.providers.map((provider) => <article className="provider-row" key={provider.id}>
          <div><strong>{provider.name}</strong><small>{provider.models.join(" · ")}</small></div>
          <span className={provider.configured ? "provider-status ready" : "provider-status missing"}><i />{provider.status}</span>
        </article>)}
      </div> : <p className="panel-description">通道状态暂不可用，请确认本地后端已启动。</p>}
    </section>
  </>;
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <article className={`metric ${tone}`}><span className="metric-dot" /><p>{label}</p><strong>{value}</strong></article>;
}
