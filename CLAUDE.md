# Cold Trail
CLI text detective game, C++20/CMake. Spec: docs/superpowers/specs/. Plan: docs/superpowers/plans/.
Layout: src/ engine, tests/ GoogleTest, data/case01.json, docs/case-format.md.
Build/test: cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build --config Debug --parallel && ctest --test-dir build -C Debug --output-on-failure
Local toolchain (not on PATH): $b="C:\Program Files\JetBrains\CLion 2026.2.3.1\bin"; $env:PATH="$b\cmake\win\x64\bin;$b\ninja\win\x64;$b\mingw\bin;$env:PATH"; configure with -G Ninja.
Team: Lead = main session (delegates, accepts). User merges PRs. Subagents in .claude/agents/: game-designer (data/), programmer (src/), qa (tests/, writes tests first, reports bugs). Stay in your lane.
Rules: no std::format, no C++23; `requires_clue` not `requires`; game text English; one accusation only.
