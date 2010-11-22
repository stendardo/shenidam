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
from __future__ import division
import threading
import sys
import re
import uuid
import subprocess
import os.path
import shutil
import tempfile
try:
    import Queue as squeue
except ImportError:
    import queue as squeue
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import shlex

NUM_PATTERN = re.compile("{seq(?:/(\d+))?}")
BASENAME_PATTERN = re.compile("{file}")
BASENAME_NOEXT_PATTERN = re.compile("{base}")
DIRNAME_PATTERN = re.compile("{dir}")
EXT_PATTERN = re.compile("{ext}")

def do_nothing(*args,**kwds):
    pass
def forward(stream):
    def inner(line):
        stream.write(line)
    return inner
class StreamReader(threading.Thread):
    def __init__(self,callbacks,stream,queue):
        self.callbacks = callbacks
        self.stream = stream
        self.queue = queue
        super(StreamReader,self).__init__()
    def run(self):
        try:
            line = self.stream.readline();
            while line:
                for callback in self.callbacks:
                    callback(line)
                line = self.stream.readline();
        except BaseException as e:
            self.queue.put(e)
class ProcessRunner(object):
    def __init__(self,command,stdout_callback=do_nothing,stderr_callback=do_nothing,periodic_notifier=do_nothing):
        self.command = command
        self.stdout_callback = stdout_callback
        self.stderr_callback = stderr_callback
        self.periodic_notifier = periodic_notifier
    def __call__(self):
        stdout_sio = StringIO.StringIO()
        stderr_sio = StringIO.StringIO()
        process = None
        exception_queue = squeue.Queue()
        try:
            process = subprocess.Popen(shlex.split(self.command),bufsize=1,stdin=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
            stdout_reader = StreamReader([forward(stdout_sio),self.stdout_callback],process.stdout,exception_queue)
            stderr_reader = StreamReader([forward(stderr_sio),self.stderr_callback],process.stderr,exception_queue)
            stdout_reader.start();
            stderr_reader.start();
            while process.poll() is None:
                try:
                    exception = exception_queue.get(timeout=0.1)
                except squeue.Empty:
                    pass
                else:
                    raise exception
                self.periodic_notifier()
        except:
            process.terminate();
            raise
        return process.returncode,stdout_sio.getvalue(),stderr_sio.getvalue()

def _parse_event(line):
    res = {}
    for x in line.split(";"):
        x = x.strip()
        x = x.split(":",1)
        if len(x)==0:
            continue
        if len(x)==1:
            res[x[0].strip()]=None
        else:
            res[x[0].strip()]=x[1].strip()
    return res
def message_handler_print(stream):
    def inner(line,event):
        stream.write(line)
    return inner
class Shenidam(object):
    def __init__(self,executable,extra_args="",message_callback=do_nothing,error_callback=forward(sys.stderr),periodic_notifier=do_nothing):
        def mycallback(line):
            if line.startswith("MESSAGE:"):
                return message_callback(line,_parse_event(line))
        self.output_callback = mycallback
        self.executable = executable
        self.extra_args = extra_args
        self.error_callback = error_callback
        self.periodic_notifier = periodic_notifier
    def __call__(self,base,input_tracks,output_tracks):
        if len(input_tracks) <= 0:
            raise ValueError("No input tracks")
        if len(output_tracks) > 0 and len(input_tracks) != len(output_tracks):
            raise ValueError("Invalid number of input tracks")
        args= "-i "
        for x in input_tracks:
            args+= "\"{0}\" ".format(x)
        if len(output_tracks)>0:
            args+= "-o "
            for x in output_tracks:
                args+= "\"{0}\" ".format(x)
        cmd = "\"{executable}\" -m {extra_args} -n {numargs} -b \"{base}\" {args}".format(executable=self.executable,base=base,numargs=len(input_tracks),args=args,extra_args=self.extra_args)
        res,stdout,stderr = ProcessRunner(cmd,self.output_callback,self.error_callback,self.periodic_notifier)()
        return cmd,res,stdout,stderr
    def can_open(self,filename):
        cmd = "\"{executable}\" -b \"{filename}\" -c".format(executable=self.executable,filename=filename)
        return not subprocess.call(shlex.split(cmd),stdin=None,stdout=None,stderr=None,shell=False)
class SubprocessError(Exception):
    def __init__(self,error):
        super(SubprocessError,self).__init__(error)

def delete_filenames(filenames,delete=True):
    if delete:
        for fn in filenames:
            try:
                os.remove(fn)
            except Exception:
                pass
class TemporaryFile(object):
    def __init__(self,fns,delete=True):
        self.filenames = list(fns)
        self.delete = delete
    def __enter__(self):
        pass
    def __exit__(self,type,value,traceback):
        delete_filenames(self.filenames,self.delete)
        return False
class StreamNotifier(object):
    def __init__(self,stream):
        self.stream = stream
        self.done = False
        self.canceled = False
    def update_major(self,minor_levels = 0, raise_if_canceled = True):
        pass
    def update_minor(self,raise_if_canceled = True):
        pass
    def set_major_text(self,text):
        print(text,file=self.stream)
    def set_minor_text(self,text):
        print("\t"+text,file=self.stream)
    def cancel(self):
        pass
    def refresh(self):
        pass
class CanceledException(Exception):
    pass
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
class CancelableProgressNotifier(object):
    def __init__(self,queue,num_major_levels):
        self.queue = queue
        self.canceled = False
        self.current_major_label = ""
        self.current_major_level = -1
        self.current_minor_level = 0
        self.num_major_levels = num_major_levels
        self.num_minor_levels = 0
        self.minor_level_streak = 1.0/num_major_levels
        self.done = False
    def update_major(self,minor_levels = 0,raise_if_canceled = True):
        if raise_if_canceled and self.canceled:
            raise CanceledException()
        self.current_major_label = ""
        self.current_major_level+=1
        self.num_minor_levels = minor_levels+1
        self.current_minor_level = 0
        x = self.current_major_level / self.num_major_levels
        if x>1:
            x=1
        self.queue.put(("level",x))
    def update_minor(self,raise_if_canceled = True):
        if raise_if_canceled and self.canceled:
            raise CanceledException()
        if self.current_major_level < 0:
            self.current_major_level = 0
        self.current_minor_level += 1
        if self.num_minor_levels != 0:
            x = self.current_major_level / self.num_major_levels + (self.current_minor_level / self.num_minor_levels)*self.minor_level_streak
        else:
            x = self.current_major_level / self.num_major_levels
        if x>1:
            x=1
        self.queue.put(("level",x))
    def set_major_text(self,text):
        self.current_major_label = text
        self.queue.put(("text",self.current_major_label))
    def set_minor_text(self,text):
        self.queue.put(("text",self.current_major_label + " - " + text))
    def refresh(self):
        if self.canceled:
            raise CanceledException()
    def cancel(self):
        self.canceled = True
class ShenidamFileProcessor(object):
    def __init__(self,model,notifier):
        self.base_fn = model.base_fn
        self.input_tracks = model.input_tracks
        self.output_params = model.output_params
        self.transcode_base = model.transcode_base if model.transcode_base is not None else not Shenidam(model.shenidam).can_open(model.base_fn)
        self.tmp_dir = model.tmp_dir
        self.output_tmp_dir = model.output_tmp_dir if model.output_tmp_dir is not None else self.tmp_dir
        self.shenidam = model.shenidam
        self.ffmpeg = model.ffmpeg
        self.shenidam_extra_args = model.shenidam_extra_args
        self.shenidam = model.shenidam
        self.ffmpeg = model.ffmpeg
        self.verbose = not model.quiet and model.verbose
        self.quiet = model.quiet
        self.notifier = notifier
        self.audio_export_params = model.audio_export_params
        self.default_audio_remix_params = model.default_audio_remix_params if model.default_audio_remix_params is not None else "-acodec copy"
        self.default_av_audio_remix_params = model.default_av_audio_remix_params if model.default_av_audio_remix_params is not None else "-vcodec copy -acodec copy"
    def create_temporary_file_name(self):
        return os.path.join(self.tmp_dir,"shenidam-av-tmp-"+uuid.uuid4().hex)
    def shenidam_updater(self,line,event):
        if event["MESSAGE"] in ("base-read","track-read","track-position-determined","wrote-file"):
            assert self.num_converted < len(self.input_tracks)
            self.notifier.update_minor()
            if event["MESSAGE"]=="base-read":
                self.notifier.set_minor_text("Base file processed")
            elif event["MESSAGE"]=="track-read":
                self.notifier.set_minor_text("Track '{0}' loaded".format(self.input_tracks[self.num_converted]))
            elif event["MESSAGE"]=="track-position-determined":
                self.notifier.set_minor_text("Track '{0}' mapped".format(self.input_tracks[self.num_converted]))
            elif event["MESSAGE"]=="wrote-file":
                self.notifier.set_minor_text("Track '{0}' exported ".format(self.input_tracks[self.num_converted]))
                self.num_converted+=1
    def convert(self):
        try:
            base = self.base_fn
            if self.transcode_base:
                base = self.create_temporary_file_name()
            with TemporaryFile([base],self.transcode_base):
                shenidam_e = Shenidam(self.shenidam)
                transcoding_required = [not shenidam_e.can_open(x) for x in self.input_tracks]
                input_fns_with_needs_transcoding = [((self.create_temporary_file_name() if transcoding_required[i] else x),transcoding_required[i]) for (i,x) in enumerate(self.input_tracks)]
                input_transcoded_fns = [x for (x,y) in input_fns_with_needs_transcoding if y]
                input_fns = [x for (x,y) in input_fns_with_needs_transcoding]
                input_fns_to_transcode = [x for (i,x) in enumerate(self.input_tracks) if transcoding_required[i]]
                self.notifier.update_major()#1 Transcoding base:
                if self.transcode_base:
                    self.notfier.set_major_text("Transcoding base")
                    self.extract_audio(self.base_fn,base)
                with TemporaryFile(input_transcoded_fns):
                    output_temp_files = [self.create_temporary_file_name() for x in self.input_tracks]
                    self.notifier.update_major(len(input_fns_to_transcode))#2 Extracting audio:
                    if len(input_fns_to_transcode):
                        self.notifier.set_major_text("Extracting audio")
                    for x,y in zip(input_fns_to_transcode,input_transcoded_fns):
                        self.notifier.update_minor()
                        self.notifier.set_minor_text("Extracting audio of file '{0}'".format(x))
                        self.extract_audio(x,y)
                    with TemporaryFile(output_temp_files):
                        self.notifier.update_major(len(input_fns)*3+1)#3 Running shenidam:
                        self.notifier.set_major_text("Running shenidam")
                        self.run_shenidam(base,input_fns,output_temp_files)
                        delete_filenames([base],self.transcode_base)
                        delete_filenames(input_transcoded_fns)
                        output_remixed_files = [[filename_from_pattern(ix[0],ix[1],output_pattern) for ix in enumerate(self.input_tracks)] for (output_pattern,d1,d2) in self.output_params]
                        remixed_temp_files = [[self.create_temporary_file_name()+"."+os.path.basename(x) for x in y] for y in output_remixed_files]
                        remixed_temp_files_all = [item for sublist in remixed_temp_files for item in sublist]
                        with TemporaryFile(remixed_temp_files_all):
                            self.notifier.update_major(len(self.output_params)*len(self.input_tracks))#4 remixing audio
                            self.notifier.set_major_text("Remixing audio")
                            for i,(output_pattern,audio_only,audio_remix_params) in enumerate(self.output_params):
                                for input_av,audio,temp_output_av in zip(self.input_tracks,output_temp_files,remixed_temp_files[i]):
                                    self.notifier.update_minor()
                                    self.notifier.set_minor_text("Remixing file '{0}'".format(input_av))
                                    self.remix_audio(input_av,audio,temp_output_av,audio_only,audio_remix_params)
                            delete_filenames(output_temp_files)
                            self.notifier.update_major(len(self.output_params)*len(self.input_tracks))#5 copying result
                            self.notifier.set_major_text("Copying result")
                            for i in range(len(output_remixed_files)):
                                for output_av,temp_output_av in zip(output_remixed_files[i],remixed_temp_files[i]):
                                    self.notifier.update_minor()
                                    self.notifier.set_minor_text("Copying file '{0}'".format(output_av))
                                    shutil.move(temp_output_av,output_av)
        finally:
            self.notifier.done=True
    

    def raise_subprocess_error(self,cmd,stderr,show_error=True):
        raise SubprocessError("Command '{cmd}' failed{error}".format(cmd=cmd,error=(", error stream was:\n"+stderr) if show_error else ""))
    def run_command(self,cmd):
        try:
            stderr_forward = forward(sys.stderr) if self.verbose else do_nothing;
            
            res,stdout,stderr = ProcessRunner(cmd,stderr_forward,stderr_forward,self.notifier.refresh)()
            if res != 0:
                self.raise_subprocess_error(cmd,stderr)
        except OSError as e:
            self.raise_subprocess_error(cmd,str(e))
    def extract_audio(self,avfilename,outfn):
        self.run_command("\"{exec_}\" -y -v 0 -loglevel error -i \"{avfilename}\" -vn {audio_export_params} \"{outfn}\"".format(exec_=self.ffmpeg,avfilename=avfilename,outfn=outfn,audio_export_params=self.audio_export_params))

    def run_shenidam(self,base_fn,track_fns,output_fns):
        try:
            self.num_converted = 0
            stderr_forward = forward(sys.stderr) if self.verbose else do_nothing;
            message_handler = self.shenidam_updater
            cmd,res,stdin,stderr = Shenidam(self.shenidam,self.shenidam_extra_args,message_handler,stderr_forward,self.notifier.refresh)(base_fn,track_fns,output_fns)
            if res != 0:
                self.raise_subprocess_error(cmd,stderr)
        except OSError as e:
            self.raise_subprocess_error(cmd,str(e))

    def remix_audio(self,avfilename,track_fn,output_fn,audio_only,audio_remix_params):
        if audio_remix_params is None or audio_remix_params.strip() == "default":
            audio_remix_params = self.default_audio_remix_params if audio_only else self.default_av_audio_remix_params
        if audio_only:
            self.run_command("\"{ffmpeg}\" -y -v 0 -loglevel error -i \"{track_fn}\" {audio_remix_params} \"{output_fn}\"".format(ffmpeg = self.ffmpeg, track_fn=track_fn,output_fn=output_fn,audio_remix_params=audio_remix_params))
        else:
            self.run_command("\"{ffmpeg}\" -y -v 0 -loglevel error -i \"{avfilename}\" -i \"{track_fn}\" -map 0:0 -map 1:0  {audio_remix_params} \"{output_fn}\"".format(ffmpeg = self.ffmpeg, avfilename=avfilename,track_fn=track_fn,output_fn=output_fn,audio_remix_params=audio_remix_params))
class FileProcessorModel(object):
    audio_export_params="-acodec pcm_s24le -f wav"
    transcode_base = None
    tmp_dir=tempfile.gettempdir()
    shenidam="shenidam"
    ffmpeg="ffmpeg"
    shenidam_extra_args=""
    quiet=False
    verbose=False
    base_fn = None
    default_av_audio_remix_params = None
    default_audio_remix_params = None
    output_tmp_dir = None
    def __init__(self):
        self.output_params=[]
        self.input_tracks = []
class ModelException(Exception):
    pass
def check_file_write(path):
    if os.path.isdir(path):
        raise ModelException("'"+path+"' is a directory")
    if not os.access(path,os.F_OK):
        path = os.path.dirname(path)
        if not path:
            path = "."
    if not os.access(path,os.W_OK):
        raise ModelException("Cannot write file '"+path+"'")
def check_file_read(path):
    if os.path.isdir(path):
        raise ModelException("'"+path+"' is a directory")
    if not os.access(path,os.R_OK):
        raise ModelException("Cannot read file '"+path+"'")
def check_model(model):
    check_file_read(model.base_fn)
    if not model.input_tracks:
        raise ModelException("No input tracks")
    if not model.output_params:
        raise ModelException("No output tracks")
    for x in model.input_tracks:
        check_file_read(x)
    for y,d1,d2 in model.output_params:
        for i,x in enumerate(model.input_tracks):
            check_file_write(filename_from_pattern(i,x,y))
    if not os.path.isdir(model.tmp_dir) and not os.access(model.tmp_dir,os.W_OK):
        raise ModelException("Cannot write to temporary directory '"+model.tmp_dir+"'")
    if not os.path.isdir(model.output_tmp_dir) and not os.access(model.output_tmp_dir,os.W_OK):
        raise ModelException("Cannot write to output temporary directory '"+model.output_tmp_dir+"'")
    if subprocess.call([model.ffmpeg ,"-version"],stdin=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False):
        raise ModelException("Cannot run ffmpeg. Check path.")
    if subprocess.call([model.shenidam,"--shenidam-return-only"],stdin=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False):
        raise ModelException("Cannot run shenidam. Check path.")
