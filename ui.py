#!/usr/bin/python

from framework import JobManager, WorkerManager

import os
import fnmatch
import sys
import subprocess
import re
import curses
from curses.textpad import Textbox

def center(win, h, w):
	(maxh, maxw) = win.getmaxyx()
	y = maxh/2 - h/2
	x = maxw/2 - w/2
	if y < 0:
		y = 0
	if x < 0:
		x = 0
	return (y, x)

def make_screen(jmgr, wmgr):
	screen = curses.initscr()
	screen.border(0)
	curses.noecho()
	screen.addstr(1, 1, "Commands:")
	screen.addstr(2, 3, "l - List all jobs")
	screen.addstr(3, 3, "a - Add new job")
	screen.addstr(4, 3, "d - Delete jobs")
	screen.addstr(5, 3, "w - List all workers")
	screen.addstr(6, 3, "n - Create new workers")
	screen.addstr(7, 3, "t - Terminate workers")
	screen.addstr(8, 3, "e - End execution")
	screen.addstr(9, 3, "q - Leave")
	while True:
		c = screen.getch()
		if c == ord('l'):
			jobs = jmgr.get_jobs()
			n = len(jobs)
			(y, x) = center(screen, n + 3, 60)
			win = curses.newwin(n + 3, 60, y, x)
			win.border(0)
			win.addstr(1, 1, "Jobs: {0}".format(n))
			y = 2
			for (id, name, done) in jobs:
				if done:
					win.addstr(y, 1, "*{0}: {1}".format(id, name))
				else:
					win.addstr(y, 1, " {0}: {1}".format(id, name))
				y = y + 1
			c = win.getch()
			while c != ord('q'):
				c = win.getch()
			del win
		elif c == ord('e'):
			(y, x) = center(screen, 3, 30)
			win = curses.newwin(3, 30, y, x)
			win.border(0)
			win.addstr(1, 1, "Type \'exit\': ")
			curses.echo()
			text = win.getstr(1, 14)
			del win
			curses.noecho()
			if text == "exit":
				curses.endwin()
				return True
		elif c == ord('q'):
			break
		screen.touchwin()
		screen.refresh()
	curses.endwin()
	return False
