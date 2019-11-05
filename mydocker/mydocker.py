#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
from ns import Clone

class RunCommand:

    def __init__(self):
        return

    def run(self):
        print("pid: {}".format(os.getpid()))
        os.system("/bin/bash")
        return


def main():
    rc = RunCommand()
    Clone(func=RunCommand.run, args=(rc,)).start().wait()
    return

if __name__ == '__main__':
    main()