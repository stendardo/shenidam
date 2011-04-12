cmake_minimum_required(VERSION 2.6)
project(ShenidamAudioMapper)

set(SHENIDAM_VERSION "0.5.0")
set(SHENIDAM_PYTHON_PATH "lib/shenidam/python")

set(EXTRA_LIBS )

option (ENABLE_OPENMP  "Use OpenMP for parallel processing if available (potential extra-small speedup on SMP machines - experimental)" OFF) 
option (ENABLE_FFTW_THREADING "Use FFTW threading support if available (potential significant speedup on SMP machines)" ON) 
option (WITH_BOOST_THREAD "Use boost::thread if available to determine total number of CPUs (effective only when ENABLE_FFTW_THREADING is available)" ON) 
option (ENABLE_TEST_MODE "Enables test mode (requires boost::random)" ON) 

INCLUDE (OptimizeForArchitecture.cmake)
OptimizeForArchitecture()
INCLUDE (CheckLibraryExists) 
INCLUDE (CheckIncludeFileCXX)
INCLUDE (CheckCXXSourceCompiles)

MACRO(CONVERT_DATA_TO_PYTHON_FILE TARGET_NAME SOURCE_FILE DEST_FILE DEPENDS)
ADD_CUSTOM_COMMAND(
	OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${DEST_FILE}
	COMMAND mkdir -p `dirname ${CMAKE_CURRENT_BINARY_DIR}/${DEST_FILE}` && echo __data__ = \\'`base64 ${PROJECT_SOURCE_DIR}/${SOURCE_FILE}`\\' > ${CMAKE_CURRENT_BINARY_DIR}/${DEST_FILE}
	DEPENDS ${PROJECT_SOURCE_DIR}/${SOURCE_FILE} ${DEPENDS}
)
add_custom_target(${TARGET_NAME} ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${DEST_FILE})
ENDMACRO()

CONVERT_DATA_TO_PYTHON_FILE(python_icon icons/qshenidam_256.png pack/qshenidam_icon.py "")

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
    else()
        message(WARNING "No OpenMP available for compiler.")
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

if (WITH_BOOST_THREAD)
    CHECK_LIBRARY_EXISTS(boost_thread _init "" HAVE_BOOST_THREAD)
    CHECK_INCLUDE_FILE_CXX( "boost/thread.hpp" HAVE_BOOST_THREAD_H)


    if (HAVE_BOOST_THREAD_H AND HAVE_BOOST_THREAD)
        set (SHENIDAM_HAVE_BOOST_THREAD 1)
        set (EXTRA_LIBS ${EXTRA_LIBS} boost_thread)
    else()
        if (NOT HAVE_BOOST_THREAD_H)
            message(WARNING "No boost::thread headers available.")
        endif()
        if (NOT HAVE_BOOST_THREAD)
            message(WARNING "No boost::thread library available.")
        endif()
    endif()

endif()
if (ENABLE_TEST_MODE)
    CHECK_CXX_SOURCE_COMPILES( "#include \"boost/random.hpp\"
boost::mt19937 gen;
int main(int argc, char** argv)
{
	boost::normal_distribution<> dist(0, 1);
	boost::variate_generator<boost::mt19937&, boost::normal_distribution<> > die(gen, dist);
	die();
	return 0;
}

" DOESNT_NEED_BOOST_RANDOM_LIB)
    if (NOT DOESNT_NEED_BOOST_RANDOM_LIB)
    	CHECK_LIBRARY_EXISTS(boost_random _init "" HAVE_BOOST_RANDOM)
    endif()
    CHECK_INCLUDE_FILE_CXX("boost/random.hpp" HAVE_BOOST_RANDOM_H)
    if (HAVE_BOOST_RANDOM_H AND (HAVE_BOOST_RANDOM OR DOESNT_NEED_BOOST_RANDOM_LIB))
        set (SHENIDAM_ENABLE_TEST_MODE 1)
	if (NOT DOESNT_NEED_BOOST_RANDOM_LIB)
	        set (EXTRA_LIBS ${EXTRA_LIBS} boost_random)
	endif()
    else()
        if (NOT HAVE_BOOST_RANDOM_H)
            message(WARNING "No boost::random headers available.")
        endif()
        if (NOT HAVE_BOOST_RANDOM)
            message(WARNING "No boost::random library available.")
        endif()
    endif()
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
target_link_libraries(shenidam_exec fftw3f samplerate sndfile m ${EXTRA_LIBS})
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
    SET(SHENIDAM_DATADIR_REL "share/shenidam/")
    SET(SHENIDAM_PYTHON_DIR "${CMAKE_INSTALL_PREFIX}/${SHENIDAM_PYTHON_DIR_REL}")

    configure_file("${PROJECT_SOURCE_DIR}/shenidam-av.in" "${PROJECT_BINARY_DIR}/shenidam-av")
    configure_file("${PROJECT_SOURCE_DIR}/qshenidam.in" "${PROJECT_BINARY_DIR}/qshenidam")
    configure_file("${PROJECT_SOURCE_DIR}/qshenidam.desktop.in" "${PROJECT_BINARY_DIR}/qshenidam.desktop")
    
    install (FILES "${PROJECT_BINARY_DIR}/shenidam-av" DESTINATION ${SHENIDAM_BINDIR_REL} PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    install (FILES "${PROJECT_BINARY_DIR}/qshenidam" DESTINATION ${SHENIDAM_BINDIR_REL} PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    set_target_properties(shenidam_exec PROPERTIES OUTPUT_NAME "shenidam")
    install (FILES "${PROJECT_SOURCE_DIR}/icons/qshenidam.svg" "${PROJECT_SOURCE_DIR}/icons/qshenidam_256.png" DESTINATION ${SHENIDAM_DATADIR_REL}/icons)
    install (FILES "${PROJECT_BINARY_DIR}/qshenidam.desktop" DESTINATION /usr/share/applications)
    
endif(WIN32)


install (TARGETS shenidam_exec DESTINATION ${SHENIDAM_BINDIR_REL})
install (TARGETS shenidam DESTINATION ${SHENIDAM_LIBDIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/shenidam.h" DESTINATION ${SHENIDAM_INCDIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/shenidam.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/shenidam-av.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
install (FILES "${PROJECT_SOURCE_DIR}/qshenidam.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})
install (FILES "${PROJECT_BINARY_DIR}/pack/qshenidam_icon.py" DESTINATION ${SHENIDAM_PYTHON_DIR_REL})


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

