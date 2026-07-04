# State of MCP Reliability — a starter league table

Official MCP reference servers, graded by [mcp-vitals](https://github.com/enached134-ctrl/mcp-vitals) (static + behavioral + agent-usability). Read-only, run locally. Not a security audit — this measures whether the tools *work* and whether an agent can *use* them.

| Server | Grade | Overall | L1 | L2 | L3 | Tools |
|---|---|---|---|---|---|---|
| memory | **A** | 94 | 89 | 100 | 89 | 9 |
| everything | **A** | 92 | 87 | 96 | 92 | 13 |
| filesystem | **C** | 71 | 79 | 64 | 75 | 14 |
| sequential-thinking | **F** | 57 | 100 | 0 | 100 | 1 |

### Agent tool-confusions observed (L3)

Where a model picked the wrong tool for a task — a description-clarity signal:
- **memory**: `delete_relations → read_graph`
- **everything**: `gzip-file-as-resource → echo`
- **filesystem**: `read_file → read_text_file`
- **filesystem**: `read_multiple_files → search_files`
- **filesystem**: `edit_file → read_text_file`

### Method & honest limitations

- **L2** generates test inputs from JSON schemas only — it has no semantic idea of what a *meaningful* argument is. A tool that needs a specific well-formed payload (e.g. sequential-thinking's single `sequentialthinking` tool) can score low on L2 because the synthetic input isn't valid *content*, even though the server is fine. Read that as "needs richer, tool-aware test cases", not "broken server".
- **L3** tasks are auto-generated (one per tool) — a starting signal, not a human-labeled benchmark. The confusions above are real, but a curated calibration set (a later milestone) would make the accuracy numbers authoritative.
- Read-only, official reference servers, run locally. This is a *starter* table; the harness (`launch/run_launch.py`) grades any list of targets.
