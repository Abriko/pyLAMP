#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess
import logging
import re
import random
import string
import os
import json

#replace default config value
def change_conf(tamplate_path, args, save_path = 'null'):
	tamplate_path = re.sub('<APPROOT>', os.path.dirname(os.path.abspath(__file__)), tamplate_path)

	# save to origin or new conf
	if save_path == 'null':
		save_path = tamplate_path

	logging.debug('loading config file %s save to %s,args: %s', tamplate_path, save_path, args)
	config_file = open(tamplate_path)
	file_content = config_file.read();
	config_file.close()

	#config_file = open('/tmp/1.txt', 'w+')
	config_file = open(save_path, 'w+')

	for a in args:
		#maybe more flags
		if a.get('flags') == 're.M':
			#print a['new'],a['old']
			match = re.compile(a['old'], flags=re.M)
			file_content = match.sub(a['new'], file_content)
		else:
			file_content = re.sub(a['old'], a['new'], file_content)

	config_file.write(file_content)
	config_file.close()

	del config_file
	del file_content

#exec system commands
def exec_cmd(cmd):
	logging.debug('exec %s', cmd)
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	logging.debug('%s return messages:\n %s \n', cmd, p.stdout.read())
	logging.debug('%s filished return code : %s', cmd, p.wait())
	return p.returncode


#generate random string
def gen_random_str(lan=12):
	return ''.join(random.sample(string.ascii_letters + string.digits, lan))


#wrap exec_cmd cp
def cp(origin, dest):
	origin = re.sub('<APPROOT>', os.path.dirname(os.path.abspath(__file__)), origin)
	return exec_cmd('\cp -f %s %s' % (origin, dest))

#check user input path
def chekc_path(path):
	if os.path.exists(path):
		return path
	else:
		logging.info('input path : %s , not exist.', path)
		return False

#check and create a dir
def create_dir(path):
	if os.path.exists(path):
		logging.debug('already have dir %s', (path))
		#return ''
	else:
		logging.debug('no dir %s, create...', (path))
		os.mkdir(path)
		#return path

def save_config(config):
	try:
		config = json.dump(config, open('/etc/lamp/config', 'w+'))
	except Exception,e:
		logging.info('save config has error : %s', e)
	return config


def load_config(config_path = '/etc/lamp/config'):
	config = {}
	try:
		config = json.load(open(config_path))
	except Exception,e:
		logging.info('load config has error : %s', e)
	return config


def get_account_name(name):
	return re.sub('\.', '_', name)


def get_yseorno(str):
	while True:
		print str
		i = raw_input('[Y/N]').lower()
		if i == 'y':
			return True
		elif i == 'n':
			return False

#get user input match it
def get_options(msginfo,options):

	while True:
		i = raw_input(msginfo)
		for o in options:
			if str(o) == i:
				return o
