"""
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

"""
from __future__ import print_function
import uuid
import sys
import subprocess
import re
import os.path
import tempfile
import shutil
import shenidam
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
class SubprocessError(Exception):
    def __init__(self,error):
        super(SubprocessError,self).__init__(error)
def raise_subprocess_error(cmd,stderr,show_error=True):
    raise SubprocessError("Command '{cmd}' failed{error}".format(cmd=cmd,error=(", error stream was:\n"+stderr) if show_error else ""))
def run_command(cmd):
    
    try:
        stderr_forward = shenidam.forward(sys.stderr) if VERBOSE else shenidam.do_nothing;
        
        res,stdout,stderr = shenidam.ProcessRunner(cmd,stderr_forward,stderr_forward)()
        if res != 0:
            raise_subprocess_error(cmd,stderr,not VERBOSE)
    except OSError as e:
        raise_subprocess_error(cmd,e)
def extract_audio(avfilename,outfn):
    run_command("{exec_} -y -v 0 -loglevel error -i \"{avfilename}\" -vn {audio_export_params} \"{outfn}\"".format(exec_=FFMPEG,avfilename=avfilename,outfn=outfn,audio_export_params=AUDIO_EXPORT_PARAMS))

def run_shenidam(base_fn,track_fns,output_fns):
    try:
        stderr_forward = shenidam.forward(sys.stderr) if VERBOSE else shenidam.do_nothing;
        message_handler = shenidam.message_handler_print(sys.stderr) if not QUIET else shenidam.do_nothing
        cmd,res,stdin,stderr = shenidam.Shenidam(SHENIDAM,SHENIDAM_PARAMS,message_handler,stderr_forward)(base_fn,track_fns,output_fns)
        if res != 0:
            raise_subprocess_error(cmd,stderr,not VERBOSE)
    except OSError as e:
        raise_subprocess_error(cmd,e)

def remix_audio(avfilename,track_fn,output_fn):
    if AUDIO_ONLY:
        run_command("{ffmpeg} -y -v 0 -loglevel error -i \"{track_fn}\" {audio_remix_params} \"{output_fn}\"".format(ffmpeg = FFMPEG, track_fn=track_fn,output_fn=output_fn,audio_remix_params=AUDIO_REMIX_PARAMS))
    else:
        run_command("{ffmpeg} -y -v 0 -loglevel error -i \"{avfilename}\" -i \"{track_fn}\" -map 0:0 -map 1:0  {audio_remix_params} \"{output_fn}\"".format(ffmpeg = FFMPEG, avfilename=avfilename,track_fn=track_fn,output_fn=output_fn,audio_remix_params=AUDIO_REMIX_PARAMS))

def parse_params(model):
    argv = sys.argv
    argc = len(argv)
    i = 1
    output_pattern = None
    audio_only = False
    audio_remix_params = None
    while i < argc:
        arg = argv[i].strip()
        i+=1
        if arg == "-v" or arg == "--verbose":
            model.verbose = True
        elif arg == "-a" or arg == "--audio-only":
            audio_only = True
        elif arg == "-q" or arg == "--quiet":
            model.quiet = True
        elif arg == "-se" or arg == "--shenidam-executable":
            if i >= argc:
	            return 1
            model.shenidam = argv[i].strip()
            i+=1;
        elif arg == "-fe" or arg == "--ffmpeg-executable":
            if i >= argc:
	            return 1;
            model.ffmpeg = argv[i].strip()
            i+=1
        elif arg == "-tb" or arg == "--transcode-base":
            model.transcode_base = True
        elif arg == "-sp" or arg == "--shenidam-params":
            if i >= argc:
	            return 1;
            model.shenidam_extra_args = argv[i].strip()
            i+=1
        elif arg == "-ntb" or arg == "--no-transcode-base":
            model.transcode_base = False
        elif arg == "-o" or arg == "--output":
            if i >= argc:
	            return 1;
            output_pattern = argv[i].strip()
            i+=1
        elif arg == "-b" or arg == "--base":
            if i >= argc:
	            return 1;
            model.base_fn = argv[i].strip()
            i+=1
        elif arg == "-aep" or arg == "--audio-export-params":
            if i >= argc:
	            return 1;
            model.audio_export_params = argv[i].strip()
            i+=1
        elif arg == "-arp" or arg == "--audio-remix-params":
            if i >= argc:
	            return 1;
            audio_remix_params = argv[i].strip()
            i+=1
        elif arg == "-td" or arg == "--temporary-directory":
            if i >= argc:
	            return 1;
            model.tmp_dir = argv[i].strip()
            i+=1
        else:
            i-=1;
            break;
    if i == argc:
        return 1;
    for j in range(i,argc):
        model.input_tracks.append(argv[j].strip())
    if audio_remix_params is None:
        audio_remix_params = "-vcodec copy -acodec copy" if not audio_only else "-acodec copy"
    model.output_patterns_with_audio_only_flag_and_remix_params = [[output_pattern,audio_only,audio_remix_params]]
    return 0;
def error(str):
    return print(str,file=sys.stderr)
def check_params(model):
    if model.quiet:
        model.verbose = False
    if model.base_fn is None:
        error("ERROR: No base defined")
        return 1;
    if len(model.input_tracks) == 0:
        error("ERROR: No tracks defined.")
        return 1;
    op = model.output_patterns_with_audio_only_flag_and_remix_params[0][0]
    if op is None or len(op) == 0:
        error("ERROR: No output defined.")
        return 1;
    if not model.shenidam:
        error("ERROR: Invalid shenidam command.")
        return 1;
    if not model.ffmpeg:
        error("ERROR: Invalid FFMPEG command")
        return 1;
    if model.transcode_base is None:
        model.transcode_base = not shenidam.Shenidam(model.shenidam).can_open(model.base_fn)
    return 0
def usage():
    error("""USAGE :{0} [options] av_track_1 ... av_track_n
Options:
-a / --audio-only : do not copy any video information into the output files.

-b / --base filename : determine the base audio (or audio-visual) file (to which the tracks will be matched) MANDATORY

-o / --output pattern: determine the pattern of output filenames. Patterns can include the strings {{seq}} (or {{seq/d}} where d is the minimum number of digits), {{file}}, {{base}}, {{ext}} (which includes the starting period) and {{dir}} MANDATORY

-td / --temporary-directory : The temporary directory in which to store the extracted audio files (default is the machine's temporary directory)

-tb / --transcode-base or --ntb / --no-transcode-base : Force transcoding (resp. no transcoding) of the base file (default is to transcode except for a file for which transcoding is not possible)

-aep / --audio-export-params quoted_param_string : parameters to pass to ffmpeg while exporting. Requires format, and sometimes codec. (default "-acodec pcm_s24le -f wav")

-arp / --audio-remix-params quoted_param_string : parameters to pass to ffmpeg while remixing (replacing the audio from the tracks with shenidam's output). Should set at least -acodec (and -vcodec if -a is not set)  (default : if -a is set "-acodec copy", otherwise "-vcodec copy -acodec copy")

-sp / --shenidam-params quoted_param_string : extra parameters to pass to shenidam

-se / --shenidam-executable command: the shenidam executable / command

-fe / --ffmpeg-executable command: the ffmpeg executable / command

""".format(sys.argv[0]))

def main():
    model = shenidam.FileProcessorModel()
    if (parse_params(model) or check_params(model)):
        usage()
        return 1;
    shenidam.ShenidamFileProcessor(model,shenidam.StreamNotifier(sys.stderr)).convert()
    return 0

if __name__ == "__main__":
    sys.exit(main())
