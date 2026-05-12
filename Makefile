CXX ?= g++
CXXFLAGS ?= -std=c++20 -Wall -Wextra -Wpedantic -O2 -Iinclude

BUILD_DIR := build
CORE_SRC := src/converter/mapping.cpp
TEST_SRC := tests/mapping_tests.cpp
DEMO_SRC := src/converter_demo.cpp

.PHONY: all test demo gui run-gui exe clean

all: test demo

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

test: $(BUILD_DIR)/mapping_tests
	./$(BUILD_DIR)/mapping_tests

demo: $(BUILD_DIR)/converter_demo

gui:
	python3 gui/converter_gui.py --self-test

run-gui:
	python3 gui/converter_gui.py

exe:
	cmd.exe /c build_exe.bat

$(BUILD_DIR)/mapping_tests: $(CORE_SRC) $(TEST_SRC) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(CORE_SRC) $(TEST_SRC) -o $@

$(BUILD_DIR)/converter_demo: $(CORE_SRC) $(DEMO_SRC) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(CORE_SRC) $(DEMO_SRC) -o $@

clean:
	rm -rf $(BUILD_DIR)
