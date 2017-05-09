#!/bin/env python

#
#   NEED TO FIX:
#       Wait for psutil to return before continuing the program.
#
#


import sys
import os.path
import subprocess
import psutil

# Local configs
basedir         = "/data/users/jtatar"  # NOTE: no '/' at the end of the path
rconfdir        = basedir + "/.config/rclone/rclone.conf"
confname        = "gDrive"
sourcefl        = basedir + "/.hpc-cloud-backup"
cleansourcefl   = basedir + "/.hpc-cloud-backup-clean"
excludefl       = basedir + "/.hpc-cloud-backup-exclude"
rclonecmdfl     = basedir + "/.hpc-cloud-backup-rclonecmd"

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
        # Note: This excludes wild-cards being allowed for paths in the source file.
        sedstr  = [ "s/\..//", "s/([`$&|><?])//g", "s/#.*//", "s,/\+$,,",\
                    "s/^[ \t]*//", "s/ *$//", "/^$/d" ]

        outfl   = open( cleansourcefl, "w" )

        cmd     = ( ['sed', '-e', sedstr[0], '-e', sedstr[1], '-e', sedstr[2],\
                    '-e', sedstr[3], '-e', sedstr[4], '-e', sedstr[5],\
                    '-e', sedstr[6], sourcefl] )

        res     = subprocess.call( cmd, stdout = outfl ) 

        outfl.close( )


#
#   Parse paths
#
def prepPaths( ):

    if os.path.isfile(sourcefl):
        
        if os.stat(sourcefl).st_size > 0:

            parseSourceFile( sourcefl )
            #excludePaths( )

            print "-> Found file {0} with paths to backup.".format( sourcefl )


        else:

            print "!!! File {0} is empty.  Nothing to backup!...".format( sourcefl )

            sys.exit( )


    else:
        
        print "!!! Couldn't find a file {0} containing paths for cloud backup. "\
                " Please crete one so we know what needs to be backuped up."\
                                                            .format( sourcefl )

        sys.exit( )


#
#   Prepare final RClone argument string:
#       setsid rclone copy -vv [source] [destination] --exclude-from filesToExclude.txt --dump-filters --log-file ~/hpc_pubdir_cloud_backup.log --transfers=32 --checkers=16 --drive-chunk-size=16384k --drive-upload-cutoff=16384k --drive-use-trash &>/dev/null
#
#
def prepExecStrings( ):
    
    if os.path.isfile(cleansourcefl):
        
        if os.stat(cleansourcefl).st_size > 0:

            with open(cleansourcefl) as fl:

                #spath = p.strip() for p in fl.readlines( )

                spath = [ p.strip() for p in fl.readlines( ) ]
                epath = [ "{0}:{1}{2}".format(confname, remotebasedir, sp)\
                                        for sp in spath ]
                
                fl.close( )

            # TODO: Check excludefl exists.
            # TODO: include --log-file 
            cmd = [ "setsid rclone copy -vv {0} {1} --exclude-from {2} "\
                        "--dump-filters --transfers=32 "\
                        "--checkers=16 --drive-chunk-size=16384k "\
                        "--drive-upload-cutoff=16384k --drive-use-trash "\
                        "&>/dev/null".format(src, dest, excludefl) \
                                        for (src, dest) in zip(spath, epath) ]

            with open(rclonecmdfl, "w") as cfl:

                cfl.write( '\n'.join(cmd) )
                cfl.close( )


        else:

            print "!!! Clean source file {0} is empty.  Nothing to backup!..."\
                                                            .format( sourcefl )

            sys.exit( )

            
    else:

        print "!!! Couldn't find a cleaned source file {0}."\
                                                            .format( cleansourcefl )

        sys.exit( )


def main( ):

    findRCloneInstances( )
    findRCloneConfig( )
    testRCloneConfig( )
    prepPaths( )
        # prepSourcePaths
        # excludeSourcePaths
        # prepDestPaths
    prepExecStrings( )


if __name__ == "__main__":

    main( )
