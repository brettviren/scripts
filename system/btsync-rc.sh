#!/bin/sh
### BEGIN INIT INFO
# Provides: btsync
# Required-Start: $local_fs $remote_fs
# Required-Stop: $local_fs $remote_fs
# Should-Start: $network
# Should-Stop: $network
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Multi-user daemonized version of btsync.
# Description: Starts the btsync daemon for all registered users.
### END INIT INFO

# /etc/init.d rc script for multi-user btsync based on
# https://gist.github.com/willolbrys/5473587
# http://seenthis.net/messages/146315
# 
# To install:
# # cp /path/to/btsync-rc.sh /etc/init.d/btsync
# # chmod +x /etc/init.d/btsync
# # update-rc.d btsync defaults

BTSYNC_DAEMON="/usr/local/bin/btsync"
BTSYNC_USERS=""
BTSYNC_CONFIG='.sync/config.json'
test -f /etc/default/btsync && . /etc/default/btsync

DAEMON="$BTSYNC_DAEMON"
test -x $DAEMON || exit 0


start() {
    for btsuser in $BTSYNC_USERS; do
	HOMEDIR=`getent passwd $btsuser | cut -d: -f6`
	config="$HOMEDIR/$BTSYNC_CONFIG"
	if [ -f $config ]; then
	    echo "Starting BTSync for $btsuser"
	    start-stop-daemon -o -c $btsuser -S -u $btsuser -x $DAEMON -- --config $config
	else
	    echo "Couldn't start BTSync for $btsuser (no $config found)"
	fi
    done
}

stop() {
    for btsuser in $BTSYNC_USERS; do
	dbpid=`pgrep -u $btsuser btsync`
	if [ ! -z "$dbpid" ]; then
	    echo "Stopping btsync for $btsuser"
	    start-stop-daemon -o -c $btsuser -K -u $btsuser -x $DAEMON
	fi
    done
}

status() {
    for btsuser in $BTSYNC_USERS; do
	dbpid=`pgrep -u $btsuser btsync`
	if [ -z "$dbpid" ]; then
	    echo "btsync for USER $btsuser: not running."
	else
	    echo "btsync for USER $btsuser: running (pid $dbpid)"
	fi
    done
}

case "$1" in
    start)
	start
	;;
    stop)
	stop
	;;
    restart|reload|force-reload)
	stop
	start
	;;
    status)
	status
	;;
    *)
	echo "Usage: /etc/init.d/btsync {start|stop|reload|force-reload|restart|status}"
	exit 1
esac

exit 0
