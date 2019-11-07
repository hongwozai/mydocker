#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
进行资源限制
memory limit in bytes
cpuset 使用cpu核数
cpushare cpu使用占比 < 1024
"""

import os
import sys
from abc import abstractmethod

class CGroup:

    def __init__(self, name):
        self.name = name
        self.subsystems = [
            MemorySubsystem(self.name),
            CpuSetSubsystem(self.name),
            CpuShareSubsystem(self.name)
        ]
        return

    def set(self, conf):
        for subsystem in self.subsystems:
            subsystem.set(conf)
        return

    def apply(self, pid):
        for subsystem in self.subsystems:
            subsystem.apply(pid)
        return

    def remove(self):
        for subsystem in self.subsystems:
            subsystem.remove()
        return

class Subsystem:

    def __init__(self):
        return

    @abstractmethod
    def set(self, conf):
        return

    def remove(self):
        os.removedirs(self.getPath())
        return

    def apply(self, pid):
        with open(self.getPath() + "/tasks", "w") as f:
            f.write("{}\n".format(pid))
        return

    def getCGroupPath(self, subsystem):
        with open("/proc/self/mountinfo") as f:
            for line in f:
                mntinfo = line.split()
                if "cgroup" in mntinfo[8]:
                    if subsystem in mntinfo[10]:
                        # print("[*] mountinfo {}({})".format(subsystem, line))
                        return mntinfo[4]
        return

    @abstractmethod
    def getPath(self):
        raise Exception("virtual class getPath")

    def getPath1(self, subsystem, path, autocreate=True):
        cgroup_path = "/".join([self.getCGroupPath(subsystem), path])
        if autocreate and not os.access(cgroup_path, os.F_OK):
            os.mkdir(cgroup_path)
        return cgroup_path

class MemorySubsystem(Subsystem):

    def __init__(self, cgroup_path):
        self.cgroup_path = cgroup_path
        return

    def set(self, conf):
        if "memoryLimit" not in conf:
            return
        with open(self.getPath() + "/memory.limit_in_bytes", "w") as f:
            f.write("{}".format(conf.get("memoryLimit")))
        return

    def getPath(self):
        return Subsystem.getPath1(self, "memory", self.cgroup_path)

def CpuSetSubsystem(Subsystem):

    def __init__(self, cgroup_path):
        self.cgroup_path = cgroup_path
        return

    def set(self, conf):
        if "cpuSet" not in conf:
            return
        with open(self.getPath() + "/cpuset.cpus", "w") as f:
            f.write("{}".format(conf.get("cpuSet")))
        return

    def getPath(self):
        return Subsystem.getPath1(self, "cpuset", self.cgroup_path)

def CpuShareSubsystem(Subsystem):

    def __init__(self, cgroup_path):
        self.cgroup_path = cgroup_path
        return

    def set(self, conf):
        if "cpuShare" not in conf:
            return
        with open(self.getPath() + "/cpu.shares", "w") as f:
            f.write("{}".format(conf.get("cpuShare")))
        return

    def getPath(self):
        return Subsystem.getPath1(self, "cpuacct", self.cgroup_path)


def main():
    s = MemorySubsystem("654321")
    print(s.getPath())
    # print(s.remove())
    s.apply(13088)
    s.set({"memoryLimit": 120000})
    return

if __name__ == '__main__':
    main()

