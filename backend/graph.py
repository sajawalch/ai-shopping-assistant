"""LangGraph workflow for the AI Shopping Assistant (Pakistan market, prices in PKR).
Shops for laptops OR mobile phones.

START -> get_requirements -> web_search -> compare_products
      -> generate_recommendation -> ask_satisfied
            yes (wants more) -> update_search -> web_search  (loop)
            no               -> END
"""
from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from tools import PK_DOMAINS, calculator, compare_products, discount_percent, parse_pkr, pkr, web_search

MODEL = os.getenv("SHOPPING_MODEL", "gpt-4o")

USE_CASES = {
    "laptop": ["gaming", "programming", "office", "university"],
    "phone": ["gaming", "photography", "daily", "battery"],
}
USE_PROMPT = {
    "laptop": "What do you need the laptop for? Gaming / Programming / Office work / University studies",
    "phone": "What do you need the phone for? Gaming / Photography / Daily use / Battery life",
}
MIN_BUDGET = {"laptop": 30000, "phone": 12000}


def llm() -> ChatOpenAI:
    return ChatOpenAI(model=MODEL, temperature=0)


# ----------------------------------------------------------------- parsing helpers
def parse_category(text: str) -> Optional[str]:
    t = text.lower()
    if re.search(r"phone|mobile|smart|iphone|android|samsung|\bcell", t):
        return "phone"
    if re.search(r"laptop|notebook|computer|\bpc\b|macbook", t):
        return "laptop"
    return None


def parse_use(category: str, text: str) -> Optional[str]:
    t = text.lower()
    if category == "laptop":
        for u in USE_CASES["laptop"]:
            if u in t:
                return u
        return "office" if "office" in t else "university" if "stud" in t else None
    if "gam" in t or "pubg" in t:
        return "gaming"
    if re.search(r"photo|camera|video|vlog|selfie", t):
        return "photography"
    if "batter" in t or "charg" in t:
        return "battery"
    if re.search(r"daily|everyday|social|whatsapp|tiktok|calls|basic|general|normal", t):
        return "daily"
    return None


# ----------------------------------------------------------------- state
class State(TypedDict, total=False):
    category: str              # "laptop" | "phone"
    budget: float
    use_case: str
    extra: str                 # extra wishes from later rounds ("Samsung only", "lighter"...)
    seen: list[str]            # product names already recommended
    candidates: list[dict]
    ranked: list[dict]
    recommendation: str
    search_error: str
    wants_more: bool
    round: int


class Product(BaseModel):
    name: str = Field(description="Full model name")
    price: float = Field(description="Current price in PKR (number only, e.g. 149999)")
    original_price: Optional[float] = Field(None, description="List price before discount, if shown")
    processor: str = Field("", description="CPU (laptop) or chipset (phone), e.g. 'Snapdragon 7 Gen 3'")
    ram_gb: int = 0
    storage_gb: int = 0
    gpu: str = Field("", description="Laptops only: dedicated GPU, empty if integrated")
    battery_mah: int = Field(0, description="Phones only: battery capacity in mAh")
    camera_mp: int = Field(0, description="Phones only: main rear camera in megapixels")
    screen: str = Field("", description="Screen size / type, e.g. '6.7\" AMOLED 120Hz'")
    url: str = ""


class Products(BaseModel):
    products: list[Product]


# ----------------------------------------------------------------- nodes
def get_requirements(state: State) -> State:
    """Ask: laptop or phone? -> budget -> what it's for."""
    if state.get("category") and state.get("budget") and state.get("use_case"):
        return {}

    category = None
    while category is None:
        category = parse_category(str(interrupt("What are you shopping for? Laptop / Mobile phone")))

    budget = None
    while budget is None:
        budget = parse_pkr(interrupt("What is your budget in PKR? (e.g. 120000, 120k or 1.5 lakh)"))
        if budget and budget < MIN_BUDGET[category]:
            print(f"(Note: new {category}s in Pakistan rarely cost under Rs {MIN_BUDGET[category]:,} "
                  f"- results may be limited.)")

    use_case = None
    while use_case is None:
        use_case = parse_use(category, str(interrupt(USE_PROMPT[category])))

    return {"category": category, "budget": budget, "use_case": use_case,
            "seen": [], "extra": "", "round": 0}


def _queries(s: State) -> list[str]:
    b = f"{int(s['budget']):,}"
    extra = f" {s['extra']}" if s.get("extra") else ""
    if s["category"] == "phone":
        uc = {"gaming": "gaming", "photography": "camera photography", "daily": "daily use",
              "battery": "long battery life"}[s["use_case"]]
        return [
            f"best {uc} mobile phone in Pakistan under Rs {b} price specs{extra}",
            f"mobile phone price in Pakistan {b} PKR {uc} RAM storage battery camera PTA approved{extra}",
            f"priceoye daraz mobile {uc} under {b}{extra}",
        ]
    uc = {"gaming": "gaming", "programming": "programming", "office": "office work",
          "university": "students university"}[s["use_case"]]
    return [
        f"best {uc} laptop in Pakistan under Rs {b} price specs{extra}",
        f"laptop price in Pakistan {b} PKR {uc} RAM processor SSD{extra}",
        f"priceoye daraz laptop {uc} under {b}{extra}",
    ]


def search_web(state: State) -> State:
    """Search the web, then extract structured specs."""
    cat = state["category"]
    noun = "mobile phones" if cat == "phone" else "laptops"
    queries = _queries(state)
    domains = PK_DOMAINS[cat]

    def run(q: str) -> list[dict]:
        return web_search.invoke({"query": q, "domains": domains})

    with ThreadPoolExecutor(max_workers=len(queries)) as pool:   # run the searches in parallel
        results = list(pool.map(run, queries))

    snippets, errors, seen_urls = [], [], set()
    for res in results:
        for r in res:
            if r["title"] == "search error":
                errors.append(r["snippet"])
            elif (r["url"], r["snippet"][:80]) not in seen_urls:
                seen_urls.add((r["url"], r["snippet"][:80]))
                snippets.append(f"- {r['title']} ({r['url']}): {r['snippet']}")
    if not snippets:
        return {"candidates": [], "search_error": errors[0] if errors else "No search results.",
                "round": state.get("round", 0) + 1}
    seen = state.get("seen", [])
    prompt = (
        f"From these web search results, extract distinct {noun} that could suit a "
        f"{state['use_case']} user in Pakistan with a budget of Rs {state['budget']:,.0f}. "
        f"All prices must be in Pakistani rupees (PKR / Rs) as listed by Pakistani stores. "
        f"Skip any result priced in another currency; never convert or invent numbers. "
        f"Only include {noun} whose specs and PKR price are stated in the results. "
        f"If a model appears several times, use the lowest current listed PKR price. "
        f"Prefer pages from Pakistani stores (PriceOye, Daraz, Mega.pk, WhatMobile, Czone). "
        f"Skip these already-shown models: {seen or 'none'}. "
        f"Extra wishes: {state.get('extra') or 'none'}.\n\n" + "\n".join(snippets)
    )
    out = llm().with_structured_output(Products, method="function_calling").invoke(prompt)
    budget = state["budget"]
    cands = [p.model_dump() for p in out.products
             if p.price and p.price <= budget * 1.05 and p.name not in seen]
    for c in cands:
        c["category"] = cat
    return {"candidates": cands, "search_error": "", "round": state.get("round", 0) + 1}


def compare(state: State) -> State:
    """Compare (at least three) options and rank them."""
    cands = state.get("candidates", [])
    for c in cands:
        c["discount_pct"] = discount_percent(c.get("original_price") or 0, c["price"])
        c["budget_left"] = calculator.invoke({"expression": f"{state['budget']} - {c['price']}"})
    ranked = compare_products.invoke({
        "products": cands, "use_case": state["use_case"],
        "budget": state["budget"], "category": state["category"],
    })
    return {"ranked": ranked}


def _row(i: int, r: dict, cat: str) -> str:
    base = (f"{i}. {r['name']} | {pkr(r['price'])} (discount {r['discount_pct']}%, "
            f"{pkr(r['budget_left'])} under budget) | ")
    if cat == "phone":
        spec = (f"Chipset {r['processor']} | RAM {r['ram_gb']}GB | Storage {r['storage_gb']}GB | "
                f"Battery {r['battery_mah']}mAh | Camera {r['camera_mp']}MP | Screen {r['screen'] or 'n/a'}")
    else:
        spec = (f"CPU {r['processor']} | RAM {r['ram_gb']}GB | Storage {r['storage_gb']}GB | "
                f"GPU {r['gpu'] or 'integrated'}")
    return f"{base}{spec} | score {r['total']}/10 | {r['url']}"


def recommend(state: State) -> State:
    """Recommend the best option."""
    cat = state["category"]
    noun = "mobile phone" if cat == "phone" else "laptop"
    ranked = state.get("ranked", [])
    if state.get("search_error"):
        text = ("I couldn't reach the store search just now, so I can't show reliable prices. "
                f"Please try again in a moment. (Details: {state['search_error']})")
    elif not ranked:
        text = (f"I couldn't find {noun}s with clear specs and prices within that budget. "
                "Try a higher budget or different requirements.")
    else:
        top = ranked[:max(3, min(len(ranked), 4))]
        table = "\n".join(_row(i, r, cat) for i, r in enumerate(top, 1))
        note = "" if len(ranked) >= 3 else (
            f"\nNOTE: only {len(ranked)} option(s) were found; say so plainly.")
        local = ("Remind the buyer to confirm the phone is PTA approved and check the warranty."
                 if cat == "phone" else "Mention checking the warranty with the seller.")
        spec_list = ("RAM, chipset, storage, battery, camera" if cat == "phone"
                     else "RAM, processor, storage")
        text = llm().invoke(
            f"A customer in Pakistan needs a {noun} for {state['use_case']} with a budget of "
            f"{pkr(state['budget'])}. Here are the options, already ranked by our comparison tool:"
            f"\n{table}{note}\n\n"
            f"Write a short comparison of the options ({spec_list}, price), then clearly "
            "recommend the top-ranked one and explain why in 2-3 sentences. "
            f"Show all prices in Rs (PKR). Use only the data given. {local}"
        ).content
    seen = state.get("seen", []) + [r["name"] for r in ranked]
    return {"recommendation": text, "seen": seen}


def ask_satisfied(state: State) -> State:
    """Show the recommendation and ask if the user wants more."""
    ans = str(interrupt({"recommendation": state["recommendation"],
                         "ranked": state.get("ranked", [])[:4],
                         "question": "Would you like more recommendations? (yes/no)"})).lower()
    return {"wants_more": ans.strip().startswith(("y", "sure", "ok"))}


def update_search(state: State) -> State:
    """Collect updated requirements and loop back to web search."""
    ans = str(interrupt("What would you like to change? (new budget in PKR, different use, brand, "
                        "etc. - or press Enter to just see other models)"))
    upd: State = {}
    new_budget = parse_pkr(ans)
    if new_budget and new_budget >= 1000:
        upd["budget"] = new_budget
    new_use = parse_use(state["category"], ans)
    if new_use:
        upd["use_case"] = new_use
    upd["extra"] = ans.strip()
    return upd


def route(state: State) -> str:
    return "update_search" if state.get("wants_more") else END


# ----------------------------------------------------------------- build
def build_graph():
    g = StateGraph(State)
    g.add_node("get_requirements", get_requirements)
    g.add_node("web_search", search_web)
    g.add_node("compare_products", compare)
    g.add_node("generate_recommendation", recommend)
    g.add_node("ask_satisfied", ask_satisfied)
    g.add_node("update_search", update_search)

    g.add_edge(START, "get_requirements")
    g.add_edge("get_requirements", "web_search")
    g.add_edge("web_search", "compare_products")
    g.add_edge("compare_products", "generate_recommendation")
    g.add_edge("generate_recommendation", "ask_satisfied")
    g.add_conditional_edges("ask_satisfied", route, {"update_search": "update_search", END: END})
    g.add_edge("update_search", "web_search")
    return g.compile(checkpointer=MemorySaver())
