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

#include <complex.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "shenidam.h"
#include "fftw3.h"
#include "float.h"
#include "samplerate.h"
#include "setjmp.h"
#include "config.h"
#ifdef SHENIDAM_PARALLEL_OMP
#include "omp.h"
#endif

typedef float sample_d;
typedef fftwf_complex sample_f;
typedef fftwf_plan FFT_PLAN;
#define FFT_FORWARD fftwf_plan_dft_r2c_1d
#define FFT_BACKWARD fftwf_plan_dft_c2r_1d
#define FFT_MALLOC fftwf_malloc
#define FFT_FREE fftwf_free
#define FFT_EXECUTE fftwf_execute
#define FFT_DESTROY_PLAN fftwf_destroy_plan



typedef struct
{
	double base_sample_rate;
	double base_real_sample_rate;
	sample_d* base;
	size_t base_num_samples;
	int num_threads;
	int src_converter;
} shenidam_t_impl ;




const char* shenidam_get_error_message(int error)
{
	switch(error)
	{
	case(INVALID_ARGUMENT):
		return "Invalid argument";
	case(ALREADY_SET_BASE_SIGNAL):
		return "Base signal already set";
	case(BASE_SIGNAL_NOT_SET):
		return "Base signal not set";
	case (NULL_OBJECT):
		return "NULL shenidam object";
	case(ALLOCATION_ERROR):
		return "Could not allocate memory";
	}
	return "Unknown error";
}

jmp_buf jb;


int initialized_module = 0;

static void* fft_ehmalloc(size_t size)
{
	void* res = FFT_MALLOC(size);
	if (res == NULL)
	{
		longjmp(jb,0);
	}
	return res;
}
static void* ehmalloc(size_t size)
{
	void* res = malloc(size);
	if (res == NULL)
	{
		longjmp(jb,0);
	}
	return res;
}
static void ehfree(void* pointer)
{
	free(pointer);
}
static void fft_ehfree(void* pointer)
{
	FFT_FREE(pointer);
}
static void normalize(sample_d* samples,size_t num_samples_d)
{
	double mean = 0;
	double var = 0;
	#pragma omp parallel for reduction(+:mean) reduction(+:var)
	for(size_t i = 0; i < num_samples_d; i++)
	{
		mean += samples[i];
		var += samples[i]*samples[i];
	}
	mean /= num_samples_d;;
	var = sqrt(var-mean*mean);
	if (var == 0)
	{
	    #pragma omp parallel for
		for(size_t i = 0; i < num_samples_d; i++)
		{
			samples[i]=(samples[i]-mean);
		}
	}
	else
	{
	    #pragma omp parallel for
		for(size_t i = 0; i < num_samples_d; i++)
		{
			samples[i]=(samples[i]-mean)/var;
		}
	}
}
static sample_f* fft(sample_d* samples_d,size_t num_samples_d,int num_threads)
{

	size_t num_samples_f = num_samples_d/2 + 1;
	sample_f* samples_f = ehmalloc(sizeof(sample_f)*num_samples_f);
	sample_d* buffer_d = FFT_MALLOC(sizeof(sample_d)*num_samples_d);
	sample_f* buffer_f = FFT_MALLOC(sizeof(sample_f)*num_samples_f);
#ifdef SHENIDAM_FFT_THREADED
    if (num_threads)
    {
        fftwf_plan_with_nthreads(num_threads);
    }
#endif
	FFT_PLAN plan = FFT_FORWARD(num_samples_d,buffer_d,buffer_f,FFTW_ESTIMATE);
	memcpy(buffer_d,samples_d,sizeof(sample_d)*num_samples_d);
	FFT_EXECUTE(plan);
	FFT_DESTROY_PLAN(plan);
	memcpy(samples_f,buffer_f,sizeof(sample_f)*num_samples_f);

	fft_ehfree(buffer_d);
	fft_ehfree(buffer_f);
	return samples_f;
}

static sample_d* ifft(sample_f* samples_f,size_t num_samples_d,int num_threads)
{

	size_t num_samples_f = num_samples_d/2 + 1;
	sample_d* samples_d = ehmalloc(sizeof(sample_d)*num_samples_d);
	sample_d* buffer_d = fft_ehmalloc(sizeof(sample_d)*num_samples_d);
	sample_f* buffer_f = fft_ehmalloc(sizeof(sample_f)*num_samples_f);
#ifdef SHENIDAM_FFT_THREADED
    if (num_threads)
    {
        fftwf_plan_with_nthreads(num_threads);
    }
#endif
	FFT_PLAN plan = FFT_BACKWARD(num_samples_d,buffer_f,buffer_d,FFTW_ESTIMATE);
	memcpy(buffer_f,samples_f,sizeof(sample_f)*num_samples_f);
	FFT_EXECUTE(plan);
	FFT_DESTROY_PLAN(plan);
	memcpy(samples_d,buffer_d,sizeof(sample_d)*num_samples_d);

	fft_ehfree(buffer_d);
	fft_ehfree(buffer_f);
	return samples_d;
}

static sample_d* resize(sample_d* samples_in, size_t num_samples_in,size_t num_samples_out)
{
	sample_d* res = (sample_d*)ehmalloc(sizeof(sample_d)*num_samples_out);
	memset(res,0,sizeof(sample_d)*num_samples_out);
	int min_num_samples = num_samples_out< num_samples_in?num_samples_out:num_samples_in;
	memcpy(res,samples_in,min_num_samples*sizeof(sample_d));
	return res;
}

static sample_f* resize_f(sample_f* samples_in, size_t num_samples_in,size_t num_samples_out)
{
	sample_f* res = (sample_f*)ehmalloc(sizeof(sample_f)*num_samples_out);
	memset(res,0,sizeof(sample_d)*num_samples_out);
	int min_num_samples = num_samples_out< num_samples_in?num_samples_out:num_samples_in;
	memcpy(res,samples_in,min_num_samples*sizeof(sample_f));
	return res;
}

typedef union
{
	signed char* byte_ptr;
	short* short_ptr;
	int* int_ptr;
	long* long_ptr;
	long long* long_long_ptr;
	double* double_ptr;
} polymorph_ptr;

static int convert_to_samples(int format,void* samples_in,size_t num_samples,sample_d** samples_out)
{
	*samples_out = (sample_d*) ehmalloc(sizeof(sample_d)*num_samples);
	sample_d* s_out = *samples_out;
    if (format == FORMAT_SINGLE)
    {
        memcpy(s_out,samples_in,sizeof(sample_d)*num_samples);
        return 0;
    }
	#define PROCESS_TYPE_F(tid,type,mem) case(tid): cur.mem = (type*)samples_in; for(size_t i = 0; i < num_samples;i++){s_out[i]=(sample_d)(*cur.mem++);}break;
	polymorph_ptr cur;
	switch (format)
	{
		PROCESS_TYPE_F(FORMAT_BYTE,signed char,byte_ptr)
		PROCESS_TYPE_F(FORMAT_SHORT,short,short_ptr)
		PROCESS_TYPE_F(FORMAT_INT,int,int_ptr)
		PROCESS_TYPE_F(FORMAT_LONG,long,long_ptr)
		PROCESS_TYPE_F(FORMAT_LONG_LONG,long long,long_long_ptr)
		PROCESS_TYPE_F(FORMAT_DOUBLE,double,double_ptr)
	default:
		free(s_out);
		return 1;
	}
	return 0;
}

static sample_d* resample(sample_d* samples_in,size_t num_samples_in,double sample_rate_ratio, size_t *num_samples_out, int num_threads, int src_converter)
{
	SRC_DATA src_data;
	src_data.data_in = samples_in;
	src_data.data_out = ehmalloc(*num_samples_out*sizeof(sample_d));
	src_data.input_frames = num_samples_in;
	src_data.output_frames = *num_samples_out;
	src_data.src_ratio = sample_rate_ratio;
	src_simple(&src_data,src_converter,1);
	*num_samples_out = src_data.output_frames_gen;
	return src_data.data_out;
}
static size_t get_common_size(size_t minimal_size)
{
	size_t res = 1;
	while(res < minimal_size)
	{
		res<<=1;
	}
	return res;
}

shenidam_t shenidam_create(double base_sample_rate,int num_threads)
{
    if (num_threads <= 1)
	{
	    num_threads = 1;
	}
	if (!initialized_module)
	{
        #ifdef SHENIDAM_FFT_THREADED
            fftwf_init_threads();
        #endif
		//Add shenidam initialization code here-
		initialized_module = 1;
	}
	
	if (setjmp(jb))
	{
		return NULL;
	}
	shenidam_t_impl* res = (shenidam_t_impl*)malloc(sizeof(shenidam_t_impl));
	res->base = NULL;
	res->base_sample_rate = base_sample_rate;
	res->num_threads = num_threads;
	res->src_converter = SRC_SINC_FASTEST;
	return res;
}
int shenidam_set_resampling_quality(shenidam_t shenidam_obj,int src_converter)
{
	if (shenidam_obj == NULL)
	{
		return NULL_OBJECT;
	}
	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);
	if (src_converter < 0 || src_converter > 4)
	{
		return INVALID_ARGUMENT;
	}
	impl->src_converter = src_converter;
}
int shenidam_set_base_audio(shenidam_t shenidam_obj,int format, void* samples,size_t num_samples,double sample_rate)
{
	if (shenidam_obj == NULL)
	{
		return NULL_OBJECT;
	}
	if (setjmp(jb))
	{
		return ALLOCATION_ERROR;
	}
	sample_d* base,*temp;
	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);
	if (impl->base!=NULL)
	{
		return ALREADY_SET_BASE_SIGNAL;
	}
	if (convert_to_samples(format, samples, num_samples,&base))
	{
		return INVALID_ARGUMENT;
	}
	normalize(base,num_samples);
	size_t num_samples_new = (size_t)round(num_samples * impl->base_sample_rate/sample_rate);
	temp = resample(base,num_samples,impl->base_sample_rate/sample_rate,&num_samples_new,impl->num_threads,impl->src_converter);
	base = temp;
	impl->base_num_samples = num_samples_new;

	impl->base = base;
	impl->base_real_sample_rate = sample_rate;

	return SUCCESS;
}

int shenidam_get_audio_range(shenidam_t shenidam_obj,int input_format,void* samples,size_t num_samples,double sample_rate,int* in_point,size_t* length)
{
	if (shenidam_obj == NULL)
	{
		return NULL_OBJECT;
	}
	if (setjmp(jb))
	{
		return ALLOCATION_ERROR;
	}
	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);

	if (impl->base == NULL)
	{
		return BASE_SIGNAL_NOT_SET;
	}
	if (sample_rate <= 0)
	{
		return INVALID_ARGUMENT;
	}
	if (num_samples == 0)
	{
		return INVALID_ARGUMENT;
	}
	sample_d* track;
	sample_d* base;
	sample_d* temp_d;
	sample_d* convolved;
	sample_f* track_f;
	sample_f* base_f;
	base = impl->base;
	if (convert_to_samples(input_format, samples, num_samples,&track))
	{
		return INVALID_ARGUMENT;
	}
	normalize(track,num_samples);
	double sample_rate_ratio = impl->base_sample_rate/sample_rate;
	if (sample_rate_ratio != 1)
	{
		size_t num_samples_temp = (size_t)ceil(num_samples*sample_rate_ratio);
		temp_d = resample(track,num_samples,sample_rate_ratio,&num_samples_temp,impl->num_threads,impl->src_converter);
		free(track);
		track = temp_d;
		num_samples = num_samples_temp;

	}
	*length = num_samples;
	size_t common_size = get_common_size(num_samples + impl->base_num_samples);
	size_t common_size_f = common_size / 2 + 1;
	temp_d = resize(track,num_samples,common_size);
	ehfree(track);
	track = temp_d;
	temp_d = resize(base,impl->base_num_samples,common_size);
	if (base != impl->base)
	{
		ehfree(base);
	}
	base = temp_d;

	track_f = fft(track,common_size,impl->num_threads);
	ehfree(track);
	base_f = fft(base,common_size,impl->num_threads);
	ehfree(base);
	#pragma omp parallel for
	for (size_t i = 0; i < common_size_f;i++)
	{
		track_f[i]=conjf(track_f[i])*base_f[i];
	}
	ehfree(base_f);
	convolved = ifft(track_f,common_size,impl->num_threads);
	ehfree(track_f);
	sample_d maxv = -DBL_MAX;
	int in = 0;
	for(size_t i = 0; i < common_size;i++)
	{
		double temp = convolved[i];
		if (temp > maxv)
		{
			maxv = temp;
			in = i;
		}
	}
	if (in > common_size-num_samples/2)
	{
		in -= common_size;
	}
	*in_point = round(in*impl->base_real_sample_rate/impl->base_sample_rate);
	*length = round(*length*impl->base_real_sample_rate/impl->base_sample_rate);
	ehfree(convolved);
	return SUCCESS;
}

int shenidam_destroy(shenidam_t shenidam_obj)
{
	if (shenidam_obj == NULL)
	{
		return NULL_OBJECT;
	}
	if (setjmp(jb))
	{
		return ALLOCATION_ERROR;
	}
	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);
	ehfree(impl->base);
	ehfree(impl);
	return SUCCESS;
}
