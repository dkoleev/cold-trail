# Cold Trail
CLI text detective game, C++20/CMake. Spec: docs/superpowers/specs/. Plan: docs/superpowers/plans/.
Layout: src/ engine, tests/ GoogleTest, data/case01.json, docs/case-format.md.
Build/test: cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build --config Debug --parallel && ctest --test-dir build -C Debug --output-on-failure
Local toolchain (not on PATH): $b="C:\Program Files\JetBrains\CLion 2026.2.3.1\bin"; $env:PATH="$b\cmake\win\x64\bin;$b\ninja\win\x64;$b\mingw\bin;$env:PATH"; configure with -G Ninja.
Team: Lead = main session (delegates, accepts). User merges PRs. Subagents in .claude/agents/: game-designer (data/), programmer (src/), qa (tests/, writes tests first, reports bugs). Stay in your lane.
PR review: 1) Lead reviews first (posts findings as a PR comment; never approves, merges or closes). 2) User reviews, then merges/closes. Remarks from Lead or user are fixed by the programmer agent, who pushes the fix to the PR branch (remarks only in tests/ or data/ go to qa / game-designer, who own those lanes).
Python tooling (MCP server case-tools in tools/case-tools/): py -3.13 -m venv .venv; .venv\Scripts\python -m pip install -e "tools/case-tools[dev]"; tests: .venv\Scripts\python -m pytest tools/case-tools. Lanes: programmer tools/case-tools/src + pyproject.toml, qa tools/case-tools/tests. `.mcp.json` registers the server; set env CASE_TOOLS_PYTHON to the venv python (e.g. .venv\Scripts\python.exe). Tools take only data/<name>.json paths.
Rules: no std::format, no C++23; `requires_clue` not `requires`; game text English; one accusation only.
