cmake_minimum_required(VERSION 2.6)
project(ShenidamAudioMapper)
SET(CMAKE_C_FLAGS "-std=c99")

include_directories ("${PROJECT_SOURCE_DIR}/include")
add_library(shenidam SHARED shenidam.c)
add_executable(shenidam_exec shenidam.c shenidam_main.cpp)
TARGET_LINK_LIBRARIES(shenidam_exec boost_random fftw3f samplerate sndfile m)
set_target_properties(shenidam_exec PROPERTIES OUTPUT_NAME "shenidam")

install (TARGETS shenidam_exec DESTINATION bin)
install (TARGETS shenidam DESTINATION lib)
install (FILES "${PROJECT_SOURCE_DIR}/shenidam.h" DESTINATION include)
install (FILES "${PROJECT_SOURCE_DIR}/shenidam-av.py" DESTINATION bin PERMISSIONS WORLD_READ WORLD_EXECUTE)
