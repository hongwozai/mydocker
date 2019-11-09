#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import time
import random
from libc import Clone, mount
from libc import MS_NODEV, MS_NOEXEC, MS_NOSUID, MS_STRICTATIME, MS_RELATIME, MS_RELATIME, MS_BIND, MS_REC, MS_PRIVATE
from libc import pivot_root
from cgroups import CGroup
import shutil

nullfile = open("/dev/null")

"""
目录结构
<path>/config.json
<path>/info.json
<path>/<uuid>/
<path>/<uuid>/<image-name>
<path>/<uuid>/writeLayer
<path>/<uuid>/mnt
"""

class Container:

    def __init__(self, path, image, cmd,
                 name="", tty=True, conf={}):
        self.path = path
        self.image = image
        self.cmd = cmd
        self.name = name
        self.uuid = self.getUUID()

        self.tty = tty
        self.clone = Clone(Container.childFunc, args=(self,), newUser=False)

        self.containerPath = os.path.join(self.path, str(self.uuid))
        self.imagePath = os.path.join(self.containerPath,
                                      os.path.basename(self.image).replace(".tar", ""))
        self.writeLayerPath = os.path.join(self.containerPath, "writeLayer")
        self.mntPath = os.path.join(self.containerPath, "mnt")
        return

    def getUUID(self):
        return int(random.uniform(0, 1000))

    # parent
    def run(self):
        # pipe 其实不去执行/proc/self/exe时，可以不用pipe来传递
        rfd, wfd = os.pipe()
        self.readpipe = os.fdopen(rfd, 'r')
        self.writepipe = os.fdopen(wfd, 'w')

        # 执行子进程
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

        # 正常退出
        print("[*] delete space...")
        self.deleteSpace()
        self.deleteSpace()
        return

    # child
    def readInitCommand(self):
        # parent close write
        self.writepipe.close()

        cmd = self.readpipe.read()
        self.readpipe.close()
        return cmd

    def pivotRoot(self, new_root):

        # new_root, put_old不能存在与同一个文件系统中
        # 所以这里要重新绑定一下（虽然实质是在一块硬盘上，一个系统，但重新绑定之后，即可）
        print("[*] mount {} rebind".format(new_root))
        # mount(new_root, new_root, "bind", MS_BIND | MS_REC)

        # !!!!!!!
        mount("none", "/", "", MS_REC|MS_PRIVATE)

        self.pivotRootPath = os.path.join(self.mntPath, ".pivot_root")
        os.mkdir(self.pivotRootPath)

        print("[*] pivot_root: new_root: {}, put_old:{}"
              .format(self.mntPath, self.pivotRootPath))

        try:
            pivot_root(self.mntPath, self.pivotRootPath)
        except Exception as e:
            print("fffff: {}".format(e))

        os.chdir("/")
        return

    def newSpace(self):
        # 容器目录
        os.mkdir(self.containerPath)
        os.mkdir(self.imagePath)
        os.mkdir(self.writeLayerPath)
        os.mkdir(self.mntPath)

        # 解压镜像
        print("[*] exec tar xvf {} -C {}".format(self.image, self.imagePath))
        status = os.system("tar xf {} -C {}".format(self.image, self.imagePath))
        if status != 0:
            print("[!!!] ERROR tar failed")
            raise Exception("tar failed")

        # 映射权限 先不使用user
        # with open("/proc/self/uid_map", "w") as f:
        #     f.write("0 1000 100")
        # with open("/proc/self/gid_map", "w") as f:
        #     f.write("0 1000 100")

        # 挂载aufs
        option = "dirs={}=rw:{}=r".format(self.writeLayerPath, self.imagePath)
        status = os.system("mount -t aufs -o {} none {}".format(option, self.mntPath))
        if status != 0:
            print("[!!!] ERROR mount aufs failed ")
            raise Exception("mount aufs failed")

        self.pivotRoot(self.mntPath)

        # mount /proc /dev /sys
        mount("proc", "/proc", "proc",
              MS_NODEV | MS_NOEXEC | MS_NOSUID)
        mount("tmpfs", "/dev", "tmpfs", MS_NOSUID | MS_STRICTATIME)
        mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_RELATIME | MS_NODEV | MS_NOEXEC)
        return

    def deleteSpace(self):
        status = os.system("umount {}".format(self.mntPath))
        print("[*] umount(ret {}) {}".format(status, self.mntPath))

        # delete
        try:
            shutil.rmtree(self.containerPath)
            pass
        except Exception as e:
            print("[*] rm {}".format(e))
        return

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

        # newspace
        try:
            self.newSpace()
        except Exception as e:
            print("[!!!] ERROR {}".format(e))
            self.deleteSpace()
            return

        # cgroup

        # exec command
        cmdvec = cmd.split()
        os.execv(cmdvec[0], cmdvec)
        return

def main():
    container = Container(path="../bin/",image="../images/busybox.tar",cmd="/bin/sh", tty=True)
    container.run()
    container.wait()
    return

if __name__ == '__main__':
    main()