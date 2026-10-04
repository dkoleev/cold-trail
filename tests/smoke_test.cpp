#include "model.h"
#include <gtest/gtest.h>

TEST(Smoke, ModelDefaultConstructs) {
    ct::Case c;
    EXPECT_TRUE(c.locations.empty());
}
