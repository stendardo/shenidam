cmake_minimum_required(VERSION 2.6)
project(ShenidamAudioMapper)
add_custom_target(dist COMMAND ${CMAKE_MAKE_PROGRAM} package_source)

SET(CMAKE_C_FLAGS "-std=c99")

include_directories ("${PROJECT_SOURCE_DIR}/include")
add_library(shenidam SHARED shenidam.c)
add_executable(shenidam_exec shenidam.c shenidam_main.cpp)
TARGET_LINK_LIBRARIES(shenidam_exec boost_random fftw3f samplerate sndfile m)
set_target_properties(shenidam_exec PROPERTIES OUTPUT_NAME "shenidam")

install (TARGETS shenidam_exec DESTINATION bin)
install (TARGETS shenidam DESTINATION lib)
install (FILES "${PROJECT_SOURCE_DIR}/shenidam.h" DESTINATION include)
install (FILES "${PROJECT_SOURCE_DIR}/shenidam-av.py" DESTINATION bin PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)



set(PROJECT_VERSION "0.1.1")
set(ARCHIVE_NAME shenidam-${PROJECT_VERSION})
add_custom_target(dist
    COMMAND git archive --prefix=${ARCHIVE_NAME}/ HEAD
        | bzip2 > ${CMAKE_BINARY_DIR}/${ARCHIVE_NAME}.tar.bz2
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
