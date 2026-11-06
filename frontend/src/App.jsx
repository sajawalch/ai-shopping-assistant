import React, { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import Dock, { CategoryTiles } from "./Dock.jsx";
import Results from "./Results.jsx";
import { api } from "./api.js";
import { rs } from "./format.js";

const STAGES = [
  "Searching Pakistani stores",
  "Reading specs and prices",
  "Ranking the options",
  "Writing your recommendation",
];

const QUESTION = {
  category: "What are you shopping for?",
  budget: "What is your budget?",
  use: "What will you use it for?",
  more: "Want to see more options?",
  change: "What should we change?",
};

// Works out which step a question belongs to if the backend did not send one.
function inferStep(message = "") {
  const t = message.toLowerCase();
  if (t.includes("shopping for")) return "category";
  if (t.includes("like to change")) return "change";
  if (t.includes("budget")) return "budget";
  if (t.includes("need the")) return "use";
  return "text";
}

// "1.5 lakh", "80k", "Rs 120,000" -> rupees (or null)
function parseRupees(text = "") {
  const m = text.toLowerCase().match(/(\d[\d,]*\.?\d*)\s*(k|thousand|lakh|lakhs|lac|lacs|million)?/);
  if (!m) return null;
  const mult = { k: 1e3, thousand: 1e3, lakh: 1e5, lakhs: 1e5, lac: 1e5, lacs: 1e5, million: 1e6 }[m[2]] || 1;
  const n = parseFloat(m[1].replace(/,/g, "")) * mult;
  return n >= 1000 ? n : null;
}

function Working({ heavy }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (!heavy) return;
    const id = setInterval(() => setI((n) => Math.min(n + 1, STAGES.length - 1)), 4500);
    return () => clearInterval(id);
  }, [heavy]);
  if (!heavy) return <div className="typing" aria-label="Loading"><i /><i /><i /></div>;
  return (
    <div className="working" role="status" aria-live="polite">
      <div className="working-bar"><span /></div>
      <ol>
        {STAGES.map((s, k) => (
          <li key={s} className={k < i ? "done" : k === i ? "now" : ""}>
            <span className="dot">{k < i ? <Icon name="check" size={12} strokeWidth={3} /> : null}</span>{s}
          </li>
        ))}
      </ol>
      <p>This usually takes 10 to 30 seconds.</p>
    </div>
  );
}

function Hero({ options, onPick }) {
  return (
    <section className="hero">
      <h1>Not sure which laptop or phone to buy?</h1>
      <p className="lede">Answer three quick questions. We check Pakistani stores and compare the best options in rupees.</p>
      <CategoryTiles options={options} onPick={onPick} />
      <ul className="trust">
        <li><Icon name="wallet" size={16} />Prices in rupees</li>
        <li><Icon name="shield" size={16} />PTA and warranty reminders for phones</li>
        <li><Icon name="check" size={16} />No sign-up needed</li>
      </ul>
    </section>
  );
}

function BriefRow({ icon, label, value }) {
  return (
    <li className={value ? "filled" : ""}>
      <span className="brief-icon"><Icon name={icon} size={18} /></span>
      <span><small>{label}</small><b>{value || "Not chosen yet"}</b></span>
    </li>
  );
}

export default function App() {
  const [threadId, setThreadId] = useState(null);
  const [feed, setFeed] = useState([]);
  const [current, setCurrent] = useState(null);
  const [brief, setBrief] = useState({});
  const [loading, setLoading] = useState(false);
  const [heavy, setHeavy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);
  const started = useRef(false);
  const lastReq = useRef(null);
  const endRef = useRef(null);

  function handle(data) {
    setThreadId(data.thread_id);
    if (data.type === "recommendation") {
      setFeed((f) => [...f, { kind: "results", laptops: data.laptops || [], text: data.message }]);
      setCurrent({ step: "more", message: data.question, options: data.options || [] });
    } else if (data.type === "done") {
      setCurrent(null);
      setDone(true);
      setFeed((f) => [...f, { kind: "done", text: data.message }]);
    } else {
      setCurrent({ step: data.step || inferStep(data.message), message: data.message, options: data.options || [] });
    }
  }

  async function run(fn) {
    lastReq.current = fn;
    setLoading(true);
    setError(null);
    try {
      handle(await fn());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function restart() {
    setFeed([]); setCurrent(null); setBrief({}); setDone(false); setHeavy(false); setThreadId(null);
    run(() => api("/api/sessions"));
  }

  useEffect(() => {
    if (started.current) return;      // React StrictMode runs effects twice in development
    started.current = true;
    run(() => api("/api/sessions"));
  }, []);

  useEffect(() => {
    const last = feed[feed.length - 1];
    if (last?.kind === "results") {
      document.getElementById("latest-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [feed, loading, current, error]);

  function pick(value, label) {
    if (!current || loading) return;
    const step = current.step;
    setFeed((f) => [...f, { kind: "q", text: QUESTION[step] || current.message }, { kind: "user", text: label }]);
    if (step === "category") setBrief((b) => ({ ...b, category: value }));
    if (step === "budget") setBrief((b) => ({ ...b, budget: Number(value) }));
    if (step === "use") setBrief((b) => ({ ...b, use: label }));
    if (step === "change") {
      const newBudget = parseRupees(value);
      if (newBudget) setBrief((b) => ({ ...b, budget: newBudget }));
    }
    setHeavy(step === "use" || step === "change");
    const tid = threadId;
    setCurrent(null);
    run(() => api(`/api/sessions/${tid}/reply`, { answer: value }));
  }

  const showHero = feed.length === 0 && !error && (current?.step === "category" || loading);
  const lastResults = feed.map((f) => f.kind).lastIndexOf("results");

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="brand-mark"><Icon name="tag" size={20} strokeWidth={2.2} /></span>
          <div><b>Sahi Pick</b><small>Laptop and phone advisor</small></div>
        </div>
        <div className="brief">
          <h2>Your brief</h2>
          <ul>
            <BriefRow icon={brief.category === "phone" ? "phone" : "laptop"} label="Looking for"
                      value={brief.category ? (brief.category === "phone" ? "Mobile phone" : "Laptop") : ""} />
            <BriefRow icon="wallet" label="Budget" value={brief.budget ? rs(brief.budget) : ""} />
            <BriefRow icon="sun" label="Used for" value={brief.use} />
          </ul>
        </div>
        <div className="tip">
          <Icon name="shield" size={18} />
          <p>Buying a phone? Check that it is PTA approved and ask the seller for warranty details before you pay.</p>
        </div>
        <button className="rail-reset" onClick={restart} disabled={loading}><Icon name="reset" size={16} />Start over</button>
      </aside>

      <div className="main">
        <div className="stream" aria-live="polite">
          <div className="stream-inner">
            {showHero && <Hero options={current?.options} onPick={pick} />}
            {feed.map((item, i) => {
              if (item.kind === "q") return <p key={i} className="qline">{item.text}</p>;
              if (item.kind === "user") return <div key={i} className="answer"><span>{item.text}</span></div>;
              if (item.kind === "results")
                return <Results key={i} laptops={item.laptops} text={item.text} category={brief.category} latest={i === lastResults} />;
              return <p key={i} className="thanks">{item.text}</p>;
            })}
            {loading && !showHero && <Working heavy={heavy} />}
            {error && (
              <div className="error" role="alert">
                <span className="error-icon"><Icon name="alert" size={20} /></span>
                <div>
                  <h3>We could not complete that</h3>
                  <p>{error}</p>
                  <p className="muted">Check that the backend is running, then try again.</p>
                  <div className="duo">
                    <button className="btn primary" onClick={() => lastReq.current && run(lastReq.current)}>Try again</button>
                    <button className="btn ghost" onClick={restart}>Start over</button>
                  </div>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        </div>
        {!showHero && !loading && !error && <Dock current={current} category={brief.category} done={done} onPick={pick} onRestart={restart} />}
      </div>
    </div>
  );
}
