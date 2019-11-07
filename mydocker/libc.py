#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
相关的c接口封装
"""

import os
from ctypes import *
from signal import SIGCHLD

libc = CDLL("libc.so.6")

# =================== clone =======================
CLONE_NEWNS   = 0x20000
CLONE_NEWUTS  = 0x4000000
CLONE_NEWIPC  = 0x8000000
CLONE_NEWPID  = 0x20000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWNET  = 0x40000000
CLONE_NEWCGROUP = 0x2000000

class Clone(object):

    def __init__(self, func=None, args=(), **kwargs):
        """
        default:
            newuts: true
            newipc: true
            newns: true
            newpid: true
            newuser: true
            stacksize: 8096
        """
        self.func = func
        self.args = args
        self.stackSize = kwargs.get("stackSize", 8096)
        self.newUts = kwargs.get("newUts", True)
        self.newIpc = kwargs.get("newIpc", True)
        self.newNs  = kwargs.get("newNs", True)
        self.newPid = kwargs.get("newPid", True)
        self.newUser = kwargs.get("newUser", True)
        self.newNet = kwargs.get("newNet", True)
        self.newCgroup = kwargs.get("newCgroup", False)
        return

    def getFlags(self):
        flags = SIGCHLD
        if self.newNs:
            flags |= CLONE_NEWNS
        if self.newUts:
            flags |= CLONE_NEWUTS
        if self.newIpc:
            flags |= CLONE_NEWIPC
        if self.newPid:
            flags |= CLONE_NEWPID
        if self.newUser:
            flags |= CLONE_NEWUSER
        if self.newNet:
            flags |= CLONE_NEWNET
        if self.newCgroup:
            flags |= CLONE_NEWCGROUP
        return flags

    def start(self):
        stack = create_string_buffer(self.stackSize)
        stack_top = c_void_p(cast(stack, c_void_p).value + self.stackSize)

        self.childPid = libc.clone(
            # 回调原型
            CFUNCTYPE(c_int, c_void_p)(Clone.cloneCallBackFunc),
            stack_top,
            self.getFlags(),
            cast(pointer(py_object(self)), c_void_p)
        );
        print("os.getpid: {}, childpid: {}".format(os.getpid(), self.childPid))
        return self

    def wait(self):
        pid, status = os.waitpid(-1, 0)
        print("pid: {}, status: {}".format(pid, status))
        return

    def childFunc(self):
        try:
            if self.func:
                self.func(*self.args)
        except Exception as e:
            print("clone func: {}".format(e))
        return 0

    @staticmethod
    def cloneCallBackFunc(pobj):
        clone = cast(pobj, POINTER(py_object)).contents.value
        return clone.childFunc()

# ====================== mount ========================
MS_RDONLY = 0x1
MS_NOSUID = 0x2
MS_NODEV  = 0x4
MS_NOEXEC = 0x8

def mount(source, target, filesystemtype, mountflags, options=""):
    return libc.mount(source, target, filesystemtype, mountflags, options)

def main():

    def hello(a, b):
        import time
        time.sleep(1)
        print("pid: {}, hello! {}, {}".format(os.getpid(), a, b))
        return

    clone = Clone(func=hello, args=(3, 4))
    clone.start()
    clone.wait()
    return

if __name__ == '__main__':
    main()