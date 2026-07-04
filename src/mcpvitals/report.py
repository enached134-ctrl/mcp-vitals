"""Render a shareable HTML report for a graded MCP server."""
# ruff: noqa: E501  (inline HTML/CSS template)

from __future__ import annotations

from . import combine, grade_letter
from .connect import Inventory
from .l1_static import LayerResult
from .l2_behavioral import LayerResult as L2Result
from .l3_agent import LayerResult as L3Result

_GRADE_COLOR = {"A": "#34D399", "B": "#5EEAD4", "C": "#FBBF24", "D": "#FB923C", "F": "#F87171"}


def render(
    inv: Inventory,
    l1: LayerResult,
    l2: L2Result | None = None,
    l3: L3Result | None = None,
) -> str:
    layer_scores = {"L1": l1.score}
    if l2 is not None:
        layer_scores["L2"] = l2.score
    if l3 is not None and not l3.note:
        layer_scores["L3"] = l3.score
    overall = combine(layer_scores)
    grade = grade_letter(overall)
    gc = _GRADE_COLOR[grade]

    l2_section = ""
    if l2 is not None:  # noqa: SIM102 - explicit for readability
        rows = ""
        for b in sorted(l2.tools, key=lambda x: (x.called, x.tool)):
            if not b.called:
                rows += f'<div class="brow skip"><span class="bname">{b.tool}</span><span class="bnote">{b.note}</span></div>'
                continue
            succ = f"{b.valid_ok}/{b.valid_total}" if b.valid_total else "–"
            grace = f"{b.graceful_errors}/{b.invalid_total}" if b.invalid_total else "–"
            rows += (
                f'<div class="brow"><span class="bname">{b.tool}</span>'
                f'<span class="bm">valid ok <b>{succ}</b></span>'
                f'<span class="bm">graceful errors <b>{grace}</b></span>'
                f'<span class="bm">p50 <b>{b.p50:.0f}ms</b></span>'
                f'<span class="bm">p95 <b>{b.p95:.0f}ms</b></span>'
                f'{"<span class=bm style=color:#FCA5A5>crashes " + str(b.crashes) + "</span>" if b.crashes else ""}</div>'
            )
        l2_section = f"""<h2>L2 · Behavioral — auto-generated suite, run against the server</h2>
          <p style="color:#7C89A0;font-size:14px;margin:-6px 0 14px;font-family:'JetBrains Mono',monospace">
          score {l2.score:.0f}/100 · {l2.summary}</p>{rows}"""

    l3_section = ""
    if l3 is not None:
        if l3.note:
            l3_section = f'<h2>L3 · Agent-usability</h2><p style="color:#94A3B8">{l3.note}</p>'
        else:
            rows = ""
            for tr in l3.trials:
                ok = tr.correct
                mark = "✓" if ok else "✕"
                cls = "ok" if ok else "no"
                pickinfo = (
                    f'<span class="l3pick">chose <b>{tr.picked or "—"}</b>'
                    f'{" · args valid" if tr.args_valid else (" · wrong tool" if not ok else " · args incomplete")}</span>'
                )
                rows += (
                    f'<div class="l3row {cls}"><span class="l3mark">{mark}</span>'
                    f'<span class="l3task">"{tr.task}" <span class="exp">→ {tr.expected}</span></span>'
                    f'{pickinfo}</div>'
                )
            conf = ""
            if l3.confusions:
                conf = ('<p class="conf">Confusions: '
                        + " · ".join(l3.confusions) + "</p>")
            l3_section = f"""<h2>L3 · Agent-usability — can a model pick the right tool?</h2>
              <p style="color:#7C89A0;font-size:14px;margin:-6px 0 14px;font-family:'JetBrains Mono',monospace">
              score {l3.score:.0f}/100 · {l3.summary} · <em>auto-generated tasks, LLM-as-agent, no server calls</em></p>{rows}{conf}"""

    tool_rows = ""
    for ts in sorted(l1.tools, key=lambda t: t.score):
        checks = "".join(
            f'<li class="{"ok" if c.ok else "no"}">{"✓" if c.ok else "✕"} {c.name}'
            f'{f" · <span>{c.detail}</span>" if c.detail else ""}</li>'
            for c in ts.checks
        )
        tg = grade_letter(ts.score)
        tool_rows += f"""<div class="tool">
          <div class="thead"><span class="tname">{ts.tool}</span>
            <span class="tscore" style="color:{_GRADE_COLOR[tg]}">{ts.score:.0f} · {tg}</span></div>
          <ul class="checks">{checks}</ul></div>"""

    layers = ""
    from . import LAYER_WEIGHTS
    done = {k: f"{v:.0f}" for k, v in layer_scores.items()}
    for lid, w in LAYER_WEIGHTS.items():
        val = done.get(lid, "—")
        cls = "layer done" if lid in done else "layer todo"
        name = {"L1": "Static", "L2": "Behavioral", "L3": "Agent-usability", "L4": "Adversarial", "L5": "Ops"}[lid]
        layers += f'<div class="{cls}"><div class="lid">{lid} · {name}</div><div class="lval">{val}</div><div class="lw">weight {w}</div></div>'

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>mcp-vitals · {inv.target}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}} body{{background:#0A0E1A;color:#E8EEF6;font-family:'Space Grotesk',sans-serif;padding:52px 24px 80px}}
.wrap{{max-width:900px;margin:0 auto}} .kick{{font-family:'JetBrains Mono',monospace;font-size:13px;letter-spacing:3px;color:#5EEAD4;text-transform:uppercase}}
.top{{display:flex;align-items:center;gap:30px;margin:18px 0 8px;flex-wrap:wrap}}
.gbadge{{width:130px;height:130px;border-radius:24px;display:flex;align-items:center;justify-content:center;font-family:'Fraunces',serif;font-weight:600;font-size:78px;border:2px solid {gc};color:{gc};box-shadow:0 0 50px {gc}22}}
.tt h1{{font-family:'JetBrains Mono',monospace;font-size:23px;color:#F4F7FB;font-weight:600;word-break:break-all}}
.tt .m{{color:#94A3B8;font-size:16px;margin-top:8px}} .tt .m b{{color:#E8EEF6}}
.layers{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:30px 0}}
.layer{{border-radius:12px;padding:16px 14px;border:1px solid rgba(148,163,184,.16)}}
.layer.done{{background:rgba(6,50,44,.3);border-color:rgba(52,211,153,.4)}} .layer.todo{{opacity:.5}}
.lid{{font-size:14px;color:#CBD5E1;font-weight:600}} .lval{{font-family:'Fraunces',serif;font-size:34px;color:#5EEAD4;margin:4px 0}} .layer.todo .lval{{color:#64748B}}
.lw{{font-family:'JetBrains Mono',monospace;font-size:12px;color:#7C89A0}}
h2{{font-size:20px;color:#F4F7FB;margin:30px 0 14px;border-bottom:1px solid rgba(148,163,184,.16);padding-bottom:10px}}
.tool{{background:rgba(20,28,45,.5);border-radius:12px;padding:18px 20px;margin-bottom:12px;border-left:3px solid {gc}}}
.thead{{display:flex;justify-content:space-between;align-items:center}} .tname{{font-family:'JetBrains Mono',monospace;font-size:18px;color:#F4F7FB;font-weight:600}}
.tscore{{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700}}
.checks{{list-style:none;margin-top:12px;display:flex;flex-direction:column;gap:5px}}
.checks li{{font-size:15px;color:#CBD5E1}} .checks li.ok{{color:#8FE9CE}} .checks li.no{{color:#FCA5A5}} .checks li span{{color:#7C89A0;font-family:'JetBrains Mono',monospace;font-size:13px}}
.brow{{display:flex;align-items:center;gap:20px;flex-wrap:wrap;background:rgba(20,28,45,.5);border-radius:10px;padding:14px 18px;margin-bottom:9px;border-left:3px solid #2DD4BF}}
.brow.skip{{border-left-color:#475569;opacity:.75}}
.bname{{font-family:'JetBrains Mono',monospace;font-size:16px;color:#F4F7FB;font-weight:600;min-width:150px}}
.bm{{font-size:14px;color:#94A3B8;font-family:'JetBrains Mono',monospace}} .bm b{{color:#8FE9CE}}
.bnote{{font-size:14px;color:#94A3B8;font-family:'JetBrains Mono',monospace;font-style:italic}}
.l3row{{display:flex;align-items:flex-start;gap:14px;background:rgba(20,28,45,.5);border-radius:10px;padding:14px 18px;margin-bottom:9px;border-left:3px solid #34D399}}
.l3row.no{{border-left-color:#F87171}}
.l3mark{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:16px}} .l3row.ok .l3mark{{color:#34D399}} .l3row.no .l3mark{{color:#FCA5A5}}
.l3task{{flex:1;color:#D6DEEA;font-size:15.5px}} .l3task .exp{{color:#7C89A0;font-family:'JetBrains Mono',monospace;font-size:13px}}
.l3pick{{font-family:'JetBrains Mono',monospace;font-size:13px;color:#94A3B8}} .l3pick b{{color:#8FE9CE}}
.conf{{margin-top:8px;color:#FCA5A5;font-family:'JetBrains Mono',monospace;font-size:13px}}
.foot{{margin-top:36px;padding-top:20px;border-top:1px solid rgba(148,163,184,.16);font-family:'JetBrains Mono',monospace;font-size:13px;color:#7C89A0}}
.err{{background:rgba(127,29,29,.3);border:1px solid rgba(248,113,113,.4);border-radius:12px;padding:18px;color:#FCA5A5}}
</style></head><body><div class="wrap">
<div class="kick">mcp-vitals · reliability grade</div>
<div class="top"><div class="gbadge">{grade}</div>
  <div class="tt"><h1>{inv.target}</h1>
    <div class="m"><b>{len(inv.tools)}</b> tools · <b>{len(inv.resources)}</b> resources · <b>{len(inv.prompts)}</b> prompts · overall <b>{overall:.0f}/100</b></div></div></div>
{'<div class="err">Connection failed: ' + inv.error + '</div>' if inv.error else ''}
<div class="layers">{layers}</div>
{l3_section}
{l2_section}
<h2>L1 · Static — schema quality per tool</h2>
{tool_rows or '<p style="color:#7C89A0">No tools enumerated.</p>'}
<div class="foot">Generated by mcp-vitals · grades L1 (static) + L2 (behavioral) + L3 (agent-usability). L4 adversarial, L5 ops — on the roadmap.</div>
</div></body></html>"""
