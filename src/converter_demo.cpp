#include "converter/mapping.hpp"

#include <iostream>

int main()
{
    converter::MappingEngine engine(converter::default_profile());

    converter::InputSnapshot input;
    input.keys.insert("W");
    input.keys.insert("D");
    input.keys.insert("Space");
    input.mouse_delta = {.x = 24, .y = -8};

    const auto state = engine.update(input, 1.0f / 60.0f);
    std::cout << converter::describe(state) << '\n';
    return 0;
}

