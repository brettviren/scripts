#!/bin/bash

# run as root to install ./btsync-rc.sh
# FIXME: put this under Ansible

mydir=$(dirname $(readlink -f $BASH_SOURCE))
cp $mydir/btsync-rc.sh /etc/init.d/btsync
cp $mydir/../btsynccfg /usr/local/bin
chmod +x /etc/init.d/btsync
update-rc.d btsync defaults

if [ ! -x /usr/local/bin/btsync ] ; then
    echo 'Warning: no /usr/local/bin/btsync, make sure you se BTSYNC_DAEMON in /etc/default/btsync'
fi
