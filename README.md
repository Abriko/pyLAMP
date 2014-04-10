pyLAMP
===========


pyLAMP is a simple Apache MySQL PHP runtime environment.

You can using pyLAMP easy installation and configuration a complex server runtime environment.

[中文说明](http://lab.hupo.me/lamp-doc/)
[其他说明]（http://blog.hupo.me/2014/pylamp-linux-apache-mysql-php-%E4%B8%80%E9%94%AE%E7%8E%AF%E5%A2%83%E5%8F%91%E5%B8%83/）

Installation
------------
First, make sure you using Ubuntu12.04 or Centos6(SELinux disabled) and have Python 2.6 or 2.7.

    # python pyLAMP/install.py

About 10 minutes can finish install. By default we create a new site and a FTP account.
Just upload you web site to **/var/www/public_html**, Now all done you can visit it.

Usage
-----------

    # python pyLAMP/lamp.py
    Usage: lamp.py [options] <arg1> <arg2> [<arg3>...]
    
    Options:
      --version         show program's version number and exit
      -h, --help        show this help message and exit
    
      Site Options:
        Site management (help keyword site)
    
        --create-site   create a site
        --edit-site     edit a site
        --delete-site   delete a site
        --list-site     list sites info
    
      FTP Options:
        Site ftp account management (help keyword ftp)
    
        --create-ftp    create a ftp account
        --edit-ftp      change passive mode port
        --delete-ftp    delete a ftp account
        --list-ftp      list ftp account info
    
      MySQL Options:
        MySQL user management (help keyword mysql)
    
        --create-mysql  create a mysql user
        --edit-mysql    change mysql user password
        --delete-mysql  delete a mysql user
        --list-mysql    list mysql user info

License
-------
Apache v2
