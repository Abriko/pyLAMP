#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import platform
import logging
import utils
import mysql
import ftp


version = 1.1

def main():
	logging.basicConfig(filename='/tmp/lampsetup.log', level=logging.DEBUG, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s', filemode='w+')
	console = logging.StreamHandler()
	console.setLevel(logging.INFO)
	#console.setLevel(logging.DEBUG)
	console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
	logging.getLogger('').addHandler(console)
	logging.info('LAMP Setup script started!\nIf an error has occurred, Please seed log file /tmp/lampsetup.log to me.\n')

	#start check
	if os.geteuid() != 0:
		logging.info('This program must be run as root, Exiting...')
		exit()
	if utils.exec_cmd('ping github.com -c 2') == 2:
		logging.info('DNS Error Has Occured, Exiting...')
		exit()


	current_os = platform.dist()[0]

	if current_os.find('Ubuntu') != -1 or current_os.find('Debian') != -1:
		go_debian()
	elif current_os.find('centos') != -1:
		go_centos()
	else:
		logging.info('System is unknown, Exiting...')
		exit()

	logging.info('LAMP Setup script finished!')

#running with debian or ubuntu
def go_debian():
	raw_input("LAMP Setup script is ready install it\nPress Enter key to continue, Press Ctrl+D to cancel the installation\n")

	#generate config file
	os.mkdir('/tmp/lamp')
	os.mkdir('/etc/lamp')
	os.mkdir('/root/lamp_bak')
  	os.mkdir('/etc/lamp/ftp_users')
	config = {}
	global version
	config['version'] = version
	config['system'] = 'u'
	config['wwwroot'] = '/var/www'
	config['apache_etc'] = '/etc/apache2'
	config['apache'] = 'apache2'
	config['ftproot'] = '/var/www'
	config['vsftpd_conf_path'] = '/etc/vsftpd.conf'
	config['root_own'] = 'www-data:www-data'

	'''
	logging.info('download files ...')
	utils.exec_cmd('wget http://s1b-static.yuki.ws/files/lamp/files.tar.xz -O /tmp/lamp/files.tar.xz')
	utils.exec_cmd('tar xvf /tmp/lamp/files.tar.xz -C /tmp/lamp')
	'''

	#setting mysql passwotrd
	mysql_root_pass = utils.gen_random_str()
	config['mysqlrootpass'] = mysql_root_pass
	utils.save_config(config)

	logging.debug('generate mysql root password : %s', mysql_root_pass)
	debconf_tmp = open('/tmp/lamp/debconf.tmp', 'w+')
	debconf_tmp.write('mysql-server mysql-server/root_password password %s\nmysql-server mysql-server/root_password_again password %s\n' % (mysql_root_pass, mysql_root_pass))
	debconf_tmp.write('iptables-persistent iptables-persistent/autosave_v4 boolean true\niptables-persistent iptables-persistent/autosave_v6 boolean true\n')
	debconf_tmp.close()
	utils.exec_cmd('debconf-set-selections /tmp/lamp/debconf.tmp')
	os.remove('/tmp/lamp/debconf.tmp')
	del debconf_tmp

	logging.info('update data packages info...')
	utils.exec_cmd('apt-get update')

	logging.info('update system, please wait...')
	#utils.exec_cmd('apt-get upgrade -y')

	logging.info('install and config packages, please wait...')
	utils.exec_cmd('apt-get install -y vim axel curl unzip build-essential python-mysqldb python-software-properties php5 apache2 libapache2-mod-php5 mysql-server php5-mysql php5-curl php5-gd php5-mcrypt php5-imagick php5-memcached php5-sqlite php5-xcache iptables-persistent libpam-mysql')


	logging.info('setting up web-server...')

	logging.debug('setting apache conf')
	httpd_conf = open('/etc/apache2/httpd.conf', 'w')
	httpd_conf.write('ServerName %s\n' % (platform.uname()[1]))
	httpd_conf.close()
	del httpd_conf

	utils.change_conf('/etc/apache2/apache2.conf',
		[
			{'old':'Timeout 300','new':'Timeout 45'},
			{'old':'MaxKeepAliveRequests 100','new':'MaxKeepAliveRequests 200'}
		]
	)

	utils.change_conf('/etc/apache2/conf.d/security',
		[
			{'old':'ServerTokens OS','new':'ServerTokens Prod'},
			{'old':'ServerSignature On','new':'ServerSignature Off'}
		]
	)

	# Enable mod-rewrite
	utils.exec_cmd('a2enmod rewrite')

	# Set apache php.ini
	logging.debug('Setting php.ini')
	utils.change_conf('/etc/php5/apache2/php.ini',
		[
			{'old':'post_max_size = 8M','new':'post_max_size = 50M'},
			{'old':'upload_max_filesize = 2M','new':'upload_max_filesize = 50M'},
			{'old':'expose_php = On','new':'expose_php = Off'},
			{'old':'display_errors = Off','new':'display_errors = On'},
			{'old':';date.timezone =','new':'date.timezone = Asia/Chongqing'},
			{'old':'request_order = "GP"','new':'request_order = "CGP"'}
		]
	)


	# Change default www dir
	utils.exec_cmd('mkdir -p /var/www/public_html')
	utils.exec_cmd('mv /var/www/index.html /var/www/public_html/')
	utils.change_conf('/etc/apache2/sites-enabled/000-default', [{'old':'/var/www','new':'/var/www/public_html'}])

	# Init phpmyadmin and lamp user pass
	utils.exec_cmd('service mysql restart')
	lamp_controluser_pass = mysql.init_db(mysql_root_pass)

	utils.cp('<APPROOT>/files/phpmyadmin_host', '/etc/apache2/mods-available/phpmyadmin.conf')
	utils.exec_cmd('ln -s /etc/apache2/mods-available/phpmyadmin.conf /etc/apache2/mods-enabled/phpmyadmin.conf')

	config['lampuser'] = 'lamp'
	config['lamppass'] = lamp_controluser_pass
	utils.save_config(config)

	# create test php script
	utils.exec_cmd(r'echo "<?php phpinfo() ?>" > /var/www/public_html/test.php')

	# Change wwwroot permissions
	utils.exec_cmd('chown -R www-data:www-data /var/www')
	utils.exec_cmd('chmod -R go-rwx /var/www')
	utils.exec_cmd('chmod -R g+rw /var/www')
	utils.exec_cmd('chmod -R o+r /var/www')

	utils.exec_cmd('service apache2 restart')

	logging.info('setting up ftp-server...')

	# Init ftp and create main account
	#ftp_pass = ftp.init_ftp()
	if platform.machine() == 'x86_64':
		utils.exec_cmd('axel -q -n 3 -o /tmp/lamp/vsftpd.deb http://ftp.jaist.ac.jp/pub/Linux/ubuntu/pool/main/v/vsftpd/vsftpd_3.0.2-1ubuntu1_amd64.deb')
		#add fix 12.04 pam.d-mysql bugs "libgcc_s.so.1 must be installed for pthread_cancel to work"
		utils.exec_cmd('DEBIAN_FRONTEND=noninteractive apt-get install -qq libpam-ldap')
	else:
		utils.exec_cmd('axel -q -n 3 -o /tmp/lamp/vsftpd.deb http://ftp.jaist.ac.jp/pub/Linux/ubuntu/pool/main/v/vsftpd/vsftpd_3.0.2-1ubuntu1_i386.deb')

	returncode = utils.exec_cmd('dpkg -i /tmp/lamp/vsftpd.deb')
	if returncode == 2:
		logging.debug('install vsftpd failed!')

	utils.change_conf('<APPROOT>/files/vsftpd_conf', [
		{'old':'<ftpuser>','new':'ftp'},
		{'old':'<guestuser>','new':'www-data'}
	], '/etc/vsftpd.conf')


	#add fix 500 OOPS: priv_sock_get_cmd
	if platform.machine() == 'x86_64':
		utils.change_conf('/etc/vsftpd.conf', [{'old':'ftp_users','new':'ftp_users\nseccomp_sandbox=NO'}])

	utils.change_conf('<APPROOT>/files/vsftpd_mysql', [{'old':'<passwd>','new':lamp_controluser_pass}], '/etc/pam.d/vsftpd-mysql')

	#set master ftp account
	args = {}
	args['username'] = 'ftpuser'
	args['path'] = '/var/www'
	args['site_id'] = 1

	ftp_pass = ftp.create_ftp(args)
	utils.exec_cmd('service vsftpd restart')


	logging.info('setting up system...')
	# Set iptables
	utils.cp('<APPROOT>/files/iptables_rules', '/etc/iptables/rules.v4')
	utils.exec_cmd('service iptables-persistent restart')

	#load kernel ip_nat_ftp
  	utils.exec_cmd('modprobe nf_nat_ftp')
  	utils.exec_cmd('echo "nf_nat_ftp" >> /etc/modules')


  	# Add auto start at boot
	utils.exec_cmd('update-rc.d apache2 defaults')
	utils.exec_cmd('update-rc.d mysql defaults')
	utils.exec_cmd('update-rc.d vsftpd defaults')

	finish_install(mysql_root_pass, ftp_pass, 'apt-get upgrade -y')





#running with debian or centos
def go_centos():
	raw_input("LAMP Setup script is ready install it\nPress Enter key to continue, Press Ctrl+D to cancel progress\n")

	#generate config file
	os.mkdir('/tmp/lamp')
	os.mkdir('/etc/lamp')
	os.mkdir('/root/lamp_bak')
  	os.mkdir('/etc/lamp/ftp_users')
	config = {}
	global version
	config['version'] = version
	config['system'] = 'c'
	config['wwwroot'] = '/var/www'
	config['apache_etc'] = '/etc/httpd'
	config['apache'] = 'httpd'
	config['ftproot'] = '/var/www'
	config['vsftpd_conf_path'] = '/etc/vsftpd/vsftpd.conf'
	config['root_own'] = 'apache:apache'


	#setting mysql passwotrd
	mysql_root_pass = utils.gen_random_str()
	config['mysqlrootpass'] = mysql_root_pass
	utils.save_config(config)

	logging.debug('generate mysql root password : %s', mysql_root_pass)


	logging.info('load yum repo...')
	utils.exec_cmd('yum install yum-priorities -y')
	utils.exec_cmd('wget http://s1b-static.yuki.ws/files/lamp/files.tar.xz -O /tmp/lamp/files.tar.xz')
	utils.exec_cmd('tar xvf /tmp/lamp/files.tar.xz -C /tmp/lamp')

	# Get system detail info
	machine = platform.machine()
	if machine == 'i686':
		machine = 'i386'
	ver = platform.dist()[1]
	if ver >= 6:
		ver = 6
		utils.exec_cmd('wget http://ftp.riken.jp/Linux/fedora/epel/6/%s/epel-release-6-8.noarch.rpm -O /tmp/lamp/epel-release.rpm' % (machine))
		utils.exec_cmd('wget http://pkgs.repoforge.org/rpmforge-release/rpmforge-release-0.5.3-1.el6.rf.%s.rpm -O /tmp/lamp/rpmforge-release.rpm' % (platform.machine()))
		#download vsftpd
		utils.exec_cmd('wget http://centos.alt.ru/repository/centos/6/%s/vsftpd-3.0.2-2.el6.%s.rpm -O /tmp/lamp/vsftpd.rpm' %(machine, platform.machine()))
	else:
		ver = 5
		utils.exec_cmd('wget http://ftp.riken.jp/Linux/fedora/epel/5/%s/epel-release-5-4.noarch.rpm -O /tmp/lamp/epel-release.rpm' % (machine))
		utils.exec_cmd('wget http://pkgs.repoforge.org/rpmforge-release/rpmforge-release-0.5.3-1.el5.rf.%s.rpm -O /tmp/lamp/rpmforge-release.rpm' % (machine))
		utils.exec_cmd('wget http://centos.alt.ru/repository/centos/5/%s/vsftpd-3.0.2-1.el5.%s.rpm -O /tmp/lamp/vsftpd.rpm' %(platform.machine(), platform.machine()))

	utils.exec_cmd('yum localinstall /tmp/lamp/*-release.rpm -y')

	# Change yum priority
	utils.change_conf('/etc/yum.repos.d/CentOS-Base.repo', [{'old':'gpgcheck=1','new':'priority=1\ngpgcheck=1'}])
	utils.change_conf('/etc/yum.repos.d/rpmforge.repo', [{'old':'enabled =','new':'priority = 10\nenabled ='}])
	utils.change_conf('/etc/yum.repos.d/epel.repo', [{'old':'enabled=','new':'priority=11\nenabled='}])

	logging.info('update system, please wait...')
	utils.exec_cmd('yum makecache')
	#utils.exec_cmd('yum update -y')

	logging.info('install and config packages, please wait...')
	utils.exec_cmd('yum install axel screen MySQL-python vim pam_mysql httpd mysql-server php php-mysql php-pdo php-mcrypt php-mbstring php-gd php-pecl-imagick php-pecl-memcached php-xcache -y')


	logging.info('setting up web-server...')
	utils.change_conf('/etc/httpd/conf/httpd.conf',
		[
			{'old':'ple.com:80','new':'ple.com:80\nServerName %s' % (platform.uname()[1])},
			{'old':'Timeout 60','new':'Timeout 45'},
			{'old':'MaxKeepAliveRequests 100','new':'MaxKeepAliveRequests 200'},
			{'old':'ServerTokens OS','new':'ServerTokens Prod'},
			{'old':'ServerSignature On','new':'ServerSignature Off'},
			{'old':'/var/www/html','new':'/var/www/public_html'},
			{'old':'#NameVirtualHost \*:80','new':'NameVirtualHost *:80'},
			{'old':'#</VirtualHost>','new':'#</VirtualHost>\nInclude sites-enabled/'}
		]
	)

	# Set apache php.ini
	logging.debug('Setting php.ini')
	utils.change_conf('/etc/php.ini',
		[
			{'old':'post_max_size = 8M','new':'post_max_size = 50M'},
			{'old':'upload_max_filesize = 2M','new':'upload_max_filesize = 50M'},
			{'old':'expose_php = On','new':'expose_php = Off'},
			{'old':';date.timezone =','new':'date.timezone = Asia/Chongqing'},
			{'old':'request_order = "GP"','new':'request_order = "CGP"'}
		]
	)

	# Fix mcrypt.ini error
	utils.change_conf('/etc/php.d/mcrypt.ini',
		[
			{'old':'module.so','new':'mcrypt.so'}
		]
	)

	os.mkdir('/etc/httpd/sites-available')
	os.mkdir('/etc/httpd/sites-enabled')
	utils.exec_cmd('mv /var/www/html /var/www/public_html')

	# Create a default site
	os.mkdir('/var/www/logs')
	utils.change_conf('<APPROOT>/files/vhost_template',
		[
			{'old':'ServerName <ServerName>','new':''},
			{'old':'<ServerName>','new':'default'},
			{'old':'<siteroot>','new':'/var/www'}
		],
	'/etc/httpd/sites-enabled/default')



	# Init phpmyadmin and lamp user pass
	utils.exec_cmd('service mysqld restart')

	utils.exec_cmd('mysqladmin -u root password \'%s\'' % (mysql_root_pass))
	utils.cp('<APPROOT>/files/phpmyadmin_host', '/etc/httpd/conf.d/phpmyadmin.conf')
	lamp_controluser_pass = mysql.init_db(mysql_root_pass)

	config['lampuser'] = 'lamp'
	config['lamppass'] = lamp_controluser_pass
	utils.save_config(config)

	
	utils.exec_cmd(r'echo "<?php phpinfo() ?>" > /var/www/public_html/test.php')

	# Change wwwroot permissions
	utils.exec_cmd('chown -R apache:apache /var/www')
	utils.exec_cmd('chmod -R go-rwx /var/www')
	utils.exec_cmd('chmod -R g+rw /var/www')
	utils.exec_cmd('chmod -R o+r /var/www')

	utils.exec_cmd('service httpd restart')

	logging.info('setting up ftp-server...')


	# Init ftp and create main account
	utils.exec_cmd('yum localinstall /tmp/lamp/vsftpd.rpm -y')
	utils.exec_cmd('mkdir -p /var/run/vsftpd')

	utils.change_conf('<APPROOT>/files/vsftpd_conf', [
		{'old':'<ftpuser>','new':'ftp'},
		{'old':'<guestuser>','new':'apache'}
	], '/etc/vsftpd/vsftpd.conf')

	utils.change_conf('<APPROOT>/files/vsftpd_mysql', [{'old':'<passwd>','new':lamp_controluser_pass}], '/etc/pam.d/vsftpd-mysql')

	args = {}
	args['username'] = 'ftpuser'
	args['path'] = '/var/www'
	args['site_id'] = 1

	ftp_pass = ftp.create_ftp(args)
	utils.exec_cmd('service vsftpd restart')


	logging.info('setting up system...')
	# Set iptables
	utils.cp('<APPROOT>/files/iptables_rules', '/etc/sysconfig/iptables')
	utils.exec_cmd('service iptables restart')

	#load kernel ip_nat_ftp
	utils.exec_cmd('modprobe nf_nat_ftp')
	utils.exec_cmd('echo "modprobe nf_nat_ftp" >> /etc/sysconfig/modules/nf_nat_ftp.modules')
	utils.exec_cmd('chmod +x /etc/sysconfig/modules/nf_nat_ftp.modules')

	# Add auto start at boot
	utils.exec_cmd('chkconfig httpd on')
	utils.exec_cmd('chkconfig mysqld on')
	utils.exec_cmd('chkconfig vsftpd on')

	finish_install(mysql_root_pass, ftp_pass, 'yum update -y')


def finish_install(mysql_root_pass, ftp_pass, cmd=''):


	if cmd != '':
		utils.exec_cmd('screen -dmS sys-update %s' % (cmd))

	finish_text = '''
-------------------------------------------------------------------------------------------------------------------
 __   __ ___ _______ _______ ___ _______ __    _   _______ _______ __   __ _______ ___     _______ _______ _______
|  |_|  |   |       |       |   |       |  |  | | |       |       |  |_|  |       |   |   |       |       |       |
|       |   |  _____|  _____|   |   _   |   |_| | |       |   _   |       |    _  |   |   |    ___|_     _|    ___|
|       |   | |_____| |_____|   |  | |  |       | |       |  | |  |       |   |_| |   |   |   |___  |   | |   |___
|       |   |_____  |_____  |   |  |_|  |  _    | |      _|  |_|  |       |    ___|   |___|    ___| |   | |    ___|
| ||_|| |   |_____| |_____| |   |       | | |   | |     |_|       | ||_|| |   |   |       |   |___  |   | |   |___
|_|   |_|___|_______|_______|___|_______|_|  |__| |_______|_______|_|   |_|___|   |_______|_______| |___| |_______|

-------------------------------------------------------------------------------------------------------------------

Important!!!
By default system will run update progress, Please don't reboot or shutdown this server in 30 minutes.


Server information

WEB&FTP root: /var/www (Make sure upload you site files to your /public_html directory)
MySQL root pass: %s
Main FTP username: ftpuser, pass: %s
phpMyAdmin url: http://domain/phpmyadmin


More information: https://github.com/Abriko/pyLAMP

Now you can press key "q" exit the installation.
	''' % (mysql_root_pass, ftp_pass)

	f = open('/tmp/lamp/finish_msg', 'w+')
	f.write(finish_text)
	f.close()
	os.system('cat /tmp/lamp/finish_msg | less')
	utils.exec_cmd('rm -rf /tmp/lamp')


if __name__ == '__main__':
    main()
