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
TEST(Solvability, Case01HasEnoughRequiredCluesAndARedHerring) {
    const Case c = real_case();
    EXPECT_GE(c.solution.required_clues.size(), 3u);
    EXPECT_LT(c.solution.required_clues.size(), c.clues.size());  // >= 1 red herring
    EXPECT_FALSE(c.solution.explanation.empty());
}
