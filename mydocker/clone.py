#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from ctypes import *

class Clone(object):

    def __init__(self, **kwargs):
        pass

def child(cloneobj):
    print("asdfasdfasdfasdfasdf")
    print(type(cloneobj))
    print(cloneobj)
    return 1

def main():
    libc = CDLL("libc.so.6")
    # libc.printf(c_char_p("hello world!\n"));

    stack = create_string_buffer(8096)
    stack_top = c_void_p(cast(stack, c_void_p).value + 8096)

    clone = Clone()
    # callback = CFUNCTYPE(c_int, c_void_p)(child)
    callback = CFUNCTYPE(c_int, c_void_p)(cloneFunc)
    b = libc.clone(callback, stack_top, 0,
                   cast(pointer(py_object(clone)), c_void_p));
    print(b)
    return

if __name__ == '__main__':
    main()