cmake_minimum_required(VERSION 2.8.12) 

# A typical CMake file for a Fortran program will look like this:
#
#  FIND_PACKAGE(MultiNest)
#  INCLUDE_DIRECTORIES(${MultiNest_INCLUDE_DIRS} ${MultiNest_MOD_DIRS})
#  ADD_EXECUTABLE(program file1 ... fileN)
#  TARGET_LINK_LIBRARIES(program ${MultiNest_LIBRARIES})
#
# As MultiNest is built in the parent directory, we simply include the
# the modules from there, and link using the defined library.

include_directories(${CMAKE_CURRENT_BINARY_DIR}/../)

FILE(GLOB SOURCE *.f90)
add_executable(obj_detect ${SOURCE})
target_link_libraries(obj_detect ${MultiNest_LIBRARIES})

# Set install directory
INSTALL(TARGETS obj_detect DESTINATION bin)
