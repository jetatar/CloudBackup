#!/bin/bash

# ./beegfs-ctl --setquota --help

export PASSWD=/tmp/,passwd

awk -F':' '$3 > 500 && $3 < 65500 {print $3}' OFS=';' /etc/passwd > $PASSWD

cd /etc/beegfs/sbak.d

for THE_UID in $(/bin/cat $PASSWD ); do
    
    ./beegfs-ctl --cfgFile=./beegfs-client.conf --setquota --uid --list $THE_UID --sizelimit=1T --inodelimit=0
    
done
