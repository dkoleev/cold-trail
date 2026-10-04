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
