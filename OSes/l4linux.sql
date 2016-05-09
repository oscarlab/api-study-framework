INSERT INTO system_compatibility (target_name, syscalls)
VALUES ('l4linux', '{
"read",
"write",
"open",
"close",
"stat",
"fstat",
"lstat",
"poll",
"lseek",
"mmap",
"mprotect",
"munmap",
"brk",
"rt_sigaction",
"rt_sigprocmask",
"rt_sigreturn",
"ioctl",
"pread64",
"pwrite64",
"readv",
"writev",
"access",
"pipe",
"select",
"sched_yield",
"mremap",
"msync",
"mincore",
"madvise",
"shmget",
"shmat",
"shmctl",
"dup",
"dup2",
"pause",
"nanosleep",
"getitimer",
"alarm",
"setitimer",
"getpid",
"sendfile",
"socket",
"connect",
"accept",
"sendto",
"recvfrom",
"sendmsg",
"recvmsg",
"shutdown",
"bind",
"listen",
"getsockname",
"getpeername",
"socketpair",
"setsockopt",
"getsockopt",
"clone",
"fork",
"vfork",
"execve",
"exit",
"wait4",
"kill",
"uname",
"semget",
"semop",
"semctl",
"shmdt",
"msgget",
"msgsnd",
"msgrcv",
"msgctl",
"fcntl",
"flock",
"fsync",
"fdatasync",
"truncate",
"ftruncate",
"getdents",
"getcwd",
"chdir",
"fchdir",
"rename",
"mkdir",
"rmdir",
"creat",
"link",
"unlink",
"symlink",
"readlink",
"chmod",
"fchmod",
"chown",
"fchown",
"lchown",
"umask",
"gettimeofday",
"getrlimit",
"getrusage",
"sysinfo",
"times",
"ptrace",
"getuid",
"syslog",
"getgid",
"setuid",
"setgid",
"geteuid",
"getegid",
"setpgid",
"getppid",
"getpgrp",
"setsid",
"setreuid",
"setregid",
"getgroups",
"setgroups",
"setresuid",
"getresuid",
"setresgid",
"getresgid",
"getpgid",
"setfsuid",
"setfsgid",
"getsid",
"capget",
"capset",
"rt_sigpending",
"rt_sigtimedwait",
"rt_sigqueueinfo",
"rt_sigsuspend",
"sigaltstack",
"utime",
"mknod",
"personality",
"ustat",
"statfs",
"fstatfs",
"sysfs",
"getpriority",
"setpriority",
"sched_setparam",
"sched_getparam",
"sched_setscheduler",
"sched_getscheduler",
"sched_get_priority_max",
"sched_get_priority_min",
"sched_rr_get_interval",
"mlock",
"munlock",
"mlockall",
"munlockall",
"vhangup",
"modify_ldt",
"pivot_root",
"sysctl",
"prctl",
"arch_prctl",
"adjtimex",
"setrlimit",
"chroot",
"sync",
"settimeofday",
"mount",
"umount2",
"swapon",
"swapoff",
"reboot",
"sethostname",
"setdomainname",
"iopl",
"ioperm",
"init_module",
"gettid",
"readahead",
"setxattr",
"lsetxattr",
"fsetxattr",
"getxattr",
"lgetxattr",
"fgetxattr",
"listxattr",
"llistxattr",
"flistxattr",
"removexattr",
"lremovexattr",
"fremovexattr",
"tkill",
"time",
"futex",
"sched_setaffinity",
"sched_getaffinity",
"io_setup",
"io_destroy",
"io_getevents",
"io_submit",
"io_cancel",
"epoll_create",
"remap_file_pages",
"getdents64",
"set_tid_address",
"restart_syscall",
"semtimedop",
"fadvise64",
"timer_create",
"timer_settime",
"timer_gettime",
"timer_getoverrun",
"timer_delete",
"clock_settime",
"clock_gettime",
"clock_getres",
"clock_nanosleep",
"exit_group",
"epoll_wait",
"epoll_ctl",
"tgkill",
"utimes",
"mq_open",
"mq_unlink",
"mq_timedsend",
"mq_timedreceive",
"mq_notify",
"mq_getsetattr",
"waitid",
"ioprio_set",
"ioprio_get",
"inotify_init",
"inotify_add_watch",
"inotify_rm_watch",
"openat",
"mkdirat",
"mknodat",
"fchownat",
"futimesat",
"newfstatat",
"unlinkat",
"renameat",
"linkat",
"symlinkat",
"readlinkat",
"fchmodat",
"faccessat",
"pselect6",
"ppoll",
"unshare",
"set_robust_list",
"get_robust_list",
"splice",
"tee",
"sync_file_range",
"vmsplice",
"utimensat",
"epoll_pwait",
"signalfd",
"timerfd_create",
"eventfd",
"fallocate",
"timerfd_settime",
"timerfd_gettime",
"accept4",
"signalfd4",
"eventfd2",
"epoll_create1",
"dup3",
"pipe2",
"inotify_init1",
"preadv",
"pwritev",
"rt_tgsigqueueinfo",
"perf_event_open",
"recvmmsg",
"prlimit64",
"name_to_handle_at",
"open_by_handle_at",
"clock_adjtime",
"syncfs",
"sendmmsg",
"setns",
"getcpu",
"process_vm_readv",
"process_vm_writev",
"finit_module",
"sched_setattr",
"sched_getattr",
"renameat2",
"seccomp",
"getrandom",
"memfd_create",
"execveat",
"membarrier"
}');