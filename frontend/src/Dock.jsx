import React, { useState } from "react";
import Icon from "./Icon.jsx";
import { lakh, rs } from "./format.js";

const USE_ICON = {
  gaming: "gamepad", programming: "code", office: "briefcase", university: "cap",
  photography: "camera", daily: "sun", battery: "battery",
};
const USE_HINT = {
  gaming: "Strong performance for games",
  programming: "Fast builds and plenty of memory",
  office: "Documents, email and meetings",
  university: "Notes, research and long days",
  photography: "The best camera for the money",
  daily: "Social media, calls and everyday apps",
  battery: "Lasts through a long day",
};
const BUDGET = {
  laptop: { min: 40000, max: 600000, step: 5000, start: 150000, presets: [80000, 120000, 180000, 250000, 400000] },
  phone: { min: 15000, max: 400000, step: 5000, start: 60000, presets: [30000, 50000, 80000, 120000, 200000] },
};

export function CategoryTiles({ options, onPick }) {
  if (!options?.length) {
    return (
      <div className="tiles two" aria-busy="true">
        <div className="tile skeleton" /><div className="tile skeleton" />
      </div>
    );
  }
  return (
    <div className="tiles two">
      {options.map((o) => {
        const phone = o.value === "phone";
        return (
          <button key={o.value} className={"tile big " + (phone ? "phone" : "laptop")}
                  onClick={() => onPick(o.value, phone ? "Mobile phone" : "Laptop")}>
            <span className="tile-icon"><Icon name={phone ? "phone" : "laptop"} size={34} strokeWidth={1.6} /></span>
            <span className="tile-title">{phone ? "Mobile phone" : "Laptop"}</span>
            <span className="tile-sub">{phone ? "Camera, battery, chipset" : "Memory, processor, storage"}</span>
          </button>
        );
      })}
    </div>
  );
}

function UseTiles({ options, onPick }) {
  return (
    <div className="tiles four">
      {options.map((o) => (
        <button key={o.value} className="tile use" onClick={() => onPick(o.value, o.label)}>
          <span className="tile-icon small"><Icon name={USE_ICON[o.value] || "tag"} size={22} /></span>
          <span className="tile-title">{o.label}</span>
          <span className="tile-sub">{USE_HINT[o.value]}</span>
        </button>
      ))}
    </div>
  );
}

function BudgetPicker({ category, onPick }) {
  const cfg = BUDGET[category] || BUDGET.laptop;
  const [value, setValue] = useState(cfg.start);
  const pct = ((value - cfg.min) / (cfg.max - cfg.min)) * 100;
  return (
    <div className="budget">
      <div className="budget-read">
        <output className="budget-amount" htmlFor="budget-range">{rs(value)}</output>
        <span className="budget-lakh">{lakh(value)}</span>
      </div>
      <input id="budget-range" type="range" min={cfg.min} max={cfg.max} step={cfg.step}
             value={value} onChange={(e) => setValue(Number(e.target.value))}
             style={{ "--pct": pct + "%" }} aria-label="Budget in rupees" />
      <div className="budget-scale"><span>{rs(cfg.min)}</span><span>{rs(cfg.max)}</span></div>
      <div className="chips">
        {cfg.presets.map((p) => (
          <button key={p} className={"chip" + (p === value ? " on" : "")} onClick={() => setValue(p)}>{lakh(p)}</button>
        ))}
      </div>
      <button className="btn primary wide" onClick={() => onPick(String(value), rs(value))}>
        Use {rs(value)} as my budget
      </button>
    </div>
  );
}

function ChangeBox({ options, onPick }) {
  const [text, setText] = useState("");
  return (
    <div className="change">
      <form className="textrow" onSubmit={(e) => { e.preventDefault(); text.trim() && onPick(text.trim(), text.trim()); }}>
        <input value={text} onChange={(e) => setText(e.target.value)}
               placeholder="For example: Samsung only, or under 1.5 lakh" aria-label="What should change" />
        <button className="btn primary" disabled={!text.trim()}><Icon name="send" size={18} />Search again</button>
      </form>
      {options.map((o) => (
        <button key={o.label} className="btn ghost" onClick={() => onPick(o.value, "Show other models")}>Just show other models</button>
      ))}
    </div>
  );
}

function TextRow({ onPick }) {
  const [text, setText] = useState("");
  return (
    <form className="textrow" onSubmit={(e) => { e.preventDefault(); text.trim() && onPick(text.trim(), text.trim()); }}>
      <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your answer" aria-label="Your answer" />
      <button className="btn primary" disabled={!text.trim()}><Icon name="send" size={18} />Send</button>
    </form>
  );
}

const TITLE = {
  category: ["What are you shopping for?", "Pick one and we will tailor the questions."],
  budget: ["What is your budget?", "Drag the slider or choose a common amount."],
  more: ["Want to see more options?", "We will skip everything you have already seen."],
  change: ["What should we change?", "A new budget, brand or use. Or skip to see other models."],
};

export default function Dock({ current, category, done, onPick, onRestart }) {
  if (done) {
    return (
      <div className="dock">
        <button className="btn primary wide" onClick={onRestart}><Icon name="reset" size={18} />Start a new search</button>
      </div>
    );
  }
  if (!current) return null;
  const { step, options = [] } = current;
  const noun = category === "phone" ? "phone" : "laptop";
  const [title, hint] = step === "use"
    ? [`What will you use the ${noun} for?`, "Choose the closest match."]
    : TITLE[step] || [current.message, ""];

  let body;
  if (step === "budget") body = <BudgetPicker category={category} onPick={onPick} />;
  else if (step === "use") body = <UseTiles options={options} onPick={onPick} />;
  else if (step === "category") body = <CategoryTiles options={options} onPick={onPick} />;
  else if (step === "more") {
    body = (
      <div className="duo">
        <button className="btn primary" onClick={() => onPick(options[0]?.value ?? "yes", "Show me more")}>Show me more options</button>
        <button className="btn ghost" onClick={() => onPick(options[1]?.value ?? "no", "I'm done")}>I'm done</button>
      </div>
    );
  } else if (step === "change") body = <ChangeBox options={options} onPick={onPick} />;
  else body = <TextRow onPick={onPick} />;

  return (
    <div className="dock" key={step}>
      <h2 className="dock-title">{title}</h2>
      {hint && <p className="dock-hint">{hint}</p>}
      {body}
    </div>
  );
}
