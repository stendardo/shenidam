# - Find Samplerate
# Find the native Samplerate includes and library
#
#  Samplerate_INCLUDES    - where to find samplerate.h
#  Samplerate_LIBRARIES   - List of libraries when using Samplerate.
#  Samplerate_FOUND       - True if Samplerate is found.

if (Samplerate_INCLUDES)
  # Already in cache, be silent
  set (Samplerate_FIND_QUIETLY TRUE)
endif (Samplerate_INCLUDES)

find_path (Samplerate_INCLUDES samplerate.h)

find_library (Samplerate_LIBRARIES NAMES samplerate)

# handle the QUIETLY and REQUIRED arguments and set Samplerate_FOUND to TRUE if
# all listed variables are TRUE
include (FindPackageHandleStandardArgs)
find_package_handle_standard_args (Samplerate DEFAULT_MSG Samplerate_LIBRARIES Samplerate_INCLUDES)

mark_as_advanced (Samplerate_LIBRARIES Samplerate_INCLUDES)