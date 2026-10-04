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
