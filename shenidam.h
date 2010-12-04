/*
 * shenidam.h
 *
 *  Created on: Oct 25, 2010
 *      Author: nabil
 */

#ifndef SHENIDAM_H_
#define SHENIDAM_H_

#include <complex.h>
#include <fftw3.h>


#ifdef __cplusplus
extern "C" {
#endif

/**
 * Audio position determiner.
 */
typedef void* shenidam_t;
/**
 * Frequential filter, taking Fourier coefficients, their size, and extra parameters.
 */
typedef void (*frequential_filter_cb)(fftwf_complex* frequencies,size_t size,void* data);
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
	ALLOCATION_ERROR = 100,
};
/**
 * Creates a handle to an empty audio position determiner. It should be destroyed with shedinam_destroy.
 * The base sample rate is the sample rate which will be used.
 */
shenidam_t shenidam_create(double base_sample_rate,int num_threads);
/**
 * Adds a filter which is applied to the Fourier transforms of both the track and the base.
 */
int shenidam_add_frequential_filter(shenidam_t shenidam,frequential_filter_cb callback,void* data);
/**
 * Sets the 1-channel "base" audio track (with a certain format, sample (LPCM) buffer, number of samples and sample rate), on which positions will be calculated.
 */
int shenidam_set_base_audio(shenidam_t res,int format, void* samples,size_t num_samples,double sample_rate);
/**
 * Sets the 1-channel "track" (with a certain format, sample (LPCM) buffer, number of samples and sample rate) of which we calculate the start position (in_point) and actual duration in n terms of samples (length).
 */
int shenidam_get_audio_range(shenidam_t shenidam_obj,int input_format,void* samples,size_t num_samples,double sample_rate,int* in_point,size_t* length);
/**
 * Destroy the audio position determiner.
 */
int shenidam_destroy(shenidam_t);
/**
 * Get the error message associated to any non-zero return code.
 */
const char* shenidam_get_error_message(int error);

#ifdef __cplusplus
}
#endif



#endif /* SHENIDAM_H_ */
