#include <csignal>
#include <cstdio>
#include <iomanip>
#include <iostream>
#include <memory>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

/* #define _GNU_SOURCE */
#include <sched.h>

using namespace std;

int run(void *arg)
{
  char buffer[1024];
  gethostname(buffer, 1024);
  cout << "child hostname(before): " << buffer << endl;

  int len = sprintf(buffer, "mydocker");
  sethostname(buffer, len);

  gethostname(buffer, 1024);
  cout << "child hostname(after): " << buffer << endl;

  system("/bin/bash");
  cout << "bash finished!" << endl;
  return 0;
}

int main(int argc, char *argv[])
{
  const int kStackSize = 8 * 1024 * 1024;
  unique_ptr<char> child_stack(new char[kStackSize]);

  char buffer[1024];
  gethostname(buffer, 1024);
  cout << endl << "curr hostname(before): " << buffer << endl;

  cout << hex;
  cout << "clone_newuts: " << CLONE_NEWUTS << endl;
  cout << "clone_newipc: " << CLONE_NEWIPC << endl;
  cout << "clone_newpid: " << CLONE_NEWPID << endl;
  cout << "clone_newns: " << CLONE_NEWNS << endl;
  cout << "clone_newuser: " << CLONE_NEWUSER << endl;
  cout << "clone_newnet: " << CLONE_NEWNET << endl;
  cout << "clone_newcgroup: " << CLONE_NEWCGROUP << endl;
  cout << dec;
  int ret = clone(run, child_stack.get() + kStackSize,
                  CLONE_NEWUTS |
                  CLONE_NEWIPC |
                  CLONE_NEWPID |
                  CLONE_NEWNS  |
                  /* CLONE_NEWUSER| */
                  SIGCHLD,
                  0);
  if (ret < 0) {
    perror("clone: ");
    return -1;
  }
  printf("clone ret: %d\n", ret);
  pid_t pid = waitpid(-1, 0, 0);
  cout << "child finished! "
       << "pid: " << pid << " "
       << "selfpid: "<< getpid() << " "
       << endl;
  gethostname(buffer, 1024);
  cout << "parent hostname(after): " << buffer << endl;
  return 0;
}