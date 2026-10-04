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
TEST(Game, AccuseKillerWithoutEvidenceIsSoftRefusal) {
    auto g = mini();
    EXPECT_TRUE(contains(run(g, "accuse butler"), "more evidence"));
    EXPECT_FALSE(g.finished());
    run(g, "go study"); run(g, "examine torn note"); run(g, "go hall"); run(g, "talk mr. grey");
    EXPECT_TRUE(contains(run(g, "accuse butler"), "CASE CLOSED"));
    EXPECT_TRUE(g.won());
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
