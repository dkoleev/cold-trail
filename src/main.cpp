#include "case_loader.h"
#include "game.h"
#include <filesystem>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    const std::filesystem::path file =
        argc > 1 ? std::filesystem::path(argv[1]) : std::filesystem::path(COLD_TRAIL_DATA_DIR) / "case01.json";
    try {
        ct::Game game(ct::load_case(file));
        std::cout << game.intro() << "\n";
        std::string line;
        while (!game.finished()) {
            std::cout << "> " << std::flush;
            if (!std::getline(std::cin, line)) break;  // EOF
            const ct::Command cmd = ct::parse_command(line);
            if (cmd.type == ct::CommandType::Quit) break;
            const std::string reply = game.execute(cmd);
            if (!reply.empty()) std::cout << reply << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
