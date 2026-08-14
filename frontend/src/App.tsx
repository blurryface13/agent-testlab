import { FormEvent, useEffect, useState } from "react";
import { ConfigOptions, Dashboard, Dataset, PreviewResult, ProviderResponse, loadConfigOptions, loadDashboard, loadProviders, previewRun } from "./api";

const navItems = [["概览", "⌘"], ["数据集", "▦"], ["运行任务", "◔"], ["结果分析", "⌁"]];
const statusLabel = { running: "运行中", completed: "已完成", queued: "队列中" };

function Icon({ children }: { children: string }) {
  return <span className="icon" aria-hidden="true">{children}</span>;
}

export function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [options, setOptions] = useState<ConfigOptions | null>(null);
  const [providers, setProviders] = useState<ProviderResponse | null>(null);
  const [source, setSource] = useState<"api" | "demo">("demo");
  const [active, setActive] = useState("概览");
  const [view, setView] = useState<"overview" | "composer" | "providers">("overview");

  const refresh = () => {
    Promise.all([loadDashboard(), loadConfigOptions(), loadProviders().catch(() => null)]).then(([nextDashboard, nextOptions, nextProviders]) => {
      setDashboard(nextDashboard.data);
      setSource(nextDashboard.source);
      setOptions(nextOptions);
      setProviders(nextProviders);
    });
  };

  useEffect(refresh, []);

  const openComposer = () => {
    setActive("运行任务");
    setView("composer");
  };
  const openProviders = () => {
    setActive("通道与额度");
    setView("providers");
  };

  const selectNav = (label: string) => {
    setActive(label);
    if (label === "运行任务") {
      setView("composer");
      return;
    }
    if (label === "结果分析") {
      setView("overview");
      setTimeout(() => document.getElementById("pipeline")?.scrollIntoView({ behavior: "smooth" }), 0);
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
        {navItems.map(([label, icon]) => <button key={label} className={active === label ? "nav-item selected" : "nav-item"} onClick={() => selectNav(label)}><Icon>{icon}</Icon>{label}</button>)}
        <div className="sidebar-separator" />
        <p className="nav-caption">系统</p>
        <button className={active === "通道与额度" ? "nav-item selected" : "nav-item"} onClick={openProviders}><Icon>⊙</Icon>通道与额度</button>
        <div className="sidebar-bottom"><span className="pulse" />Pipeline ready<br /><small>v0.1 · local workspace</small></div>
      </aside>

      <main className="content" id="workspace">
        {view === "composer" ? (
          <RunComposer datasets={dashboard.datasets} options={options} onBack={() => { setView("overview"); setActive("概览"); }} />
        ) : view === "providers" ? (
          <ProviderConsole providers={providers} onBack={() => { setView("overview"); setActive("概览"); }} onRefresh={refresh} />
        ) : (
          <>
            <section className="page-heading">
              <div><p className="eyebrow">PIPELINE OVERVIEW</p><h1>实验概览</h1><p className="subtle">本地产物索引</p></div>
              <div className="heading-actions"><button className="secondary" onClick={refresh}><Icon>↻</Icon>刷新</button><button className="primary" onClick={openComposer}><Icon>＋</Icon>新建运行</button></div>
            </section>

            <section className="metric-strip" aria-label="核心指标">
              <Metric label="已索引数据集" value={dashboard.dataset_count.toString()} note="demo 生成产物" tone="blue" />
              <Metric label="已索引样本" value={dashboard.sample_count.toString()} note="可用于本地运行单" tone="teal" />
              <Metric label="最近标签命中" value={`${Math.round(dashboard.latest_validation_rate * 100)}%`} note="文本标签校验，非 ASR" tone="violet" />
            </section>

            <section className="dashboard-grid">
              <section className="panel category-panel">
                <div className="panel-heading"><h2>小类样本覆盖</h2><button className="text-button" onClick={() => document.getElementById("datasets")?.scrollIntoView({ behavior: "smooth" })}>查看数据集 <span>→</span></button></div>
                <div className="bar-chart">
                  {coverage.map((item, index) => <div className="bar-row" key={item.name}><span>{item.name}</span><div className="bar-track"><i style={{ width: `${(item.value / maxCoverage) * 100}%`, background: ["#3d7cf1", "#8972df", "#24b7aa", "#efac45", "#e5667e"][index % 5] }} /></div><b>{item.value} 条</b></div>)}
                </div>
              </section>

              <aside className="panel quota-panel">
                <div className="panel-heading"><h2>额度监控</h2><span className="updated">账单侧同步</span></div>
                <div className="quota-list">{dashboard.quotas.map((quota) => <div className="quota" key={quota.name}><div className="quota-top"><div><strong>{quota.name}</strong><span>{quota.vendor}</span></div><b>{quota.remaining}</b></div><div className="quota-meter"><i className={quota.tone} style={{ width: `${quota.percent}%` }} /></div></div>)}</div>
                <button className="quota-link" onClick={openProviders}>管理模型通道 <span>→</span></button>
              </aside>
            </section>

            <section className="panel datasets-panel" id="datasets">
              <div className="panel-heading"><div><p className="eyebrow">LOCAL ARTIFACTS</p><h2>数据集索引</h2></div><span className="updated">只读 · demo/outputs</span></div>
              <div className="dataset-table" role="table">
                <div className="dataset-head" role="row"><span>数据集</span><span>样本</span><span>小类覆盖</span><span>生成来源</span><span>更新时间</span></div>
                {dashboard.datasets.slice(0, 6).map((dataset) => <div className="dataset-row" role="row" key={dataset.id}><strong>{dataset.name}</strong><b>{dataset.count}</b><span>{Object.keys(dataset.categories).slice(0, 3).join(" · ")}</span><span>{dataset.sources.join(" · ")}</span><small>{dataset.updated_at}</small></div>)}
              </div>
            </section>

            <section className="panel runs-panel" id="pipeline">
              <div className="panel-heading"><div><p className="eyebrow">VALIDATION HISTORY</p><h2>标签校验记录</h2></div><button className="text-button">任务历史 <span>→</span></button></div>
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
      <button className="back-button" onClick={onBack}><Icon>←</Icon>返回实验概览</button>
      <p className="eyebrow">LOCAL RUN SHEET</p><h1>新建本地运行单</h1>
      <p className="subtle">先确认数据集与模型组合。提交只生成预检结果，不会调用模型、读取密钥或写入 demo。</p>
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
              {options.t2i_models.map((model) => <option key={model.id} value={model.id}>{model.name} · {model.channel}</option>)}
            </select>
          </label>
        </div>
        <div className="form-section"><p className="eyebrow">03 / JUDGES</p><h2>VLM 裁判模型</h2><p className="field-hint">最多两个交叉裁判；当前预检不会调用任一模型。</p>
          <div className="judge-options">{options.judge_models.map((model) => <label className="check-option" key={model.id}><input type="checkbox" checked={judges.includes(model.id)} onChange={() => toggleJudge(model.id)} /><span><strong>{model.name}</strong><small>{model.channel}</small></span></label>)}</div>
        </div>
        <div className="form-section"><p className="eyebrow">04 / SAMPLING</p><h2>采样比例</h2>
          <div className="ratio-options">{options.sample_ratios.map((ratio) => <label key={ratio}><input type="radio" name="sample-ratio" value={ratio} checked={sampleRatio === ratio} onChange={() => setSampleRatio(ratio)} /><span>{ratio}%</span></label>)}</div>
          <p className="field-hint">固定每条提示词 1 张图，预计选择 {selectedCount} 条提示词。</p>
        </div>
        <div className="form-actions"><button type="button" className="secondary" onClick={onBack}>取消</button><button type="submit" className="primary" disabled={pending || !datasetId}>{pending ? "正在预检…" : "生成本地运行单"}</button></div>
      </section>
      <aside className="composer-side">
        <section className="panel guard-panel"><p className="eyebrow">EXECUTION GUARD</p><h2>本次操作边界</h2>
          <ul><li>只读取 <code>demo/outputs</code> 的数据集索引。</li><li>不执行生图、裁判、生成或 LLM 自优化。</li><li>不读取 API Key，不使用 APIDock、DMX 或 Zhipu 额度。</li><li>正式运行仍需由 worker 接收这份配置。</li></ul>
        </section>
        <section className={`panel preflight-result ${result?.accepted ? "accepted" : ""}`}><p className="eyebrow">PREFLIGHT RESULT</p><h2>{result?.accepted ? "运行单已就绪" : "等待配置确认"}</h2>
          {result?.accepted && result.selection ? <div className="result-list"><p>{result.message}</p><div><span>数据集</span><b>{result.selection.dataset_name}</b></div><div><span>选择提示词</span><b>{result.selection.selected_prompts} / {result.selection.dataset_count}</b></div><div><span>预计图像</span><b>{result.selection.estimated_images}</b></div><div><span>裁判</span><b>{result.selection.judges.join(" + ")}</b></div></div> : <p className="panel-description">提交后在这里确认所选样本数与安全边界，再把配置交给正式执行 worker。</p>}
          {error && <p className="inline-error">{error}</p>}
        </section>
      </aside>
    </form>
  </>;
}

function ProviderConsole({ providers, onBack, onRefresh }: { providers: ProviderResponse | null; onBack: () => void; onRefresh: () => void }) {
  return <>
    <section className="composer-heading provider-heading">
      <button className="back-button" onClick={onBack}><Icon>←</Icon>返回实验概览</button>
      <p className="eyebrow">CHANNELS & BUDGET</p><h1>通道与额度</h1>
    </section>
    <section className="panel provider-panel">
      <div className="provider-toolbar"><span>密钥只保留在本机环境文件中，界面不读取或显示密钥。</span><button className="secondary" onClick={onRefresh}><Icon>↻</Icon>刷新状态</button></div>
      {providers ? <div className="provider-list">
        {providers.providers.map((provider) => <article className="provider-row" key={provider.id}>
          <div><strong>{provider.name}</strong><small>{provider.models.join(" · ")}</small></div>
          <code>{provider.base_url}</code>
          <span className={provider.configured ? "provider-status ready" : "provider-status missing"}><i />{provider.status}</span>
          <p>{provider.quota_note}</p>
        </article>)}
      </div> : <p className="panel-description">通道状态暂不可用，请确认本地后端已启动。</p>}
    </section>
  </>;
}

function Metric({ label, value, note, tone }: { label: string; value: string; note: string; tone: string }) {
  return <article className={`metric ${tone}`}><span className="metric-dot" /><p>{label}</p><strong>{value}</strong><small>{note}</small></article>;
}
