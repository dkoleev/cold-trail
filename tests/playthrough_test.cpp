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

TEST(Playthrough, AccusingKillerImmediatelyIsSoftRefusal) {
    const Case c = real_case();
    Game g(c);
    EXPECT_TRUE(contains(g.execute({CommandType::Accuse, name_of(c.people, c.solution.killer)}), "more evidence"));
    EXPECT_FALSE(g.finished());
}

TEST(Playthrough, AccusingInnocentImmediatelyLoses) {
    const Case c = real_case();
    Game g(c);
    const auto innocent = std::ranges::find_if(c.people, [&](const Person& p) { return p.id != c.solution.killer; });
    g.execute({CommandType::Accuse, innocent->name});
    EXPECT_TRUE(g.finished());
    EXPECT_FALSE(g.won());
}
