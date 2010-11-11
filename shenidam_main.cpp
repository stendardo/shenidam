/*
 * shenidam_main.cpp
 *
 *  Created on: Nov 1, 2010
 *      Author: nabil
 */

#include "shenidam.h"

#include "sndfile.h"
#include "stdlib.h"
#include "string.h"
#include "stdio.h"

#include "boost/random.hpp"
#include "ctime"
#include <vector>
#include <string>
#include <cmath>
#include <cstdlib>




static int read_sndfile_average(SNDFILE* sndfile,SF_INFO* info,float** result)
{
	size_t n = (size_t) std::ceil(info->frames/1024.0);
	float *res = *result =(float*) malloc(sizeof(float)*n*1024);
	float* frame = (float*)malloc(sizeof(float)*info->channels*1024);

	for (int i = 0; i < n;i++)
	{

		sf_readf_float(sndfile,frame,1024);
		for (int k = 0; k < 1024; k++)
		{
			float s = 0;
			for (int j = 0 ; j < info->channels; j++)
			{
				s+=frame[k*info->channels + j];
			}
			res[i*1024+k]=s/info->channels;
		}
	}
	free(frame);
	return 0;
}
bool quiet = false;
bool test = false;
bool verbose = false;
bool base_set = false;
bool default_output = false;
bool output_mapping = false;
double size_test_track = 300;
std::vector<std::string> in_tracks;
std::vector<std::string> out_tracks;
std::string base_filename;
double sample_rate = 16000;
int num_files = 0;
double threshold = 1;
int num_tries = 5;
boost::mt19937 gen(std::time(0));
double randn(double m, double s)
{
	boost::normal_distribution<> dist(m, s);
	boost::variate_generator<boost::mt19937&, boost::normal_distribution<> > die(gen, dist);
	return die();
}
int randi(int from, int to)
{
	boost::uniform_int<> dist(from, to);
	boost::variate_generator<boost::mt19937&, boost::uniform_int<> > die(gen, dist);
	return die();
}
void add_gaussian_noise(float* samples,size_t num_samples_d,double sigma)
{
	for(size_t i = 0; i < num_samples_d; i++)
	{
		samples[i] += randn(0,sigma);
	}
}
void normalize(float* samples,size_t num_samples_d)
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
int copy_partial_sndfile(SNDFILE* sndfile,SF_INFO* info_in,SNDFILE* out,int in, size_t sample_length)
{
	if (!info_in->seekable)
	{


		fprintf(stderr,"Error: Base file not seekable");

		return 1;
	}
	long real_in = in < 0?0:in;
	sf_seek(sndfile,real_in,SEEK_SET);
	long end = in + sample_length;
	
	if (((size_t)end) > info_in->frames)
	{
		end = info_in->frames;
	}
	size_t j = 0;
	float* frame =(float*) malloc(sizeof(float)*info_in->channels*1024);
	memset(frame,0,sizeof(float)*info_in->channels*1024);
	for(long i = in; i < 0; i++)
	{
		sf_writef_float(out,frame,1);
		j++;
	}
	for(size_t i = 0; i < end; i++)
	{
	    size_t frames_to_transfer = end -j;
	    frames_to_transfer = frames_to_transfer>1024?1024:frames_to_transfer;
		sf_readf_float(sndfile,frame,frames_to_transfer);
		sf_writef_float(out,frame,frames_to_transfer);
		j+=frames_to_transfer;
	}
	memset(frame,0,sizeof(float)*info_in->channels*1024);
	for(; j < sample_length; j++)
	{
		sf_writef_float(out,frame,1);
	}
	free(frame);
	return 0;
}
int parse_options(int argc, char** argv)
{
	int i = 1;
	while(i < argc)
	{
		 std::string arg(argv[i++]);
		 if (arg == "-q" || arg == "--quiet")
		 {
			 quiet = true;
		 }
		 else if (arg == "-t" || arg == "--test")
		 {
			 test = true;
		 }
		 else if (arg == "-v" || arg == "--verbose")
		 {
			 verbose = true;
		 }
		 else if (arg == "-n" || arg == "--number-tracks")
		 {
			 if (i == argc) return 1;
			 if (num_files != 0)
			 {
				 fprintf(stderr,"ERROR: Number of tracks already defined.\nNote: If set, it must be set before any input our output tracks.\n");
			 }
			 num_files = strtol(argv[i++],NULL,10);
			 if (num_files <= 0)
			 {
				 fprintf(stderr,"ERROR: Invalid number of tracks!\n");
				 return 1;
			 }
		 }
		 else if (arg == "-b" || arg == "--base")
		 {
			 if (i == argc) return 1;
			 if (base_set) return 1;
			 base_filename = argv[i++];
			 base_set = true;
		 }
		 else if (arg == "-i" || arg == "--input")
		 {
			 if (!in_tracks.empty())
			 {
				 fprintf(stderr,"ERROR: Input tracks already set.\n");
				 return 1;
			 }
			 if (num_files == 0)
			 {
				 num_files = 1;
			 }
			 for (int j = 0; j < num_files;j++)
			 {
				 if (i == argc) return 1;
				 in_tracks.push_back(std::string(argv[i++]));
			 }
		 }
		 else if (arg == "-o" || arg == "--output")
		 {
			 if (default_output)
			 {
				 fprintf(stderr,"ERROR: Cannot set both default output and output track names.\n");
				 return 1;
			 }
			 if (!out_tracks.empty())
			 {
				 fprintf(stderr,"ERROR: Output tracks already set.\n");
				 return 1;
			 }
			 if (num_files == 0)
			 {
				 num_files = 1;
			 }
			 for (int j = 0; j < num_files;j++)
			 {
				 if (i == argc) return 1;
				 out_tracks.push_back(std::string(argv[i++]));
			 }
		 }
		 else if (arg == "-d" || arg == "--default-output")
		 {
			 if (!out_tracks.empty())
			 {
				 fprintf(stderr,"ERROR: Cannot set both default output and output track names.\n");
				 return 1;
			 }
			 default_output = true;
		 }
		 else if (arg == "-m" || arg == "--output-mapping" )
		 {
			 output_mapping = true;
		 }
		 else if (arg == "-s" || arg == "--sample-rate")
		 {
			 if (i == argc) return 1;
			 sample_rate = strtod(argv[i++],NULL);
			 if (sample_rate <= 0)
			 {
				 fprintf(stderr,"ERROR: Invalid sample rate.\n");
				 return 1;
			 }
		 }
		 else if (arg == "-nt" || arg == "--num-tries")
		 {
			 if (i == argc) return 1;
			 num_tries = strtol(argv[i++],NULL,10);
			 if (num_tries <= 0)
			 {
				 fprintf(stderr,"ERROR: Invalid number of tries!\n");
				 return 1;
			 }
		 }
		 else if (arg == "-tt" || arg == "--test-threshold")
		 {
			 if (i == argc) return 1;
			 threshold = strtod(argv[i++],NULL);
			 if (threshold <= 1E-6)
			 {
				 fprintf(stderr,"ERROR: Invalid or too small threshold.\n");
				 return 1;
			 }
		 }
		 else if (arg == "-ts" || arg == "--test-track-size")
		 {
			 if (i == argc) return 1;
			 size_test_track = strtod(argv[i++],NULL);
			 if (threshold <= 0)
			 {
				 fprintf(stderr,"ERROR: Invalid test track size.\n");
				 return 1;
			 }
		 }
		 else
		 {
			 return 1;
		 }

	}
	return 0;
}
void usage()
{
	fprintf(stderr,"USAGE: shenidam [params]\nOptions:\n\t-n integer\n\t--number-tracks integer\n\t\tNumber of tracks to match to the base (default 1).\nIf set, it must be set before the list of (input or output) tracks.\n\n"
			"\t-q\n\t--quiet\n\t\tsuppress messages\n\n"
			"\t-v\n\t--verbose\n\t\tverbose mode\n\n"
			"\t-b track_filename\n\t--base track_filename\n\t\tset the base track"
			"\t-i [filename_1 .. filename_n]\n\t--input [filename_1 .. filename_n]\n\t\tset the n input tracks\n\n"
			"\t-o [filename_1 .. filename_n]\n\t--output [filename_1 .. filename_n]\n\t\tset the n output tracks\n\n"
			"\t-d\n\t--default-output [filename_1 .. filename_n]\n\t\tset the n output tracks\n\n"
			"\t-m\n\t--output-mapping [filename_1 .. filename_n]\n\t\toutput the mapping sample in-position and length\n\n"
			"\t-s\n\t--sample-rate\n\t\tSample rate for audio processing (default 16000, more means more memory and cpu cycles and potentially more precise calculation).\n\n"
			"\t-t\n\t--test\n\t\ttest mode (requires only base). Tests critical noise boundary according to number of tries and threshold.\n\n"
			"\t-nt\n\t--num-tries integer\n\t\tNumber of tries for test mode (default 5). More means more precise boundary and processing time.\n\n"
			"\t-tt\n\t--test-threshold real\n\t\tThreshold for determining critical noise boundary (Default 0.1, less means more precise boundary)\n\n"
			"\t-ta\n\t--test-track-size real\n\t\tSize in seconds of generated track for test mode (Default 120s, needs to be less than the audio signal's length.)\n\n");

}

std::string get_default_output_filename(std::string input_filename)
{
	return input_filename + ".shenidam";
}
int process_audio()
{
	shenidam_t processor = shenidam_create(sample_rate);
	SF_INFO base_info;
	memset(&base_info,0,sizeof(SF_INFO));
	SNDFILE* base = sf_open(base_filename.c_str(),SFM_READ,&base_info);
	if (base == NULL)
	{
		return 1;
	}
	float* base_b;
	read_sndfile_average(base,&base_info,&base_b);
	shenidam_set_base_audio(processor,FORMAT_SINGLE,(void*)base_b,base_info.frames,(double)base_info.samplerate);
	free(base_b);
	for (int i = 0; i < num_files; i++)
	{
		std::string input_fn = in_tracks[i];
		size_t length;
		int in;
		SF_INFO track_info;
		memset(&track_info,0,sizeof(SF_INFO));
		float* track_b;
		SNDFILE* track = sf_open(input_fn.c_str(),SFM_READ,&track_info);
		read_sndfile_average(track,&track_info,&track_b);
		sf_close(track);
		if (shenidam_get_audio_range(processor,FORMAT_SINGLE,(void*)track_b,track_info.frames,(double)track_info.samplerate,&in,&length))
		{
			fprintf(stderr,"ERROR: Error mapping track to base .\n");
			free(track);
			continue;
		}
		if (default_output || out_tracks.size())
		{
			SF_INFO out_info = base_info;
			out_info.frames = length;
			std::string out_fn;
			if (default_output)
			{
				out_fn = get_default_output_filename(input_fn);
			}
			else
			{
				out_fn = out_tracks[i];
			}
			SNDFILE* out = sf_open(out_fn.c_str(),SFM_WRITE,&out_info);
			if (copy_partial_sndfile(base,&base_info,out,in,length))
			{
				sf_close(base);
				sf_close(out);
				return 1;
			}
			sf_close(out);
			if (output_mapping)
			{
				long in_val = in;
				long length_val = length;
				printf("%ld\t%ld\n",in_val,length_val);
			}
		}

	}
	sf_close(base);
	return 0;
}
bool test_once(shenidam_t processor, float* base,size_t total_num_samples,double sample_rate,size_t num_samples_track, double sigma)
{
	int real_in = randi(0,total_num_samples-num_samples_track-1);
	float* track = (float*) malloc(num_samples_track*sizeof(float));
	memcpy(track,&base[real_in],num_samples_track*sizeof(float));
	add_gaussian_noise(track,num_samples_track,sigma);
	size_t dummy;
	int in;
	shenidam_get_audio_range(processor,FORMAT_SINGLE,track,num_samples_track,sample_rate,&in,&dummy);
	free(track);
	return std::abs(in - real_in)<sample_rate*threshold;

}
bool test_n(shenidam_t processor, float* base,size_t total_num_samples,double sample_rate,size_t num_samples_track, double sigma,int num_tries)
{
	int num_succeeded = 0;
	int num_failed = 0;
	if (!quiet)
	{
		printf("Testing with Sigma = %g\n",sigma);
	}
	for(int i = 0; i < num_tries;i++)
	{
		if (!test_once(processor,base,total_num_samples,sample_rate,num_samples_track,sigma))
		{
			if (verbose)
			{
				printf("Match Failed!\n");
			}
			num_failed++;
		}
		else
		{
			if (verbose)
			{
				printf("Match Succeeded!\n");
			}
			num_succeeded++;
		}
		if (num_failed > num_tries/2)
		{
			return false;
		}
		else if (num_succeeded > num_tries/2)
		{
			return true;
		}
	}
	return true;
}
int do_test()
{
	shenidam_t processor = shenidam_create(sample_rate);
	SF_INFO base_info;
	memset(&base_info,0,sizeof(SF_INFO));
	SNDFILE* base = sf_open(base_filename.c_str(),SFM_READ,&base_info);
	if (base == NULL)
	{
		return 1;
	}
	float* base_b;
	read_sndfile_average(base,&base_info,&base_b);
	sf_close(base);
	//normalize(base_b,base_info.frames);
	size_t total_num_samples = base_info.frames;
	size_t num_samples_track = (size_t)ceil(size_test_track*base_info.samplerate);
	if (num_samples_track >= total_num_samples)
	{
		fprintf(stderr,"ERROR: Track size larger than base size. Choose smaller track size or longer base.");
	}
	double sample_rate = (double)base_info.samplerate;
	shenidam_set_base_audio(processor,FORMAT_SINGLE,(void*)base_b,base_info.frames,(double)base_info.samplerate);
	double in = 0.0;
	double out = 100.0;
	while(test_n(processor,base_b,total_num_samples,sample_rate,num_samples_track,out,num_tries))
	{
		in = out;
		out += 100;
	}

	while((out - in)>0.01)
	{
		double midpoint = (in+out) / 2;
		if (test_n(processor,base_b,total_num_samples,sample_rate,num_samples_track,midpoint,num_tries))
		{
			in = midpoint;
		}
		else
		{
			out = midpoint;
		}
	}
	double critical_noise_sd = (in+out)/2;
	double cnsd_db = 10*log(1/(critical_noise_sd*critical_noise_sd));
	printf("Critical noise %g (%g db)\n",critical_noise_sd,cnsd_db);
	free(base_b);
	shenidam_destroy(processor);
	return 0;
}
int main(int argc, char **argv) {
	if(parse_options(argc,argv))
	{
		usage();
		return 1;
	}
	bool has_output = test || output_mapping || default_output || out_tracks.size();
	bool has_input = test || in_tracks.size();
	if (quiet && verbose)
	{
		verbose = false;
	}
	if (!base_set)
	{
		fprintf(stderr,"ERROR: A base file is required.\n");
		usage();
		return 1;
	}
	if (!has_output)
	{
		fprintf(stderr,"ERROR: No output. One of [-o, -d, -t, -m] is required.\n");
		usage();
		return 1;
	}
	if (!has_input)
	{
		fprintf(stderr,"ERROR: No input. One of [-t, -i] is required.\n");
		usage();
		return 1;
	}
	if (test)
	{
		return do_test();
	}
	else
	{
		return process_audio();
	}
}
