import { useEffect, useState } from "react";
import { Dashboard, loadDashboard } from "./api";

const navItems = [
  ["概览", "⌘"], ["数据集", "▦"], ["运行任务", "◔"], ["结果分析", "⌁"],
];

const statusLabel = { running: "运行中", completed: "已完成", queued: "队列中" };

function Icon({ children }: { children: string }) {
  return <span className="icon" aria-hidden="true">{children}</span>;
}

export function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [source, setSource] = useState<"api" | "demo">("demo");
  const [active, setActive] = useState("概览");

  useEffect(() => {
    loadDashboard().then(({ data, source: nextSource }) => {
      setDashboard(data);
      setSource(nextSource);
    });
  }, []);

  if (!dashboard) return <main className="loading">正在读取实验概览…</main>;
  const maxCategory = Math.max(...dashboard.category_asr.map((item) => item.value));

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">↗</span><span>T2I Safety Eval</span><em>LAB</em></div>
        <nav aria-label="主导航"><a className="current" href="#workspace">工作台</a><a href="#pipeline">Pipeline</a><a href="#docs">文档</a></nav>
        <div className="top-actions"><span className={`source-badge ${source}`}><i />{source === "api" ? "已连接本地服务" : "演示数据"}</span><button className="avatar" aria-label="当前用户">D</button></div>
      </header>

      <aside className="sidebar">
        <p className="nav-caption">评测工作台</p>
        {navItems.map(([label, icon]) => <button key={label} className={active === label ? "nav-item selected" : "nav-item"} onClick={() => setActive(label)}><Icon>{icon}</Icon>{label}</button>)}
        <div className="sidebar-separator" />
        <p className="nav-caption">系统</p>
        <button className="nav-item"><Icon>⊙</Icon>模型与通道</button>
        <button className="nav-item"><Icon>⚙</Icon>本地配置</button>
        <div className="sidebar-bottom"><span className="pulse" />Pipeline ready<br /><small>v0.1 · local workspace</small></div>
      </aside>

      <main className="content" id="workspace">
        <section className="page-heading">
          <div><p className="eyebrow">PIPELINE OVERVIEW</p><h1>实验概览</h1><p className="subtle">所有指标由本地 pipeline 结果计算，不上传数据集或密钥。</p></div>
          <div className="heading-actions"><button className="secondary"><Icon>↻</Icon>刷新</button><button className="primary"><Icon>＋</Icon>新建运行</button></div>
        </section>

        <section className="metric-strip" aria-label="核心指标">
          <Metric label="总体 ASR" value={`${Math.round(dashboard.asr * 100)}%`} note="风险类 · 已完成运行" tone="blue" />
          <Metric label="已生成图像" value={dashboard.generated.toString()} note="当前实验批次" tone="teal" />
          <Metric label="拒答率" value={`${Math.round(dashboard.refusal_rate * 100)}%`} note="生成侧，非 ASR" tone="violet" />
          <Metric label="等待任务" value={dashboard.queued.toString()} note="等待本地执行" tone="orange" />
        </section>

        <section className="dashboard-grid">
          <section className="panel category-panel">
            <div className="panel-heading"><div><p className="eyebrow">RISK COVERAGE</p><h2>小类攻击成功率</h2></div><button className="text-button">查看全部 <span>→</span></button></div>
            <p className="panel-description">按生成来源小类分组展示，大类评估器输出决定最终 ASR。</p>
            <div className="bar-chart">
              {dashboard.category_asr.map((item) => <div className="bar-row" key={item.name}><span>{item.name}</span><div className="bar-track"><i style={{ width: `${(item.value / maxCategory) * 100}%`, background: item.color }} /></div><b>{item.value}%</b></div>)}
            </div>
            <div className="method-note"><span>◎</span><p>VLM 按大类作二元安全判定，小类仅用于生成控制与归因分析。</p></div>
          </section>

          <aside className="panel quota-panel">
            <div className="panel-heading"><div><p className="eyebrow">COST WATCH</p><h2>额度监控</h2></div><span className="updated">刚刚更新</span></div>
            <p className="panel-description">执行前检查通道可用性，避免误用受限额度。</p>
            <div className="quota-list">{dashboard.quotas.map((quota) => <div className="quota" key={quota.name}><div className="quota-top"><div><strong>{quota.name}</strong><span>{quota.vendor}</span></div><b>{quota.remaining}</b></div><div className="quota-meter"><i className={quota.tone} style={{ width: `${quota.percent}%` }} /></div></div>)}</div>
            <button className="quota-link">管理模型通道 <span>→</span></button>
          </aside>
        </section>

        <section className="panel runs-panel" id="pipeline">
          <div className="panel-heading"><div><p className="eyebrow">RECENT ACTIVITY</p><h2>最近运行</h2></div><button className="text-button">任务历史 <span>→</span></button></div>
          <div className="run-table" role="table">
            <div className="run-head" role="row"><span>运行</span><span>数据集</span><span>被测模型</span><span>进度 / ASR</span><span>状态</span></div>
            {dashboard.runs.map((run) => <div className="run-row" role="row" key={run.id}><div><strong>{run.id}</strong><small>{run.created_at}</small></div><span>{run.dataset}</span><span className="model-pill">{run.model}</span><div className="run-progress"><div><i style={{ width: `${run.progress}%` }} /></div><b>{run.asr !== undefined ? `ASR ${Math.round(run.asr * 100)}%` : `${run.progress}%`}</b></div><span className={`status ${run.status}`}><i />{statusLabel[run.status]}</span></div>)}
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value, note, tone }: { label: string; value: string; note: string; tone: string }) {
  return <article className={`metric ${tone}`}><span className="metric-dot" /><p>{label}</p><strong>{value}</strong><small>{note}</small></article>;
}
