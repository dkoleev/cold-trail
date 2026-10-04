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
