# mcp-vitals

**Reliability grades for MCP servers — run behavioral + agent-usability evals against *your*
server, in CI. Open source.**

[![CI](https://github.com/enached134-ctrl/mcp-vitals/actions/workflows/ci.yml/badge.svg)](https://github.com/enached134-ctrl/mcp-vitals/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

Security scanners tell you whether an MCP server is *safe*. Hosted leaderboards grade its
*definitions* from the outside. **Neither tells you whether the tools actually work — or
whether an AI agent can figure out how to use them.** That behavioral, agent-usability layer
is what `mcp-vitals` measures, as a CLI you point at your own server and wire into CI.

## Where it fits (honest landscape, July 2026)

| Tool | What it checks | Run it yourself? | Behavioral? | Agent-usability? |
|---|---|---|---|---|
| mcp-scan / mcp-scanner / ScanMCP | **security** (injection, poisoning) | ✅ | — | — |
| ToolBench (Arcade), MCP directories | **static** definition quality, protocol, security | ❌ hosted index | — | — |
| **mcp-vitals** | **does it work + can agents use it** | ✅ **CLI + CI** | ✅ | ✅ |

Complementary, not competing: mcp-vitals *runs* `mcp-scan` as its security sub-check and can
ingest ToolBench-style static findings. It adds the half nobody runs on your server: **behavior
and agent-usability.**

## The grade (five layers → one A–F score)

| Layer | Weight | What it measures |
|---|---|---|
| **L1 · Static** | 15 | schema quality: description completeness, param docs, naming clarity, spec compliance (deterministic linter) |
| **L2 · Behavioral** | 30 | auto-generated test suite run in a sandbox: success rate, graceful errors, p50/p95 latency, output-schema conformance |
| **L3 · Agent-usability** | 25 | *the layer nobody measures* — LLM-as-judge task battery: can a model pick the right tool and construct a valid call? tool-selection + argument accuracy |
| **L4 · Adversarial** | 15 | injection-bait, tool-description poisoning heuristics, over-permission flags (+ runs `mcp-scan`) |
| **L5 · Ops** | 15 | auth, TLS, rate-limit/timeout handling, error taxonomy |

Outputs: `score.json` · a shareable `report.html` · a README badge · CI mode that exits
non-zero when the grade regresses against a baseline.

## Status — building in public

- [x] **M1**: connector (enumerate tools/resources/prompts) + L1 static linter + HTML report — grades a real server end-to-end
- [ ] M2: L2 behavioral sandbox suite
- [ ] M3: L3 agent-usability judge battery (+ calibration) + L4 + L5
- [ ] M4: GitHub Action + badge endpoint + the launch run (grade the top public MCP servers)

## Quickstart

```bash
pip install -e .
mcpvitals grade "python -m agentic_rag_mcp.server"   # any stdio command or http(s):// URL
# → writes report.html + score.json
```

## License

MIT
