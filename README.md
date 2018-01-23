# AraoSecret

Free web password manager


## Installation

* Create user for our service

        su  # as root
        adduser --no-create-home --disabled-password --disabled-login arao
        
* Create PostgreSQL database

        # I suggest previously create a secure password with
        # pwgen 10 1 --secure
        su postgres
        createuser --no-createdb --pwprompt --no-createrole --no-superuser\
                   arao
        createdb --owner=arao arao_secret

* Create and edit main configuration

        su  # As root
        mkdir /etc/arao_secret
        cp ./conf/main.conf /etc/arao_secret
        chmod 600 /etc/arao_secret/main.conf
        chown arao /etc/arao_secret/main.conf
        # Edit the file
        nano /etc/arao_secret/main.conf
