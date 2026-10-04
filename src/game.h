#pragma once
#include "model.h"
#include "parser.h"
#include <string>
#include <vector>

namespace ct {
class Game {
public:
    explicit Game(Case c);
    std::string intro() const;
    std::string execute(const Command& cmd);  // reply text; "" for empty input
    bool finished() const { return state_ != State::Playing; }
    bool won() const { return state_ == State::Won; }

private:
    enum class State { Playing, Won, Lost };
    std::string look() const;
    std::string go(const std::string& arg);
    std::string talk(const std::string& arg);
    std::string examine(const std::string& arg);
    std::string clues() const;
    std::string accuse(const std::string& arg);
    static std::string help();
    bool has(const std::string& clue_id) const;
    bool learn(const std::string& clue_id);  // true if new
    const Location& here() const;

    Case case_;
    std::string location_;
    std::vector<std::string> found_;
    State state_ = State::Playing;
};
}  // namespace ct
