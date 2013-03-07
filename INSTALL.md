Installation Notes for a Dokuwiki Farm
======================================

Webserver
---------

I prefer nginx on Debian (testing). 

    apt-get install nginx php5-fpm php5-gd

I don't want to keep IP logs, so I put the farm behind a reverse proxy and drop the outer logs. Inner logs are kept for debugging purposes.

#### /etc/nginx/conf.d/anon-bouncer.conf
    
    worker_processes auto;
    server {
	listen 80;
	listen [::]:80 ipv6only=on;
	listen 443 ssl;
	server_name _;
	access_log /dev/null;
	error_log /dev/null;
	location / {
		proxy_pass http://unix:/var/run/nginx.sock:/;
		proxy_cache_key "$host$request_uri$cookie_user";
		proxy_set_header Host $http_host;
                proxy_hide_header X-Powered-By;
 	}
	ssl_certificate /etc/nginx/ssl/cert.crt;
	ssl_certificate_key /etc/nginx/ssl/cert.key;
	ssl_prefer_server_ciphers on;
        keepalive_timeout    70;
	ssl_session_timeout 10m;
	ssl_session_cache   shared:SSL:10m;
        add_header Strict-Transport-Security "max-age=31556926;includeSubDomains";
        add_header X-Frame-Options deny;
        add_header X-Content-Security-Policy "allow 'self'; script-src 'self'; img-src *; media-src *; object-src 'none'; frame-src 'none'; xhr-src 'none';";
    }

#### /etc/nginx/sites-available/dokuwiki-farm

    server {
        listen 127.0.0.1:80 default_server;
        server_name _;
        root /var/www/dokuwiki/;
        index index.php doku.php;

        location / {
                index doku.php;
                try_files $uri $uri/ @dokuwiki;
        }

        location @dokuwiki {
                rewrite ^/_media/(.*) /lib/exe/fetch.php?media=$1 last;
                rewrite ^/_detail/(.*) /lib/exe/detail.php?media=$1 last;
                rewrite ^/_export/([^/]+)/(.*) /doku.php?do=export_$1&id=$2 last;
                rewrite ^/(.*) /doku.php?id=$1 last;
        }

        location ~ \.php$ {
                try_files $uri =404;
                fastcgi_split_path_info ^(.+\.php)(/.+)$;
                fastcgi_pass unix:/var/run/php5-fpm.sock;
                fastcgi_index index.php;
                include fastcgi_params;
        }

        location ~ /(data|conf|bin|inc)/ {
                deny all;
        }

        location ~ /lib/ {
                expires 30d;
        }

        location ~ /\.ht {
                deny all;
        }
    }

Dokuwiki
--------

I prefer the stable git branch of Dokuwiki. Don't forget to `git pull`regularly. Before you do, check the Dokuwiki Changelog!

    apt-get install git
    mkdir /var/www
    cd /var/www
    git clone git://github.com/splitbrain/dokuwiki.git
    cd dokuwiki
    git checkout -b stable origin/stable


### Farm setup

Read https://www.dokuwiki.org/farms

    mkdir /var/www/farm
    cp /var/dokuwiki/inc/preload.php.dist /var/dokuwiki/inc/preload.php

#### Edit preload.php

    if(!defined('DOKU_FARMDIR')) define('DOKU_FARMDIR', '/var/www/farm');
    include(fullpath(dirname(__FILE__)).'/farm.php');

#### Create prototype animal

    cd /var/www/farm
    wget https://www.dokuwiki.org/_media/dokuwiki_farm_animal.zip
    unzip dokuwiki_farm_animal.zip

    mv _animal prototype.example.com
    chown www-data:www-data -R prototype.example.com 

If you have a wildcard DNS entry for your domain, you should now be able to access `prototype.example.com`. Default login is `admin`, password `admin`. Reconfigure it to your liking. This will become your prototype for other animals.

Since we don't want the prototype to stay public, we rename it back to `_animal`.

    mv prototype.example.com _animal
 
To create a new animal by hand, you simply have to copy the directory:

    cp -a _animal shiny.example.com

`createwiki` expects the prototype to have this name.

Useful plugins & templates
--------------------------

    cd /var/www/dokuwiki/lib/plugins
    git clone https://github.com/splitbrain/dokuwiki-plugin-captcha.git captcha
    git clone https://github.com/marklundeberg/dokuwiki-plugin-backup.git backup
    git clone https://github.com/lupo49/plugin-cspheader.git cspheader

    cd /var/www/dokuwiki/lib/tpl
    git clone https://github.com/syn-systems/dokuwiki-template-monobook.git monobook
    git clone https://github.com/samfisch/dokuwiki-template-arctic.git arctic
    git clone https://github.com/moba/dokuwiki-minimal.git headstrong-minimal

Public farming
--------------

For public farms, you want to restrict some configuration settings and disable the plugin manager. Otherwise farmers will be able to run arbitrary PHP code!
 
    rm -r /var/www/dokuwiki/lib/plugins/plugin/

#### /var/www/farm/prototype.example.com/conf/local.protected.php

    $conf['savedir'] = DOKU_CONF.'../data';
    $conf['updatecheck'] = 0;
    $conf['htmlok'] = 0;
    $conf['phpok'] = 0;
    $conf['basedir'] = '';
    $conf['baseurl'] = '';
    $conf['dmode'] = 0755;
    $conf['fmode'] = 0644;
    $conf['allowdebug'] = 0;
    $conf['fullpath'] = 0;
    $conf['authtype'] = 'authplain';
    $conf['securecookie'] = 1;
    $conf['relnofollow'] = 1;
    $conf['indexdelay'] = '60*60*24*5';
    $conf['iexssprotect'] = 1;
    $conf['im_convert'] = '';
    $conf['fetchsize'] = 0;
    $conf['compress'] = 1;
    $conf['cssdatauri'] = 0;
    $conf['broken_iua'] = 0;
    $conf['xsendfile'] = 0;
    $conf['dnslookups'] = 0;
    $conf['proxy']['host'] = '';
    $conf['proxy']['port'] = '';
    $conf['safemodehack'] = 0;
    $conf['mailfrom'] = 'no-reply@example.com';

### Harden PHP

I limit public animals to 1 MB file uploads.

#### /etc/php5/conf.d/hosts.ini

    [PATH=/var/www/]
    open_basedir = /var/www/
    upload_tmp_dir=/var/www/tmp
    session.save_path=/var/www/tmp
    allow_url_fopen = Off
    upload_max_filesize = 1M
    disable_functions = exec,passthru,shell_exec,system,proc_open,popen,curl_exec,curl_multi_exec,show_source,chroot,chdir,fsockopen,pfsockopen,socket_create,socket_create_listen,phpinfo

Createwiki Web Interface
------------------------

### Set up UWSGI for Python in Nginx

    apt-get install python uwsgi uwsgi-plugin-python

    git clone https://github.com/moba/createdokuwiki.git /var/www/createwiki/
    
    chown -R www-data:www-data /var/www/createwiki/
    cd /var/www/createwiki/
    virtualenv ./env
    source env/bin/activate
    pip install flask flask-mail
    deactivate
    
#### /etc/nginx/sites-available/createwiki

    server {
            listen 127.0.0.1:80;
            server_name createwiki.example.com;
            root /var/www/createwiki/static;
    
            location / {
                    try_files $uri @regwiki;
            }
    
            location @regwiki {
                    include uwsgi_params;
                    uwsgi_param UWSGI_CHDIR /var/www/createwiki/;
                    uwsgi_param UWSGI_PYHOME /var/www/createwiki/env;
                    uwsgi_param UWSGI_MODULE createwiki;
                    uwsgi_param UWSGI_CALLABLE app;
                    uwsgi_pass unix:/tmp/uwsgi-createwiki.sock;
            }
    
    }

Make active:

    ln -s /etc/nginx/sites-available/createwiki /etc/nginx/sites-enabled
    
#### /etc/uwsgi/apps-available/createwiki.ini 

    [uwsgi]
    plugins = python
    gid = www-data
    uid = www-data
    vhost = true
    logdate
    socket = /tmp/uwsgi-createwiki.sock
    master = true
    processes = 1
    harakiri = 20
    limit-as = 128
    memory-report
    no-orphans
    catch-exceptions

Enjoy!
======
