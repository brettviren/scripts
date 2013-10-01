#!/bin/bash

export PREFIX=$HOME/opt/sawfish-git
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig
PATH=$PREFIX/bin:$PATH

cwd=$(pwd)
log=$cwd/log
rm -f $log

runit () {
    echo "in $(pwd): $@"
    $@ >> $log 2>&1
    err=$?
    if [ "$err" = "0" ] ; then
	return
    fi
    echo "cmd failed with $err in $(pwd):"
    echo "$@"
    exit $err
}

goto () {
    local dir=$1 ; shift
    pushd $dir >> $log 2>&1
}
goback () {
    popd >> $log 2>&1
}

gitit () {
    local pkg=$1 ; shift
    if [ -z "$pkg" ] ; then
	echo "No package given"
	exit 1
    fi
    local url="https://github.com/SawfishWM/${pkg}.git"
    if [ ! -d $pkg ] ; then
	runit git clone $url
    else
	goto $pkg
	runit git pull
	goback
     fi
 }

 bldit () {
     local pkg=$1 ; shift
     goto $pkg
     if [ ! -f config.status ] ; then
	 runit /bin/bash ./autogen.sh --prefix=$PREFIX 
     fi
     #if [ ! -f config.status ] ; then
     #    runit ./configure --prefix=$PREFIX 
     #fi

     runit make
     runit make install
     goback
 }

 for pkg in librep rep-gtk sawfish
 do
     gitit $pkg
     bldit $pkg
done

