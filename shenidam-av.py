#!/usr/bin/env python
from __future__ import print_function
import uuid
import sys
import subprocess
import re
import os.path
import tempfile
import shutil
FFMPEG = "ffmpeg"
SHENIDAM = "shenidam"
AUDIO_REMIX_PARAMS = None
AUDIO_EXPORT_PARAMS ="-acodec pcm_s24le -f wav"
SHENIDAM_PARAMS =""
INPUT_TRACKS =  []
BASE_FN = None
OUTPUT_PATTERN = ""
TRANSCODE_BASE = None
VERBOSE = False
QUIET = False
TEMP_DIR = tempfile.gettempdir()
NUM_PATTERN = re.compile("{seq(?:/(\d+))?}")
BASENAME_PATTERN = re.compile("{file}")
BASENAME_NOEXT_PATTERN = re.compile("{base}")
DIRNAME_PATTERN = re.compile("{dir}")
EXT_PATTERN = re.compile("{ext}")
AUDIO_ONLY = False
def run_command(cmd):
    
    try:
        p = subprocess.Popen(cmd,stdin=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
        res = p.communicate(None)
        if p.returncode != 0:
            print("ERROR: Command '{0}' failed, standard error was:\n{1}".format(cmd,res[1]),file=sys.stderr)
            raise Exception()
    except OSError as e:
        print(e,file=sys.stderr)
        raise Exception()

def extract_audio(avfilename,outfn):
    run_command("{exec_} -y -v 0 -loglevel error -i \"{avfilename}\" -vn {audio_export_params} \"{outfn}\"".format(exec_=FFMPEG,avfilename=avfilename,outfn=outfn,audio_export_params=AUDIO_EXPORT_PARAMS))

def run_shenidam(base_fn,track_fns,output_fns):
    res = "{shenidam} {shenidam_params} -b \"{base_fn}\" -n {num_tracks} ".format(shenidam_params=SHENIDAM_PARAMS,num_tracks=len(track_fns),shenidam=SHENIDAM,base_fn=base_fn)
    res+= "-i "
    for x in track_fns:
        res+= "\"{0}\" ".format(x)
    res+= "-o "
    for x in output_fns:
        res+= "\"{0}\" ".format(x)
    run_command(res)

def remix_audio(avfilename,track_fn,output_fn):
    if AUDIO_ONLY:
        run_command("{ffmpeg} -y -v 0 -loglevel error -i {track_fn} {audio_remix_params} {output_fn}".format(ffmpeg = FFMPEG, track_fn=track_fn,output_fn=output_fn,audio_remix_params=AUDIO_REMIX_PARAMS))
    else:
        run_command("{ffmpeg} -y -v 0 -loglevel error -i {avfilename} -i {track_fn} -map 0:0 -map 1:0  {audio_remix_params} {output_fn}".format(ffmpeg = FFMPEG, avfilename=avfilename,track_fn=track_fn,output_fn=output_fn,audio_remix_params=AUDIO_REMIX_PARAMS))
def parse_params():
    global VERBOSE, QUIET, SHENIDAM, FFMPEG, SHENIDAM_PARAMS, TRANSCODE_BASE, OUTPUT_PATTERN, BASE_FN, AUDIO_EXPORT_PARAMS, AUDIO_REMIX_PARAMS, SHENIDAM_PARAMS, TEMP_DIR, AUDIO_ONLY;
    argv = sys.argv
    argc = len(argv)
    i = 1
    while i < argc:
        arg = argv[i].strip()
        i+=1
        if arg == "-v" or arg == "--verbose":
            VERBOSE = True
        if arg == "-a" or arg == "--audio-only":
            AUDIO_ONLY = True
        elif arg == "-q" or arg == "--quiet":
            QUIET = True
        elif arg == "-se" or arg == "--shenidam-executable":
            if i >= argc:
	            return 1
            SHENIDAM = argv[i].strip()
            i+=1;
        elif arg == "-fe" or arg == "--ffmpeg-executable":
            if i >= argc:
	            return 1;
            FFMPEG = argv[i].strip()
            i+=1
        elif arg == "-tb" or arg == "--transcode-base":
            TRANSCODE_BASE = True
        elif arg == "-sp" or arg == "--shenidam-params":
            if i >= argc:
	            return 1;
            SHENIDAM_PARAMS = argv[i].strip()
            i+=1
        elif arg == "-ntb" or arg == "--no-transcode-base":
            TRANSCODE_BASE = False
        elif arg == "-o" or arg == "--output":
            if i >= argc:
	            return 1;
            OUTPUT_PATTERN = argv[i].strip()
            i+=1
        elif arg == "-b" or arg == "--base":
            if i >= argc:
	            return 1;
            BASE_FN = argv[i].strip()
            i+=1
        elif arg == "-aep" or arg == "--audio-export-params":
            if i >= argc:
	            return 1;
            AUDIO_EXPORT_PARAMS = argv[i].strip()
            i+=1
        elif arg == "-arp" or arg == "--audio-remix-params":
            if i >= argc:
	            return 1;
            AUDIO_REMIX_PARAMS = argv[i].strip()
            i+=1
        elif arg == "-sp" or arg == "--shenidam-params":
            if i >= argc:
	            return 1;
            SHENIDAM_PARAMS = argv[i].strip()
            i+=1
        elif arg == "-td" or arg == "--temporary-directory":
            if i >= argc:
	            return 1;
            TEMP_DIR = argv[i].strip()
            i+=1
        else:
            i-=1;
            break;
    if i == argc:
        return 1;
    for j in range(i,argc):
        INPUT_TRACKS.append(argv[j].strip())
    return 0;
def filename_from_pattern(i,filename,pattern):
    basename = os.path.basename(filename)
    basename_noext,ext = os.path.splitext(basename)
    dirname = os.path.dirname(filename)
    if dirname == "":
        dirname="."
    def repl(matchobj):
        x = str(i)
        if (matchobj.group(1) is None):
            return x
        n = int(matchobj.group(1))
        for j in range(len(x),n):
            x = '0'+x
        return x
    pattern = re.sub(NUM_PATTERN,repl,pattern)
    pattern = re.sub(BASENAME_PATTERN,basename,pattern)
    pattern = re.sub(BASENAME_NOEXT_PATTERN,basename_noext,pattern)
    pattern = re.sub(DIRNAME_PATTERN,dirname,pattern)
    pattern = re.sub(EXT_PATTERN,ext,pattern)
    return pattern
def error(str):
    return print(str,file=sys.stderr)
def check_params():
    global TRANSCODE_BASE,AUDIO_REMIX_PARAMS;
    if QUIET and VERBOSE:
        VERBOSE = False
    if BASE_FN is None:
        error("ERROR: No base defined")
        return 1;
    if len(INPUT_TRACKS) == 0:
        error("ERROR: No tracks defined.")
        return 1;
    if len(OUTPUT_PATTERN) == 0:
        error("ERROR: No output defined.")
        return 1;
    if not SHENIDAM:
        error("ERROR: Invalid shenidam command.")
        return 1;
    if not FFMPEG:
        error("ERROR: Invalid FFMPEG command")
        return 1;
    if TRANSCODE_BASE is None:
        base_lower = BASE_FN.lower()
        TRANSCODE_BASE = not base_lower.endswith(".wav") and not base_lower.endswith(".aiff") and not base_lower.endswith(".flac")
    if AUDIO_REMIX_PARAMS is None:
        AUDIO_REMIX_PARAMS = "-vcodec copy -acodec copy" if not AUDIO_ONLY else "-acodec copy"
    return 0
def usage():
    error("""USAGE :{0} [options] av_track_1 ... av_track_n
Options:
-a / --audio-only : do not copy any video information into the output files.

-b / --base filename : determine the base audio (or audio-visual) file (to which the tracks will be matched) MANDATORY

-o / --output pattern: determine the pattern of output filenames. Patterns can include the strings {{seq}} (or {{seq/d}} where d is the minimum number of digits), {{file}}, {{base}}, {{ext}} and {{dir}} MANDATORY

-td / --temporary-directory : The temporary directory in which to store the extracted audio files (default /tmp/)

-tb / --transcode-base or --ntb / --no-transcode-base : Force transcoding (resp. no transcoding) of the base file (default is to transcode except for a number of predefined "safe" extensions (e.g. .wav)

-aep / --audio-export-params quoted_param_string : parameters to pass to ffmpeg while exporting. Requires format, and sometimes codec. (default "-acodec pcm_s24le -f wav")

-arp / --audio-remix-params quoted_param_string : parameters to pass to ffmpeg while remixing (replacing the audio from the tracks with shenidam's output). Should set at least -vcodec and -acodec (default :"-acodec copy" if -a is set, "-vcodec copy -acodec copy" otherwise)

-sp / --shenidam-params quoted_param_string : extra parameters to pass to shenidam

-se / --shenidam-executable command: the shenidam executable / command

-fe / --ffmpeg-executable command: the ffmpeg executable / command

""".format(sys.argv[0]))

class TemporaryFile(object):
    def __init__(self,fns,delete=True):
        self.filenames = list(fns)
        self.delete = delete
    def __enter__(self):
        pass
    def __exit__(self,type,value,traceback):
        if self.delete:
            for fn in self.filenames:
                try:
                    os.remove(fn)
                except Exception:
                    pass
        return False
def create_temporary_file_name():
    return os.path.join(TEMP_DIR,"shenidam-av-tmp-"+uuid.uuid4().hex)
def convert():
    base = BASE_FN
    if TRANSCODE_BASE:
        base = create_temporary_file_name()
    with TemporaryFile([base],TRANSCODE_BASE):
        if TRANSCODE_BASE:
            extract_audio(BASE_FN,base)
        input_transcoded_fns = [create_temporary_file_name() for x in INPUT_TRACKS]
        with TemporaryFile(input_transcoded_fns):
            error("Extracting Audio")
            output_remixed_files = [filename_from_pattern(ix[0],ix[1],OUTPUT_PATTERN) for ix in enumerate(INPUT_TRACKS)]
            output_temp_files = [create_temporary_file_name() for x in INPUT_TRACKS]
            remixed_temp_files = [create_temporary_file_name()+"."+os.path.basename(x) for x in output_remixed_files]
            for x,y in zip(INPUT_TRACKS,input_transcoded_fns):
                extract_audio(x,y)
            with TemporaryFile(output_temp_files):
                error("Running Shenidam")
                run_shenidam(base,input_transcoded_fns,output_temp_files)
                error("Remixing Audio")
                with TemporaryFile(remixed_temp_files):
                    for input_av,audio,output_av,temp_output_av in zip(INPUT_TRACKS,output_temp_files,output_remixed_files,remixed_temp_files):
                        remix_audio(input_av,audio,temp_output_av)
                        shutil.move(temp_output_av,output_av)
def main():
    if (parse_params() or check_params()):
        usage()
        return 1;
    convert()
    return 0

if __name__ == "__main__":
    sys.exit(main())
