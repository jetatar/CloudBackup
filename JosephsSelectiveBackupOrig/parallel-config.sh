#######################################################################################
## HPC Selective Backup Configuration File
## J. Farran 7/2016
##
## You can edit the following values at any time.  The backup process re-reads this
## conf file during each user save, so the number of RSYNCS and system LOAD can be
## change at any time and if the backup.sh script detects a change when it is running,
## it will self update and report the fact.
##
## PARALLEL_MAX_RSYNCS -> How many RSYNC to run in parallel on the node.
## PARALLEL_MAX_LOAD   -> Maximum system load.  No more RSYNC's are spawned if the
##                        load is this high or higher.
##
#######################################################################################

export PARALLEL_MAX_RSYNCS=100
export PARALLEL_MAX_LOAD=50
