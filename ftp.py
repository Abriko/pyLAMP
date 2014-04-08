#!/usr/bin/python
# -*- coding: utf-8 -*-

#import argparse
import logging
import mysql
import utils



def create_ftp(args):
  config = utils.load_config()
  # using user name as ftp path or custom ftp path
  if not args.get('path') or args.get('path') == 'username':
    args['path'] = '%s/%s' % (config['ftproot'], args['username'])
  else:
    if not utils.chekc_path(args['path']):
      logging.info('exiting...')
      return

  # add ftp user mysql record
  ftp_pass = mysql.create_mysql_ftpuser(args)
  if ftp_pass == None:
    logging.info('create ftp account failed. exiting...')
    return

  utils.change_conf('<APPROOT>/files/vsftpd_user_template', [{'old':'<path>','new':args['path']}], '/etc/lamp/ftp_users/%s' % (args['username']))

  utils.exec_cmd('mkdir -p %s' % (args['path']))
  utils.exec_cmd('chown %s -R %s' % (config['root_own'], args['path']))

  utils.exec_cmd('service vsftpd reload')
  return ftp_pass

#change ftp server pasv port, args: 'main_port,max_port' e.g '50000,50004'
def change_pasv_port(ports):
  config = utils.load_config()
  ports = ports.strip()
  ports = ports.split(',')
  min_port = 0
  max_port = 0
  try:
    min_port = ports[0]
    max_port = ports[1]
  except:
    logging.info('input format error, exiting...')
    return

  #print min_port
  #print max_port
  utils.change_conf(config['vsftpd_conf_path'],
      [
        {'flags':'re.M','old':r"^pasv_min_port.*?$",'new':'pasv_min_port=%s' % (min_port)},
        {'flags':'re.M','old':r"^pasv_max_port.*?$",'new':'pasv_max_port=%s' % (max_port)}
      ]
  )


# delete ftp user mysql record
def delete_ftp(name):
  r = mysql.delete_mysql_ftpuser(name)
  if r:
    filename = '/etc/lamp/ftp_users/%s' % r.username

    utils.exec_cmd('rm -rf %s' % filename)
    utils.exec_cmd('service vsftpd reload')

# delete site all ftp user
def delete_ftp_bysite(site_id):
  logging.debug('delete ftps by site_id: %s', site_id)
  ftps = mysql.get_ftps_bysite(site_id)

  for f in ftps:
    delete_ftp(str(f.id))

