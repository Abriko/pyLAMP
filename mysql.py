#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import logging
import json
import utils
import sys

def init_db(mysql_root_pass):
	import db
	import platform

	logging.info('download phpmyadmin and config')
	utils.exec_cmd('axel -q -n 10 -o /tmp/lamp/phpmyadmin.tar.xz http://softlayer-ams.dl.sourceforge.net/project/phpmyadmin/phpMyAdmin/4.1.8/phpMyAdmin-4.1.8-all-languages.tar.xz')
	utils.exec_cmd('tar xf /tmp/lamp/phpmyadmin.tar.xz -C /var/www')
	utils.exec_cmd('mv /var/www/phpMyAdmin* /var/www/phpmyadmin')


	data = db.Connection(host='localhost',database='mysql',user='root',password=mysql_root_pass)

	# Support centos change all root pass
	data.execute("SET PASSWORD FOR 'root'@'127.0.0.1' = PASSWORD('%s');" % (mysql_root_pass))
	data.execute("SET PASSWORD FOR 'root'@'%s' = PASSWORD('%s');" % (platform.uname()[1], mysql_root_pass))

	# Create lamp&phpmyadmin control user
	lamp_controluser_pass = utils.gen_random_str()
	logging.debug('generate control user password : %s', lamp_controluser_pass)
	data.execute('CREATE USER "lamp"@"localhost" IDENTIFIED BY \"%s\";CREATE DATABASE IF NOT EXISTS `lamp`;GRANT ALL PRIVILEGES ON *.* TO "lamp"@"localhost" WITH GRANT OPTION;' % (lamp_controluser_pass))


	# Clean up default users
	data.execute('delete from mysql.user where user="";')
	data.execute("DROP USER ''@'%%';")

	#data.execute('delete from mysql.user where user = "root" and host != "localhost";flush privileges')
	data.execute("flush privileges;")
	del data

	utils.exec_cmd('mysql -uroot -p%s < %s/files/create_tables.sql' % (mysql_root_pass, os.path.dirname(os.path.abspath(__file__))))
	utils.cp('<APPROOT>/files/phpmyadmin_config.inc.php', '/var/www/phpmyadmin/config.inc.php')

	utils.change_conf('/var/www/phpmyadmin/config.inc.php',
		[
			{'old':'lamp_pass_value','new':lamp_controluser_pass},
			{'old':'blowfish_secret_value','new':utils.gen_random_str(20)}
		]
	)
	return lamp_controluser_pass


# create mysql user and database
def create_mysqluser(args):
	import db
	config = utils.load_config()
	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])


	if data.get('SELECT USER FROM mysql.user where user = \"%s\"' % args['username']):
		logging.info('mysql user already exists, exiting...')
		return None

	logging.debug('create mysql user and database: %s', args['username'])
	user_pass = utils.gen_random_str()
	try:
	# create user
		data.execute('CREATE USER \"%s\"@"localhost" IDENTIFIED BY \"%s\";' % (args['username'], user_pass))
		data.execute('CREATE DATABASE IF NOT EXISTS `%s`' % (args['username']))
		data.execute('GRANT ALL PRIVILEGES ON `%s`.* TO \"%s\"@"localhost";' % (args['username'], args['username']))

		# create user info
		data.execute('INSERT INTO `lamp`.`lamp__mysql` (`id`, `site_id`, `login_name`) VALUES (NULL, %i, \"%s\");' % (args['site_id'], args['username']))
	except Exception,e:
		logging.info('create mysql user has some errors : %s', e)
		user_pass = None
	finally:
		del data

	return user_pass

# delete mysql user and database
def delete_mysql(arg=None):
	config = utils.load_config()
	m = check_mysql_id(arg)
	logging.debug('get mysql info m: %s', m)

	if not utils.get_yseorno('Do you really want to delete mysql user: %s and drop databases that have the same names as the users?' % m[1]):
		sys.exit()

	import db
	config = json.load(open('/etc/lamp/config'))

	if utils.get_yseorno('Do you want to backup database?'):
		bk_name = backup_database(m[1], config)
		print 'Database backup to %s' % bk_name


	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])
	try:
		r_mysql = data.get('SELECT user, host FROM mysql.user WHERE user = \"%s\"' % m[1])

		logging.debug('del mysql %s, %s', m, r_mysql)
		if r_mysql:
			data.execute('DROP USER \"%s\"@\"%s\"' % (r_mysql.user, r_mysql.host))
			data.execute('DROP DATABASE %s' % m[1])

			data.execute('DELETE FROM lamp__mysql WHERE login_name = \"%s\"' % r_mysql.user)
		else:
			logging.info('Nothing to delete..')
	except Exception,e:
		logging.info('delete mysql and database has some errors : %s', str(e))
		#sys.exit(1)
	finally:
		del data

	#return bk_name


def delete_mysql_bysite(site_id):
	import db
	config = utils.load_config()
	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])
	mysqls = data.query('SELECT m.id, m.login_name FROM lamp__mysql AS m WHERE m.site_id = %s' % site_id)

	logging.debug('delete mysqls by site_id: %s,mysqls: %s', site_id, mysqls)
	for m in mysqls:
		bk_name = backup_database(m.login_name, config)
		print 'Database %s backup to %s' % (m.login_name, bk_name)

		r_mysql = data.get('SELECT user, host FROM mysql.user WHERE user = \"%s\"' % m.login_name)
		logging.debug('del mysql %s, %s', m.login_name, r_mysql)
		try:
			data.execute('DROP USER \"%s\"@\"%s\"' % (r_mysql.user, r_mysql.host))
			data.execute('DROP DATABASE %s' % m.login_name)

			data.execute('DELETE FROM lamp__mysql WHERE login_name = \"%s\"' % m.login_name)
		except Exception,e:
			logging.info('delete mysql and database has some errors : %s', str(e))

	del data

def backup_database(name, config):
	import datetime
	dt = datetime.datetime.now()
	name = '/root/lamp_bak/%s-%s.sql.gz' % (name, dt.strftime('%Y-%m-%d_%H:%M'))
	utils.exec_cmd('mysqldump -u%s -p%s lamp  | gzip > %s' % (config['lampuser'], config['lamppass'], name))
	return name


def reset_mysql_pass(arg=None):
	m = check_mysql_id(arg)

	import db
	config = utils.load_config()
	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])
	user_pass = utils.gen_random_str()
	try:
		data.execute('UPDATE mysql.user SET password=PASSWORD(\'%s\') WHERE user=\'%s\'' % (user_pass, m[1]))
		data.execute('FLUSH PRIVILEGES')
	except Exception,e:
		logging.info('delete mysql and database has some errors : %s', str(e))
		sys.exit(1)
	finally:
		del data

	print 'MySQL user: %s password change to: %s' % (m[1], user_pass)

# get all mysql info
def get_mysqls(arg=None):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	if not arg:
		mysqls = data.query('SELECT m.id, m.site_id, m.login_name, s.domain FROM lamp__mysql AS m, lamp__sites AS s WHERE m.site_id = s.id ORDER BY m.id')
	elif arg[0].isdigit():
		mysqls = data.query('SELECT m.id, m.site_id, m.login_name, s.domain FROM lamp__mysql AS m, lamp__sites AS s WHERE m.site_id = s.id AND m.id = %s ORDER BY m.id' % arg[0])
	else:
		mysqls = data.query('SELECT m.id, m.site_id, m.login_name, s.domain FROM lamp__mysql AS m, lamp__sites AS s WHERE m.site_id = s.id AND m.login_name LIKE \"%%{0}%%\" ORDER BY m.id'.format(arg[0]))

	print 'MySQL(%i):' % len(mysqls)
	if mysqls:
		for m in mysqls:
			print '-' * 50
			print '\nID\tuser\tsite'
			print '%s \t%s \t%s' % (m.id, m.login_name, m.domain)


# check input mysql id, return login_name
def check_mysql_id(arg):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	mid = -1
	# get all mysql user
	mysqls = data.query('SELECT m.id, m.site_id, m.login_name, s.domain FROM lamp__mysql AS m, lamp__sites AS s WHERE m.site_id = s.id ORDER BY m.id')

	if arg and arg[0].isdigit():
		mid = arg[0]


	while True:

		if mid == -1:
			print '\nID\tuser\t\tsite'
			for m in mysqls:
				print '%s \t%s  \t%s' % (m.id, m.login_name, m.domain)
			mid = raw_input('Please input MySQL id:')

		for m in mysqls:
			if str(m.id) == mid:
				return [mid, m.login_name]
		# no found in this loop
		mid = -1


'''
sites
'''

def create_site(domain, site_root):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	site = data.get('select domain, site_root from lamp.lamp__sites where domain = "%s"' % domain)
	if site:
		logging.info('domain %s already exists, exiting...', domain)
		sys.exit(1)

	logging.debug('insert site domain: %s, site_root: %s', domain, site_root)
	try:
		site = data.insert('lamp__sites',domain=domain, site_root=site_root)
	except Exception,e:
		logging.info('insert site to mysql has some errors : %s', str(e))
		site = -0
	finally:
		del data

	return site


def delete_site(domain):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	if domain.isdigit():
		site = data.get('SELECT id, domain, site_root FROM lamp.lamp__sites WHERE id = %s' % domain)
	else:
		site = data.get('SELECT id, domain, site_root FROM lamp.lamp__sites WHERE domain = "%s"' % domain)

	if not site:
		logging.info('domain %s don\'t exists, Please pick one:', domain)
		site = check_site_id()

	logging.debug('delete site domain: %s', domain)

	# don't delete default site
	if site.id == 1:
		logging.warning('You can\'t delete default site')
		sys.exit(-1)

	try:
		data.execute('DELETE FROM lamp.lamp__sites WHERE domain = "%s"' % domain)

	except Exception,e:
		logging.info('delete site to mysql has some errors : %s', str(e))
		site = -0
	finally:
		del data

	logging.debug('site: %s deleted', site)
	return site


def update_site_alias(site_id, alias):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])
	alias = json.dumps(alias)
	try:
		data.execute('UPDATE lamp__sites SET alias=\'%s\' WHERE id=%s' % (alias, site_id))
	except Exception,e:
		logging.info('update site alias has some errors: %s', str(e))
		return False
	finally:
		del data
	return True

# list all site, or use id and domain to search site
def get_sites(arg=None):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	if not arg:
		sites = data.query('SELECT id, domain, site_root, alias FROM lamp.lamp__sites ORDER BY id')
	elif arg[0].isdigit():
		sites = data.query('SELECT id, domain, site_root, alias FROM lamp.lamp__sites WHERE id = %s' % arg[0])
	else:
		sites = data.query('SELECT id, domain, site_root, alias FROM lamp.lamp__sites WHERE domain LIKE \"%%{0}%%\" ORDER BY id'.format(arg[0]))

	for s in sites:
	  r_ftp = data.query('SELECT username, local_root FROM lamp.lamp__ftp WHERE site_id  = %s', s.id)
	  r_mysql = data.query('SELECT login_name FROM lamp.lamp__mysql WHERE site_id  = %s', s.id)

	  print '-' * 50
	  print 'ID\tdomain\t\tpath'
	  print '%s\t%s  \t%s' % (s.id, s.domain, s.site_root)

	  if s.alias:
		  site_alias = json.loads(s.alias)
		  alias = ''
		  for a in site_alias:
		  	alias = alias + a + '\t'
		  print '\nAlias: %s' % alias

	  print '\nFTP(%i): user\t\tpath' % len(r_ftp)
	  if r_ftp:
		  for f in r_ftp:
		   print '\t%s  \t%s' % (f.username, f.local_root)

	  print '\nMySQL(%i): user' % len(r_mysql)
	  if r_mysql:
		  for m in r_mysql:
		  	print '\t%s' % m.login_name


# check input site id, return site domain
def check_site_id(arg=None):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	sid = -1
	sites = data.query('SELECT id, domain, site_root, alias FROM lamp.lamp__sites ORDER BY id')

	if arg and arg[0].isdigit():
		sid = arg[0]


	while True:

		if sid == -1:
			print 'ID\tdomain\t\tpath'
			for s in sites:
				print '%s\t%s \t%s' % (s.id, s.domain, s.site_root)
			sid = raw_input('[ID]:')

		for s in sites:
			if str(s.id) == sid:
				return s
		sid = -1


'''
ftp
'''

def create_mysql_ftpuser(args):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	#check exists site
	#FIXME: can create cross dir ftp
	site = data.get('SELECT domain, site_root FROM lamp.lamp__sites WHERE id = %i' % args['site_id'])
	if site == None:
		logging.info('input site is not exists...')
		return

	user_pass = utils.gen_random_str()
	logging.debug('generate ftp root password : %s, site domain: %s', user_pass, site['domain'])
	try:
		data.execute('INSERT INTO `lamp`.`lamp__ftp` (`id`, `site_id`, `username`, `password`, `local_root`) VALUES (NULL, %i, \'%s\', password(\'%s\'), \'%s\');' % (args['site_id'], args['username'], user_pass, args['path']))
	except Exception,e:
		logging.info('insert ftpuser to mysql has some errors : %s', str(e))
		user_pass = ''
	finally:
		del data
	return user_pass




def delete_mysql_ftpuser(username):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	if username.isdigit():
		r = data.get('SELECT id, username, local_root FROM lamp__ftp WHERE id = \"%s\"' % username)
	else:
		r = data.get('SELECT id, username, local_root FROM lamp__ftp WHERE username = \"%s\"' % username)


	if not r:
		logging.info('FTP: %s don\'t exist! Please give me ftp id or username', username)
		r = check_ftp_id()


	try:
		logging.debug('del ftp: %s, r: %s', username, r)
		data.execute('DELETE FROM lamp__ftp WHERE id = %s' % r.id)
	except Exception,e:
		logging.info('delete ftpuser to mysql has some errors : %s', str(e))
		return False
	finally:
		del data
	return r


def get_ftps_bysite(site_id):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	ftps = data.query('SELECT f.id FROM lamp__ftp AS f WHERE f.site_id = %s' % site_id)

	logging.debug('delete ftps by site_id: %s, ftps: %s', site_id, ftps)

	del data
	return ftps



def get_ftps(arg=None):
	import db
	config = utils.load_config()
	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	if not arg:
		ftps = data.query('SELECT f.id, f.site_id, f.username, f.local_root, s.domain FROM lamp__ftp AS f, lamp__sites AS s WHERE f.site_id = s.id ORDER BY f.id')
	elif arg[0].isdigit():
		ftps = data.query('SELECT f.id, f.site_id, f.username, f.local_root, s.domain FROM lamp__ftp AS f, lamp__sites AS s WHERE f.site_id = s.id AND f.id = %s ORDER BY f.id' % arg[0])
	else:
		ftps = data.query('SELECT f.id, f.site_id, f.username, f.local_root, s.domain FROM lamp__ftp AS f, lamp__sites AS s WHERE f.site_id = s.id AND f.username LIKE \"%%{0}%%\" ORDER BY f.id'.format(arg[0]))

	print 'FTP(%i):' % len(ftps)
	if ftps:
		for f in ftps:
			print '-' * 50
			print '\nID\tuser\t\tpath\t\tsite'
			print '%s \t%s \t%s \t%s' % (f.id, f.username, f.local_root, f.domain)


# check input ftp id, return ftp user
def check_ftp_id(arg=None):
	import db
	config = utils.load_config()

	data = db.Connection(host='127.0.0.1',database='lamp',user=config['lampuser'],password=config['lamppass'])

	fid = -1
	ftps = data.query('SELECT f.id, f.site_id, f.username, f.local_root, s.domain FROM lamp__ftp AS f, lamp__sites AS s WHERE f.site_id = s.id ORDER BY f.id')

	if arg and arg[0].isdigit():
		fid = arg[0]


	while True:

		if fid == -1:
			print '\nID\tuser\t\tpath\t\tsite'
			for f in ftps:
				print '%s \t%s  \t%s  \t%s' % (f.id, f.username, f.local_root, f.domain)
			fid = raw_input('Please input FTP id:')

		for f in ftps:
			if str(f.id) == fid:
				return f
		fid = -1

