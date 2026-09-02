// test_compile.cpp - Simple test file for compilation workflow
// This file tests that the exact verification workflow can compile C++ code

#include <cstdint>

// Simple function to test compilation
int32_t test_function(int32_t x, int32_t y) {
    if (x > y) {
        return x - y;
    } else {
        return y - x;
    }
}

// Another function with branches
bool test_branches(int32_t value) {
    if (value == 0) {
        return false;
    } else if (value > 0) {
        return true;
    } else {
        return false;
    }
}
