cmake_minimum_required(VERSION 2.6)
project(ShenidamAudioMapper)

set(SHENIDAM_VERSION "0.4.9")
set(SHENIDAM_PYTHON_PATH "lib/shenidam/python")

set(EXTRA_LIBS )

option (ENABLE_OPENMP  "Use OpenMP for parallel processing if available (potential small speedup on SMP machines)" OFF) 
option (ENABLE_FFTW_THREADING "Use FFTW threading support if available (potential significant speedup on SMP machines)" ON) 



INCLUDE (CheckLibraryExists) 

if(ENABLE_OPENMP)
    find_package(OpenMP)
    set(SHENIDAM_PARALLEL_OMP ${OPENMP_FOUND})
    if (OPENMP_FOUND)
        CHECK_LIBRARY_EXISTS(gomp omp_get_num_threads "" HAVE_GOMP)
        if(HAVE_GOMP)
            set(EXTRA_LIBS ${EXTRA_LIBS} gomp)
        endif(HAVE_GOMP)
        set(CMAKE_C_FLAGS ${CMAKE_C_FLAGS} ${OPENMP_C_FLAGS})
        set(CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS} ${OPENMP_CXX_FLAGS})
    endif(OPENMP_FOUND)
endif()

CHECK_LIBRARY_EXISTS(fftw3f fftwf_plan_dft_r2c_1d "" HAVE_FFTWF)
if (NOT HAVE_FFTWF)
    message(SEND_ERROR "No single-precision fftw3 available")
endif()

CHECK_LIBRARY_EXISTS(sndfile sf_open "" HAVE_SNDFILE)
if (NOT HAVE_SNDFILE)
    message(SEND_ERROR "No sndfile library available.")
endif()

CHECK_LIBRARY_EXISTS(samplerate src_simple "" HAVE_SRC)
if (NOT HAVE_SRC)
    message(SEND_ERROR "No libsamplerate library available.")
endif()

CHECK_LIBRARY_EXISTS(boost_thread _init "" HAVE_BOOST_THREAD)
if (NOT HAVE_BOOST_THREAD)
    message(SEND_ERROR "No boost-thread library available.")
endif()

CHECK_LIBRARY_EXISTS(boost_random _init "" HAVE_BOOST_RANDOM)
if (NOT HAVE_BOOST_RANDOM)
    message(SEND_ERROR "No boost-random library available.")
endif()


if(ENABLE_FFTW_THREADING)

    CHECK_LIBRARY_EXISTS(fftw3f fftwf_init_threads "" HAVE_COMBINED_FFTWF_THREADS)
    set(CMAKE_REQUIRED_LIBRARIES )
    if(HAVE_COMBINED_FFTWF_THREADS)
        set(SHENIDAM_FFT_THREADED ${HAVE_COMBINED_FFTWF_THREADS})
    else()
        set(CMAKE_REQUIRED_LIBRARIES fftw3f)
        CHECK_LIBRARY_EXISTS(fftw3f_threads fftwf_init_threads "" SHENIDAM_FFT_THREADED)
        set(CMAKE_REQUIRED_LIBRARIES )
        if (SHENIDAM_FFT_THREADED)
            set(EXTRA_LIBS ${EXTRA_LIBS} fftw3f_threads)
        endif()
    endif()
endif()

if(SHENIDAM_FFT_THREADED OR SHENIDAM_PARALLEL_OMP)
    set(CMAKE_THREAD_PREFER_PTHREADS 1)
    find_package(Threads)
    set(CMAKE_EXE_LINKER_FLAGS ${CMAKE_EXE_LINKER_FLAGS} ${CMAKE_THREAD_LIBS_INIT}) 
endif()

include_directories ("${PROJECT_SOURCE_DIR}/include")
add_library(shenidam SHARED shenidam.c)
add_executable(shenidam_exec shenidam.c shenidam_main.cpp)
target_link_libraries(shenidam_exec boost_random boost_thread fftw3f samplerate sndfile m ${EXTRA_LIBS})
configure_file("${PROJECT_SOURCE_DIR}/config.h.in" "${PROJECT_BINARY_DIR}/config.h")
include_directories("${PROJECT_BINARY_DIR}")#for config.h

if(WIN32)
    if(MINGW)
        SET(CMAKE_C_FLAGS "-std=c99 ${CMAKE_C_FLAGS}")
    endif(MINGW)
    SET(SHENIDAM_PYTHON_DIR_REL "lib/shenidam/python")
    SET(SHENIDAM_PYTHON_DIR "${CMAKE_INSTALL_PREFIX}/${SHENIDAM_PYTHON_DIR_REL}")
    set_target_properties(shenidam_exec PROPERTIES OUTPUT_NAME "shenidam.exe")
    SET(SHENIDAM_BINDIR_REL "bin/")
    SET(SHENIDAM_INCDIR_REL "include/")
    SET(SHENIDAM_INCDIR_REL "lib/")
else()
    find_package(PythonInterp)
    SET(SHENIDAM_BINDIR_REL "bin/")
    SET(SHENIDAM_INCDIR_REL "include/")
    SET(SHENIDAM_LIBDIR_REL "lib/")
    SET(CMAKE_C_FLAGS "-std=c99 ${CMAKE_C_FLAGS}")
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

