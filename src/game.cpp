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

std::string Game::intro() const { return case_.title + "\n\n" + case_.intro + "\n\n" + look() + "\nType 'help' for commands."; }

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
    if (normalize(here().name) == normalize(arg) || normalize(here().id) == normalize(arg))
        return "You are already in " + here().name + ".";
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
    o << p->name << " - " << p->description << "\n";
    bool spoke = false;
    for (const auto& ln : p->talk) {
        if (ln.requires_clue && !has(*ln.requires_clue)) continue;
        spoke = true;
        o << "  \"" << ln.text << "\"\n";
        if (ln.reveals && learn(*ln.reveals)) o << "  [New clue] " << by_id(case_.clues, *ln.reveals)->text << "\n";
    }
    if (!spoke) o << p->name << " has nothing to say.\n";
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
    if (p->id == s.killer) return "You suspect " + p->name + ", but you need more evidence before you can accuse.";
    state_ = State::Lost;
    return "You accuse " + p->name + ". Wrong. The killer escapes. GAME OVER.";
}

std::string Game::help() {
    return "Commands: look, go <place>, talk <person>, examine <item>, clues, accuse <person>, help, quit.\n"
           "You get ONE accusation. Choose wisely.";
}
}  // namespace ct
