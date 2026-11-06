"""The three required tools: Web Search, Calculator, Product Comparison (laptops + mobile phones)."""
from __future__ import annotations

import ast
import operator
import os
import re
from typing import Optional

from langchain_core.tools import tool

# --------------------------------------------------------------------------
# 1. Web Search Tool
#    Uses Tavily when TAVILY_API_KEY is set (reliable on hosting servers, can be
#    limited to Pakistani shops). Falls back to DuckDuckGo, which is free but is
#    often blocked on cloud hosts.
# --------------------------------------------------------------------------
PK_DOMAINS = {
    "phone": ["priceoye.pk", "whatmobile.com.pk", "daraz.pk", "mega.pk", "homeshopping.pk"],
    "laptop": ["priceoye.pk", "daraz.pk", "mega.pk", "czone.com.pk", "shophive.com", "homeshopping.pk"],
}


def search_provider() -> str:
    return "tavily" if os.getenv("TAVILY_API_KEY") else "duckduckgo"


def _tavily(query: str, max_results: int, domains: Optional[list]) -> list[dict]:
    import httpx

    key = os.environ["TAVILY_API_KEY"]
    body = {
        "api_key": key,
        "query": query,
        "search_depth": os.getenv("TAVILY_DEPTH", "advanced"),  # "basic" uses fewer credits
        "max_results": max_results,
        "include_answer": False,
    }
    if domains:
        body["include_domains"] = domains
    r = httpx.post("https://api.tavily.com/search", json=body,
                   headers={"Authorization": f"Bearer {key}"}, timeout=45)
    r.raise_for_status()
    return [
        {"title": x.get("title", ""), "url": x.get("url", ""), "snippet": (x.get("content") or "")[:1500]}
        for x in r.json().get("results", [])
    ]


def _ddg(query: str, max_results: int) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:  # older package name
        from duckduckgo_search import DDGS  # type: ignore
    hits = DDGS().text(query, region="pk-en", max_results=max_results)
    return [
        {"title": h.get("title", ""), "url": h.get("href", ""), "snippet": h.get("body", "")}
        for h in hits
    ]


@tool
def web_search(query: str, max_results: int = 8, domains: Optional[list[str]] = None) -> list[dict]:
    """Search the web (Pakistan) for laptops / mobile phones, specifications and PKR prices.

    `domains` optionally limits results to those shops. Returns [{title, url, snippet}].
    On failure returns one item whose title is "search error".
    """
    errors: list[str] = []
    if os.getenv("TAVILY_API_KEY"):
        try:
            hits = _tavily(query, max_results, domains)
            if not hits and domains:          # shops had nothing: try the whole web
                hits = _tavily(query, max_results, None)
            if hits:
                return hits
            errors.append("Tavily returned no results")
        except Exception as exc:
            errors.append(f"Tavily: {type(exc).__name__}: {str(exc)[:150]}")
    try:
        hits = _ddg(query, max_results)
        if hits:
            return hits
        errors.append("DuckDuckGo returned no results")
    except Exception as exc:
        errors.append(f"DuckDuckGo: {type(exc).__name__}: {str(exc)[:150]}")
    return [{"title": "search error", "url": "", "snippet": "; ".join(errors)}]


# --------------------------------------------------------------------------
# PKR helpers
# --------------------------------------------------------------------------
def parse_pkr(text: str) -> float | None:
    """'80000', '80k', '1.5 lakh', '1 lac', 'Rs 120,000', '1 million' -> rupees."""
    m = re.search(r"(\d[\d,]*\.?\d*)\s*(k|thousand|lakh|lac|lacs|lakhs|million|m)?\b", str(text).lower())
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    mult = {"k": 1e3, "thousand": 1e3, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
            "million": 1e6, "m": 1e6}.get(m.group(2) or "", 1)
    return n * mult


def pkr(x: float) -> str:
    return f"Rs {x:,.0f}"


# --------------------------------------------------------------------------
# 2. Calculator Tool
# --------------------------------------------------------------------------
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


@tool
def calculator(expression: str) -> float:
    """Safely evaluate an arithmetic expression, e.g. '(1299 - 999) / 1299 * 100'."""
    return _eval(ast.parse(expression, mode="eval"))


def discount_percent(original: float, price: float) -> float:
    """Percent saved going from `original` to `price` (computed with the calculator)."""
    if not original or original <= price:
        return 0.0
    return round(calculator.invoke({"expression": f"({original} - {price}) / {original} * 100"}), 1)


# --------------------------------------------------------------------------
# 3. Product Comparison Tool  (laptops: RAM, processor, storage, GPU, price
#                              phones : RAM, processor, storage, battery, camera, price)
# --------------------------------------------------------------------------
# Weights per use case
LAPTOP_WEIGHTS = {
    "gaming":      {"cpu": 0.20, "ram": 0.15, "storage": 0.10, "gpu": 0.40, "price": 0.15},
    "programming": {"cpu": 0.35, "ram": 0.30, "storage": 0.15, "gpu": 0.00, "price": 0.20},
    "office":      {"cpu": 0.25, "ram": 0.20, "storage": 0.15, "gpu": 0.00, "price": 0.40},
    "university":  {"cpu": 0.25, "ram": 0.20, "storage": 0.15, "gpu": 0.00, "price": 0.40},
}
PHONE_WEIGHTS = {
    "gaming":      {"cpu": 0.35, "ram": 0.20, "storage": 0.05, "battery": 0.15, "camera": 0.00, "price": 0.25},
    "photography": {"cpu": 0.10, "ram": 0.10, "storage": 0.15, "battery": 0.10, "camera": 0.40, "price": 0.15},
    "daily":       {"cpu": 0.15, "ram": 0.15, "storage": 0.15, "battery": 0.20, "camera": 0.10, "price": 0.25},
    "battery":     {"cpu": 0.10, "ram": 0.05, "storage": 0.10, "battery": 0.50, "camera": 0.05, "price": 0.20},
}


def cpu_score(proc: str) -> float:
    """Rough 0-10 tier score from a laptop processor name."""
    p = (proc or "").lower()
    m = re.search(r"\bm([1-9])\b\s*(pro|max|ultra)?", p)
    if "apple" in p or m:
        gen = int(m.group(1)) if m else 2
        bump = {"pro": 1.5, "max": 2.5, "ultra": 3.0}.get(m.group(2) if m else None, 0)
        return min(10, 5.5 + gen * 0.5 + bump)
    tier = 0.0
    if re.search(r"ultra\s*9|i9|ryzen\s*9", p): tier = 9
    elif re.search(r"ultra\s*7|i7|ryzen\s*7", p): tier = 7.5
    elif re.search(r"ultra\s*5|i5|ryzen\s*5", p): tier = 6
    elif re.search(r"i3|ryzen\s*3", p): tier = 4
    elif p: tier = 3
    if re.search(r"\b(h|hx|hs)\b|\d{4,5}h", p): tier += 0.8  # performance-class suffix
    return min(10, tier)


def phone_cpu_score(proc: str) -> float:
    """Rough 0-10 tier score from a phone chipset name."""
    p = (proc or "").lower()
    if not p:
        return 0.0
    if m := re.search(r"snapdragon\s*(\d)(\+|s)?\s*(elite|gen\s*(\d))?", p):
        series = int(m.group(1))
        if m.group(3) and m.group(3).startswith("elite"):
            return 10.0
        gen = int(m.group(4)) if m.group(4) else 1
        base = {8: 7.5, 7: 6.0, 6: 4.8, 4: 3.2}.get(series, 3.0) + 0.5 * (gen - 1)
        base += 0.3 if m.group(2) == "+" else -0.3 if (m.group(2) == "s" and series == 8) else 0
        return round(min(10, base), 1)
    if m := re.search(r"dimensity\s*(\d{4})", p):
        n = int(m.group(1))
        base = {9: 8.6, 8: 6.8, 7: 5.8, 6: 4.4}.get(n // 1000, 3.5) + (n % 1000) / 100 * 0.15
        return round(min(10, base), 1)
    if m := re.search(r"\ba(\d{2})\b", p):          # Apple A-series (A15, A17 Pro...)
        return round(min(10, 5 + (int(m.group(1)) - 12) * 0.8 + (0.3 if "pro" in p else 0)), 1)
    if m := re.search(r"tensor\s*g(\d)", p):
        return 6 + int(m.group(1)) * 0.5
    if m := re.search(r"exynos\s*(\d{4})", p):
        n = int(m.group(1))
        return round(min(10, 7 + (n - 2000) / 500) if n >= 2000 else 4.5 + (n - 1000) / 500, 1)
    if m := re.search(r"helio\s*g(\d+)", p):
        return round(2.8 + (int(m.group(1)) - 80) * 0.07, 1)
    if "kirin" in p: return 6.0
    if "unisoc" in p or "spreadtrum" in p: return 2.5
    return 3.0


def gpu_score(gpu: str) -> float:
    g = (gpu or "").lower()
    m = re.search(r"rtx\s*(\d{4})", g)
    if m:
        n = int(m.group(1))
        tier, gen = (n % 1000) / 10, n // 1000  # e.g. 4060 -> tier 6, gen 4
        return min(10, 0.8 * tier + 0.5 * (gen - 3) + 0.5)
    if "gtx" in g or "rx" in g or "arc" in g: return 4
    return 1 if g else 0


def _norm(v: float, lo: float, hi: float) -> float:
    return max(0.0, min(10.0, (v - lo) / (hi - lo) * 10))


@tool
def compare_products(products: list[dict], use_case: str, budget: float, category: str = "laptop") -> list[dict]:
    """Compare products and rank them best-first for a use case.

    category="laptop": RAM, processor, storage, GPU, price.
    category="phone":  RAM, processor, storage, battery (mAh), main camera (MP), price.
    Each product dict needs: name, price, ram_gb, storage_gb, processor
    (laptop: optional gpu; phone: optional battery_mah, camera_mp).
    Returns the products ranked best-first, each with component `scores` and `total` (0-10).
    """
    phone = category == "phone"
    w = (PHONE_WEIGHTS if phone else LAPTOP_WEIGHTS).get(
        use_case, PHONE_WEIGHTS["daily"] if phone else LAPTOP_WEIGHTS["office"])
    ranked = []
    for p in products:
        price = float(p.get("price") or 0) or budget
        scores = {"price": _norm(budget - price, -0.1 * budget, 0.5 * budget)}  # cheaper = better
        if phone:
            scores.update({
                "cpu": phone_cpu_score(p.get("processor", "")),
                "ram": _norm(p.get("ram_gb") or 0, 3, 16),
                "storage": _norm(p.get("storage_gb") or 0, 64, 512),
                "battery": _norm(p.get("battery_mah") or 0, 3000, 6500),
                "camera": _norm(p.get("camera_mp") or 0, 12, 200),
            })
        else:
            scores.update({
                "cpu": cpu_score(p.get("processor", "")),
                "ram": _norm(p.get("ram_gb") or 0, 4, 32),
                "storage": _norm(p.get("storage_gb") or 0, 128, 2000),
                "gpu": gpu_score(p.get("gpu", "")),
            })
        total = round(sum(scores[k] * w[k] for k in w), 2)
        ranked.append({**p, "scores": {k: round(v, 1) for k, v in scores.items()}, "total": total})
    return sorted(ranked, key=lambda x: x["total"], reverse=True)
