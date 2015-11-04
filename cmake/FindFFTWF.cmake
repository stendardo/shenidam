# - Find FFTWF
# Find the native FFTWF includes and library
#
#  FFTWF_INCLUDES    - where to find fftw3.h
#  FFTWF_LIBRARIES   - List of libraries when using FFTWF.
#  FFTWF_THREADS_LIBRARY  - List of extra libraries when using FFTWF with threads.
#  FFTWF_THREADS_FOUND  - True if we are using threads.
#  FFTWF_FOUND       - True if FFTWF is found.
INCLUDE (CheckLibraryExists) 
if (FFTWF_INCLUDES)
  # Already in cache, be silent
  set (FFTWF_FIND_QUIETLY TRUE)
endif()

find_path (FFTWF_INCLUDES fftw3.h)

find_library (FFTWF_LIBRARY NAMES fftw3f)



include (FindPackageHandleStandardArgs)
if(FFTWF_FIND_COMPONENTS)
  foreach(component ${FFTWF_FIND_COMPONENTS})
  	if (component STREQUAL threads)
  		set(FFTWF_THREADS_REQUESTED TRUE)
  		CHECK_LIBRARY_EXISTS(fftw3f fftwf_init_threads "" FFTWF_HAVE_COMBINED_THREADS)
		if(FFTWF_HAVE_COMBINED_THREADS) #libfftwf already has thread support built in
			set(FFTWF_THREADS_FOUND,TRUE)
			set(FFTWF_THREADS_LIBRARY )
		else()
			find_library (FFTWF_THREADS_LIBRARY NAMES fftw3f_threads)
			
		endif()
  	endif()
  endforeach()
endif()

if (FFTWF_THREADS_REQUESTED AND NOT FFTWF_HAVE_COMBINED_THREADS)
	set(FFTWF_LIBRARIES ${FFTWF_LIBRARY} ${FFTWF_THREADS_LIBRARY})
	find_package_handle_standard_args (FFTWF_THREADS DEFAULT_MSG FFTWF_THREADS_LIBRARY)		
	
else()
	set(FFTWF_LIBRARIES ${FFTWF_LIBRARY})
endif()



find_package_handle_standard_args (FFTWF DEFAULT_MSG FFTWF_LIBRARY FFTWF_INCLUDES)
# handle the QUIETLY and REQUIRED arguments and set FFTWF_FOUND to TRUE if
# all listed variables are TRUE



mark_as_advanced (FFTWF_LIBRARIES FFTWF_INCLUDES FFTWF_HAVE_COMBINED_THREADS FFTWF_THREADS_LIBRARY)