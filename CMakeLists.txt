cmake_minimum_required(VERSION 2.8)
project(ShenidamAudioMapper)


set(SHENIDAM_VERSION "1.0")



IF(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
   SET(CMAKE_BUILD_TYPE RelWithDebInfo)
ENDIF()

# Select flags.
SET(CMAKE_CXX_FLAGS "-Wall")
SET(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g -fprefetch-loop-arrays -funroll-loops")
SET(CMAKE_CXX_FLAGS_RELEASE "-O2 -funroll-loops -fprefetch-loop-arrays")
SET(CMAKE_CXX_FLAGS_DEBUG  "-O0 -g")
SET(CMAKE_CXX_FLAGS "-std=c++11")


set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")
INCLUDE (OptimizeForArchitecture)
OptimizeForArchitecture()
MACRO(CONVERT_DATA_TO_PYTHON_FILE TARGET_NAME SOURCE_FILE DEST_FILE DEPENDS)

add_custom_target(${TARGET_NAME} ALL DEPENDS ${CMAKE_BINARY_DIR}/${DEST_FILE})
ENDMACRO()

option (ENABLE_FFTW_THREADING "Use FFTW threading support (potential significant speedup on SMP machines)" ON) 
option (ENABLE_TEST_MODE "Enables test mode (requires boost::random)" ON) 
option (WITH_SHENIDAM_AV "Create the command-line client shenidam-av (requires Python 2.7 at runtime)" ON) 
option (WITH_QSHENIDAM "Create the graphical client qshenidam (requires PyQT at runtime)" ON) 


if (ENABLE_FFTW_THREADING)
    find_package(FFTWF REQUIRED COMPONENTS threads)
    set(CMAKE_THREAD_PREFER_PTHREADS 1)
    find_package(Threads)
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${CMAKE_THREAD_LIBS_INIT}") 
    set(SHENIDAM_FFT_THREADED TRUE)
else()
    find_package(FFTWF REQUIRED)
endif()
find_package(Sndfile REQUIRED)
find_package(Samplerate REQUIRED)
if (ENABLE_TEST_MODE)
    find_package(Boost 1.36.0 REQUIRED COMPONENTS random)
    set(SHENIDAM_ENABLE_TEST_MODE TRUE)
endif()


include_directories ("${CMAKE_SOURCE_DIR}/include")
add_library(shenidam SHARED src/shenidam.c)
add_executable(shenidam_exec src/shenidam.c src/shenidam_main.cpp)
target_link_libraries(shenidam ${FFTWF_LIBRARIES} ${Samplerate_LIBRARIES} m )

if (ENABLE_TEST_MODE)
    target_link_libraries(shenidam_exec ${FFTWF_LIBRARIES} ${Samplerate_LIBRARIES} ${Sndfile_LIBRARIES} ${Boost_LIBRARIES} m)
else()
    target_link_libraries(shenidam_exec ${FFTWF_LIBRARIES} ${Samplerate_LIBRARIES} ${Sndfile_LIBRARIES} m)
endif()
configure_file("${CMAKE_SOURCE_DIR}/templates/config.h.in" "${CMAKE_BINARY_DIR}/config.h")
include_directories("${CMAKE_BINARY_DIR}")#for config.h

SET(SHENIDAM_BINDIR_REL "bin/")
SET(SHENIDAM_INCDIR_REL "include/")
SET(SHENIDAM_LIBDIR_REL "lib/")
SET(CMAKE_C_FLAGS "-std=c99 ${CMAKE_C_FLAGS}")

set_target_properties(shenidam_exec PROPERTIES OUTPUT_NAME "shenidam")
install (TARGETS shenidam_exec DESTINATION ${SHENIDAM_BINDIR_REL})
install (TARGETS shenidam DESTINATION ${SHENIDAM_LIBDIR_REL})
install (FILES "${CMAKE_SOURCE_DIR}/include/shenidam.h" DESTINATION ${SHENIDAM_INCDIR_REL})

if (WITH_SHENIDAM_AV OR WITH_QSHENIDAM)
    SET(SHENIDAM_PYTHON_DIR_REL "lib/shenidam/python/")
    find_package(PythonInterp)
    install (FILES "${CMAKE_SOURCE_DIR}/python/shenidam.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
    
    if (WITH_SHENIDAM_AV)
        configure_file("${CMAKE_SOURCE_DIR}/templates/shenidam-av.in" "${CMAKE_BINARY_DIR}/shenidam-av")
        SET(SHENIDAM_PYTHON_DIR "${CMAKE_INSTALL_PREFIX}/${SHENIDAM_PYTHON_DIR_REL}")
        install (FILES "${CMAKE_SOURCE_DIR}/python/shenidam_av.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
        install (PROGRAMS "${CMAKE_BINARY_DIR}/shenidam-av" DESTINATION ${SHENIDAM_BINDIR_REL})
    endif()
    if (WITH_QSHENIDAM)
        ADD_CUSTOM_COMMAND(
            OUTPUT ${CMAKE_BINARY_DIR}/qshenidam_icon.py
            COMMAND echo __data__ = \\'`base64 ${CMAKE_SOURCE_DIR}/icons/qshenidam_256.png`\\' > ${CMAKE_BINARY_DIR}/qshenidam_icon.py
            DEPENDS ${CMAKE_SOURCE_DIR}/icons/qshenidam_256.png
        )
        add_custom_target(qshenidam_icon ALL 
              DEPENDS ${CMAKE_BINARY_DIR}/qshenidam_icon.py)
        
        
        SET(SHENIDAM_DATADIR_REL "share/shenidam/")
        configure_file("${CMAKE_SOURCE_DIR}/templates/qshenidam.in" "${CMAKE_BINARY_DIR}/qshenidam")
        configure_file("${CMAKE_SOURCE_DIR}/templates/qshenidam.desktop.in" "${CMAKE_BINARY_DIR}/qshenidam.desktop")
        install (PROGRAMS "${CMAKE_BINARY_DIR}/qshenidam" DESTINATION ${SHENIDAM_BINDIR_REL})
        install (FILES "${CMAKE_SOURCE_DIR}/icons/qshenidam.svg" "${CMAKE_SOURCE_DIR}/icons/qshenidam_256.png" DESTINATION ${SHENIDAM_DATADIR_REL}/icons)
        install (FILES "${CMAKE_BINARY_DIR}/qshenidam.desktop" DESTINATION /usr/share/applications)
        install (FILES "${CMAKE_SOURCE_DIR}/python/qshenidam.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
        install (FILES "${CMAKE_BINARY_DIR}/qshenidam_icon.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
    endif()
endif()


set(ARCHIVE_NAME shenidam-${SHENIDAM_VERSION})
add_custom_target(dist
    COMMAND git archive --prefix=${ARCHIVE_NAME}/ HEAD
        | bzip2 > ${CMAKE_BINARY_DIR}/${ARCHIVE_NAME}.tar.bz2
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
    
#uninstall target
configure_file(
    "${CMAKE_SOURCE_DIR}/templates/cmake_uninstall.cmake.in" "${CMAKE_BINARY_DIR}/cmake_uninstall.cmake" IMMEDIATE @ONLY)
add_custom_target(uninstall
    COMMAND ${CMAKE_COMMAND} -P ${CMAKE_BINARY_DIR}/cmake_uninstall.cmake)

