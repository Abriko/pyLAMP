#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import mysql
import os
import json
import sys
import utils

config = utils.load_config()


# create site dir and database info, return site_id
def site_create(args):
	site_root = '%s/%s' % (config['wwwroot'], args['username'])

	logging.debug('create site, args: %s', args)
	# add site record
	site_id = mysql.create_site(args['domain'], site_root)

	if site_id != -1:
		utils.create_dir(site_root)
		utils.create_dir('%s/logs' % site_root)
		utils.create_dir('%s/public_html' % site_root)

		utils.change_conf('<APPROOT>/files/vhost_template',
			[
				{'old':'<ServerName>','new':args['domain']},
				{'old':'<siteroot>','new':site_root}
			],
		'%s/sites-available/%s' % (config['apache_etc'], args['username']))

		enable_site(args['domain'])

	return site_id


def delete_site(args):
	site_root = '%s/%s' % (config['wwwroot'], args['username'])

	logging.debug('delete site, args: %s', args['domain'])
	site = mysql.delete_site(args['domain'])

	if site != -1:
		if utils.get_yseorno('Do you want backup site files?'):
			import datetime
			dt = datetime.datetime.now()
			# backup all site files to root dir
			utils.exec_cmd('tar czf /root/lamp_bak/%s-%s.tar.gz -C %s %s' %(args['domain'], dt.strftime('%Y-%m-%d_%H:%M'), config['wwwroot'], args['username']))

		utils.exec_cmd('rm -rf %s' % site_root)
		mysql.delete_mysql_bysite(site.id)

		import ftp
		ftp.delete_ftp_bysite(site.id)


def edit_site(args):
	site = mysql.check_site_id()
	msg = '''
1. Add domain alias
2. Remove domain alias
3. Enable this site
4. Disable this site

Please select option:'''

	opt = utils.get_options(msg, [1, 2, 3, 4])
	if opt == 1:
		add_alias(site, args)
	elif opt == 2:
		remove_alias(site, args)
	elif opt == 3:
		enable_site(site.domain)
	elif opt == 4:
		disable_site(site.domain)

def add_alias(site, args):
	site_alias = get_alias_data(site)
	index = find_alias(site_alias, args)
	if index:
		logging.info('you input domain already exists...')
		sys.exit(1)

	site_alias.append(args)
	save_alias(site, site_alias)


def remove_alias(site, args):
	site_alias = get_alias_data(site)
	index = find_alias(site_alias, args)
	if not index:
		logging.info('you input domain not exists...')
		sys.exit(1)

	del site_alias[index - 1]
	save_alias(site, site_alias)


def find_alias(site_alias, alias):
	i = 1
	for a in site_alias:
		if a == alias:
			return i
		i = i + 1

	return False


def get_alias_data(site):
	logging.debug('load alias data, site: %s', site)
	try:
		return json.loads(site.alias)
	except Exception,e:
		logging.debug('load alias data error, msg: %s', e)
		return []


def save_alias(site, alias):
	filename = utils.get_account_name(site.domain)

	conf_alias = 'ServerAlias %s#Alias'
	for a in alias:
		conf_alias = conf_alias % (a + ' %s')

	conf_alias = conf_alias % ''

	utils.change_conf('%s/sites-available/%s' % (config['apache_etc'], filename),
		[
			{'flags':'re.M','old':r"ServerAlias.*?$",'new':conf_alias}
		])

	utils.exec_cmd('service %s reload' % config['apache'])

	mysql.update_site_alias(site.id, alias)

'''
TODO:
maybe enable and disable site need add mysql record
'''
def enable_site(domain):
	filename = utils.get_account_name(domain)
	file1 = '%s/sites-available/%s' % (config['apache_etc'], filename)
	file2 = '%s/sites-enabled/%s' % (config['apache_etc'], filename)

	if not os.path.isfile(file1):
		logging.info('apache conf file: %s no exists!',file1)
		return

	if os.path.isfile(file2):
		logging.info('this site already enabled!')
		return

	utils.exec_cmd('ln -s %s %s' % (file1, file2))
	utils.exec_cmd('service %s reload' % config['apache'])


def disable_site(domain):
	filename = utils.get_account_name(domain)
	file1 = '%s/sites-available/%s' % (config['apache_etc'], filename)
	file2 = '%s/sites-enabled/%s' % (config['apache_etc'], filename)

	if not os.path.isfile(file1):
		logging.info('apache conf file: %s no exists!')
		return

	if not os.path.isfile(file2):
		logging.info('this site is not enabled!')
		return

	utils.exec_cmd('rm -rf %s' % (file2))
	utils.exec_cmd('service %s reload' % config['apache'])
