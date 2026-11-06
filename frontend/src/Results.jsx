import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import Icon from "./Icon.jsx";
import { rs } from "./format.js";

const METRICS = {
  laptop: [["cpu", "Processor"], ["ram", "Memory"], ["storage", "Storage"], ["gpu", "Graphics"], ["price", "Value for budget"]],
  phone: [["cpu", "Chipset"], ["ram", "Memory"], ["storage", "Storage"], ["battery", "Battery"], ["camera", "Camera"], ["price", "Value for budget"]],
};

function specRows(l, category) {
  const gb = (v) => (v ? `${v} GB` : "Not listed");
  if (category === "phone") {
    return [
      ["Chipset", l.processor || "Not listed"], ["Memory", gb(l.ram_gb)], ["Storage", gb(l.storage_gb)],
      ["Battery", l.battery_mah ? `${l.battery_mah} mAh` : "Not listed"],
      ["Main camera", l.camera_mp ? `${l.camera_mp} MP` : "Not listed"], ["Screen", l.screen || "Not listed"],
    ];
  }
  return [
    ["Processor", l.processor || "Not listed"], ["Memory", gb(l.ram_gb)], ["Storage", gb(l.storage_gb)],
    ["Graphics", l.gpu || "Integrated"],
  ];
}

function useMounted() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setOn(true)));
    return () => cancelAnimationFrame(id);
  }, []);
  return on;
}

function Ring({ value }) {
  const on = useMounted();
  const R = 34, C = 2 * Math.PI * R;
  return (
    <div className="ring" role="img" aria-label={`Score ${value.toFixed(1)} out of 10`}>
      <svg viewBox="0 0 84 84" width="96" height="96">
        <circle cx="42" cy="42" r={R} className="ring-track" />
        <circle cx="42" cy="42" r={R} className="ring-fill" strokeDasharray={C}
                strokeDashoffset={on ? C * (1 - value / 10) : C} transform="rotate(-90 42 42)" />
      </svg>
      <span className="ring-num"><b>{value.toFixed(1)}</b><i>/10</i></span>
    </div>
  );
}

function Bars({ item, category }) {
  const on = useMounted();
  const rows = (METRICS[category] || METRICS.laptop).filter(([k]) => item.scores && k in item.scores);
  return (
    <ul className="bars">
      {rows.map(([k, label]) => (
        <li key={k}>
          <span className="bar-label">{label}</span>
          <span className="bar-track"><span className="bar-fill" style={{ width: on ? `${item.scores[k] * 10}%` : "0%" }} /></span>
          <span className="bar-val">{item.scores[k].toFixed(1)}</span>
        </li>
      ))}
    </ul>
  );
}

function Specs({ item, category }) {
  return (
    <dl className="specs">
      {specRows(item, category).map(([k, v]) => (<React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>))}
    </dl>
  );
}

function Savings({ item }) {
  return (
    <div className="savings">
      {item.discount_pct > 0 && <span className="pill jade">{item.discount_pct}% off</span>}
      {item.budget_left > 0 && <span className="pill soft">{rs(item.budget_left)} under budget</span>}
    </div>
  );
}

function Listing({ url }) {
  if (!url) return null;
  return (
    <a className="btn primary" href={url} target="_blank" rel="noreferrer noopener">
      View listing <Icon name="external" size={16} />
    </a>
  );
}

function TopPick({ item, category }) {
  return (
    <article className="top">
      <div className="top-main">
        <span className="badge"><Icon name="check" size={14} strokeWidth={2.4} />Best match for you</span>
        <h3 className="top-name">{item.name}</h3>
        <div className="tag lg">{rs(item.price)}</div>
        <Savings item={item} />
        <Specs item={item} category={category} />
        <Listing url={item.url} />
      </div>
      <div className="top-why">
        <div className="why-head"><Ring value={item.total} /><div><h4>Why it ranked first</h4><p>Scored against your budget and what you need it for.</p></div></div>
        <Bars item={item} category={category} />
      </div>
    </article>
  );
}

function Runner({ item, rank, category }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={"runner" + (open ? " open" : "")}>
      <button className="runner-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="rank">#{rank}</span>
        <span className="runner-name">{item.name}</span>
        <span className="tag">{rs(item.price)}</span>
        <span className="score-chip">{item.total.toFixed(1)}</span>
        <Icon name="chevron" size={18} className="chev" />
      </button>
      {open && (
        <div className="runner-body">
          <div><Specs item={item} category={category} /><Savings item={item} /><Listing url={item.url} /></div>
          <Bars item={item} category={category} />
        </div>
      )}
    </li>
  );
}

export default function Results({ laptops = [], text, category, latest }) {
  const cat = category || laptops[0]?.category || "laptop";
  if (!laptops.length) {
    return (
      <section className="results empty" id={latest ? "latest-result" : undefined}>
        <span className="empty-icon"><Icon name="search" size={22} /></span>
        <h3>No clear matches yet</h3>
        <div className="prose"><ReactMarkdown>{String(text || "")}</ReactMarkdown></div>
        <p className="muted">Try a higher budget or a different use. You can change both in the next step.</p>
      </section>
    );
  }
  const [first, ...rest] = laptops;
  return (
    <section className="results" id={latest ? "latest-result" : undefined}>
      <header className="results-head">
        <h2>Your top matches</h2>
        <span>{laptops.length} options compared in rupees</span>
      </header>
      <TopPick item={first} category={cat} />
      {rest.length > 0 && (
        <>
          <h3 className="sub">Also worth a look</h3>
          <ul className="runners">{rest.map((it, i) => <Runner key={it.name + i} item={it} rank={i + 2} category={cat} />)}</ul>
        </>
      )}
      <aside className="take">
        <h3>Our take</h3>
        <div className="prose"><ReactMarkdown>{String(text || "")}</ReactMarkdown></div>
      </aside>
    </section>
  );
}
