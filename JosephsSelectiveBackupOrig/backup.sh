#!/bin/bash
export BACKUP_LOG_FILE=$(/bin/mktemp --suffix=-selective-backup -p /tmp)
exec > >(tee -a ${BACKUP_LOG_FILE} )
exec 2> >(tee -a ${BACKUP_LOG_FILE} >&2)

#######################################################################################
## HPC Selective Backup main backup script.
## Joseph Farran 7/2016
## 
#######################################################################################

. /root/.bashrc
. /data/hpc/selective-backup/configuration-file.sh
. /data/hpc/selective-backup/parallel-config.sh
. /data/hpc/selective-backup/functions.sh
. /data/hpc/selective-backup/functions-basic.sh

#######################################################################################
## Main code

CHECK_LOCK

export BACKUP_START_TIME=$(/bin/date)

if [ $TESTING == 1 ];then 
    BANNER "=====> RUNNING IN TESTING MODE ( DRY-RUN / NO EMAILS ) <====="
    DRY_RUN_OPTION=" --dry-run"
fi

BANNER "HPC SELECTIVE BACKUP BEGIN"
printf "\n ---> Saving to [ $STORAGE ]\n"

/bin/rm -Rf $TEMP
/bin/mkdir --mode 755 -p $TEMP
/bin/mkdir --mode 755 -p $RSYNC_LOGS
/bin/mkdir --mode 755 -p $RSYNC_TO_PROCESS
/bin/mkdir --mode 700 -p $RSYNC_CLEAN
/bin/mkdir --mode 700 -p $RSYNC_ERROR
/bin/mkdir --mode 700 -p $RSYNC_START_END
/bin/mkdir --mode 700 -p $USERS_TO_EMAIL
/bin/mkdir --mode 700 -p $USERS_WITH_MEGADIR
/bin/mkdir --mode 700 -p $DAYS_TO_KEEP_DELETED_FILES

printf "\n ---> Create LIST of users to process...\n"
if [ $TESTING == 1 ];then
    awk -F':' ' $4 == 200 {print $1}' OFS=';' /etc/passwd              > $PASSWD_USER_LIST   # Staff accounts only
else
    awk -F':' ' $3 > 500 && $3 < 65500 {print $1}' OFS=';' /etc/passwd > $PASSWD_USER_LIST
fi

printf " ---> Found [ %d ] accounts to process\n\n" $(/usr/bin/wc -l < $PASSWD_USER_LIST)

BANNER "CONFIGURING THE BACKUP PROCESS at $TEMP"

for THE_USER in $(/bin/cat $PASSWD_USER_LIST); do

    if [ ! -d /data/users/$THE_USER ];then     # Has user been removed?
        printf " User [ $RUSER ] has no home directory at /data/users/$RUSER.  Skipping.\n"
        continue
    fi

    export USER_RSYNC_FILE=/data/users/$THE_USER/$USER_RSYNC
    export USER_RSYNC_EXCLUDE_FILE=/data/users/$THE_USER/$USER_RSYNC_EXCLUDE
    export USER_RSYNC_EXCLUDE_MEGADIR_FILE=/data/users/$THE_USER/$USER_RSYNC_EXCLUDE_MEGADIR
    export USER_RSYNC_CLEAN=$RSYNC_CLEAN/$THE_USER
    export DELETED=$STORAGE/$THE_USER/DELETED-FILES/$DATE_YMD

    CREATE_USER_RSYNC_FILE $THE_USER

    # Cleanup the user's configuration file.  We work only with our cleaned version.
    # Dont allow  < > | \ : ( ) & ; # ? * 
    /bin/cat $USER_RSYNC_FILE                 | \
	/usr/bin/dos2unix                     | \
	/bin/sed -e 's/\..//'                 | \
	/bin/sed -e 's/([`$&|><?])//g'        | \
	/bin/sed -e 's/#.*//'                 | \
	/bin/sed -e "s,/\+$,,"                | \
	/bin/sed -e 's/^[ \t]*//'             | \
 	/bin/sed -e 's/ *$//'                 | \
 	/bin/sed -e '/^$/d'         > $USER_RSYNC_CLEAN        
    
    EMAIL_CHECK=$(/bin/grep "^HPC_SEND_EMAIL_SUMMARY" $USER_RSYNC_CLEAN)
    if [ ! -z "$EMAIL_CHECK" ];then
	printf "summary\n" >> $USERS_TO_EMAIL/$THE_USER
    fi
    EMAIL_CHECK=$(/bin/grep "^HPC_SEND_EMAIL_ON_ERROR" $USER_RSYNC_CLEAN)
    if [ ! -z "$EMAIL_CHECK" ];then
	printf "error\n"   >> $USERS_TO_EMAIL/$THE_USER
    fi
    
    export IFS=$'\n'
    for RDATA in $(/bin/cat $USER_RSYNC_CLEAN | /bin/grep "^/"); do
	if [ ! -z "$RDATA" ];then 
	    if [ -s $USER_RSYNC_EXCLUDE_MEGADIR_FILE ];then
		MEGADIR_EXCLUDE_FILE="--exclude-from=$USER_RSYNC_EXCLUDE_MEGADIR_FILE"
		/bin/cp $USER_RSYNC_EXCLUDE_MEGADIR_FILE  $USERS_WITH_MEGADIR/$THE_USER
	    else
		MEGADIR_EXCLUDE_FILE=""
	    fi
	    
	    echo "/usr/bin/timeout $MAX_HOURS_TO_RUN_RSYNC /usr/bin/rsync $DRY_RUN_OPTION"  \
		" $(/bin/cat $GLOBAL_RSYNC_OPTIONS)"          \
		" --exclude-from=$GLOBAL_RSYNC_EXCLUDE"       \
		" --exclude-from=$USER_RSYNC_EXCLUDE_FILE"    \
		" $MEGADIR_EXCLUDE_FILE"                      \
		" --backup --backup-dir=$DELETED"             \
		" '$RDATA'  '$STORAGE/$THE_USER'"   >> $RSYNC_TO_PROCESS/$THE_USER
	fi
    done

    SET_FILE_OWNERSHIP "$THE_USER" "$RSYNC_TO_PROCESS/$THE_USER" "700"
done

BANNER "Parallel RSYNC's Start"

printf "\n ---> Starting Parallel RSYNCs with:\n"
printf "      [%d] Parallel RSYNC's\n      [%d] Max System Load\n\n" $PARALLEL_MAX_RSYNCS $PARALLEL_MAX_LOAD

export -f RSYNC_FUNCTION
export -f CLEAN_DELETED_FILES
cd $RSYNC_TO_PROCESS
/bin/ls | /usr/bin/shuf | \
    /usr/bin/parallel --max-procs $PARALLEL_MAX_RSYNCS --load $PARALLEL_MAX_LOAD  \
    "CLEAN_DELETED_FILES {}; RSYNC_FUNCTION {};"

BANNER "Parallel RSYNC's Done"

/bin/find $STORAGE -maxdepth 1 -mindepth 1 -type d -exec /bin/chmod 700 {} \;
/bin/find $TEMP -type f -exec /bin/chmod 600 {} \;

BANNER "Total RSYNC's Found in Error"

printf "\nThere were a total of [ %d ] users who had RSYNC errors.\n\n" $( /bin/ls $RSYNC_ERROR | /usr/bin/wc -l )
/bin/ls $RSYNC_ERROR
printf "\n\n"

BANNER  "User's Email Notification"

cd $USERS_TO_EMAIL
for THE_USER in $(/bin/ls); do
    EMAIL_USER_FUNCTION $THE_USER
done

BANNER  "Processing data files (.data)"

/usr/bin/wc -l $RSYNC_LOGS/* | sort -n | /usr/bin/tac   > $USERS_RSYNC_COUNT
/bin/ls -lt $RSYNC_START_END | /bin/grep -v "^total "   > $USERS_RSYNC_START_END_LIST

BANNER "HPC SELECTIVE BACKUP DONE"

export BACKUP_END_TIME=$(/bin/date)

printf "\n ---> Start Time [ $BACKUP_START_TIME ]\n"
printf " --->   End Time [ $BACKUP_END_TIME ]\n"

if [ $TESTING == 1 ];then
    printf "\n =====> TESTING MODE DONE ( DRY-RUN DONE ) <=====\n"
    /bin/mv $BACKUP_LOG_FILE  $TEMP/backup.log
    printf "\nRun log file is [ $TEMP/backup.log ]\n\n"
else
    if [ -d $RUN_LOGS/$DATE_YMD ];then
	export DATE_YMD=$(/bin/date +"%Y-%m%d-%H%M")  # Already ran for today, add time
	printf " Backup re-ran on same day.  Saving logs to day+time [ $DATE_YMD ]\n"
    fi
    
    printf "\n ---> Saving the logs for this RUN to:\n    [ $RUN_LOGS/$DATE_YMD ]\n\n"
    
    /usr/bin/rsync -rva "$TEMP/"  $RUN_LOGS/$DATE_YMD  >& /dev/null
    /bin/chmod 700    $RUN_LOGS/$DATE_YMD
    /bin/mv $BACKUP_LOG_FILE  $RUN_LOGS/$DATE_YMD/backup.log
fi

EMAIL_SUPPORT_FUNCTION

/bin/rm -f $LOCK
exit
