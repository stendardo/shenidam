import threading
import subprocess
import sys
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
def do_nothing(*args,**kwds):
    pass
def forward(stream):
    def inner(line):
        stream.write(line)
    return inner
class StreamReader(threading.Thread):
    def __init__(self,callbacks,stream):
        self.callbacks = callbacks
        self.stream = stream
        super(StreamReader,self).__init__()
    def run(self):
        try:
            line = self.stream.readline();
            while line:
                for callback in self.callbacks:
                    callback(line)
                line = self.stream.readline();
        except KeyboardInterrupt:
            threading.current_thread().interrupt_main()
class ProcessRunner(object):
    def __init__(self,command,stdout_callback=do_nothing,stderr_callback=do_nothing):
        self.command = command
        self.stdout_callback = stdout_callback
        self.stderr_callback = stderr_callback
    def __call__(self):
        stdout_sio = StringIO.StringIO()
        stderr_sio = StringIO.StringIO()
        process = None
        try:
            process = subprocess.Popen(self.command,bufsize=1,stdin=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
            stdout_reader = StreamReader([forward(stdout_sio),self.stdout_callback],process.stdout)
            stderr_reader = StreamReader([forward(stderr_sio),self.stderr_callback],process.stderr)
            stdout_reader.start();
            stderr_reader.start();
            stdout_reader.join();
            stderr_reader.join();
            process.wait();
        except:
            try:
                process.terminate();
            except Exception:
                pass
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
    def __init__(self,executable,extra_args,message_callback,error_callback=forward(sys.stderr)):
        def mycallback(line):
            return message_callback(line,_parse_event(line))
        self.output_callback = mycallback
        self.executable = executable
        self.extra_args = extra_args
        self.error_callback = error_callback
    def __call__(self,base,input_tracks,output_tracks):
        if len(input_tracks) <= 0:
            raise ValueError("No input tracks")
        if len(input_tracks) != len(output_tracks):
            raise ValueError("len(input_tracks) != len(output_tracks)")
        args= "-i "
        for x in input_tracks:
            args+= "\"{0}\" ".format(x)
        args+= "-o "
        for x in output_tracks:
            args+= "\"{0}\" ".format(x)
        cmd = "{executable} -m {extra_args} -n {numargs} -b \"{base}\" {args}".format(executable=self.executable,base=base,numargs=len(input_tracks),args=args,extra_args=self.extra_args)
        res,stdout,stderr = ProcessRunner(cmd,self.output_callback,self.error_callback)()
        return cmd,res,stdout,stderr
