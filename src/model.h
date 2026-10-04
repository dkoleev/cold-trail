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
