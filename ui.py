#!/usr/bin/python

import os
import fnmatch
import sys
import subprocess
import re
import curses
import signal
import socket

def center(win, h, w):
	(maxh, maxw) = win.getmaxyx()
	y = maxh/2 - h/2
	x = maxw/2 - w/2
	if y < 0:
		y = 0
	if x < 0:
		x = 0
	return (y, x)

def show_list(screen, name, items, print_func, extra_keys=None,
		extra_keys_args=None):
	(maxy, maxx) = screen.getmaxyx()
	n = len(items)
	if n + 3 > maxy:
		n = maxy - 3
	(winy, winx) = center(screen, n + 3, 60)
	start = 0
	left = 0
	win = None
	while True:
		if not win:
			win = curses.newwin(n + 3, 60, winy, winx)
			win.keypad(1)
			win.border(0)
			win.addstr(1, 1, "{0}: {1}".format(name, len(items)))
			y = 2
			for i in range(n):
				s = print_func(items[start + i])
				s = s[left:]
				if len(s) > 58:
					s = s[:58]
				win.addstr(y, 1, s)
				y = y + 1

		c = win.getch()
		if c == ord('q'):
			break
		if c == curses.KEY_UP:
			if start > 0:
				start -= 1
				del win
				win = None
			continue
		if c == curses.KEY_DOWN:
			if start + n < len(items):
				start += 1
				del win
				win = None
			continue
		if c == curses.KEY_LEFT:
			if left > 0:
				left -= 1
				del win
				win = None
			continue
		if c == curses.KEY_RIGHT:
			left += 1
			del win
			win = None
			continue
		if extra_keys:
			if extra_keys(screen, c, extra_keys_args):
				break
			del win
			win = None
			continue
	del win

def print_job(job):
	(id, name, status) = job
	if status:
		if status.success:
			return "*{0}: {1}".format(id, name)
		else:
			return "!{0}: {1}".format(id, name)
	else:
		return " {0}: {1}".format(id, name)

def print_worker(worker):
	(name, job) = worker
	if job:
		return "{0}: Job {1}".format(name, job)
	else:
		return "{0}: Idle".format(name)

def print_task(task):
	(k, t) = task
	return "{0}: {1}".format(k, t.name)

def task_keys(screen, key, args):
	(scheduler, keys) = args
	task = None
	for (k, t) in keys:
		if key == ord(k):
			task = t
	if not task:
		return False
	(y, x) = center(screen, 2 + len(task.arg_defs), 60)
	win = curses.newwin(2 + len(task.arg_defs), 60, y, x)
	win.border(0)
	y = 1
	run_args = []
	for a in task.arg_defs:
		win.addstr(y, 1, a + ": ")
		curses.echo()
		text = win.getstr(y, len(a) + 3)
		curses.noecho()
		y += 1
		run_args.append(text)
	del win
	task.create_job(scheduler, run_args)
	return True

def show_message(screen, message):
	n = len(message)
	(y, x) = center(screen, 3, n + 2)
	win = curses.newwin(3, n + 2, y, x)
	win.border(0)
	win.addstr(1, 1, message)
	win.getch()
	del win

def confirm_exit(screen):
	(y, x) = center(screen, 3, 30)
	win = curses.newwin(3, 30, y, x)
	win.border(0)
	win.addstr(1, 1, "Type \'exit\': ")
	curses.echo()
	text = win.getstr(1, 14)
	del win
	curses.noecho()
	return text == "exit"

def make_screen(scheduler, tasks):
	sighandler = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, signal.SIG_IGN)

	log = os.open("ui.log", os.O_RDWR|os.O_CREAT|os.O_TRUNC)
	olderr = os.dup(2)
	os.dup2(log, 2)

	ret = False
	screen = curses.initscr()
	screen.border(0)
	curses.noecho()
	screen.addstr(0, 1, socket.gethostname())
	screen.addstr(2, 1, "Commands:")
	screen.addstr(3, 3, "l - List all jobs")
	screen.addstr(4, 3, "a - Add new job")
	screen.addstr(5, 3, "r - requeue a job")
	screen.addstr(6, 3, "c - Clear finished jobs")
	screen.addstr(7, 3, "w - List all workers")
	screen.addstr(8, 3, "n - Create new worker")
	screen.addstr(9, 3, "f - Requeue failed jobs")
	screen.addstr(10, 3, "p - Print failed jobs and clear")
	screen.addstr(11, 3, "e - End execution")
	screen.addstr(12, 3, "q - Leave")
	while True:
		c = screen.getch()
		if c == ord('l'):
			show_list(screen, "Jobs", scheduler.get_jobs(), print_job)
		elif c == ord('a'):
			keys = []
			for i in range(len(tasks)):
				if i < 10:
					keys.append((chr(ord('0') + i),
						tasks[i]))
				else:
					keys.append((chr(ord('a') + i - 10),
						tasks[i]))

			show_list(screen, "Tasks", keys, print_task,
					task_keys, (scheduler, keys))
		elif c == ord('r'):
			(y, x) = center(screen, 3, 30)
			win = curses.newwin(3, 30, y, x)
			win.border(0)
			win.addstr(1, 1, "Job ID: ")
			curses.echo()
			try:
				id = int(win.getstr(1, 9))
			except:
				del win
				pass
			else:
				del win
				curses.noecho()
				scheduler.requeue_job(id)
		elif c == ord('c'):
			scheduler.clear_jobs()
			show_message(screen, "finished jobs are cleared")
		elif c == ord('w'):
			show_list(screen, "Workers", scheduler.get_workers(), print_worker)
		elif c == ord('n'):
			scheduler.add_worker()
			show_message(screen, "A new worker is created")
		elif c == ord('f'):
			x = scheduler.requeue_failed_jobs()
			message = "Requeued " + str(x) + "failed jobs"
			show_message(screen, message)
		elif c == ord('p'):
			scheduler.print_failed_jobs()
			scheduler.clear_failed_jobs()
			show_message(screen, "Failed jobs logged and cleared")
		elif c == ord('e'):
			if confirm_exit(screen):
				scheduler.exit()
				break
		elif c == ord('q'):
			break
		screen.redrawwin()
		screen.refresh()

	curses.endwin()
	os.dup2(olderr, 2)
	signal.signal(signal.SIGINT, sighandler)
