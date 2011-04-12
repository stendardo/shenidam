/*
    Copyright 2010 Nabil Stendardo <nabil@stendardo.org>

    This file is part of Shenidam.

    Shenidam is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) version 2 of the same License.

    Shenidam is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Shenidam.  If not, see <http://www.gnu.org/licenses/>.

 */

#ifndef SHENIDAM_H_
#define SHENIDAM_H_

#include <complex.h>
#include <fftw3.h>
#include <samplerate.h>


#ifdef __cplusplus
extern "C" {
#endif

/**
 * Audio position determiner.
 */
typedef void* shenidam_t;
/**
 * The LPCM buffer formats.
 */
enum SHENIDAM_FORMAT{
	FORMAT_BYTE, //signed char
	FORMAT_SHORT, //short
	FORMAT_INT, //int
	FORMAT_LONG, //long
	FORMAT_LONG_LONG, //long long
	FORMAT_SINGLE, //float
	FORMAT_DOUBLE //double
};
enum SHENIDAM_ERROR_CODES
{
	SUCCESS = 0, //No error, the command returned successfully
	INVALID_ARGUMENT = 1,
	ALREADY_SET_BASE_SIGNAL = 2,
	BASE_SIGNAL_NOT_SET = 3,
	NULL_OBJECT = 4,
	ALLOCATION_ERROR = 100,
};
/**
 * Creates a handle to an empty audio position determiner. It should be destroyed with shedinam_destroy.
 * The base sample rate is the sample rate which will be used for processing.
 * 
 * @param base_sample_rate the sample rate in which to do the processing.
 * @param num_threads the number of threads in which to do the processing.
 * @return an empty shenidam object.
 */
shenidam_t shenidam_create(double base_sample_rate,int num_threads);

/**
 * Sets the resampling quality of the shenidam object
 * 
 * @param shenidam_obj the shenidam object.
 * @param src_converter the libsamplerate converter to use (taken from samplerate.h)
 * @return SUCCESS or error code.
 */
int shenidam_set_resampling_quality(shenidam_t res,int src_converter);
/**
 * Sets the 1-channel "base" audio track (with a certain format, sample (LPCM) buffer, number of samples and sample rate), on which positions will be calculated.
 * 
 * @param shenidam_obj the shenidam object.
 * @param format the (raw) format the samples are in.
 * @param samples the base samples in the specified format.
 * @param num_samples the number of samples.
 * @param sample_rate the base sample rate.
 * @return SUCCESS or error code.
 */
int shenidam_set_base_audio(shenidam_t shenidam_obj,int format, void* samples,size_t num_samples,double sample_rate);

/**
 * Sets the 1-channel "track" (with a certain format, sample (LPCM) buffer, number of samples and sample rate) of which we calculate the start position (in_point) and actual duration in n terms of samples (length).
 * 
 * @param shenidam_obj the shenidam object.
 * @param input_format the (raw) format the samples are in.
 * @param samples the track samples in the specified format.
 * @param num_samples the number of samples.
 * @param sample_rate the base sample rate.
 * @param in_point the sample index of the base in which the audio starts (can be negative).
 * @param length the length of the matching portion of the base.
 * @return SUCCESS, or error code.
 */
int shenidam_get_audio_range(shenidam_t shenidam_obj,int input_format,void* samples,size_t num_samples,double sample_rate,int* in_point,size_t* length);
/**
 * Destroy the audio position determiner.
 * 
 * @param shenidam_obj the shenidam object.
 * @return SUCCESS, or error code.
 */
int shenidam_destroy(shenidam_t);
/**
 * Get the error message associated to any non-zero return code.
 * 
 * @param error the error code.
 * @return an error message.
 * 
 */
const char* shenidam_get_error_message(int error);

#ifdef __cplusplus
}
#endif



#endif /* SHENIDAM_H_ */
