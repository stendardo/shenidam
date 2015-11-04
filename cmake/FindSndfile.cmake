# - Find Sndfile
# Find the native Sndfile includes and library
#
#  Sndfile_INCLUDES    - where to find sndfile.h
#  Sndfile_LIBRARIES   - List of libraries when using Sndfile.
#  Sndfile_FOUND       - True if Sndfile is found.

if (Sndfile_INCLUDES)
  # Already in cache, be silent
  set (Sndfile_FIND_QUIETLY TRUE)
endif (Sndfile_INCLUDES)

find_path (Sndfile_INCLUDES sndfile.h)

find_library (Sndfile_LIBRARIES NAMES sndfile)

# handle the QUIETLY and REQUIRED arguments and set Sndfile_FOUND to TRUE if
# all listed variables are TRUE
include (FindPackageHandleStandardArgs)
find_package_handle_standard_args (Sndfile DEFAULT_MSG Sndfile_LIBRARIES Sndfile_INCLUDES)

mark_as_advanced (Sndfile_LIBRARIES Sndfile_INCLUDES)