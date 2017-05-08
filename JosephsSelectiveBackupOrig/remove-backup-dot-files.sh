#!/bin/bash

exit   # Coment to run.

export PASSWD=/tmp/,passwd

awk -F':' '$3 > 500 && $3 < 65500 {print $1}' OFS=';' /etc/passwd > $PASSWD

for THE_USER in $(/bin/cat $PASSWD ); do
    
    TEST=/data/users/$THE_USER/.hpc-rsync-selective-backup
    if [ -f $TEST ];then
	/bin/rm  $TEST
    fi

    TEST=/data/users/$THE_USER/.hpc-rsync-selective-backup-exclude
    if [ -f $TEST ];then
	/bin/rm  $TEST
    fi

    TEST=/data/users/$THE_USER/.hpc-rsync-selective-backup-exclude-megadirs
    if [ -f $TEST ];then
	/bin/rm  $TEST
    fi



done
