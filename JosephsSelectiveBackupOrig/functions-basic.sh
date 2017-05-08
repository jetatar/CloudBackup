#######################################################################################
## HPC Selective Backup Basic Subroutines ( Simple housekeeping functions )
## J. Farran 7/2016
##
#######################################################################################

#######################################################################################
function CHECK_LOCK () {

    if [ -f $LOCK ]; then
        date >> $LOCK
        /usr/bin/logger -s "**************************************************************"
        /usr/bin/logger -s "**** $BASE/backup.sh ALREADY RUNNING..."
        /usr/bin/logger -s "**** Lock File: $LOCK"
        /usr/bin/logger -s "**** Sending email"
        /usr/bin/logger -s "**************************************************************"

	THE_EMAIL=$(/bin/mktemp -p /tmp )
	
	if [ $TESTING == 1 ];then 
	    RECIPIENT="jfarran@uci.edu"
	else
	    RECIPIENT="hpc-support@uci.edu"
	fi
    
	/bin/cat<<EOF>>$THE_EMAIL
To: $RECIPIENT
From: "HPC Selective Backup Service" <hpc-support@uci.edu>
Content-type: text/plain; charset=us-ascii
Subject: Selective backup ALREADY RUNNING.

Greetings,

An instance of Selective backup was just now started but the previous one
has not yet completed.    Cannot start new backup until current one is
done.

Lock file: $LOCK

Lock file contents:
$(/bin/cat $LOCK)

Adios.

EOF
	
	/usr/sbin/sendmail -t < $THE_EMAIL
	/bin/rm -f              $THE_EMAIL
        echo "Exiting..."
        exit
    else
        echo "$$"  > $LOCK
        date      >> $LOCK
    fi
}

#######################################################################################
function BANNER () {

    printf '\n%80s\n' | tr ' ' '*'
    printf "$1\n" | /bin/sed -e :a -e 's/^.\{1,80\}$/ & /;ta'
    printf '%80s\n' | tr ' ' '*'
}


#######################################################################################
function SET_FILE_OWNERSHIP () {    # Example:  SET_FILE_OWNERSHIP jfarran file 600                                                                                                                      
    THIS_USER=$1
    THIS_FILE=$2
    THIS_MODE=$3

    if [ ! -f $THIS_FILE ];then
	/bin/touch $THIS_FILE
    fi
    /bin/chown $(/usr/bin/id -u $THIS_USER) $THIS_FILE
    /bin/chgrp $(/usr/bin/id -g $THIS_USER) $THIS_FILE
    /bin/chmod $THIS_MODE                   $THIS_FILE
}

