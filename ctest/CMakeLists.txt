cmake_minimum_required(VERSION 3.6)

project(mydocker)

set(TEST_DIR ${PROJECT_SOURCE_DIR})
set(SRC_DIR  ${PROJECT_SOURCE_DIR})
set(THIRD_PARTY_DIR third_party)

set(CMAKE_CXX_STANDARD 11)

add_executable(ns_test ${TEST_DIR}/ns_test.cc)
add_executable(mount_test ${TEST_DIR}/mount_test.cc)
# add_executable(mydocker ${SRC_FILES})