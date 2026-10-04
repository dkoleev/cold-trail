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
