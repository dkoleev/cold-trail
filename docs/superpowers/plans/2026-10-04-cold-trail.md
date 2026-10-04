# Cold Trail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI text detective game (C++20), one data-driven case, built by an agent team (Lead + game-designer + programmer + qa).

**Architecture:** `detective_core` static lib (parser, loader, game engine) + `detective` exe (stdin loop) + `unit_tests` (GoogleTest). Case = JSON in `data/`. Engine returns strings, no I/O inside -> testable.

**Tech Stack:** C++20, CMake >= 3.20, nlohmann/json 3.11.3, GoogleTest 1.15.2 (both FetchContent), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-04-cold-trail-design.md`

## Global Constraints
- C++20: `CMAKE_CXX_STANDARD 20`, REQUIRED ON, extensions OFF. No C++23.
- No `std::format` unless CI proves it builds on all 3 platforms; use streams/concat.
- Game text + commands: English.
- One accusation: wrong `accuse` = game over.
- CI on `pull_request`: ubuntu-latest, windows-latest, macos-latest must be green.
- Ownership (agents write only here): game-designer `data/`, `docs/case-format.md`; programmer `src/`, `CMakeLists.txt`, unit tests `tests/*_test.cpp` for its own code; qa `tests/solvability_test.cpp`, `tests/playthrough_test.cpp`, new tests. Lead: everything else, merges, routing bugs.
- `requires` is a C++20 keyword -> C++ field is `requires_clue`; JSON key stays `"requires"`.
- Every commit message ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Build/test cmd: `cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build --config Debug --parallel && ctest --test-dir build -C Debug --output-on-failure`.

## Order
1 -> 2 -> {3, 4, 5 parallel} -> 6 (needs 4,5) -> 7 -> 8 (needs 3,6) -> 9.

## Contract: case JSON
Top: `title, intro, start(locId), locations[], people[], items[], clues[], solution`.
- location: `id,name,description,exits[locId],items[itemId]`
- person: `id,name,description,location(locId),talk[]`; talk line: `text`, optional `requires`(clueId; line shown only if found), optional `reveals`(clueId; learned when line shown)
- item: `id,name,description`, optional `reveals`(clueId); examinable only in its location
- clue: `id,text`
- solution: `killer(personId), required_clues[clueId], explanation`
- ids lowercase snake_case; names unique case-insensitively across locations/people/items (player types names).

## Review Focus
1. Empty / whitespace-only / unknown command -> no crash, hint `help`. (Tasks 5, 6)
2. Mixed case + multi-word args (`ACCUSE MR. GREY`, `go   Study `) resolve. (Tasks 5, 6)
3. Examine/talk twice -> clue not duplicated, no second `[New clue]`. (Task 6)
4. Commands after game over refused; stdin EOF exits cleanly; missing/corrupt case file -> message + exit 1, no crash. (Tasks 6, 7)
5. `accuse` with no arg / unknown name -> NOT fatal (typo must not burn the only chance); killer without full evidence -> lose. (Task 6)

---

### Task 1: CMake skeleton + CI green (Lead)

**Files:** Create `CMakeLists.txt`, `src/model.h`, `src/model.cpp`, `src/main.cpp`, `tests/CMakeLists.txt`, `tests/smoke_test.cpp`

**Produces:** targets `detective_core`, `detective`, `unit_tests`; macro `COLD_TRAIL_DATA_DIR`; `ct::Case` model types.

- [ ] **Step 1:** `git switch -c feat/initial-game`; check `cmake --version` + a compiler. If missing -> ask user (CLion bundles cmake).
- [ ] **Step 2:** `CMakeLists.txt`
```cmake
cmake_minimum_required(VERSION 3.20)
project(cold_trail LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
FetchContent_Declare(json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_MakeAvailable(json)

file(GLOB CORE_SOURCES CONFIGURE_DEPENDS src/*.cpp)
list(FILTER CORE_SOURCES EXCLUDE REGEX "src/main\\.cpp$")
add_library(detective_core STATIC ${CORE_SOURCES})
target_include_directories(detective_core PUBLIC src)
target_link_libraries(detective_core PUBLIC nlohmann_json::nlohmann_json)
target_compile_definitions(detective_core PUBLIC COLD_TRAIL_DATA_DIR="${CMAKE_SOURCE_DIR}/data")

add_executable(detective src/main.cpp)
target_link_libraries(detective PRIVATE detective_core)

enable_testing()
FetchContent_Declare(googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.15.2.tar.gz
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)
add_subdirectory(tests)
```
- [ ] **Step 3:** `src/model.h`
```cpp
#pragma once
#include <optional>
#include <string>
#include <vector>

namespace ct {
struct Clue { std::string id, text; };
struct Item { std::string id, name, description; std::optional<std::string> reveals; };
struct Line { std::string text; std::optional<std::string> requires_clue, reveals; };
struct Person { std::string id, name, description, location; std::vector<Line> talk; };
struct Location { std::string id, name, description; std::vector<std::string> exits, items; };
struct Solution { std::string killer; std::vector<std::string> required_clues; std::string explanation; };
struct Case {
    std::string title, intro, start;
    std::vector<Location> locations;
    std::vector<Person> people;
    std::vector<Item> items;
    std::vector<Clue> clues;
    Solution solution;
};
}  // namespace ct
```
`src/model.cpp`: `#include "model.h"` (keeps lib non-empty). `src/main.cpp`: `#include <iostream>` / `int main() { std::cout << "Cold Trail\n"; }`
- [ ] **Step 4:** `tests/CMakeLists.txt`
```cmake
file(GLOB TEST_SOURCES CONFIGURE_DEPENDS *_test.cpp)
add_executable(unit_tests ${TEST_SOURCES})
target_link_libraries(unit_tests PRIVATE detective_core GTest::gtest_main)
include(GoogleTest)
gtest_discover_tests(unit_tests)
```
`tests/smoke_test.cpp`
```cpp
#include "model.h"
#include <gtest/gtest.h>

TEST(Smoke, ModelDefaultConstructs) {
    ct::Case c;
    EXPECT_TRUE(c.locations.empty());
}
```
- [ ] **Step 5:** Run build/test cmd. Expected: 1 test PASS.
- [ ] **Step 6:** Commit `chore: cmake skeleton`; `git push -u origin feat/initial-game`; `gh pr create --draft --fill`; `gh pr checks --watch`. Expected: 3 platforms green. If one fails (gtest/json/MSVC) fix here before moving on.

---

### Task 2: Agents + project CLAUDE.md (Lead)

**Files:** Create `.claude/agents/game-designer.md`, `.claude/agents/programmer.md`, `.claude/agents/qa.md`, `CLAUDE.md`

- [ ] **Step 1:** `.claude/agents/game-designer.md`
```markdown
---
name: game-designer
description: Designs Cold Trail rules and the detective case (locations, suspects, clues, dialogue). Use for data/ and docs/case-format.md.
tools: Read, Write, Edit, Glob, Grep
model: sonnet
---
You are game designer of Cold Trail, a CLI text detective game (player finds the maniac).
Own: data/*.json, docs/case-format.md. Never edit src/, tests/, CMakeLists.txt.
Format contract is in the plan (docs/superpowers/plans/2026-10-04-cold-trail.md, "Contract: case JSON"). Do not change the format; ask Lead.
Fair play: killer deducible from clue texts alone. At least one red herring. Text in English.
Report: files changed, short solution walkthrough, open questions.
```
- [ ] **Step 2:** `.claude/agents/programmer.md`
```markdown
---
name: programmer
description: Implements Cold Trail engine in C++20 (parser, case loader, game). Use for src/ and CMakeLists.txt.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
---
You are the C++20 programmer of Cold Trail.
Own: src/, CMakeLists.txt, unit tests tests/<unit>_test.cpp for your own code. Never edit data/, docs/case-format.md, qa's tests.
TDD: failing test first, run it, minimal code, run again. Follow the interfaces given in your task exactly.
Build/test: cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build --config Debug --parallel && ctest --test-dir build -C Debug --output-on-failure
Never use std::format or C++23. `requires` is a keyword: field is requires_clue.
Commit per task. Report: what you built, test output summary, deviations.
```
- [ ] **Step 3:** `.claude/agents/qa.md`
```markdown
---
name: qa
description: Tests Cold Trail - solvability validator, scripted playthrough, bug hunting. Reports bugs, does not fix src/.
tools: Read, Write, Edit, Glob, Grep, Bash
model: sonnet
---
You are QA of Cold Trail.
Own: tests/solvability_test.cpp, tests/playthrough_test.cpp, new tests you add. Never edit src/ or data/; report bugs to Lead with repro (input -> actual vs expected).
Build/test: cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build --config Debug --parallel && ctest --test-dir build -C Debug --output-on-failure
Try to break it: odd input, repeated actions, bad files. Report: tests added, bugs found.
```
- [ ] **Step 4:** `CLAUDE.md`
```markdown
# Cold Trail
CLI text detective game, C++20/CMake. Spec: docs/superpowers/specs/. Plan: docs/superpowers/plans/.
Layout: src/ engine, tests/ GoogleTest, data/case01.json, docs/case-format.md.
Build/test: cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build --config Debug --parallel && ctest --test-dir build -C Debug --output-on-failure
Team: Lead = main session (delegates, accepts, merges). Subagents in .claude/agents/: game-designer (data/), programmer (src/), qa (tests, bug reports). Stay in your lane.
Rules: no std::format, no C++23; `requires_clue` not `requires`; game text English; one accusation only.
```
- [ ] **Step 5:** Reload agents (`/agents` or restart session), confirm 3 listed. Commit `chore: agent team + CLAUDE.md`, push.

---

### Task 3: Case format doc + case01 (game-designer)

**Files:** Create `docs/case-format.md`, `data/case01.json`

**Produces:** the shipped case; Tasks 7-8 rely on it.

- [ ] **Step 1:** Lead dispatches `game-designer` with: write `docs/case-format.md` (field table + invariants from "Contract: case JSON") and `data/case01.json`.
- [ ] **Step 2:** Case constraints (all checked by Task 8 tests): 5-6 locations, 4-5 people, 8-10 clues; every location reachable from `start`; every clue obtainable by walking/examining/talking; talk-unlock chain depth <= 3; >= 3 required clues; >= 1 red herring clue (not in `required_clues`); `explanation` non-empty and derivable from clue texts.
- [ ] **Step 3:** Validate JSON syntax: `Get-Content data/case01.json -Raw | ConvertFrom-Json | Out-Null` (PowerShell). Expected: no error.
- [ ] **Step 4:** Commit `feat: case01 + format doc`.

---

### Task 4: Case model loader (programmer)

**Files:** Create `src/case_loader.h`, `src/case_loader.cpp`, `tests/test_support.h`, `tests/case_loader_test.cpp`

**Consumes:** `ct::Case` (Task 1).
**Produces:** `Case parse_case(std::string_view)`, `Case load_case(const std::filesystem::path&)` (throw `std::runtime_error`); `tests/test_support.h`: `kMiniCase`, `contains()`, `replace_all()`.

- [ ] **Step 1:** `tests/test_support.h`
```cpp
#pragma once
#include <string>

inline constexpr const char* kMiniCase = R"json({
 "title":"Mini","intro":"A body lies in the hall.","start":"hall",
 "locations":[
  {"id":"hall","name":"Hall","description":"A cold marble hall.","exits":["study"],"items":[]},
  {"id":"study","name":"Study","description":"Papers everywhere.","exits":["hall"],"items":["note"]}],
 "people":[
  {"id":"butler","name":"Mr. Grey","description":"Stiff and pale.","location":"hall","talk":[
    {"text":"I saw nothing."},
    {"text":"Fine, I lied about my alibi.","requires":"c_note","reveals":"c_alibi"}]},
  {"id":"maid","name":"Ann","description":"Nervous.","location":"study","talk":[{"text":"I was asleep."}]}],
 "items":[{"id":"note","name":"torn note","description":"A threat, signed G.","reveals":"c_note"}],
 "clues":[{"id":"c_note","text":"A threatening note signed G."},{"id":"c_alibi","text":"The butler lied about his alibi."}],
 "solution":{"killer":"butler","required_clues":["c_note","c_alibi"],"explanation":"The butler wrote the note and lied."}
})json";

inline bool contains(const std::string& s, const std::string& part) {
    return s.find(part) != std::string::npos;
}

inline std::string replace_all(std::string s, const std::string& from, const std::string& to) {
    for (std::size_t p = 0; (p = s.find(from, p)) != std::string::npos; p += to.size()) s.replace(p, from.size(), to);
    return s;
}
```
- [ ] **Step 2:** `tests/case_loader_test.cpp`
```cpp
#include "case_loader.h"
#include "test_support.h"
#include <gtest/gtest.h>
#include <stdexcept>

using namespace ct;

TEST(CaseLoader, ParsesMiniCase) {
    const Case c = parse_case(kMiniCase);
    EXPECT_EQ(c.title, "Mini");
    EXPECT_EQ(c.locations.size(), 2u);
    EXPECT_EQ(c.people[0].talk[1].requires_clue, "c_note");
    EXPECT_EQ(c.items[0].reveals, "c_note");
    EXPECT_EQ(c.solution.killer, "butler");
}
TEST(CaseLoader, RejectsMalformedJson) { EXPECT_THROW(parse_case("{not json"), std::runtime_error); }
TEST(CaseLoader, RejectsMissingField) { EXPECT_THROW(parse_case(R"({"title":"x"})"), std::runtime_error); }
TEST(CaseLoader, RejectsDanglingStart) {
    EXPECT_THROW(parse_case(replace_all(kMiniCase, "\"start\":\"hall\"", "\"start\":\"nowhere\"")), std::runtime_error);
}
TEST(CaseLoader, RejectsDanglingClueRef) {
    EXPECT_THROW(parse_case(replace_all(kMiniCase, "\"reveals\":\"c_note\"", "\"reveals\":\"c_ghost\"")), std::runtime_error);
}
TEST(CaseLoader, RejectsUnknownKiller) {
    EXPECT_THROW(parse_case(replace_all(kMiniCase, "\"killer\":\"butler\"", "\"killer\":\"ghost\"")), std::runtime_error);
}
TEST(CaseLoader, RejectsDuplicateIds) {
    EXPECT_THROW(parse_case(replace_all(kMiniCase, "\"id\":\"maid\"", "\"id\":\"butler\"")), std::runtime_error);
}
TEST(CaseLoader, MissingFileThrows) { EXPECT_THROW(load_case("no/such/file.json"), std::runtime_error); }
```
- [ ] **Step 3:** Run build/test. Expected: FAIL (compile: `case_loader.h` not found).
- [ ] **Step 4:** `src/case_loader.h`
```cpp
#pragma once
#include "model.h"
#include <filesystem>
#include <string_view>

namespace ct {
Case parse_case(std::string_view json_text);        // throws std::runtime_error
Case load_case(const std::filesystem::path& file);  // throws std::runtime_error
}  // namespace ct
```
`src/case_loader.cpp`
```cpp
#include "case_loader.h"
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <nlohmann/json.hpp>

namespace ct {
namespace {
using nlohmann::json;

std::string str(const json& j, const char* key) { return j.at(key).get<std::string>(); }
std::vector<std::string> strs(const json& j, const char* key) { return j.at(key).get<std::vector<std::string>>(); }
std::optional<std::string> opt(const json& j, const char* key) {
    if (!j.contains(key) || j[key].is_null()) return std::nullopt;
    return j[key].get<std::string>();
}

Case from_json(const json& j) {
    Case c;
    c.title = str(j, "title");
    c.intro = str(j, "intro");
    c.start = str(j, "start");
    for (const auto& l : j.at("locations"))
        c.locations.push_back({str(l, "id"), str(l, "name"), str(l, "description"), strs(l, "exits"), strs(l, "items")});
    for (const auto& p : j.at("people")) {
        Person person{str(p, "id"), str(p, "name"), str(p, "description"), str(p, "location"), {}};
        for (const auto& t : p.at("talk")) person.talk.push_back({str(t, "text"), opt(t, "requires"), opt(t, "reveals")});
        c.people.push_back(std::move(person));
    }
    for (const auto& i : j.at("items"))
        c.items.push_back({str(i, "id"), str(i, "name"), str(i, "description"), opt(i, "reveals")});
    for (const auto& k : j.at("clues")) c.clues.push_back({str(k, "id"), str(k, "text")});
    const auto& s = j.at("solution");
    c.solution = {str(s, "killer"), strs(s, "required_clues"), str(s, "explanation")};
    return c;
}

template <class T>
std::set<std::string> unique_ids(const std::vector<T>& v, const char* kind) {
    std::set<std::string> out;
    for (const auto& x : v)
        if (!out.insert(x.id).second) throw std::runtime_error(std::string("duplicate ") + kind + " id: " + x.id);
    return out;
}

void need(const std::set<std::string>& known, const std::string& id, const std::string& what) {
    if (!known.count(id)) throw std::runtime_error("unknown " + what + ": " + id);
}

void validate(const Case& c) {
    const auto locs = unique_ids(c.locations, "location");
    const auto people = unique_ids(c.people, "person");
    const auto items = unique_ids(c.items, "item");
    const auto clues = unique_ids(c.clues, "clue");
    need(locs, c.start, "start location");
    for (const auto& l : c.locations) {
        for (const auto& e : l.exits) need(locs, e, "exit of " + l.id);
        for (const auto& i : l.items) need(items, i, "item in " + l.id);
    }
    for (const auto& p : c.people) {
        need(locs, p.location, "location of " + p.id);
        for (const auto& ln : p.talk) {
            if (ln.requires_clue) need(clues, *ln.requires_clue, "required clue of " + p.id);
            if (ln.reveals) need(clues, *ln.reveals, "revealed clue of " + p.id);
        }
    }
    for (const auto& i : c.items)
        if (i.reveals) need(clues, *i.reveals, "clue of item " + i.id);
    need(people, c.solution.killer, "killer");
    for (const auto& r : c.solution.required_clues) need(clues, r, "solution clue");
}
}  // namespace

Case parse_case(std::string_view text) {
    try {
        Case c = from_json(json::parse(text));
        validate(c);
        return c;
    } catch (const json::exception& e) {
        throw std::runtime_error(std::string("invalid case file: ") + e.what());
    }
}

Case load_case(const std::filesystem::path& file) {
    std::ifstream in(file);
    if (!in) throw std::runtime_error("cannot open case file: " + file.string());
    std::stringstream ss;
    ss << in.rdbuf();
    return parse_case(ss.str());
}
}  // namespace ct
```
- [ ] **Step 5:** Run build/test. Expected: all PASS.
- [ ] **Step 6:** Commit `feat: case loader with validation`.

---

### Task 5: Command parser (programmer)

**Files:** Create `src/parser.h`, `src/parser.cpp`, `tests/parser_test.cpp`

**Produces:** `enum class CommandType`, `struct Command{type,arg}`, `Command parse_command(std::string_view)`, `std::string normalize(std::string_view)` (trim + lowercase).

- [ ] **Step 1:** `tests/parser_test.cpp`
```cpp
#include "parser.h"
#include <gtest/gtest.h>

using namespace ct;

TEST(Parser, SimpleVerbs) {
    EXPECT_EQ(parse_command("look").type, CommandType::Look);
    EXPECT_EQ(parse_command("clues").type, CommandType::Clues);
    EXPECT_EQ(parse_command("help").type, CommandType::Help);
    EXPECT_EQ(parse_command("quit").type, CommandType::Quit);
}
TEST(Parser, VerbWithArgKeepsArgCase) {
    const Command c = parse_command("accuse Dr. Vale");
    EXPECT_EQ(c.type, CommandType::Accuse);
    EXPECT_EQ(c.arg, "Dr. Vale");
}
TEST(Parser, CaseAndWhitespaceInsensitiveVerb) {
    const Command c = parse_command("  GO   Study \t");
    EXPECT_EQ(c.type, CommandType::Go);
    EXPECT_EQ(c.arg, "Study");
}
TEST(Parser, EmptyAndBlankLines) {
    EXPECT_EQ(parse_command("").type, CommandType::Empty);
    EXPECT_EQ(parse_command("  \t ").type, CommandType::Empty);
}
TEST(Parser, UnknownVerb) { EXPECT_EQ(parse_command("dance wildly").type, CommandType::Unknown); }
TEST(Parser, Normalize) { EXPECT_EQ(normalize("  Mr. GREY "), "mr. grey"); }
```
- [ ] **Step 2:** Run build/test. Expected: FAIL (`parser.h` not found).
- [ ] **Step 3:** `src/parser.h`
```cpp
#pragma once
#include <string>
#include <string_view>

namespace ct {
enum class CommandType { Look, Go, Talk, Examine, Clues, Accuse, Help, Quit, Empty, Unknown };
struct Command {
    CommandType type = CommandType::Unknown;
    std::string arg;
};
Command parse_command(std::string_view line);
std::string normalize(std::string_view text);  // trim + lowercase
}  // namespace ct
```
`src/parser.cpp`
```cpp
#include "parser.h"
#include <algorithm>
#include <cctype>
#include <unordered_map>

namespace ct {
namespace {
std::string trim(std::string_view s) {
    const auto b = s.find_first_not_of(" \t\r\n");
    if (b == std::string_view::npos) return {};
    const auto e = s.find_last_not_of(" \t\r\n");
    return std::string(s.substr(b, e - b + 1));
}
}  // namespace

std::string normalize(std::string_view text) {
    std::string s = trim(text);
    std::ranges::transform(s, s.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return s;
}

Command parse_command(std::string_view line) {
    const std::string t = trim(line);
    if (t.empty()) return {CommandType::Empty, {}};
    const auto sp = t.find_first_of(" \t");
    const std::string verb = normalize(t.substr(0, sp));
    const std::string arg = sp == std::string::npos ? std::string{} : trim(t.substr(sp));
    static const std::unordered_map<std::string, CommandType> verbs = {
        {"look", CommandType::Look},       {"go", CommandType::Go},         {"talk", CommandType::Talk},
        {"examine", CommandType::Examine}, {"clues", CommandType::Clues},   {"accuse", CommandType::Accuse},
        {"help", CommandType::Help},       {"quit", CommandType::Quit}};
    const auto it = verbs.find(verb);
    return {it == verbs.end() ? CommandType::Unknown : it->second, arg};
}
}  // namespace ct
```
- [ ] **Step 4:** Run build/test. Expected: all PASS.
- [ ] **Step 5:** Commit `feat: command parser`.

---

### Task 6: Game engine (programmer)

**Files:** Create `src/game.h`, `src/game.cpp`, `tests/game_test.cpp`

**Consumes:** `ct::Case`, `parse_case` (tests only), `Command`, `parse_command`, `normalize`, `kMiniCase`, `contains`.
**Produces:** `class Game { explicit Game(Case); std::string intro() const; std::string execute(const Command&); bool finished() const; bool won() const; }`

- [ ] **Step 1:** `tests/game_test.cpp`
```cpp
#include "case_loader.h"
#include "game.h"
#include "test_support.h"
#include <gtest/gtest.h>

using namespace ct;

namespace {
std::string run(Game& g, const char* line) { return g.execute(parse_command(line)); }
Game mini() { return Game(parse_case(kMiniCase)); }
void gather_all_evidence(Game& g) {
    run(g, "go study"); run(g, "examine torn note"); run(g, "go hall"); run(g, "talk mr. grey");
}
}  // namespace

TEST(Game, IntroShowsTitleAndStartLocation) {
    auto g = mini();
    const std::string s = g.intro();
    EXPECT_TRUE(contains(s, "Mini"));
    EXPECT_TRUE(contains(s, "Hall"));
}
TEST(Game, LookListsExitsAndPeople) {
    auto g = mini();
    const std::string s = run(g, "look");
    EXPECT_TRUE(contains(s, "Study"));
    EXPECT_TRUE(contains(s, "Mr. Grey"));
}
TEST(Game, GoToExitAndRejectNonExit) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "go   STUDY "), "Papers"));
    EXPECT_TRUE(contains(run(g, "go attic"), "can't go"));
    EXPECT_TRUE(contains(run(g, "go"), "where"));
}
TEST(Game, ExamineRevealsClueOnce) {
    auto g = mini();
    run(g, "go study");
    EXPECT_TRUE(contains(run(g, "examine TORN NOTE"), "[New clue]"));
    EXPECT_FALSE(contains(run(g, "examine torn note"), "[New clue]"));
    EXPECT_TRUE(contains(run(g, "clues"), "threatening note"));
}
TEST(Game, ExamineNeedsItemInCurrentLocation) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "examine torn note"), "nothing like that"));
}
TEST(Game, TalkGatedLineUnlocksAfterClueAndRevealsOnce) {
    auto g = mini();
    const std::string first = run(g, "talk mr. grey");
    EXPECT_TRUE(contains(first, "I saw nothing"));
    EXPECT_FALSE(contains(first, "lied"));
    run(g, "go study"); run(g, "examine torn note"); run(g, "go hall");
    const std::string second = run(g, "talk Mr. Grey");
    EXPECT_TRUE(contains(second, "lied about my alibi"));
    EXPECT_TRUE(contains(second, "[New clue]"));
    EXPECT_FALSE(contains(run(g, "talk mr. grey"), "[New clue]"));
}
TEST(Game, TalkToPersonElsewhereFails) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "talk ann"), "nobody"));
}
TEST(Game, CluesEmptyAtStart) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "clues"), "no clues"));
}
TEST(Game, AccuseKillerWithEvidenceWins) {
    auto g = mini();
    gather_all_evidence(g);
    EXPECT_TRUE(contains(run(g, "ACCUSE MR. GREY"), "CASE CLOSED"));
    EXPECT_TRUE(g.finished());
    EXPECT_TRUE(g.won());
}
TEST(Game, AccuseKillerWithoutEvidenceLoses) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "accuse butler"), "GAME OVER"));
    EXPECT_TRUE(g.finished());
    EXPECT_FALSE(g.won());
}
TEST(Game, AccuseWrongPersonLoses) {
    auto g = mini();
    gather_all_evidence(g);
    EXPECT_TRUE(contains(run(g, "accuse ann"), "GAME OVER"));
    EXPECT_FALSE(g.won());
}
TEST(Game, AccuseUnknownOrEmptyIsNotFatal) {
    auto g = mini();
    run(g, "accuse zorro");
    run(g, "accuse");
    EXPECT_FALSE(g.finished());
}
TEST(Game, CommandsAfterGameOverAreRefused) {
    auto g = mini();
    run(g, "accuse ann");
    EXPECT_TRUE(contains(run(g, "look"), "closed"));
}
TEST(Game, UnknownAndEmptyCommands) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "dance"), "Unknown command"));
    EXPECT_EQ(run(g, ""), "");
    EXPECT_EQ(run(g, "   "), "");
    EXPECT_FALSE(g.finished());
}
TEST(Game, HelpListsCommands) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "help"), "accuse"));
}
```
- [ ] **Step 2:** Run build/test. Expected: FAIL (`game.h` not found).
- [ ] **Step 3:** `src/game.h`
```cpp
#pragma once
#include "model.h"
#include "parser.h"
#include <string>
#include <vector>

namespace ct {
class Game {
public:
    explicit Game(Case c);
    std::string intro() const;
    std::string execute(const Command& cmd);  // reply text; "" for empty input
    bool finished() const { return state_ != State::Playing; }
    bool won() const { return state_ == State::Won; }

private:
    enum class State { Playing, Won, Lost };
    std::string look() const;
    std::string go(const std::string& arg);
    std::string talk(const std::string& arg);
    std::string examine(const std::string& arg);
    std::string clues() const;
    std::string accuse(const std::string& arg);
    static std::string help();
    bool has(const std::string& clue_id) const;
    bool learn(const std::string& clue_id);  // true if new
    const Location& here() const;

    Case case_;
    std::string location_;
    std::vector<std::string> found_;
    State state_ = State::Playing;
};
}  // namespace ct
```
`src/game.cpp`
```cpp
#include "game.h"
#include <algorithm>
#include <sstream>

namespace ct {
namespace {
template <class T>
const T* by_id(const std::vector<T>& v, const std::string& id) {
    for (const auto& x : v)
        if (x.id == id) return &x;
    return nullptr;
}
template <class T>
const T* by_arg(const std::vector<T>& v, const std::string& arg) {
    const std::string key = normalize(arg);
    if (key.empty()) return nullptr;
    for (const auto& x : v)
        if (normalize(x.id) == key || normalize(x.name) == key) return &x;
    return nullptr;
}
std::string join(const std::vector<std::string>& v) {
    std::string out;
    for (std::size_t i = 0; i < v.size(); ++i) out += (i ? ", " : "") + v[i];
    return out;
}
}  // namespace

Game::Game(Case c) : case_(std::move(c)), location_(case_.start) {}

const Location& Game::here() const { return *by_id(case_.locations, location_); }

bool Game::has(const std::string& id) const { return std::ranges::find(found_, id) != found_.end(); }

bool Game::learn(const std::string& id) {
    if (has(id)) return false;
    found_.push_back(id);
    return true;
}

std::string Game::intro() const { return case_.title + "\n\n" + case_.intro + "\n\n" + look(); }

std::string Game::execute(const Command& cmd) {
    if (finished()) return "The case is closed. Type 'quit' to leave.";
    switch (cmd.type) {
        case CommandType::Look: return look();
        case CommandType::Go: return go(cmd.arg);
        case CommandType::Talk: return talk(cmd.arg);
        case CommandType::Examine: return examine(cmd.arg);
        case CommandType::Clues: return clues();
        case CommandType::Accuse: return accuse(cmd.arg);
        case CommandType::Help: return help();
        case CommandType::Quit:
        case CommandType::Empty: return "";
        case CommandType::Unknown: return "Unknown command. Type 'help'.";
    }
    return "";
}

std::string Game::look() const {
    const Location& loc = here();
    std::ostringstream o;
    o << "== " << loc.name << " ==\n" << loc.description << "\n";
    std::vector<std::string> names;
    for (const auto& id : loc.exits) names.push_back(by_id(case_.locations, id)->name);
    o << "Exits: " << join(names) << "\n";
    names.clear();
    for (const auto& id : loc.items) names.push_back(by_id(case_.items, id)->name);
    if (!names.empty()) o << "Items: " << join(names) << "\n";
    names.clear();
    for (const auto& p : case_.people)
        if (p.location == loc.id) names.push_back(p.name);
    if (!names.empty()) o << "People: " << join(names) << "\n";
    return o.str();
}

std::string Game::go(const std::string& arg) {
    if (arg.empty()) return "Go where?";
    for (const auto& id : here().exits) {
        const Location* dest = by_id(case_.locations, id);
        if (normalize(dest->name) == normalize(arg) || normalize(id) == normalize(arg)) {
            location_ = id;
            return look();
        }
    }
    return "You can't go there from here.";
}

std::string Game::talk(const std::string& arg) {
    if (arg.empty()) return "Talk to whom?";
    const Person* p = by_arg(case_.people, arg);
    if (!p || p->location != location_) return "There is nobody like that here.";
    std::ostringstream o;
    o << p->name << ":\n";
    for (const auto& ln : p->talk) {
        if (ln.requires_clue && !has(*ln.requires_clue)) continue;
        o << "  \"" << ln.text << "\"\n";
        if (ln.reveals && learn(*ln.reveals)) o << "  [New clue] " << by_id(case_.clues, *ln.reveals)->text << "\n";
    }
    return o.str();
}

std::string Game::examine(const std::string& arg) {
    if (arg.empty()) return "Examine what?";
    const Item* it = by_arg(case_.items, arg);
    const auto& local = here().items;
    if (!it || std::ranges::find(local, it->id) == local.end()) return "You see nothing like that here.";
    std::string out = it->description + "\n";
    if (it->reveals && learn(*it->reveals)) out += "[New clue] " + by_id(case_.clues, *it->reveals)->text + "\n";
    return out;
}

std::string Game::clues() const {
    if (found_.empty()) return "You have no clues yet.";
    std::string out = "Clues:\n";
    for (const auto& id : found_) out += "  - " + by_id(case_.clues, id)->text + "\n";
    return out;
}

std::string Game::accuse(const std::string& arg) {
    if (arg.empty()) return "Accuse whom?";
    const Person* p = by_arg(case_.people, arg);
    if (!p) return "Nobody by that name is part of this case.";
    const Solution& s = case_.solution;
    const bool evidence = std::ranges::all_of(s.required_clues, [this](const std::string& c) { return has(c); });
    if (p->id == s.killer && evidence) {
        state_ = State::Won;
        return "You name " + p->name + ". The evidence holds. CASE CLOSED.\n" + s.explanation;
    }
    state_ = State::Lost;
    if (p->id == s.killer) return "You name " + p->name + ", but you lack the evidence. The killer walks free. GAME OVER.";
    return "You accuse " + p->name + ". Wrong. The killer escapes. GAME OVER.";
}

std::string Game::help() {
    return "Commands: look, go <place>, talk <person>, examine <item>, clues, accuse <person>, help, quit.\n"
           "You get ONE accusation. Choose wisely.";
}
}  // namespace ct
```
- [ ] **Step 4:** Run build/test. Expected: all PASS.
- [ ] **Step 5:** Commit `feat: game engine`.

---

### Task 7: CLI main loop (programmer)

**Files:** Modify `src/main.cpp`

**Consumes:** `load_case`, `Game`, `parse_command`, `COLD_TRAIL_DATA_DIR`.

- [ ] **Step 1:** Replace `src/main.cpp`
```cpp
#include "case_loader.h"
#include "game.h"
#include <filesystem>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    const std::filesystem::path file =
        argc > 1 ? std::filesystem::path(argv[1]) : std::filesystem::path(COLD_TRAIL_DATA_DIR) / "case01.json";
    try {
        ct::Game game(ct::load_case(file));
        std::cout << game.intro() << "\n";
        std::string line;
        while (!game.finished()) {
            std::cout << "> " << std::flush;
            if (!std::getline(std::cin, line)) break;  // EOF
            const ct::Command cmd = ct::parse_command(line);
            if (cmd.type == ct::CommandType::Quit) break;
            const std::string reply = game.execute(cmd);
            if (!reply.empty()) std::cout << reply << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
```
- [ ] **Step 2:** Build. Run (PowerShell; exe path is `build/Debug/detective.exe` on MSVC, `build/detective` otherwise):
  - `"look`nhelp`nquit" | .\build\detective.exe` -> intro, help text, exit code 0.
  - `.\build\detective.exe < NUL` -> exits cleanly, code 0 (EOF).
  - `.\build\detective.exe missing.json` -> `error: cannot open case file...`, code 1.
- [ ] **Step 3:** Commit `feat: CLI main loop`, push.

---

### Task 8: Solvability + playthrough tests (qa)

**Files:** Create `tests/solvability_test.cpp`, `tests/playthrough_test.cpp`

**Consumes:** `data/case01.json` (Task 3), `Game` (Task 6), `load_case`.

- [ ] **Step 1:** `tests/solvability_test.cpp`
```cpp
#include "case_loader.h"
#include "test_support.h"
#include <gtest/gtest.h>
#include <filesystem>
#include <queue>
#include <set>

using namespace ct;

namespace {
Case real_case() { return load_case(std::filesystem::path(COLD_TRAIL_DATA_DIR) / "case01.json"); }

std::set<std::string> reachable_locations(const Case& c) {
    std::set<std::string> seen{c.start};
    std::queue<std::string> q;
    q.push(c.start);
    while (!q.empty()) {
        const std::string id = q.front();
        q.pop();
        for (const auto& l : c.locations)
            if (l.id == id)
                for (const auto& e : l.exits)
                    if (seen.insert(e).second) q.push(e);
    }
    return seen;
}

// Clues a player can collect by walking, examining and talking (fixed point over talk gates).
std::set<std::string> reachable_clues(const Case& c) {
    const auto locs = reachable_locations(c);
    std::set<std::string> clues;
    for (bool changed = true; changed;) {
        changed = false;
        for (const auto& l : c.locations) {
            if (!locs.count(l.id)) continue;
            for (const auto& iid : l.items)
                for (const auto& it : c.items)
                    if (it.id == iid && it.reveals) changed |= clues.insert(*it.reveals).second;
        }
        for (const auto& p : c.people) {
            if (!locs.count(p.location)) continue;
            for (const auto& ln : p.talk) {
                if (ln.requires_clue && !clues.count(*ln.requires_clue)) continue;
                if (ln.reveals) changed |= clues.insert(*ln.reveals).second;
            }
        }
    }
    return clues;
}
}  // namespace

TEST(Solvability, ValidatorWorksOnMiniCase) {
    const auto clues = reachable_clues(parse_case(kMiniCase));
    EXPECT_EQ(clues, (std::set<std::string>{"c_note", "c_alibi"}));
}
TEST(Solvability, ValidatorDetectsUnreachableClue) {
    // gate the alibi line on a clue nobody can reveal -> c_alibi unreachable
    Case c = parse_case(kMiniCase);
    c.clues.push_back({"c_ghost", "never found"});
    c.people[0].talk[1].requires_clue = "c_ghost";
    EXPECT_FALSE(reachable_clues(c).count("c_alibi"));
}
TEST(Solvability, Case01SizeBudget) {
    const Case c = real_case();
    EXPECT_GE(c.locations.size(), 5u); EXPECT_LE(c.locations.size(), 6u);
    EXPECT_GE(c.people.size(), 4u);    EXPECT_LE(c.people.size(), 5u);
    EXPECT_GE(c.clues.size(), 8u);     EXPECT_LE(c.clues.size(), 10u);
}
TEST(Solvability, Case01AllLocationsReachable) {
    const Case c = real_case();
    EXPECT_EQ(reachable_locations(c).size(), c.locations.size());
}
TEST(Solvability, Case01EveryClueObtainable) {
    const Case c = real_case();
    const auto got = reachable_clues(c);
    for (const auto& k : c.clues) EXPECT_TRUE(got.count(k.id)) << "unobtainable clue: " << k.id;
}
TEST(Solvability, Case01RequiredCluesAreEnoughAndRedHerringExists) {
    const Case c = real_case();
    EXPECT_GE(c.solution.required_clues.size(), 3u);
    EXPECT_LT(c.solution.required_clues.size(), c.clues.size());  // >= 1 red herring
    EXPECT_FALSE(c.solution.explanation.empty());
}
```
- [ ] **Step 2:** `tests/playthrough_test.cpp`
```cpp
#include "case_loader.h"
#include "game.h"
#include "test_support.h"
#include <gtest/gtest.h>
#include <algorithm>
#include <filesystem>
#include <map>
#include <queue>

using namespace ct;

namespace {
Case real_case() { return load_case(std::filesystem::path(COLD_TRAIL_DATA_DIR) / "case01.json"); }

template <class T>
std::string name_of(const std::vector<T>& v, const std::string& id) {
    return std::ranges::find_if(v, [&](const T& x) { return x.id == id; })->name;
}

// Shortest route of location ids from `from` to `to` (excluding `from`).
std::vector<std::string> route(const Case& c, const std::string& from, const std::string& to) {
    std::map<std::string, std::string> parent{{from, from}};
    std::queue<std::string> q;
    q.push(from);
    while (!q.empty()) {
        const std::string cur = q.front();
        q.pop();
        if (cur == to) break;
        for (const auto& l : c.locations)
            if (l.id == cur)
                for (const auto& e : l.exits)
                    if (parent.emplace(e, cur).second) q.push(e);
    }
    std::vector<std::string> path;
    for (std::string at = to; at != from; at = parent.at(at)) path.push_back(at);
    std::reverse(path.begin(), path.end());
    return path;
}
}  // namespace

TEST(Playthrough, BotSolvesCase01) {
    const Case c = real_case();
    Game g(c);
    std::string at = c.start;
    for (int round = 0; round < 5; ++round)  // repeated so talk-unlocks propagate
        for (const auto& loc : c.locations) {
            for (const auto& step : route(c, at, loc.id))
                ASSERT_FALSE(contains(g.execute({CommandType::Go, name_of(c.locations, step)}), "can't go"));
            at = loc.id;
            for (const auto& item : loc.items) g.execute({CommandType::Examine, name_of(c.items, item)});
            for (const auto& p : c.people)
                if (p.location == loc.id) g.execute({CommandType::Talk, p.name});
        }
    const std::string reply = g.execute({CommandType::Accuse, name_of(c.people, c.solution.killer)});
    EXPECT_TRUE(contains(reply, "CASE CLOSED")) << reply;
    EXPECT_TRUE(g.won());
}

TEST(Playthrough, AccusingKillerImmediatelyLoses) {
    const Case c = real_case();
    Game g(c);
    g.execute({CommandType::Accuse, name_of(c.people, c.solution.killer)});
    EXPECT_TRUE(g.finished());
    EXPECT_FALSE(g.won());
}
```
- [ ] **Step 3:** Run build/test. Expected: all PASS. A failure = bug in `data/` or `src/` -> qa reports to Lead with repro; do NOT fix in place.
- [ ] **Step 4:** qa exploratory pass: odd input via the exe (very long line, `go` with tabs, binary junk, corrupt JSON via `argv[1]`). Report findings; add a test per confirmed bug (red first), Lead routes fix to owner.
- [ ] **Step 5:** Commit `test: solvability + playthrough`.

---

### Task 9: README, final check, merge (Lead)

**Files:** Create `README.md`

- [ ] **Step 1:** `README.md`: what the game is, commands list, build (`cmake` cmd from Global Constraints), run (`build/detective [case.json]`), CLion note (open folder -> CMake auto-loads, run config `detective`), team roles table.
- [ ] **Step 2:** Full local build/test. Expected: all PASS. Play case01 manually once to sanity-check feel/text.
- [ ] **Step 3:** Commit `docs: README`, push. `gh pr ready`; `gh pr checks --watch`. Expected: 3 platforms green.
- [ ] **Step 4:** Ask user before merging PR to `main`.

---

## Unresolved questions
1. Accuse killer without enough clues: plan = lose (one chance). Or soft "need more evidence" non-fatal?
2. Programmer writes its own unit tests in `tests/` (deviates from spec table, where qa owns `tests/`). OK?
3. Local cmake + compiler on PATH? Else use CLion's bundled toolchain.
4. Merge PR to `main` yourself, or may Lead merge after green CI?
5. Private repo: macOS Actions minutes cost 10x (free tier 2000 min/month). Fine, or make repo public?
