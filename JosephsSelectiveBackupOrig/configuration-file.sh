#######################################################################################
## HPC Selective Backup Configuration File
## J. Farran 7/2016
##
## Various configuration parameters for the main backup.sh script.
##
#######################################################################################

export TESTING=0       # 0=No testing, 1=Testing

export DEFAULT_DAYS_TO_KEEP_DELETED_FILES=60
export MAX_DAYS_TO_KEEP_DELETED_FILES=90
export MAX_HOURS_TO_RUN_RSYNC="18h"

export BASE=/data/hpc/selective-backup

export GLOBAL_RSYNC_OPTIONS=$BASE/global-rsync-options.data
export GLOBAL_RSYNC_EXCLUDE=$BASE/global-rsync-exclude.data

export DATE_YMD=$(/bin/date +"%Y-%m%d")

export STORAGE_ROOT=/sbak/selective-backup
export STORAGE=$STORAGE_ROOT/hpc-backups
export RSYNC_LOGS=$STORAGE_ROOT/hpc-logs/$DATE_YMD
export USER_RSYNC=.hpc-selective-backup
export USER_RSYNC_EXCLUDE=.hpc-selective-backup-exclude
export USER_RSYNC_EXCLUDE_MEGADIR=.hpc-selective-backup-exclude-megadirs

export DRY_RUN_OPTION=""
export RUN_LOGS=$BASE/run-logs
export TEMP=$BASE/processing-tmp
export PASSWD_USER_LIST=$TEMP/passwd-user-list.data
export USERS_RSYNC_COUNT=$TEMP/users-rsync-count.data
export USERS_RSYNC_START_END_LIST=$TEMP/users-rsync-start-end.data
export RSYNC_CLEAN=$TEMP/rsync-clean
export RSYNC_TO_PROCESS=$TEMP/rsync-to-process
export RSYNC_ERROR=$TEMP/rsync-errors
export RSYNC_START_END=$TEMP/rsync-start-end-times
export USERS_WITH_MEGADIR=$TEMP/users-with-megadir
export USERS_TO_EMAIL=$TEMP/users-to-email
export DAYS_TO_KEEP_DELETED_FILES=$TEMP/days-to-keep-deleted-files

export LOCK=/var/lock/hpc-selective-backup.lock

