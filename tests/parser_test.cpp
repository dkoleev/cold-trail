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
