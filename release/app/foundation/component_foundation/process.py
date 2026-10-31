"""Bounded subprocess execution for pinned local adapters only."""
import ctypes
import os
import subprocess
import threading
import time
from ctypes import wintypes
from .safety import FoundationError


class Job:
    def __init__(self, process, memory_mb=512):
        self.handle = None
        if os.name != 'nt':
            raise FoundationError('This release supports Windows only')
        class Basic(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                        ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class Extended(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', Basic), ('IoInfo', IO), ('ProcessMemoryLimit', ctypes.c_size_t),
                        ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.handle = self.api.CreateJobObjectW(None, None)
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000 | 0x100 | 0x8  # kill-on-close, memory, active process
        info.BasicLimitInformation.ActiveProcessLimit = 1
        info.ProcessMemoryLimit = memory_mb * 1024 * 1024
        if not self.handle or not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise FoundationError('Unable to configure process limits')
        if not self.api.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            code = ctypes.get_last_error()
            self.close()
            raise FoundationError('Unable to enforce process limits: ' + str(code))

    def terminate(self):
        if self.handle:
            self.api.TerminateJobObject(self.handle, 1)

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def execute(argv, cwd, timeout, max_output=1024 * 1024, memory_mb=512):
    # Explicit environment allowlist; no provider credentials or inherited Python hooks.
    env = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'NUMBER_OF_PROCESSORS') if key in os.environ}
    env.update({'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'})
    started = time.monotonic()
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    job = None
    buffers = [bytearray(), bytearray()]
    overflow = threading.Event()
    def drain(pipe, dest):
        try:
            while True:
                part = pipe.read(4096)
                if not part:
                    break
                remaining = max_output - len(dest)
                dest.extend(part[:max(0, remaining)])
                if len(part) > remaining:
                    overflow.set()
        finally:
            pipe.close()
    try:
        job = Job(proc, memory_mb)
        workers = [threading.Thread(target=drain, args=(proc.stdout, buffers[0]), daemon=True),
                   threading.Thread(target=drain, args=(proc.stderr, buffers[1]), daemon=True)]
        for worker in workers:
            worker.start()
        outcome = 'completed'
        while proc.poll() is None:
            if overflow.is_set():
                outcome = 'output_limit'
                job.terminate()
                break
            if time.monotonic() - started > timeout:
                outcome = 'timeout'
                job.terminate()
                break
            time.sleep(0.02)
        proc.wait(timeout=5)
        for worker in workers:
            worker.join(timeout=5)
        if overflow.is_set():
            outcome = 'output_limit'
        return {'outcome': outcome, 'exit_code': proc.returncode,
                'elapsed_seconds': round(time.monotonic() - started, 6),
                'stdout': bytes(buffers[0]), 'stderr': bytes(buffers[1]),
                'limits': {'timeout_seconds': timeout, 'output_bytes_per_stream': max_output,
                           'memory_mb': memory_mb, 'active_processes': 1},
                'environment': env}
    finally:
        if proc.poll() is None:
            if job:
                job.terminate()
            else:
                proc.kill()
        proc.wait(timeout=5)
        if job:
            job.close()

