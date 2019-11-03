cmake_minimum_required(VERSION 3.6)

project(mydocker)

set(TEST_DIR test)
set(SRC_DIR  src)
set(THIRD_PARTY_DIR third_party)

set(CMAKE_CXX_STANDARD 11)

aux_source_directory(${SRC_DIR} SRC_FILES)

add_executable(ns_test ${TEST_DIR}/ns_test.cc)

# add_executable(mydocker ${SRC_FILES})