cmake_minimum_required(VERSION 2.6)
project(ShenidamAudioMapper)

set(SHENIDAM_VERSION "0.2.0")
set(SHENIDAM_PYTHON_PATH "lib/shenidam/python")


find_package(PythonInterp)

include_directories ("${PROJECT_SOURCE_DIR}/include")
add_library(shenidam SHARED shenidam.c)
add_executable(shenidam_exec shenidam.c shenidam_main.cpp)
target_link_libraries(shenidam_exec boost_random fftw3f samplerate sndfile m)
configure_file("${PROJECT_SOURCE_DIR}/config.h.in" "${PROJECT_BINARY_DIR}/config.h")
include_directories("${PROJECT_BINARY_DIR}")#for config.h


if(WIN32)
    if(MINGW)
        SET(CMAKE_C_FLAGS "-std=c99")
    endif(MINGW)
    SET(SHENIDAM_PYTHON_DIR_REL "lib/")
    SET(SHENIDAM_PYTHON_DIR "${CMAKE_INSTALL_PREFIX}/${SHENIDAM_PYTHON_DIR_REL}")
    set_target_properties(shenidam_exec PROPERTIES OUTPUT_NAME "shenidam.exe")
    SET(SHENIDAM_BINDIR_REL "./")
    SET(SHENIDAM_INCDIR_REL "include/")
    SET(SHENIDAM_INCDIR_REL "lib/")
else()
    SET(SHENIDAM_BINDIR_REL "bin/")
    SET(SHENIDAM_INCDIR_REL "include/")
    SET(SHENIDAM_LIBDIR_REL "lib/")
    SET(CMAKE_C_FLAGS "-std=c99")
    SET(SHENIDAM_PYTHON_DIR_REL "lib/shenidam/python/")
    SET(SHENIDAM_PYTHON_DIR "${CMAKE_INSTALL_PREFIX}/${SHENIDAM_PYTHON_DIR_REL}")

    configure_file("${PROJECT_SOURCE_DIR}/shenidam-av.in" "${PROJECT_BINARY_DIR}/shenidam-av")
    configure_file("${PROJECT_SOURCE_DIR}/qshenidam.in" "${PROJECT_BINARY_DIR}/qshenidam")
    install (FILES "${PROJECT_BINARY_DIR}/shenidam-av" DESTINATION ${SHENIDAM_BINDIR_REL} PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    install (FILES "${PROJECT_BINARY_DIR}/qshenidam" DESTINATION ${SHENIDAM_BINDIR_REL} PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    set_target_properties(shenidam_exec PROPERTIES OUTPUT_NAME "shenidam")
    
endif(WIN32)










install (TARGETS shenidam_exec DESTINATION ${SHENIDAM_BINDIR_REL})
install (TARGETS shenidam DESTINATION ${SHENIDAM_LIBDIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/shenidam.h" DESTINATION ${SHENIDAM_INCDIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/shenidam.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/shenidam-av.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/qshenidam.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})



set(ARCHIVE_NAME shenidam-${SHENIDAM_VERSION})
add_custom_target(dist
    COMMAND git archive --prefix=${ARCHIVE_NAME}/ HEAD
        | bzip2 > ${CMAKE_BINARY_DIR}/${ARCHIVE_NAME}.tar.bz2
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR})
    
# uninstall target
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake_uninstall.cmake.in" "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake" IMMEDIATE @ONLY)

add_custom_target(uninstall
    COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake)

