#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
from libc import Clone, mount
from libc import MS_NODEV, MS_NOEXEC, MS_NOSUID

nullfile = open("/dev/null")

class Container:

    def __init__(self, cmd, tty=True):
        self.cmd = cmd
        self.clone = Clone(Container.childFunc, args=(self,))
        self.tty = tty

        # pipe 其实不去执行/proc/self/exe时，可以不用pipe来传递
        rfd, wfd = os.pipe()
        self.readpipe = os.fdopen(rfd, 'r')
        self.writepipe = os.fdopen(wfd, 'w')
        return

    # parent
    def run(self):
        self.clone.start()
        # parent close read
        self.readpipe.close()

        self.writepipe.write(self.cmd)
        self.writepipe.close()
        print("cmd: %s" % self.cmd)
        return

    # parent
    def wait(self):
        self.clone.wait()
        return

    # child
    def readInitCommand(self):
        # parent close write
        self.writepipe.close()

        cmd = self.readpipe.read()
        self.readpipe.close()
        return cmd

    # child
    def childFunc(self):
        # parse arg
        if not self.tty:
            sys.stdout = nullfile
            sys.stdin  = nullfile
            sys.stderr = nullfile
            print("[*] stdin/out/err Redirect /dev/null.")

        # read init command
        cmd = self.readInitCommand()
        print("[*] command: {}".format(cmd))

        # mount /proc
        ret = mount("proc", "/proc", "proc", MS_NODEV | MS_NOEXEC | MS_NOSUID)
        if ret != 0:
            print("[!!!] ERROR mount proc failed({})".format(ret))
            return

        # cgroup

        # exec command
        os.system(cmd)
        # os.exec
        return

def main():
    container = Container(cmd="/bin/bash", tty=True)
    container.run()
    container.wait()
    return

if __name__ == '__main__':
    main()