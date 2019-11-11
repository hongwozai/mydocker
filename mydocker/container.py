#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import time
import random
from libc import Clone, mount
from libc import MS_NODEV, MS_NOEXEC, MS_NOSUID, MS_STRICTATIME, MS_RELATIME, MS_RELATIME, MS_BIND, MS_REC, MS_PRIVATE
from libc import MNT_DETACH
from libc import pivot_root
from libc import umount
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
                 name="", tty=True, net="bridge", volume=""):
        self.path = path
        self.image = image
        self.cmd = cmd
        self.name = name
        self.uuid = self.getUUID()
        self.volume = volume
        self.tty = tty

        netMod = True
        if net == "host":
            netMod = False

        self.clone = Clone(Container.childFunc, args=(self,),
                           newUser=False,
                           newNet=netMod)

        self.containerPath = os.path.join(self.path, str(self.uuid))
        self.imagePath = os.path.join(self.containerPath,
                                      os.path.basename(self.image).replace(".tar", ""))
        self.writeLayerPath = os.path.join(self.containerPath, "writeLayer")
        self.mntPath = os.path.join(self.containerPath, "mnt")

        v = self.volume.split(":")
        if v[1].startswith("/"):
            v[1] = v[1].lstrip("/")
        self.originVolumePath = v[0]
        self.volumeMntPath = os.path.join(self.mntPath, v[1])

        return

    def getUUID(self):
        return int(random.uniform(0, 1000))

    # 需要在clone start之后运行
    def getChildPid(self):
        return self.clone.childPid

    # parent
    def run(self):
        # pipe 其实不去执行/proc/self/exe时，可以不用pipe来传递
        rfd, wfd = os.pipe()
        self.readpipe = os.fdopen(rfd, 'r')
        self.writepipe = os.fdopen(wfd, 'w')

        # 执行子进程
        self.clone.start()

        if self.clone.childPid == -1:
            print("[!!!] child start failed")
            return

        # parent close read
        self.readpipe.close()

        self.writepipe.write(self.cmd)
        self.writepipe.close()
        print("cmd: %s" % self.cmd)
        return

    # parent
    def wait(self):
        if not self.clone.wait():
            return

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

        # !!!!!!! 这句是重点，可以保证pivot_root的成功运行
        # pivot_root限制new_root与put_old不能是MS_SHARED，来避免传播到其他namespace
        mount("none", "/", "", MS_REC|MS_PRIVATE)

        self.pivotRootPath = os.path.join(self.mntPath, ".pivot_root")
        os.mkdir(self.pivotRootPath)

        print("[*] pivot_root: new_root: {}, put_old:{}"
              .format(self.mntPath, self.pivotRootPath))

        pivot_root(self.mntPath, self.pivotRootPath)

        os.chdir("/")

        # 取消掉.pivot_root
        ret = umount("/.pivot_root", MNT_DETACH)
        print("[*] umount /.pivot_root ret: {}".format(self.pivotRootPath, ret))
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

        # volume 同样使用aufs方式挂载
        os.mkdir(self.volumeMntPath)
        status = os.system("mount -t aufs -o dirs={} none {}".
                           format(self.originVolumePath, self.volumeMntPath))
        print("[*] status: {}, mount {} to {}".format(status, self.originVolumePath, self.volumeMntPath))

        # pivot_root
        self.pivotRoot(self.mntPath)

        # mount /proc /dev /sys
        mount("proc", "/proc", "proc",
              MS_NODEV | MS_NOEXEC | MS_NOSUID)
        mount("tmpfs", "/dev", "tmpfs", MS_NOSUID | MS_STRICTATIME)
        mount("sysfs", "/sys", "sysfs", MS_NOSUID | MS_RELATIME | MS_NODEV | MS_NOEXEC)
        return

    def deleteSpace(self):
        status = os.system("umount {}".format(self.volumeMntPath))
        print("[*] umount(ret {}) {}".format(status, self.volumeMntPath))

        status = os.system("umount {}".format(self.mntPath))
        print("[*] umount(ret {}) {}".format(status, self.mntPath))

        # delete
        try:
            shutil.rmtree(self.containerPath)
            pass
        except Exception as e:
            print("[*] rm {}".format(e))
        print("[*] rm {}".format(self.containerPath))
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
    container = Container(path="../bin/",
                          image="../images/busybox.tar",
                          cmd="/bin/sh",
                          tty=True,
                          net="bridge",
                          volume="../volume:/root/home")
    container.run()
    container.wait()
    return

if __name__ == '__main__':
    main()
