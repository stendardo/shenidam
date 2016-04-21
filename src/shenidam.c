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
#include "config.h"


inline intmax_t max(intmax_t a, intmax_t b)
{
	return a > b?a:b;
}

inline intmax_t min(intmax_t a, intmax_t b)
{
	return a < b?a:b;
}

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
	double working_sample_rate;
	double base_sample_rate;
	sample_d* base_working;
	sample_d* base_fullres;
	size_t base_num_samples_working;
	size_t base_num_samples_fullres;
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
	}
	return "Unknown error";
}


int initialized_module = 0;

static void* fft_ehmalloc(size_t size)
{
	void* res = FFT_MALLOC(size);
	if (res == NULL)
	{
		fprintf(stderr,"[fft_ehmalloc] ERROR: could not allocate buffer of size %zd - likely out of memory\n",size);
	}
	return res;
}
static void* ehmalloc(size_t size)
{
	void* res = malloc(size);
	if (res == NULL)
	{
		fprintf(stderr,"[ehmalloc] ERROR: could not allocate buffer of size %zd - likely OOM\n",size);
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
	
	for(size_t i = 0; i < num_samples_d; i++)
	{
		mean += samples[i];
		var += samples[i]*samples[i];
	}
	mean /= num_samples_d;;
	var = sqrt(var-mean*mean);
	if (var == 0)
	{
		for(size_t i = 0; i < num_samples_d; i++)
		{
			samples[i]=(samples[i]-mean);
		}
	}
	else
	{
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
	sample_d* buffer_d = fft_ehmalloc(sizeof(sample_d)*num_samples_d);
	sample_f* buffer_f = fft_ehmalloc(sizeof(sample_f)*num_samples_f);
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
		initialized_module = 1;
	}
	
	shenidam_t_impl* res = (shenidam_t_impl*)malloc(sizeof(shenidam_t_impl));
	res->base_working = NULL;
	res->base_fullres = NULL;
	res->working_sample_rate = base_sample_rate;
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
	sample_d* base,*temp;
	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);

	if (impl->base_working!=NULL)
	{
		return ALREADY_SET_BASE_SIGNAL;
	}
	if (convert_to_samples(format, samples, num_samples,&base))
	{
		return INVALID_ARGUMENT;
	}
	normalize(base,num_samples);
	impl->base_fullres = malloc(num_samples*sizeof(sample_d));
	memcpy(impl->base_fullres,base,num_samples*sizeof(sample_d));

	impl->base_num_samples_fullres = num_samples;
	size_t num_samples_new = (size_t)round(num_samples * impl->working_sample_rate/sample_rate);
	temp = resample(base,num_samples,impl->working_sample_rate/sample_rate,&num_samples_new,impl->num_threads,impl->src_converter);
	ehfree(base);
	base = temp;
	impl->base_num_samples_working = num_samples_new;

	impl->base_working = base;
	impl->base_sample_rate = sample_rate;

	return SUCCESS;
}

int shenidam_refine_audio_range(shenidam_t shenidam_obj,int input_format,void* samples,size_t track_num_samples,double track_sample_rate, intmax_t *in_point)
{
	if (shenidam_obj == NULL)
	{
		return NULL_OBJECT;
	}
	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);

	if (impl->base_working == NULL)
	{
		return BASE_SIGNAL_NOT_SET;
	}
	if (track_sample_rate <= 0)
	{
		return INVALID_ARGUMENT;
	}
	if (track_num_samples == 0)
	{
		return INVALID_ARGUMENT;
	}

	double sample_rate_ratio_base_work = impl->base_sample_rate/impl->working_sample_rate;
	int radius = ceil(sample_rate_ratio_base_work);
	if (radius <= 1)
	{
		return SUCCESS;
	}
	sample_d* track;
	sample_d* base;
	sample_d* temp_d;
	base = impl->base_fullres;
	if (convert_to_samples(input_format, samples, track_num_samples,&track))
	{
		return INVALID_ARGUMENT;
	}
	normalize(track,track_num_samples);
	double sample_rate_ratio = impl->base_sample_rate/track_sample_rate;
	double track_num_samples_base = track_num_samples;
	if (sample_rate_ratio != 1)
	{
		size_t track_num_samples_temp = (size_t)ceil(track_num_samples*sample_rate_ratio);
		temp_d = resample(track,track_num_samples,sample_rate_ratio,&track_num_samples_temp,impl->num_threads,impl->src_converter);
		free(track);
		track = temp_d;
		track_num_samples_base = track_num_samples_temp;
	}

	intmax_t in_track = *in_point;
	intmax_t out_track = in_track + round(track_num_samples_base*impl->base_sample_rate/track_sample_rate);

	intmax_t in_base = 0;
	intmax_t out_base = impl->base_num_samples_fullres;

	intmax_t overlapping_in = max(in_base,in_track);
	intmax_t overlapping_out = min(out_base,out_track);

	if (overlapping_in > overlapping_out)
	{
		return SUCCESS;//Shouldn't happen
	}

	
	sample_d* buffer = calloc((2*radius+1),sizeof(sample_d));

	for (int j = -radius ; j <= radius; j++)
	{
		for (intmax_t base_sample = overlapping_in + radius; base_sample < overlapping_out - radius; base_sample++)
		{
			intmax_t track_sample = base_sample - *in_point;
			
			sample_d a = base[base_sample ];
			sample_d b = track[track_sample + j];
			buffer[j+radius] += a * b;
		}
	}

	free(track);

	double maxV = -DBL_MAX;
	int iMax = -1;
	for (int i = 0 ; i < 2*radius + 1; i++)
	{
		if (buffer[i] > maxV)
		{
			maxV = buffer[i];
			iMax = i;
		}
	}
	*in_point -= iMax - radius;
	
}

int shenidam_get_audio_range(shenidam_t shenidam_obj,int input_format,void* samples,size_t track_num_samples,double track_sample_rate,intmax_t* in_point,size_t* length)
{
	if (shenidam_obj == NULL)
	{
		return NULL_OBJECT;
	}
	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);

	if (impl->base_working == NULL)
	{
		return BASE_SIGNAL_NOT_SET;
	}
	if (track_sample_rate <= 0)
	{
		return INVALID_ARGUMENT;
	}
	if (track_num_samples == 0)
	{
		return INVALID_ARGUMENT;
	}
	sample_d* track;
	
	sample_d* base;
	sample_d* temp_d;
	sample_d* convolved;
	sample_f* track_f;
	sample_f* base_f;
	base = impl->base_working;
	if (convert_to_samples(input_format, samples, track_num_samples,&track))
	{
		return INVALID_ARGUMENT;
	}
	normalize(track,track_num_samples);

	double sample_rate_ratio = impl->working_sample_rate/track_sample_rate;
	double track_num_samples_working = track_num_samples;
	
	

	if (sample_rate_ratio != 1)
	{
		size_t track_num_samples_temp = (size_t)ceil(track_num_samples*sample_rate_ratio);

		temp_d = resample(track,track_num_samples,sample_rate_ratio,&track_num_samples_temp,impl->num_threads,impl->src_converter);
		free(track);
		track = temp_d;
		track_num_samples_working = track_num_samples_temp;
	}
	size_t common_size = get_common_size(track_num_samples_working + impl->base_num_samples_working);
	size_t common_size_f = common_size / 2 + 1;
	temp_d = resize(track,track_num_samples_working,common_size);
	ehfree(track);
	track = temp_d;
	temp_d = resize(base,impl->base_num_samples_working,common_size);
	base = temp_d;

	track_f = fft(track,common_size,impl->num_threads);
	ehfree(track);
	base_f = fft(base,common_size,impl->num_threads);
	ehfree(base);
	for (size_t i = 0; i < common_size_f;i++)
	{
		track_f[i]=conjf(track_f[i])*base_f[i];
	}
	ehfree(base_f);
	convolved = ifft(track_f,common_size,impl->num_threads);
	ehfree(track_f);
	sample_d maxv = -DBL_MAX;
	intmax_t in = 0;
	for(size_t i = 0; i < common_size;i++)
	{
		double temp = convolved[i];
		if (temp > maxv)
		{
			maxv = temp;
			in = i;
		}
	}

	
	

	if (in > (track_num_samples_working<impl->base_num_samples_working?common_size-track_num_samples_working:impl->base_num_samples_working))
	{
		in -= common_size;
	}
	
	double sample_rate_ratio_base_work = impl->base_sample_rate/impl->working_sample_rate;
	ehfree(convolved);
	*in_point = round(in*sample_rate_ratio_base_work);
	*length = round(track_num_samples*impl->base_sample_rate/track_sample_rate);
	shenidam_refine_audio_range(shenidam_obj,input_format,samples,track_num_samples,track_sample_rate,in_point);
	
	return SUCCESS;
}

int shenidam_destroy(shenidam_t shenidam_obj)
{
	if (shenidam_obj == NULL)
	{
		return NULL_OBJECT;
	}

	shenidam_t_impl* impl =((shenidam_t_impl*)shenidam_obj);
	ehfree(impl->base_working);
	ehfree(impl->base_fullres);
	ehfree(impl);
	return SUCCESS;
}
