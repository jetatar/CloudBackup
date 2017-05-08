######################################################################################
## HPC Selective Backup Subroutines
## J. Farran 6/2016
##
#######################################################################################
. /data/hpc/selective-backup/configuration-file.sh

#######################################################################################
#######################################################################################
function CREATE_USER_RSYNC_FILE () {
    
    RUSER=$1
    
    if [ ! -d /data/users/$RUSER ];then
	printf " User [ $RUSER ] has no home directory at /data/users/$RUSER.  Skipping.\n"
	return
    fi

    if [ ! -e $USER_RSYNC_EXCLUDE_FILE ]; then
	printf " --> Creating [ $USER_RSYNC_EXCLUDE_FILE ]\n"
	SET_FILE_OWNERSHIP "$RUSER" "$USER_RSYNC_EXCLUDE_FILE" "600"
    fi

    if [ -s $USER_RSYNC_FILE ]; then   # User already has a dot hpc file. No need to create new one.
	return
    fi

    printf " --> Creating [ $USER_RSYNC_FILE ]\n"
    cat >>$USER_RSYNC_FILE<<EOF
#######################################################################################
#######################################################################################
##                       HPC Selective Backup Configuration File                     ##
##                             For details, please visit:                            ##
##                      https://hpc.oit.uci.edu/selective-backup                     ##
#######################################################################################
#######################################################################################
#
# UN-comment any 'HPC_' line below to select that option.
# HPC_SEND_EMAIL_SUMMARY   # Send me daily rsync backup email summaries.
# HPC_SEND_EMAIL_ON_ERROR  # Send me email ONLY if rsync backup encounters error(s).
# HPC_KEEP_DELETED=14      # Keep up to X days deleted files on backup server.
#
# Your rsync EXCLUDE file is located at: 
#      $USER_RSYNC_EXCLUDE_FILE
#
# Specify directories or files to backup, one per line.  All paths must begin
# with root forward slash "/".   The order is important as the saves are
# processed in the sequence you specify below one at a time.
# 
/data/users/$RUSER
/pub/$RUSER
EOF
    
    for FILE_SYSTEM in {"/dfs1","/dfs2"}; do
	for DIR in $(/usr/bin/find $FILE_SYSTEM -maxdepth 1 -mindepth 1 -type d); do
	    if [ -d $DIR/$RUSER ]; then 
		echo "$DIR/$RUSER" >> $USER_RSYNC_FILE
	    fi
	done
    done
    
    SET_FILE_OWNERSHIP "$RUSER" "$USER_RSYNC_FILE" "600"
}

#######################################################################################
function CLEAN_DELETED_FILES () {                                                      
                                                                                       
    RUSER=$1            

    printf "\nPruning [ $RUSER ]\n"

    DAYS_TO_KEEP=$DEFAULT_DAYS_TO_KEEP_DELETED_FILES
    DAYS_TO_KEEP_CHECK=$(/bin/grep "^HPC_KEEP_DELETED" $RSYNC_CLEAN/$RUSER | /bin/awk -F= '{print $2}')
                                                                                                       
    if [ ! -z "$DAYS_TO_KEEP_CHECK" ];then                                                             
        if [ "$DAYS_TO_KEEP_CHECK" -gt "$MAX_DAYS_TO_KEEP_DELETED_FILES" ]; then                                                    
            printf " Days to keep cannot be greater than $MAX_DAYS_TO_KEEP_DELETED_FILES.\n"
        elif [ "$DAYS_TO_KEEP_CHECK" -lt "-1" ]; then                                                   
            printf " Days to keep cannot be less than negative 1.\n"
        else
            export DAYS_TO_KEEP=$DAYS_TO_KEEP_CHECK
        fi
    fi
    echo $DAYS_TO_KEEP > $DAYS_TO_KEEP_DELETED_FILES/$RUSER

    if [ ! -d $STORAGE/$RUSER/DELETED-FILES ];then
        printf "Nothing to Prune at [ $STORAGE/$RUSER/DELETED-FILES ].\n"
	return
    fi
    
    if [ $TESTING == 1 ];then
	printf "[TESTING - Fake Prunning] over [ $DAYS_TO_KEEP ] days old.\n"

	/bin/find $STORAGE/$RUSER/DELETED-FILES   \
            -maxdepth 1                           \
            -mindepth 0                           \
            -type d                               \
            -mtime +$DAYS_TO_KEEP                 \
	    -exec /bin/ls -ld "{}" \;
    else
	printf "Prunning [ $STORAGE/$RUSER/DELETED-FILES ] over [ $DAYS_TO_KEEP ] days old.\n"
	
	/bin/find $STORAGE/$RUSER/DELETED-FILES   \
            -maxdepth 1                           \
            -mindepth 0                           \
            -type d                               \
            -mtime +$DAYS_TO_KEEP                 \
	    -exec /bin/ls -ld "{}" \; -exec /bin/rm -Rf "{}" \;
    fi
    printf "Pruning done [ $RUSER ].\n"
}

#######################################################################################
function RSYNC_FUNCTION () {

    RUSER=$1

    printf "Rsycing [ $RUSER ].\n"
    
    . /data/hpc/selective-backup/functions-basic.sh

    USER_LOG=$RSYNC_LOGS/$RUSER
    USER_ERROR=$RSYNC_ERROR/$RUSER

    /bin/touch $USER_LOG

    printf "Your RSYNC backup START and END times for this session was:\n     $(/bin/date +'%c')\n" > $RSYNC_START_END/$RUSER
    
    export IFS=$'\n'
    for RDATA in $(/bin/cat $RUSER); do
	printf '\n%80s\n' | tr ' ' '*'                                      >> $USER_LOG
	/bin/echo "$RDATA" | /bin/awk -F\' '{print $(NF-3)}' | tr '\n' ' '  >> $USER_LOG
	printf '\n%80s\n' | tr ' ' '*'                                      >> $USER_LOG

	status=0
        /usr/bin/sudo -Eu $RUSER /bin/bash -v -c $RDATA  >> $USER_LOG 2>&1
	status=$?

	if [ $status -ne 0 ]; then
	    PATH_IN_ERROR=$(/bin/echo "$RDATA" | /bin/awk -F\' '{print $(NF-3)}') 
	    printf '%80s\n' | tr ' ' '='                                                    >> $USER_ERROR
	    if [ $status -eq 12 ];then  # Disk QUOTA Error
		printf 'RSYNC error [%d] ( DISK QUOTA LIMIT REACHED ) while processing: %s\n' "$status" "$PATH_IN_ERROR" >> $USER_ERROR
	    elif [ $status -eq 124 ];then  # Rsync Ran out of time
		printf 'RSYNC error [%d] ( RSYNC RAN OUT OF TIME ) while processing: %s\n' "$status" "$PATH_IN_ERROR" >> $USER_ERROR
	    else
		printf 'RSYNC error [%d] while processing: %s\n' "$status" "$PATH_IN_ERROR"  >> $USER_ERROR
	    fi
	    printf '%80s\n' | tr ' ' '='                                                    >> $USER_ERROR
	    SET_FILE_OWNERSHIP "$RUSER" "$USER_ERROR" "600"
	fi
    done
    printf "     $(/bin/date +'%c')\n\n" >> $RSYNC_START_END/$RUSER

    if [ -f $USER_ERROR ];then     # Include the errors found at the start of the log file.
	/bin/mv -f $USER_LOG  $USER_LOG.hold
	printf "\n***************************************************************\n" >> $USER_LOG
	printf "*** Errors found during your selective backup rsync process ***\n"   >> $USER_LOG
	printf "***************************************************************\n\n" >> $USER_LOG

	printf "RSYNC Path(s) in error:\n"    >> $USER_LOG
	/bin/cat $USER_ERROR                  >> $USER_LOG
	printf "\n\nComplete RSYNC LOG:\n"    >> $USER_LOG
	/bin/cat $USER_LOG.hold               >> $USER_LOG
	/bin/rm -f $USER_LOG.hold
    fi
    SET_FILE_OWNERSHIP "$RUSER" "$USER_LOG" "600"

    printf " --->  Done with: [ $RUSER ]\n";
}

#######################################################################################
function EMAIL_USER_FUNCTION () {

    THIS_USER=$1
    
    if [ $TESTING == 1 ];then
	printf "Testing mode set.  NOT sending email to [ $THIS_USER ].\n"
	return; 
    fi

    ACTION_CHECK=$(/bin/grep "error" $USERS_TO_EMAIL/$THIS_USER )

    if [ -n "$ACTION_CHECK" ];then 
	EMAIL_ONLY_ON_ERROR=true;
    else
	EMAIL_ONLY_ON_ERROR=""
    fi

    if [ -f $RSYNC_ERROR/$THIS_USER ]; then    # User has RSYNC errors
	ERRORS=$(/bin/grep "^RSYNC error \[" $RSYNC_ERROR/$THIS_USER | /usr/bin/wc -l )
    	SUBJECT="HPC Selective Backup Summary:  [ $ERRORS ] Error(s) found."
    else
	SUBJECT="HPC Selective Backup Summary."
    fi

    if [ -n "$EMAIL_ONLY_ON_ERROR" ] && [ ! -f $RSYNC_ERROR/$THIS_USER ]; then
	printf "User [ $THIS_USER ] requesting email on error but no errors found.  Skipping.\n"
	return
    fi

    printf " ---> Emailing [ $THIS_USER ]\n"
    
    THE_EMAIL=$(/bin/mktemp -p /tmp )

    if [ -f $DAYS_TO_KEEP_DELETED_FILES/$THIS_USER ]; then
	KEEP_DELETED=$(/bin/cat $DAYS_TO_KEEP_DELETED_FILES/$THIS_USER)
    else
	KEEP_DELETED=$DEFAULT_DAYS_TO_KEEP_DELETED_FILES
    fi
    
    /bin/cat<<EOF>>$THE_EMAIL
To: $THIS_USER@hpc-s.oit.uci.edu
From: "HPC Selective Backup Service" <hpc-support@uci.edu>
Content-type: text/plain; charset=us-ascii
Subject: $SUBJECT

Greetings,

The following HPC selective backup summary is being sent at your request.

If you wish to stop these emails, update your ~/$USER_RSYNC
file accordingly.  For full details please visit:

     https://hpc.oit.uci.edu/selective-backup

Your complete RSYNC log for this backup run is available from the HPC
interactive node at:

     less $RSYNC_LOGS/$THIS_USER

You requested to keep DELETED files for a period of [ $KEEP_DELETED ] days.
Deleted files are kept by day at: $STORAGE/$THIS_USER/DELETED-FILES

Your data was backed-up to the following directory which you can access from
the HPC interactive node:

     $STORAGE/$THIS_USER

EOF

    /bin/cat $RSYNC_START_END/$THIS_USER                 >> $THE_EMAIL

    if [ -s $RSYNC_CLEAN/$THE_USER ];then
	printf "\nDirectories / Files Processed:\n"      >> $THE_EMAIL
	printf "==============================\n"        >> $THE_EMAIL
	/bin/cat $RSYNC_CLEAN/$THE_USER | /bin/grep "^/" >> $THE_EMAIL
    fi
    if [ -s $RSYNC_ERROR/$THIS_USER ];then
	printf "\n\nErrors Encountered:\n"               >> $THE_EMAIL
	/bin/cat $RSYNC_ERROR/$THIS_USER                 >> $THE_EMAIL
    fi
    /usr/sbin/sendmail -t < $THE_EMAIL
    /bin/rm -f              $THE_EMAIL
}

#######################################################################################
function EMAIL_SUPPORT_FUNCTION () {
    
    if [ $TESTING == 1 ];then 
	NOTE="******** THIS IS A DRY-RUN AND NOT A REAL BACKUP SAVE ( NO SAVES ) *********"
	NOTE2="(TEST ONLY - DRY RUN)"
#	RECIPIENT="hpc-support@uci.edu"
	RECIPIENT="jfarran@uci.edu"
    else
	NOTE=""
	NOTE2=""
	RECIPIENT="hpc-support@uci.edu"
    fi
    
    THE_EMAIL=$(/bin/mktemp -p /tmp )

    MEGA_DIR_COUNT=$(/bin/ls $USERS_WITH_MEGADIR | /usr/bin/wc -l )
    EMAIL_NOTIFICATION_COUNT=$(/bin/ls $USERS_TO_EMAIL | /usr/bin/wc -l )
    USERS_WITH_RSYNC_ERROR=$(/bin/ls $RSYNC_ERROR | /usr/bin/wc -l )
    
    /bin/cat<<EOF>>$THE_EMAIL
To: $RECIPIENT
From: "HPC Selective Backup Service" <hpc-support@uci.edu>
Subject: HPC Selective Backup Stats $NOTE2
Content-type: text/plain; charset=us-ascii
$NOTE

HPC Selective Backup statistics for run date [ $DATE_YMD ]

Note: Following stats assumes saves started at midnight and completed
      before the end of the day (24 hours).

$(/bin/cat $PASSWD_USER_LIST | /usr/bin/wc -l ) = Accounts processed
    [ $RUN_LOGS/$DATE_YMD/passwd-user-list.data ]

$(/bin/cat $RSYNC_CLEAN/* | /usr/bin/wc -l ) = Total Directories / Files to be saved to backup server.
    [ $RUN_LOGS/$DATE_YMD/rsync-clean ]

$USERS_WITH_RSYNC_ERROR = Users with RSYNC's in ERROR
    [ $RUN_LOGS/$DATE_YMD/rsync-errors ]

$EMAIL_NOTIFICATION_COUNT = Users requesting email notifications.
    [ $RUN_LOGS/$DATE_YMD/users-to-email ]

$MEGA_DIR_COUNT = Users with MegaDIR ( created from Robinhood scans ).
    [ $RUN_LOGS/$DATE_YMD/users-with-megadir ]


Total RSYNC lines processed including Top 10 users:
---------------------------------------------------
$(/bin/cat $USERS_RSYNC_COUNT | /usr/bin/head -11 )


Backup Start Time [ $BACKUP_START_TIME ]
  Backup End Time [ $BACKUP_END_TIME ]

Top 10 users taking the longest (hh:mm) to complete RSYNC:
----------------------------------------------------------
$(/bin/cat $USERS_RSYNC_START_END_LIST | /usr/bin/head -10 )

Backup Location:  [ $STORAGE ]
Accessible from HPC services node (nas-7-1) and HPC interactive compute node (compute-1-13)

Complete backup log for this run [ $RUN_LOGS/$DATE_YMD/backup.log ]

DF Disk status of $STORAGE:

$(/bin/df -hT $STORAGE ) 

EOF
    /usr/sbin/sendmail -t < $THE_EMAIL
    /bin/rm -f              $THE_EMAIL
}
