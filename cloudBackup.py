#!/bin/env python

import sys
import os.path
import subprocess
import psutil

# Local configs
basedir     = "/data/users/jtatar"  # NOTE: no '/' at the end of the path
rconfdir    = basedir + "/.config/rclone/rclone.conf"
confname    = "gDrive"
sourcefl    = basedir + "/.hpc-cloud-backup"
excludefl   = basedir + "/.hpc-cloud-backup-exclude"


# Remote configs
remotebasedir = "UCI_HPC_Backup"

#
#   Don't want to start another CloudBackup/RClone process if there are any 
#   already running.
#
def findRCloneInstances( ):
    
    for pid in psutil.pids():

        p   = psutil.Process( pid ) 
        cmd = p.cmdline( )

        # TODO: This should be a while loop in order to print all already running 
        # instances.
        if 'python' in cmd and 'cBackup.py' in cmd:
            print "!!! Found an already running instance of Cloud Backup with PID"\
                    " {0}.".format( pid )
            
            sys.exit( )


#
#   Find RClone user configuration file.  The user should have gone through
#   initial RClone configuration specifying a unique name for the Google Drive
#   HPC configuration.
#   
#   TODO: Check that the script is being executed on the right compute node/queue.
#
def findRCloneConfig( ):

    if os.path.isfile(rconfdir):
        print "-> Configuration file %s found." % rconfdir 

        if confname in open(rconfdir).read():
            print "-> Found %s configuration for UCI HPC Cloud backup." % confname

        else:
            print "!!! RClone configuration name %s for UCI HPC Cloud backup " \
                                    "not found in %s" % (confname, rconfdir)
            sys.exit( )

    else:
        print "!!! RClone configuration file not found. :("

        sys.exit( )

#
#   Test to make sure tocken and config are valid by checking to see if UCIHPCBackup
#   directory exists in the user's remote drive.
#
def testRCloneConfig( ):

    cmd             = ( ['rclone', 'lsd', str(confname)+":"] )
                                            #shell = True security hazard?
    result          = subprocess.Popen( cmd,    stdout = subprocess.PIPE, 
                                                stderr = subprocess.PIPE,
                                                shell = False ) 
    (dirs, errs)    = result.communicate( )

    if result.returncode != 0:
        
        print "!!! Command {0} failed with returncode {1}".format( cmd,\
                                                                result.returncode )

        sys.exit( )

    if remotebasedir in dirs:

        print "-> Backup base directory %s:%s found on remote." % (confname,\
                                                                    remotebasedir)

    else:
        
        print "!!! Cound't find base directory %s:%s on cloud." % (confname,\
                                                                    remotebasedir)
        sys.exit( )


#
#   Duplicating Joseph Farran's Selective Backup Paths parser to maintain
#   convention.  TODO: Replace dos2unix and sed, with a 1 liner dos2unix 
#   and replace sed with sub.re.  May also want to change subprocess.call() 
#   to Pcall()
#
def parseSourceFile( sourcefl ):
    
    cmd     = ( ['/usr/bin/dos2unix', str(sourcefl)] )

    result  = subprocess.Popen( cmd, shell = False )
    (cleanerSource, err) = result.communicate( )

    if result.returncode != 0:

        print "!!! Failed to parse {0}".format( sourcefl )

        sys.exit() 

    else:
        # Duplicating Selective Backup 'sed' string
        sedstr  = [ "s/\..//", "s/([`$&|><?])//g", "s/#.*//", "s,/\+$,,",\
                    "s/^[ \t]*//", "s/ *$//", "/^$/d" ]

        outfl   = open( sourcefl + "-clean", "w" )

        cmd     = ( ['sed', '-e', sedstr[0], '-e', sedstr[1], '-e', sedstr[2],\
                    '-e', sedstr[3], '-e', sedstr[4], '-e', sedstr[5],\
                    '-e', sedstr[6], sourcefl] )

        res     = subprocess.call( cmd, stdout = outfl ) 


#
#   Parse source paths
#
def prepPaths( ):

    if os.path.isfile(sourcefl):
        
        if os.stat(sourcefl).st_size > 0:

            parseSourceFile( sourcefl )

            print "-> Found file {0} with paths to backup.".format( sourcefl )


        else:

            print "!!! File {0} is empty.  Nothing to backup!...".format( sourcefl )

            sys.exit( )


    else:
        
        print "!!! Couldn't find a file {0} containing paths for cloud backup. "\
                " Please crete one so we know what needs to be backuped up."\
                                                            .format( sourcefl )

        sys.exit( )




def main( ):

    findRCloneInstances( )
    findRCloneConfig( )
    testRCloneConfig( )
    prepPaths( )
        # prepSourcePaths
        # excludeSourcePaths
        # prepDestPaths
    #prepExecString( )


if __name__ == "__main__":

    main( )
