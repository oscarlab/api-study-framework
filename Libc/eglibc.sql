INSERT INTO library_compatibility (target_name, lib, calls)
VALUES ('eglibc', 4449, '{
"_rtld_global",
"__libc_enable_secure",
"__tls_get_addr",
"_rtld_global_ro",
"_dl_find_dso_for_object",
"_dl_starting_up",
"_dl_argv",
"putwchar",
"__strspn_c1",
"__gethostname_chk",
"__strspn_c2",
"setrpcent",
"__wcstod_l",
"__strspn_c3",
"epoll_create",
"sched_get_priority_min",
"__getdomainname_chk",
"klogctl",
"__tolower_l",
"dprintf",
"setuid",
"__wcscoll_l",
"iswalpha",
"__internal_endnetgrent",
"chroot",
"__gettimeofday",
"_IO_file_setbuf",
"daylight",
"getdate",
"__vswprintf_chk",
"_IO_file_fopen",
"pthread_cond_signal",
"pthread_cond_signal",
"strtoull_l",
"xdr_short",
"lfind",
"_IO_padn",
"strcasestr",
"xdr_int64_t",
"__libc_fork",
"wcstod_l",
"socket",
"key_encryptsession_pk",
"argz_create",
"putchar_unlocked",
"__stpcpy_chk",
"__xpg_basename",
"__res_init",
"xdr_pmaplist",
"__ppoll_chk",
"fgetsgent_r",
"getc",
"wcpncpy",
"_IO_wdefault_xsputn",
"mkdtemp",
"srand48_r",
"sighold",
"__sched_getparam",
"__default_morecore",
"iruserok",
"cuserid",
"isnan",
"setstate_r",
"wmemset",
"_IO_file_stat",
"argz_replace",
"globfree64",
"argp_usage",
"timerfd_gettime",
"_sys_nerr",
"_sys_nerr",
"_sys_nerr",
"_sys_nerr",
"clock_adjtime",
"getdate_err",
"argz_next",
"__fork",
"getspnam_r",
"__sched_yield",
"__gmtime_r",
"l64a",
"_IO_file_attach",
"wcsftime_l",
"gets",
"fflush",
"_authenticate",
"getrpcbyname",
"putc_unlocked",
"hcreate",
"strcpy",
"a64l",
"xdr_long",
"sigsuspend",
"__libc_init_first",
"shmget",
"_IO_wdo_write",
"getw",
"gethostid",
"__cxa_at_quick_exit",
"__rawmemchr",
"flockfile",
"wcsncasecmp_l",
"argz_add",
"inotify_init1",
"__backtrace_symbols",
"_IO_un_link",
"vasprintf",
"__wcstod_internal",
"authunix_create",
"_mcount",
"__wcstombs_chk",
"wmemcmp",
"gmtime_r",
"fchmod",
"__printf_chk",
"obstack_vprintf",
"sigwait",
"setgrent",
"__fgetws_chk",
"__register_atfork",
"iswctype_l",
"wctrans",
"acct",
"exit",
"_IO_vfprintf",
"execl",
"re_set_syntax",
"htonl",
"wordexp",
"endprotoent",
"getprotobynumber_r",
"isinf",
"__assert",
"clearerr_unlocked",
"fnmatch",
"xdr_keybuf",
"gnu_dev_major",
"__islower_l",
"readdir",
"htons",
"xdr_uint32_t",
"pathconf",
"sigrelse",
"seed48_r",
"psiginfo",
"__nss_hostname_digits_dots",
"execv",
"sprintf",
"_IO_putc",
"nfsservctl",
"envz_merge",
"strftime_l",
"setlocale",
"memfrob",
"mbrtowc",
"srand",
"iswcntrl_l",
"getutid_r",
"execvpe",
"iswblank",
"tr_break",
"__libc_pthread_init",
"__vfwprintf_chk",
"fgetws_unlocked",
"__write",
"__select",
"towlower",
"ttyname_r",
"fopen",
"gai_strerror",
"fgetspent",
"strsignal",
"wcsncpy",
"strncmp",
"getnetbyname_r",
"getprotoent_r",
"svcfd_create",
"ftruncate",
"xdr_unixcred",
"dcngettext",
"xdr_rmtcallres",
"_IO_puts",
"inet_nsap_addr",
"inet_aton",
"ttyslot",
"__rcmd_errstr",
"wordfree",
"posix_spawn_file_actions_addclose",
"getdirentries",
"_IO_unsave_markers",
"_IO_default_uflow",
"__strtold_internal",
"__wcpcpy_chk",
"optind",
"__strcpy_small",
"erand48",
"wcstoul_l",
"modify_ldt",
"argp_program_version",
"__libc_memalign",
"isfdtype",
"getfsfile",
"__strcspn_c1",
"__strcspn_c2",
"lcong48",
"getpwent",
"__strcspn_c3",
"re_match_2",
"__nss_next2",
"__free_hook",
"putgrent",
"getservent_r",
"argz_stringify",
"open_wmemstream",
"inet6_opt_append",
"clock_getcpuclockid",
"setservent",
"timerfd_create",
"strrchr",
"posix_openpt",
"svcerr_systemerr",
"fflush_unlocked",
"__isgraph_l",
"__swprintf_chk",
"vwprintf",
"wait",
"setbuffer",
"posix_memalign",
"posix_spawnattr_setschedpolicy",
"getipv4sourcefilter",
"__vwprintf_chk",
"__longjmp_chk",
"tempnam",
"isalpha",
"strtof_l",
"regexec",
"regexec",
"llseek",
"revoke",
"re_match",
"tdelete",
"pipe",
"readlinkat",
"__wctomb_chk",
"get_avphys_pages",
"authunix_create_default",
"_IO_ferror",
"getrpcbynumber",
"__sysconf",
"argz_count",
"__strdup",
"__readlink_chk",
"register_printf_modifier",
"__res_ninit",
"setregid",
"tcdrain",
"setipv4sourcefilter",
"wcstold",
"cfmakeraw",
"_IO_proc_open",
"perror",
"shmat",
"__sbrk",
"_IO_str_pbackfail",
"__tzname",
"rpmatch",
"__getlogin_r_chk",
"__isoc99_sscanf",
"statvfs64",
"__progname",
"pvalloc",
"__libc_rpc_getport",
"dcgettext",
"_IO_fprintf",
"registerrpc",
"_IO_wfile_overflow",
"wcstoll",
"posix_spawnattr_setpgroup",
"_environ",
"qecvt_r",
"__arch_prctl",
"ecvt_r",
"_IO_do_write",
"getutxid",
"wcscat",
"_IO_switch_to_get_mode",
"__fdelt_warn",
"wcrtomb",
"__key_gendes_LOCAL",
"sync_file_range",
"__signbitf",
"getnetbyaddr",
"_obstack",
"connect",
"wcspbrk",
"__isnan",
"errno",
"__open64_2",
"_longjmp",
"envz_remove",
"ngettext",
"ldexpf",
"fileno_unlocked",
"error_print_progname",
"__signbitl",
"in6addr_any",
"lutimes",
"stpncpy",
"munlock",
"ftruncate64",
"key_get_conv",
"getpwuid",
"dl_iterate_phdr",
"__nss_disable_nscd",
"getpwent_r",
"mmap64",
"sendfile",
"inet6_rth_init",
"ldexpl",
"inet6_opt_next",
"__libc_allocate_rtsig_private",
"ecb_crypt",
"ungetwc",
"__wcstof_l",
"versionsort",
"xdr_longlong_t",
"tfind",
"_IO_printf",
"__argz_next",
"wmemcpy",
"recvmmsg",
"__fxstatat64",
"posix_spawnattr_init",
"__sigismember",
"get_current_dir_name",
"semctl",
"fputc_unlocked",
"verr",
"mbsrtowcs",
"getprotobynumber",
"fgetsgent",
"getsecretkey",
"__nss_services_lookup2",
"unlinkat",
"__libc_thread_freeres",
"isalnum_l",
"xdr_authdes_verf",
"_IO_2_1_stdin_",
"__fdelt_chk",
"__strtof_internal",
"closedir",
"initgroups",
"inet_ntoa",
"wcstof_l",
"__freelocale",
"pmap_rmtcall",
"glob64",
"__fwprintf_chk",
"putc",
"nanosleep",
"setspent",
"xdr_char",
"fchdir",
"__mempcpy_chk",
"__isinf",
"fopencookie",
"wcstoll_l",
"ftrylockfile",
"endaliasent",
"isalpha_l",
"_IO_wdefault_pbackfail",
"feof_unlocked",
"__nss_passwd_lookup2",
"isblank",
"getusershell",
"uselocale",
"svc_sendreply",
"re_search_2",
"getgrgid",
"siginterrupt",
"epoll_wait",
"fputwc",
"error",
"mkfifoat",
"get_kernel_syms",
"getrpcent_r",
"ftell",
"__isoc99_scanf",
"_res",
"__read_chk",
"inet_ntop",
"signal",
"strncpy",
"__res_nclose",
"__fgetws_unlocked_chk",
"getdomainname",
"personality",
"puts",
"__iswupper_l",
"mbstowcs",
"__vsprintf_chk",
"__newlocale",
"getpriority",
"getsubopt",
"fork",
"tcgetsid",
"putw",
"ioperm",
"warnx",
"_IO_setvbuf",
"pmap_unset",
"iswspace",
"_dl_mcount_wrapper_check",
"__cxa_thread_atexit_impl",
"isastream",
"vwscanf",
"fputws",
"sigprocmask",
"_IO_sputbackc",
"strtoul_l",
"listxattr",
"in6addr_loopback",
"regfree",
"lcong48_r",
"sched_getparam",
"inet_netof",
"gettext",
"waitid",
"futimes",
"_IO_init_wmarker",
"callrpc",
"sigfillset",
"gtty",
"time",
"ntp_adjtime",
"getgrent",
"__libc_malloc",
"__wcsncpy_chk",
"readdir_r",
"sigorset",
"_IO_flush_all",
"setreuid",
"vfscanf",
"memalign",
"drand48_r",
"endnetent",
"fsetpos64",
"hsearch_r",
"__stack_chk_fail",
"wcscasecmp",
"_IO_feof",
"key_setsecret",
"daemon",
"svc_run",
"__lxstat",
"_IO_wdefault_finish",
"__wcstoul_l",
"shmctl",
"inotify_rm_watch",
"xdr_quad_t",
"_IO_fflush",
"unlink",
"__mbrtowc",
"putchar",
"xdrmem_create",
"pthread_mutex_lock",
"listen",
"fgets_unlocked",
"putspent",
"xdr_int32_t",
"msgrcv",
"__ivaliduser",
"__send",
"select",
"getrpcent",
"iswprint",
"getsgent_r",
"__iswalnum_l",
"mkdir",
"ispunct_l",
"argp_program_version_hook",
"__libc_fatal",
"__sched_cpualloc",
"shmdt",
"process_vm_writev",
"realloc",
"__pwrite64",
"fstatfs",
"setstate",
"_libc_intl_domainname",
"if_nameindex",
"h_nerr",
"btowc",
"__argz_stringify",
"_IO_ungetc",
"rewinddir",
"strtold",
"_IO_adjust_wcolumn",
"fsync",
"__iswalpha_l",
"getaliasent_r",
"xdr_key_netstres",
"prlimit",
"clock",
"__obstack_vprintf_chk",
"towupper",
"xdr_replymsg",
"sockatmark",
"putmsg",
"abort",
"stdin",
"_IO_flush_all_linebuffered",
"xdr_u_short",
"strtoll",
"_exit",
"svc_getreq_common",
"name_to_handle_at",
"wcstoumax",
"vsprintf",
"sigwaitinfo",
"moncontrol",
"__res_iclose",
"socketpair",
"div",
"memchr",
"__strtod_l",
"strpbrk",
"scandirat",
"memrchr",
"ether_aton",
"hdestroy",
"__read",
"tolower",
"cfree",
"popen",
"ruserok_af",
"_tolower",
"step",
"towctrans",
"__dcgettext",
"lsetxattr",
"setttyent",
"__isoc99_swscanf",
"malloc_info",
"__open64",
"__bsd_getpgrp",
"setsgent",
"getpid",
"kill",
"getcontext",
"__isoc99_vfwscanf",
"strspn",
"pthread_condattr_init",
"imaxdiv",
"program_invocation_name",
"svcraw_create",
"posix_fallocate64",
"fanotify_init",
"__sched_get_priority_max",
"argz_extract",
"bind_textdomain_codeset",
"fgetpos",
"strdup",
"_IO_fgetpos64",
"creat64",
"svc_exit",
"getc_unlocked",
"inet_pton",
"strftime",
"__flbf",
"lockf64",
"_IO_switch_to_main_wget_area",
"xencrypt",
"putpmsg",
"xdr_uint16_t",
"__libc_system",
"tzname",
"__libc_mallopt",
"sysv_signal",
"pthread_attr_getschedparam",
"strtoll_l",
"__sched_cpufree",
"__dup2",
"pthread_mutex_destroy",
"fgetwc",
"chmod",
"vlimit",
"sbrk",
"__assert_fail",
"clntunix_create",
"iswalnum",
"__toascii_l",
"__isalnum_l",
"printf",
"__getmntent_r",
"ether_ntoa_r",
"finite",
"__connect",
"quick_exit",
"getnetbyname",
"mkstemp",
"flock",
"statvfs",
"error_at_line",
"rewind",
"_null_auth",
"strcoll_l",
"llabs",
"localtime_r",
"wcscspn",
"vtimes",
"__stpncpy",
"__libc_secure_getenv",
"copysign",
"inet6_opt_finish",
"__nanosleep",
"setjmp",
"modff",
"iswlower",
"__poll",
"isspace",
"strtod",
"tmpnam_r",
"__confstr_chk",
"fallocate",
"__wctype_l",
"setutxent",
"fgetws",
"__wcstoll_l",
"__isalpha_l",
"strtof",
"iswdigit_l",
"__wcsncat_chk",
"gmtime",
"__uselocale",
"__ctype_get_mb_cur_max",
"ffs",
"__iswlower_l",
"xdr_opaque_auth",
"modfl",
"envz_add",
"putsgent",
"strtok",
"getpt",
"endpwent",
"_IO_fopen",
"strtol",
"sigqueue",
"fts_close",
"isatty",
"setmntent",
"endnetgrent",
"lchown",
"mmap",
"_IO_file_read",
"getpw",
"setsourcefilter",
"GLIBC_PRIVATE",
"fgetspent_r",
"sched_yield",
"glob_pattern_p",
"strtoq",
"__strsep_1c",
"__clock_getcpuclockid",
"wcsncasecmp",
"xdr_u_quad_t",
"ctime_r",
"getgrnam_r",
"clearenv",
"wctype_l",
"fstatvfs",
"sigblock",
"__libc_sa_len",
"__key_encryptsession_pk_LOCAL",
"pthread_attr_setscope",
"svcudp_create",
"iswxdigit_l",
"feof",
"strchrnul",
"swapoff",
"__ctype_tolower",
"syslog",
"posix_spawnattr_destroy",
"__strtoul_l",
"eaccess",
"__fread_unlocked_chk",
"fsetpos",
"pread64",
"inet6_option_alloc",
"dysize",
"symlink",
"getspent",
"_IO_wdefault_uflow",
"pthread_attr_setdetachstate",
"fgetxattr",
"srandom_r",
"truncate",
"isprint",
"__libc_calloc",
"posix_fadvise",
"memccpy",
"getloadavg",
"execle",
"wcsftime",
"__fentry__",
"ldiv",
"__nss_configure_lookup",
"cfsetispeed",
"xdr_void",
"ether_ntoa",
"tee",
"xdr_key_netstarg",
"fgetc",
"parse_printf_format",
"strfry",
"_IO_vsprintf",
"reboot",
"getaliasbyname_r",
"jrand48",
"execlp",
"gethostbyname_r",
"c16rtomb",
"swab",
"_IO_funlockfile",
"_IO_flockfile",
"__strsep_2c",
"seekdir",
"__mktemp",
"__isascii_l",
"isblank_l",
"pmap_getport",
"alphasort64",
"makecontext",
"fdatasync",
"register_printf_specifier",
"authdes_getucred",
"truncate64",
"__ispunct_l",
"__iswgraph_l",
"strtoumax",
"argp_failure",
"__strcasecmp",
"fgets",
"__vfscanf",
"__openat64_2",
"__iswctype",
"posix_spawnattr_setflags",
"getnetent_r",
"clock_nanosleep",
"sched_setaffinity",
"sched_setaffinity",
"vscanf",
"getpwnam",
"inet6_option_append",
"getppid",
"calloc",
"_IO_unsave_wmarkers",
"_nl_default_dirname",
"getmsg",
"_dl_addr",
"msync",
"renameat",
"_IO_init",
"__signbit",
"futimens",
"asctime_r",
"strlen",
"freelocale",
"__wmemset_chk",
"initstate",
"wcschr",
"isxdigit",
"mbrtoc16",
"ungetc",
"_IO_file_init",
"__wuflow",
"__ctype_b",
"lockf",
"ether_line",
"xdr_authdes_cred",
"__clock_gettime",
"qecvt",
"iswctype",
"__mbrlen",
"tmpfile",
"xdr_int8_t",
"__internal_setnetgrent",
"envz_entry",
"pivot_root",
"sprofil",
"__towupper_l",
"rexec_af",
"xprt_unregister",
"xdr_authunix_parms",
"_IO_2_1_stdout_",
"newlocale",
"tsearch",
"getaliasbyname",
"svcerr_progvers",
"isspace_l",
"inet6_opt_get_val",
"argz_insert",
"gsignal",
"gethostbyname2_r",
"__cxa_atexit",
"posix_spawn_file_actions_init",
"__fwriting",
"prctl",
"setlogmask",
"malloc_stats",
"xdr_enum",
"__towctrans_l",
"__strsep_3c",
"h_errlist",
"unshare",
"fread_unlocked",
"brk",
"send",
"isprint_l",
"setitimer",
"__towctrans",
"__isoc99_vsscanf",
"sys_sigabbrev",
"sys_sigabbrev",
"setcontext",
"iswupper_l",
"signalfd",
"sigemptyset",
"inet6_option_next",
"_dl_sym",
"openlog",
"getaddrinfo",
"_IO_init_marker",
"getchar_unlocked",
"__res_maybe_init",
"memset",
"dirname",
"__gconv_get_alias_db",
"localeconv",
"cfgetospeed",
"writev",
"_IO_default_xsgetn",
"isalnum",
"setutent",
"_seterr_reply",
"_IO_switch_to_wget_mode",
"inet6_rth_add",
"fgetc_unlocked",
"swprintf",
"getchar",
"warn",
"getutid",
"__gconv_get_cache",
"glob",
"strstr",
"semtimedop",
"__secure_getenv",
"wcsnlen",
"strcspn",
"__wcstof_internal",
"islower",
"tcsendbreak",
"telldir",
"__strtof_l",
"utimensat",
"fcvt",
"__get_cpu_features",
"_IO_setbuffer",
"_IO_iter_file",
"rmdir",
"__errno_location",
"tcsetattr",
"__strtoll_l",
"bind",
"fseek",
"xdr_float",
"chdir",
"open64",
"confstr",
"muntrace",
"read",
"inet6_rth_segments",
"memcmp",
"getsgent",
"getwchar",
"getpagesize",
"xdr_sizeof",
"getnameinfo",
"dgettext",
"_IO_ftell",
"putwc",
"__pread_chk",
"_IO_sprintf",
"_IO_list_lock",
"getrpcport",
"__syslog_chk",
"endgrent",
"asctime",
"strndup",
"init_module",
"mlock",
"xdrrec_skiprecord",
"clnt_sperrno",
"__strcoll_l",
"mbsnrtowcs",
"__gai_sigqueue",
"toupper",
"sgetsgent_r",
"mbtowc",
"setprotoent",
"__getpid",
"eventfd",
"netname2user",
"_toupper",
"svctcp_create",
"getsockopt",
"getdelim",
"_IO_wsetb",
"setgroups",
"setxattr",
"clnt_perrno",
"_IO_doallocbuf",
"erand48_r",
"lrand48",
"grantpt",
"ttyname",
"mbrtoc32",
"mempcpy",
"pthread_attr_init",
"herror",
"getopt",
"wcstoul",
"utmpname",
"__fgets_unlocked_chk",
"getlogin_r",
"isdigit_l",
"vfwprintf",
"_IO_seekoff",
"__setmntent",
"hcreate_r",
"tcflow",
"wcstouq",
"_IO_wdoallocbuf",
"rexec",
"msgget",
"fwscanf",
"xdr_int16_t",
"_dl_open_hook",
"__getcwd_chk",
"fchmodat",
"envz_strip",
"dup2",
"clearerr",
"dup3",
"rcmd_af",
"environ",
"pause",
"__rpc_thread_svc_max_pollfd",
"unsetenv",
"__posix_getopt",
"rand_r",
"__finite",
"_IO_str_init_static",
"timelocal",
"xdr_pointer",
"argz_add_sep",
"wctob",
"longjmp",
"__fxstat64",
"_IO_file_xsputn",
"strptime",
"clnt_sperror",
"__adjtimex",
"__vprintf_chk",
"shutdown",
"fattach",
"setns",
"vsnprintf",
"_setjmp",
"poll",
"malloc_get_state",
"getpmsg",
"_IO_getline",
"ptsname",
"fexecve",
"re_comp",
"clnt_perror",
"qgcvt",
"svcerr_noproc",
"__fprintf_chk",
"open_by_handle_at",
"_IO_marker_difference",
"__wcstol_internal",
"_IO_sscanf",
"__strncasecmp_l",
"sigaddset",
"ctime",
"iswupper",
"svcerr_noprog",
"fallocate64",
"_IO_iter_end",
"getgrnam",
"__wmemcpy_chk",
"adjtimex",
"pthread_mutex_unlock",
"sethostname",
"_IO_setb",
"__pread64",
"mcheck",
"xdr_reference",
"__isblank_l",
"getpwuid_r",
"endrpcent",
"netname2host",
"inet_network",
"isctype",
"putenv",
"wcswidth",
"pmap_set",
"fchown",
"pthread_cond_broadcast",
"pthread_cond_broadcast",
"_IO_link_in",
"ftok",
"xdr_netobj",
"catopen",
"__wcstoull_l",
"register_printf_function",
"__sigsetjmp",
"__isoc99_wscanf",
"preadv64",
"stdout",
"__ffs",
"inet_makeaddr",
"getttyent",
"__curbrk",
"gethostbyaddr",
"get_phys_pages",
"_IO_popen",
"argp_help",
"__ctype_toupper",
"fputc",
"frexp",
"__towlower_l",
"gethostent_r",
"_IO_seekmark",
"psignal",
"verrx",
"setlogin",
"versionsort64",
"__internal_getnetgrent_r",
"fseeko64",
"_IO_file_jumps",
"fremovexattr",
"__wcscpy_chk",
"__libc_valloc",
"create_module",
"recv",
"__isoc99_fscanf",
"_IO_sungetc",
"getsid",
"_rpc_dtablesize",
"mktemp",
"inet_addr",
"__mbstowcs_chk",
"getrusage",
"_IO_peekc_locked",
"_IO_remove_marker",
"__sendmmsg",
"__malloc_hook",
"__isspace_l",
"iswlower_l",
"fts_read",
"getfsspec",
"__strtoll_internal",
"iswgraph",
"ualarm",
"query_module",
"__dprintf_chk",
"fputs",
"posix_spawn_file_actions_destroy",
"strtok_r",
"endhostent",
"pthread_cond_wait",
"pthread_cond_wait",
"argz_delete",
"__isprint_l",
"__woverflow",
"xdr_u_long",
"__wmempcpy_chk",
"fpathconf",
"iscntrl_l",
"regerror",
"strnlen",
"nrand48",
"sendmmsg",
"getspent_r",
"wmempcpy",
"argp_program_bug_address",
"lseek",
"setresgid",
"ftime",
"xdr_string",
"sigaltstack",
"memcpy",
"getwc",
"memcpy",
"endusershell",
"__sched_get_priority_min",
"getwd",
"mbrlen",
"freopen64",
"posix_spawnattr_setschedparam",
"getdate_r",
"fclose",
"_IO_adjust_column",
"_IO_seekwmark",
"__nss_lookup",
"__sigpause",
"euidaccess",
"symlinkat",
"rand",
"pselect",
"pthread_setcanceltype",
"tcsetpgrp",
"nftw64",
"__memmove_chk",
"wcscmp",
"nftw64",
"mprotect",
"__getwd_chk",
"ffsl",
"__nss_lookup_function",
"getmntent",
"__wcscasecmp_l",
"__libc_dl_error_tsd",
"__strtol_internal",
"__vsnprintf_chk",
"mkostemp64",
"__wcsftime_l",
"_IO_file_doallocate",
"pthread_setschedparam",
"strtoul",
"hdestroy_r",
"fmemopen",
"endspent",
"munlockall",
"sigpause",
"getutmp",
"getutmpx",
"vprintf",
"xdr_u_int",
"setsockopt",
"_IO_default_xsputn",
"malloc",
"svcauthdes_stats",
"eventfd_read",
"strtouq",
"getpass",
"remap_file_pages",
"siglongjmp",
"__ctype32_tolower",
"uselib",
"xdr_keystatus",
"sigisemptyset",
"strfmon",
"duplocale",
"killpg",
"xdr_int",
"strcat",
"accept4",
"umask",
"__isoc99_vswscanf",
"strcasecmp",
"ftello64",
"fdopendir",
"realpath",
"realpath",
"pthread_attr_getschedpolicy",
"modf",
"ftello",
"timegm",
"__libc_dlclose",
"__libc_mallinfo",
"raise",
"setegid",
"__clock_getres",
"setfsgid",
"malloc_usable_size",
"_IO_wdefault_doallocate",
"__isdigit_l",
"_IO_vfscanf",
"remove",
"sched_setscheduler",
"timespec_get",
"wcstold_l",
"setpgid",
"aligned_alloc",
"__openat_2",
"getpeername",
"wcscasecmp_l",
"__strverscmp",
"__fgets_chk",
"__res_state",
"pmap_getmaps",
"__strndup",
"sys_errlist",
"sys_errlist",
"sys_errlist",
"frexpf",
"sys_errlist",
"mallwatch",
"_flushlbf",
"mbsinit",
"towupper_l",
"__strncpy_chk",
"getgid",
"asprintf",
"tzset",
"__libc_pwrite",
"re_compile_pattern",
"re_max_failures",
"frexpl",
"__lxstat64",
"svcudp_bufcreate",
"xdrrec_eof",
"isupper",
"vsyslog",
"fstatfs64",
"__strerror_r",
"finitef",
"getutline",
"__uflow",
"prlimit64",
"__mempcpy",
"strtol_l",
"__isnanf",
"svc_getreq_poll",
"finitel",
"__nl_langinfo_l",
"__sched_cpucount",
"pthread_attr_setinheritsched",
"nl_langinfo",
"svc_pollfd",
"__vsnprintf",
"setfsent",
"__isnanl",
"hasmntopt",
"clock_getres",
"opendir",
"__libc_current_sigrtmax",
"wcsncat",
"getnetbyaddr_r",
"__mbsrtowcs_chk",
"_IO_fgets",
"gethostent",
"bzero",
"rpc_createerr",
"__sigaddset",
"argp_err_exit_status",
"mcheck_check_all",
"__isinff",
"clnt_broadcast",
"pthread_condattr_destroy",
"__environ",
"__statfs",
"getspnam",
"__wcscat_chk",
"inet6_option_space",
"__xstat64",
"fgetgrent_r",
"clone",
"__ctype_b_loc",
"sched_getaffinity",
"__isinfl",
"__iswpunct_l",
"__xpg_sigpause",
"getenv",
"sched_getaffinity",
"sscanf",
"profil",
"preadv",
"jrand48_r",
"setresuid",
"__open_2",
"recvfrom",
"__profile_frequency",
"wcsnrtombs",
"svc_fdset",
"ruserok",
"_obstack_allocated_p",
"fts_set",
"nice",
"xdr_u_longlong_t",
"xdecrypt",
"regcomp",
"__fortify_fail",
"getitimer",
"__open",
"isgraph",
"optarg",
"catclose",
"clntudp_bufcreate",
"getservbyname",
"__freading",
"stderr",
"wcwidth",
"msgctl",
"inet_lnaof",
"sigdelset",
"ioctl",
"syncfs",
"gnu_get_libc_release",
"fchownat",
"alarm",
"_IO_2_1_stderr_",
"_IO_sputbackwc",
"__libc_pvalloc",
"system",
"xdr_getcredres",
"__wcstol_l",
"err",
"vfwscanf",
"chflags",
"inotify_init",
"timerfd_settime",
"getservbyname_r",
"ffsll",
"xdr_bool",
"__isctype",
"setrlimit64",
"sched_getcpu",
"group_member",
"_IO_free_backup_area",
"munmap",
"_IO_fgetpos",
"posix_spawnattr_setsigdefault",
"_obstack_begin_1",
"endsgent",
"_nss_files_parse_pwent",
"ntp_gettimex",
"wait3",
"__getgroups_chk",
"wait4",
"_obstack_newchunk",
"advance",
"inet6_opt_init",
"__fpu_control",
"gethostbyname",
"__snprintf_chk",
"__lseek",
"wcstol_l",
"posix_spawn_file_actions_adddup2",
"optopt",
"error_message_count",
"__iscntrl_l",
"seteuid",
"mkdirat",
"wcscpy",
"dup",
"setfsuid",
"__vdso_clock_gettime",
"mrand48_r",
"pthread_exit",
"__memset_chk",
"getwchar_unlocked",
"xdr_u_char",
"re_syntax_options",
"pututxline",
"fchflags",
"clock_settime",
"getlogin",
"msgsnd",
"arch_prctl",
"scalbnf",
"sigandset",
"_IO_file_finish",
"sched_rr_get_interval",
"__sysctl",
"xdr_double",
"getgroups",
"scalbnl",
"readv",
"rcmd",
"getuid",
"iruserok_af",
"readlink",
"lsearch",
"fscanf",
"__abort_msg",
"mkostemps64",
"ether_aton_r",
"__printf_fp",
"readahead",
"mremap",
"removexattr",
"host2netname",
"xdr_pmap",
"_IO_switch_to_wbackup_area",
"execve",
"getprotoent",
"_IO_wfile_sync",
"getegid",
"xdr_opaque",
"setrlimit",
"getopt_long",
"_IO_file_open",
"settimeofday",
"open_memstream",
"sstk",
"getpgid",
"utmpxname",
"__fpurge",
"_dl_vsym",
"__strncat_chk",
"__libc_current_sigrtmax_private",
"strtold_l",
"vwarnx",
"posix_madvise",
"posix_spawnattr_getpgroup",
"__mempcpy_small",
"fgetpos64",
"rexecoptions",
"index",
"execvp",
"pthread_attr_getdetachstate",
"_IO_wfile_xsputn",
"mincore",
"mallinfo",
"getauxval",
"freeifaddrs",
"__duplocale",
"malloc_trim",
"svcudp_enablecache",
"_IO_str_underflow",
"__wcsncasecmp_l",
"linkat",
"_IO_default_pbackfail",
"inet6_rth_space",
"_IO_free_wbackup_area",
"pthread_cond_timedwait",
"pthread_cond_timedwait",
"_IO_fsetpos",
"getpwnam_r",
"freopen",
"__clock_nanosleep",
"__libc_alloca_cutoff",
"__realloc_hook",
"getsgnam",
"strncasecmp",
"backtrace_symbols_fd",
"__xmknod",
"remque",
"__recv_chk",
"inet6_rth_reverse",
"_IO_wfile_seekoff",
"ptrace",
"towlower_l",
"getifaddrs",
"scalbn",
"putwc_unlocked",
"printf_size_info",
"h_errno",
"if_nametoindex",
"__wcstold_l",
"__wcstoll_internal",
"_res_hconf",
"creat",
"__fxstat",
"_IO_file_close_it",
"_IO_file_close",
"strncat",
"key_decryptsession_pk",
"sendfile64",
"__check_rhosts_file",
"wcstoimax",
"sendmsg",
"__backtrace_symbols_fd",
"pwritev",
"__strsep_g",
"strtoull",
"__wunderflow",
"__fwritable",
"_IO_fclose",
"ulimit",
"__sysv_signal",
"__realpath_chk",
"obstack_printf",
"_IO_wfile_underflow",
"posix_spawnattr_getsigmask",
"fputwc_unlocked",
"drand48",
"__nss_passwd_lookup",
"qsort_r",
"xdr_free",
"__obstack_printf_chk",
"fileno",
"pclose",
"__isxdigit_l",
"__bzero",
"sethostent",
"re_search",
"inet6_rth_getaddr",
"__setpgid",
"__dgettext",
"gethostname",
"pthread_equal",
"fstatvfs64",
"sgetspent_r",
"__libc_ifunc_impl_list",
"__clone",
"utimes",
"pthread_mutex_init",
"usleep",
"sigset",
"__ctype32_toupper",
"ustat",
"chown",
"__cmsg_nxthdr",
"_obstack_memory_used",
"__libc_realloc",
"splice",
"posix_spawn",
"posix_spawn",
"__iswblank_l",
"_itoa_lower_digits",
"_IO_sungetwc",
"getcwd",
"__getdelim",
"eventfd_write",
"xdr_vector",
"__progname_full",
"swapcontext",
"lgetxattr",
"__rpc_thread_svc_fdset",
"error_one_per_line",
"__finitef",
"xdr_uint8_t",
"wcsxfrm_l",
"if_indextoname",
"authdes_pk_create",
"swscanf",
"vmsplice",
"svcerr_decode",
"gnu_get_libc_version",
"fwrite",
"updwtmpx",
"__finitel",
"des_setparity",
"getsourcefilter",
"copysignf",
"fread",
"__cyg_profile_func_enter",
"isnanf",
"lrand48_r",
"qfcvt_r",
"fcvt_r",
"iconv_close",
"gettimeofday",
"iswalnum_l",
"adjtime",
"getnetgrent_r",
"_IO_wmarker_delta",
"endttyent",
"seed48",
"rename",
"copysignl",
"sigaction",
"isnanl",
"rtime",
"_IO_default_finish",
"getfsent",
"epoll_ctl",
"__isoc99_vwscanf",
"__iswxdigit_l",
"__ctype_init",
"_IO_fputs",
"fanotify_mark",
"madvise",
"_nss_files_parse_grent",
"getnetname",
"_dl_mcount_wrapper",
"passwd2des",
"setnetent",
"__sigdelset",
"mkstemp64",
"__stpcpy_small",
"scandir",
"isinff",
"gnu_dev_minor",
"__libc_current_sigrtmin_private",
"geteuid",
"__libc_siglongjmp",
"getresgid",
"statfs",
"ether_hostton",
"mkstemps64",
"sched_setparam",
"iswalpha_l",
"__memcpy_chk",
"srandom",
"quotactl",
"__iswspace_l",
"getrpcbynumber_r",
"isinfl",
"__open_catalog",
"sigismember",
"__isoc99_vfscanf",
"getttynam",
"atof",
"re_set_registers",
"__call_tls_dtors",
"clock_gettime",
"pthread_attr_setschedparam",
"bcopy",
"setlinebuf",
"__stpncpy_chk",
"getsgnam_r",
"wcswcs",
"atoi",
"xdr_hyper",
"__strtok_r_1c",
"__iswprint_l",
"stime",
"getdirentries64",
"textdomain",
"posix_spawnattr_getschedparam",
"sched_get_priority_max",
"tcflush",
"atol",
"inet6_opt_find",
"wcstoull",
"mlockall",
"sys_siglist",
"ether_ntohost",
"sys_siglist",
"waitpid",
"ftw64",
"iswxdigit",
"stty",
"__fpending",
"unlockpt",
"close",
"__mbsnrtowcs_chk",
"strverscmp",
"xdr_union",
"backtrace",
"catgets",
"posix_spawnattr_getschedpolicy",
"lldiv",
"pthread_setcancelstate",
"endutent",
"tmpnam",
"inet_nsap_ntoa",
"strerror_l",
"open",
"twalk",
"srand48",
"svcunixfd_create",
"toupper_l",
"ftw",
"iopl",
"__wcstoull_internal",
"strerror_r",
"sgetspent",
"_IO_iter_begin",
"pthread_getschedparam",
"__fread_chk",
"c32rtomb",
"dngettext",
"vhangup",
"__rpc_thread_createerr",
"localtime",
"key_secretkey_is_set",
"endutxent",
"swapon",
"umount",
"lseek64",
"__wcsnrtombs_chk",
"ferror_unlocked",
"difftime",
"wctrans_l",
"strchr",
"capset",
"_Exit",
"flistxattr",
"clnt_spcreateerror",
"obstack_free",
"pthread_attr_getscope",
"getaliasent",
"_sys_errlist",
"_sys_errlist",
"_sys_errlist",
"_sys_errlist",
"sigreturn",
"rresvport_af",
"secure_getenv",
"sigignore",
"iswdigit",
"__monstartup",
"svcerr_weakauth",
"iswcntrl",
"fcloseall",
"__wprintf_chk",
"__timezone",
"funlockfile",
"endmntent",
"fprintf",
"getsockname",
"scandir64",
"utime",
"hsearch",
"_nl_domain_bindings",
"argp_error",
"__strpbrk_c2",
"abs",
"sendto",
"__strpbrk_c3",
"iswpunct_l",
"addmntent",
"updwtmp",
"__strtold_l",
"__nss_database_lookup",
"_IO_least_wmarker",
"vfork",
"rindex",
"addseverity",
"xprt_register",
"__poll_chk",
"epoll_create1",
"getgrent_r",
"key_gendes",
"__vfprintf_chk",
"mktime",
"mblen",
"tdestroy",
"sysctl",
"__getauxval",
"clnt_create",
"xdr_rmtcall_args",
"alphasort",
"timezone",
"__strtok_r",
"xdrstdio_create",
"mallopt",
"strtoimax",
"getline",
"__malloc_initialize_hook",
"__iswdigit_l",
"__stpcpy",
"getrpcbyname_r",
"get_myaddress",
"iconv",
"imaxabs",
"program_invocation_short_name",
"bdflush",
"mkstemps",
"lremovexattr",
"re_compile_fastmap",
"setusershell",
"fdopen",
"_IO_str_seekoff",
"_IO_wfile_jumps",
"readdir64",
"xdr_callmsg",
"svcerr_auth",
"qsort",
"canonicalize_file_name",
"__getpgid",
"_IO_sgetn",
"iconv_open",
"process_vm_readv",
"_IO_fsetpos64",
"__strtod_internal",
"strfmon_l",
"mrand48",
"wcstombs",
"posix_spawnattr_getflags",
"accept",
"__libc_free",
"gethostbyname2",
"__nss_hosts_lookup",
"__strtoull_l",
"cbc_crypt",
"_IO_str_overflow",
"argp_parse",
"__after_morecore_hook",
"xdr_netnamestr",
"envz_get",
"_IO_seekpos",
"getresuid",
"__vsyslog_chk",
"posix_spawnattr_setsigmask",
"hstrerror",
"__strcasestr",
"inotify_add_watch",
"_IO_proc_close",
"statfs64",
"tcgetattr",
"toascii",
"authnone_create",
"isupper_l",
"getutxline",
"sethostid",
"tmpfile64",
"sleep",
"wcsxfrm",
"times",
"_IO_file_sync",
"strxfrm_l",
"__libc_allocate_rtsig",
"__wcrtomb_chk",
"__ctype_toupper_loc",
"clntraw_create",
"pwritev64",
"insque",
"__getpagesize",
"epoll_pwait",
"valloc",
"__strcpy_chk",
"__ctype_tolower_loc",
"getutxent",
"_IO_list_unlock",
"obstack_alloc_failed_handler",
"__vdprintf_chk",
"xdr_array",
"fputws_unlocked",
"llistxattr",
"__nss_group_lookup2",
"__cxa_finalize",
"__libc_current_sigrtmin",
"umount2",
"syscall",
"sigpending",
"bsearch",
"__assert_perror_fail",
"strncasecmp_l",
"freeaddrinfo",
"__vasprintf_chk",
"get_nprocs",
"setvbuf",
"getprotobyname_r",
"__xpg_strerror_r",
"__wcsxfrm_l",
"vsscanf",
"fgetpwent",
"gethostbyaddr_r",
"setaliasent",
"xdr_rejected_reply",
"capget",
"__sigsuspend",
"readdir64_r",
"getpublickey",
"__sched_setscheduler",
"__rpc_thread_svc_pollfd",
"svc_unregister",
"fts_open",
"setsid",
"pututline",
"sgetsgent",
"__resp",
"getutent",
"posix_spawnattr_getsigdefault",
"iswgraph_l",
"wcscoll",
"register_printf_type",
"printf_size",
"pthread_attr_destroy",
"__wcstoul_internal",
"xdr_uint64_t",
"nrand48_r",
"svcunix_create",
"__sigaction",
"_nss_files_parse_spent",
"cfsetspeed",
"__wcpncpy_chk",
"__libc_freeres",
"fcntl",
"wcsspn",
"getrlimit64",
"wctype",
"inet6_option_init",
"__iswctype_l",
"__libc_clntudp_bufcreate",
"ecvt",
"__wmemmove_chk",
"__sprintf_chk",
"bindresvport",
"rresvport",
"__asprintf",
"cfsetospeed",
"fwide",
"__strcasecmp_l",
"getgrgid_r",
"pthread_cond_init",
"pthread_cond_init",
"setpgrp",
"cfgetispeed",
"wcsdup",
"atoll",
"bsd_signal",
"__strtol_l",
"ptsname_r",
"xdrrec_create",
"__h_errno_location",
"fsetxattr",
"_IO_file_seekoff",
"_IO_ftrylockfile",
"__close",
"_IO_iter_next",
"getmntent_r",
"labs",
"link",
"obstack_exit_failure",
"__strftime_l",
"xdr_cryptkeyres",
"innetgr",
"openat",
"_IO_list_all",
"futimesat",
"_IO_wdefault_xsgetn",
"__iswcntrl_l",
"__pread64_chk",
"vdprintf",
"vswprintf",
"_IO_getline_info",
"clntudp_create",
"scandirat64",
"getprotobyname",
"strptime_l",
"argz_create_sep",
"tolower_l",
"__fsetlocking",
"__ctype32_b",
"__backtrace",
"__xstat",
"wcscoll_l",
"__madvise",
"getrlimit",
"sigsetmask",
"key_encryptsession",
"scanf",
"isdigit",
"getxattr",
"lchmod",
"iscntrl",
"mount",
"getdtablesize",
"sys_nerr",
"random_r",
"sys_nerr",
"sys_nerr",
"__toupper_l",
"sys_nerr",
"iswpunct",
"errx",
"strcasecmp_l",
"wmemchr",
"memmove",
"key_setnet",
"_IO_file_write",
"uname",
"svc_max_pollfd",
"wcstod",
"_nl_msg_cat_cntr",
"__chk_fail",
"svc_getreqset",
"mcount",
"posix_spawnp",
"__isoc99_vscanf",
"mprobe",
"posix_spawnp",
"_IO_file_overflow",
"wcstof",
"backtrace_symbols",
"__wcsrtombs_chk",
"_IO_list_resetlock",
"_mcleanup",
"__wctrans_l",
"isxdigit_l",
"_IO_fwrite",
"sigtimedwait",
"pthread_self",
"wcstok",
"ruserpass",
"svc_register",
"__waitpid",
"wcstol",
"endservent",
"fopen64",
"pthread_attr_setschedpolicy",
"vswscanf",
"ctermid",
"__nss_group_lookup",
"pread",
"wcschrnul",
"__libc_dlsym",
"__endmntent",
"wcstoq",
"pwrite",
"sigstack",
"mkostemp",
"__vfork",
"__freadable",
"strsep",
"iswblank_l",
"mkostemps",
"_IO_file_underflow",
"_obstack_begin",
"getnetgrent",
"__morecore",
"bindtextdomain",
"wcsrtombs",
"__nss_next",
"user2netname",
"access",
"fmtmsg",
"__sched_getscheduler",
"qfcvt",
"mcheck_pedantic",
"mtrace",
"ntp_gettime",
"_IO_getc",
"pipe2",
"memmem",
"__fxstatat",
"__fbufsize",
"loc1",
"_IO_marker_delta",
"rawmemchr",
"loc2",
"sync",
"bcmp",
"getgrouplist",
"sysinfo",
"sigvec",
"getwc_unlocked",
"opterr",
"svc_getreq",
"argz_append",
"setgid",
"malloc_set_state",
"__strcat_chk",
"wprintf",
"__argz_count",
"ulckpwdf",
"fts_children",
"strxfrm",
"getservbyport_r",
"mkfifo",
"openat64",
"sched_getscheduler",
"faccessat",
"on_exit",
"__key_decryptsession_pk_LOCAL",
"__res_randomid",
"setbuf",
"fwrite_unlocked",
"strcmp",
"_IO_gets",
"__libc_longjmp",
"recvmsg",
"__strtoull_internal",
"iswspace_l",
"islower_l",
"__underflow",
"pwrite64",
"strerror",
"__asprintf_chk",
"__strfmon_l",
"xdr_wrapstring",
"tcgetpgrp",
"__libc_start_main",
"fgetwc_unlocked",
"dirfd",
"_nss_files_parse_sgent",
"nftw",
"xdr_des_block",
"nftw",
"xdr_cryptkeyarg2",
"xdr_callhdr",
"setpwent",
"iswprint_l",
"semop",
"endfsent",
"__isupper_l",
"wscanf",
"ferror",
"getutent_r",
"authdes_create",
"stpcpy",
"ppoll",
"__strxfrm_l",
"fdetach",
"pthread_cond_destroy",
"ldexp",
"fgetpwent_r",
"pthread_cond_destroy",
"__wait",
"gcvt",
"fwprintf",
"xdr_bytes",
"setenv",
"setpriority",
"__libc_dlopen_mode",
"posix_spawn_file_actions_addopen",
"nl_langinfo_l",
"_IO_default_doallocate",
"__gconv_get_modules_db",
"__recvfrom_chk",
"_IO_fread",
"fgetgrent",
"setdomainname",
"write",
"__clock_settime",
"getservbyport",
"if_freenameindex",
"strtod_l",
"getnetent",
"wcslen",
"getutline_r",
"posix_fallocate",
"__pipe",
"fseeko",
"lckpwdf",
"xdrrec_endofrecord",
"towctrans_l",
"inet6_opt_set_val",
"vfprintf",
"strcoll",
"ssignal",
"random",
"globfree",
"delete_module",
"_sys_siglist",
"_sys_siglist",
"basename",
"argp_state_help",
"__wcstold_internal",
"ntohl",
"closelog",
"getopt_long_only",
"getpgrp",
"isascii",
"get_nprocs_conf",
"wcsncmp",
"re_exec",
"clnt_pcreateerror",
"monstartup",
"__ptsname_r_chk",
"__fcntl",
"ntohs",
"snprintf",
"__overflow",
"__isoc99_fwscanf",
"posix_fadvise64",
"xdr_cryptkeyarg",
"__strtoul_internal",
"wmemmove",
"sysconf",
"__gets_chk",
"_obstack_free",
"setnetgrent",
"gnu_dev_makedev",
"xdr_u_hyper",
"__xmknodat",
"wcstoull_l",
"_IO_fdopen",
"inet6_option_find",
"clnttcp_create",
"isgraph_l",
"getservent",
"__ttyname_r_chk",
"wctomb",
"locs",
"fputs_unlocked",
"__memalign_hook",
"siggetmask",
"putwchar_unlocked",
"semget",
"putpwent",
"_IO_str_init_readonly",
"xdr_accepted_reply",
"initstate_r",
"__vsscanf",
"wcsstr",
"free",
"_IO_file_seek",
"ispunct",
"__daylight",
"__cyg_profile_func_exit",
"wcsrchr",
"pthread_attr_getinheritsched",
"__readlinkat_chk",
"__nss_hosts_lookup2",
"key_decryptsession",
"vwarn",
"wcpcpy"
}');
