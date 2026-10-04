#pragma once
#include "model.h"
#include <filesystem>
#include <string_view>

namespace ct {
Case parse_case(std::string_view json_text);        // throws std::runtime_error
Case load_case(const std::filesystem::path& file);  // throws std::runtime_error
}  // namespace ct
