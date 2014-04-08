#!/usr/bin/python
# -*- coding: utf-8 -*-
import optparse
import logging
import sys
import sites
import ftp
import mysql
import utils



def main():
  logging.basicConfig(filename='/tmp/lamp.log', level=logging.DEBUG, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s', filemode='w')
  console = logging.StreamHandler()
  console.setLevel(logging.INFO)
  #console.setLevel(logging.DEBUG)
  console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
  logging.getLogger('').addHandler(console)

  parse_args()

'''
sites
'''
def create_site(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  if not v:
    print parser.format_help()
    sys.exit(1)

  args = {}
  args['domain'] = v[0]
  args['username'] = utils.get_account_name(args['domain'])


  args['site_id'] = sites.site_create(args)
  if args['site_id'] == -1:
    logging.info('create site failed')

  mysql_pass = mysql.create_mysqluser(args)
  if not mysql_pass:
    logging.info('create mysql info failed')

  ftp_pass = ftp.create_ftp(args)

  print '|\n|create site %s success \n|' % (args['domain'])
  print '|ftp username: %s password: %s' % (args['username'], ftp_pass)
  print '|mysql username: %s password: %s\n|' % (args['username'], mysql_pass)
  sys.exit(0)



def delete_site(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  if not v:
    print parser.format_help()
    sys.exit(1)

  args = {}
  args['domain'] = v[0]
  args['username'] = utils.get_account_name(args['domain'])
  sites.delete_site(args)
  sys.exit(0)

def edit_site(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)[0]
  sites.edit_site(v)
  sys.exit(0)

def list_site(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  mysql.get_sites(v)
  sys.exit(0)



'''
ftps
'''
def create_ftp(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  if not v:
    print parser.format_help()
    sys.exit(1)

  args = {}
  args['username'] = v[0]

  print '\nSelect FTP user belong to?\n'
  s = mysql.check_site_id()

  args['path'] = s.site_root
  args['site_id'] = s.id

  ftp_pass = ftp.create_ftp(args)
  print 'created FTP user: %s, password: %s' % (v[0], ftp_pass)
  sys.exit(0)



def delete_ftp(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  if not v:
    print parser.format_help()
    sys.exit(1)
  ftp.delete_ftp(v[0])
  sys.exit(0)


def pasv_port(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  if not v:
    print parser.format_help()
    sys.exit(1)
  ftp.change_pasv_port(v[0])
  sys.exit(0)

def list_ftp(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  mysql.get_ftps(v)
  sys.exit(0)




def create_mysql(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  if not v:
    print parser.format_help()
    sys.exit(1)

  print '\nSelect MySQL user belong to?\n'
  s = mysql.check_site_id()
  args = {}
  args['username'] = v[0]
  args['site_id']  = s.id
  mysql_pass = mysql.create_mysqluser(args)
  print 'created MySQL user: %s, password: %s' % (v[0], mysql_pass)
  sys.exit(0)

def delete_mysql(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  mysql.delete_mysql(v)
  sys.exit(0)

# change mysql user password
def chpass_mysql(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  mysql.reset_mysql_pass(v)
  sys.exit(0)

def list_mysql(option, opt_str, value, parser):
  v = get_value(option, opt_str, value, parser)
  mysql.get_mysqls(v)
  sys.exit(0)



# get parser callback values
def get_value(option, opt_str, value, parser):
    assert value is None
    value = []

    def floatable(str):
         try:
             float(str)
             return True
         except ValueError:
             return False

    for arg in parser.rargs:
         # stop on --foo like options
         if arg[:2] == "--" and len(arg) > 2:
             break
         # stop on -a, but not on -3 or -3.0
         if arg[:1] == "-" and len(arg) > 1 and not floatable(arg):
             break
         value.append(arg)

    del parser.rargs[:len(value)]
    setattr(parser.values, option.dest, value)
    # print value

    return value



def parse_args():
  parser = optparse.OptionParser(usage='%prog [options] <arg1> <arg2> [<arg3>...]',
                               version='1.0',
                               )


  site_opts = optparse.OptionGroup(
      parser, 'Site Options',
      'Site management (help keyword site)',
      )
  site_opts.add_option('--create-site', action='callback', dest='site_mode', callback=create_site,
                        help='create a site')
  site_opts.add_option('--edit-site', action='callback', dest='site_mode', callback=edit_site,
                        help='edit a site')
  site_opts.add_option('--delete-site', action='callback', dest='site_mode', callback=delete_site,
                        help='delete a site')
  site_opts.add_option('--list-site', action='callback', dest='site_mode',  callback=list_site,
                        help='list sites info')
  parser.add_option_group(site_opts)


  ftp_opts = optparse.OptionGroup(
      parser, 'FTP Options',
      'Site ftp account management (help keyword ftp)',
      )
  ftp_opts.add_option('--create-ftp', action='callback', dest='ftp_mode', callback=create_ftp,
                        help='create a ftp account')
  '''
  TODO: need add change ftp user password function
  ftp_opts.add_option('--edit-ftp', action='callback', dest='ftp_mode', callback=edit_ftp,
                        help='change passive mode port')
  '''
  ftp_opts.add_option('--pasv-port', action='callback', dest='ftp_mode', callback=pasv_port,
                        help='change passive mode port')
  ftp_opts.add_option('--delete-ftp', action='callback', dest='ftp_mode', callback=delete_ftp,
                        help='delete a ftp account')
  ftp_opts.add_option('--list-ftp', action='callback', dest='ftp_mode', callback=list_ftp,
                        help='list ftp account info')
  parser.add_option_group(ftp_opts)


  mysql_opts = optparse.OptionGroup(
      parser, 'MySQL Options',
      'MySQL user management (help keyword mysql)',
      )
  mysql_opts.add_option('--create-mysql', action='callback', dest='mysql_mode', callback=create_mysql,
                        help='create a mysql user')
  mysql_opts.add_option('--pass-mysql', action='callback', dest='mysql_mode', callback=chpass_mysql,
                        help='change mysql user password')
  mysql_opts.add_option('--delete-mysql', action='callback', dest='mysql_mode', callback=delete_mysql,
                        help='delete a mysql user')
  mysql_opts.add_option('--list-mysql', action='callback', dest='mysql_mode', callback=list_mysql,
                        help='list mysql user info')
  parser.add_option_group(mysql_opts)


  (options, args) = parser.parse_args()
  logging.debug('get options: %s', options)
  print parser.format_help()


if __name__ == '__main__':
    main()
