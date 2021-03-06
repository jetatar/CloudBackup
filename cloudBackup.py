#!/bin/env python

#   TODO: Add .exclude-clean as .backup-clean
#
#   J. Tatar
#   Ver. alpha


import sys
import os
import signal
import errno
import time
import subprocess
import psutil
import daemon # https://pypi.python.org/pypi/python-daemon
import daemon.pidfile
import logging
import lockfile
import argparse
import ConfigParser
from collections import deque
import getpass

# Local configs

basedir         = os.path.expanduser( "~" )
username        = getpass.getuser( )
#basedir         = "/data/users/jtatar"  # NOTE: no '/' at the end of the path
clouddir        = basedir + "/.hpc_cloud_backup"
rc_conf_file    = ""
confname        = "gDrive"
logdir          = clouddir + "/logs"
logfl           = logdir + "/cloudbackup.log"
configfl        = clouddir + "/config"
sesslogdir      = logdir + "/sessions"
cloudpidfl      = clouddir + "/cloudbackup.pid"

rc_exe_path     = ""

sourcefl        = clouddir + "/backup"
cleansourcefl   = clouddir + "/.backup_clean"
excludefl       = clouddir + "/exclude"
rclonecmdfl     = clouddir + "/.backup_rclonecmd"

qdir            = clouddir + "/queue"
qjobsdir        = clouddir + "/queue/jobs"
qlogsdir        = clouddir + "/queue/logs"
queues          = "grb,grb64"
maxqjobs        = 0

#dt              = 1 # time between backups (1 min after the first backup ends, the second will begin)


# Remote configs
remotebasedir = "UCI_HPC_Backup"


#
#   Configure logging.
#
def confLogging( ):
    
    log     = logging.getLogger( __name__ )
    log.setLevel( logging.INFO )
    lfh     = logging.FileHandler( logfl )
    lformat = logging.Formatter( 
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s' )
    lfh.setFormatter( lformat )

    log.addHandler( lfh )

    log.info( "Configured Logging." )


#
#   Don't want to start another CloudBackup/RClone process if there are any 
#   already running.
#
def findRCloneInstances( pname = "" ):

    log         = logging.getLogger( __name__ )
    THIS_PID    = os.getpid( )
    
    log.info( "Checking for existing Cloud Backup instances." )

    for pid in psutil.process_iter( ):

        if pid.pid != THIS_PID:

            try:
                pcmd = pid.cmdline( )
                pcmd = ' '.join( pcmd )

            except( psutil.NoSuchProcess, psutil.AccessDenied ) as err:

                log.info( "!!! Couldn't process pid in running processes."\
                                                            "Error: %s", err )

                pass

            if not pname == "":

                if pname in pcmd:

                    log.info( "!!! Found a running instance of Cloud Backup"\
                                " with PID {}.  This pid {}.  Cmdline: {}"\
                                    .format(pid.pid, THIS_PID, pid.cmdline()) )

                    sys.exit( )


def getRCloneInstances( pid = None, pname = "", pfl = "" ):

    log         = logging.getLogger( __name__ )
    THIS_PID    = os.getpid( )
    runningPID  = []
    
    log.info( "Checking for existing RClone instances." )

    for pid in psutil.process_iter( ):

        if pid.pid != THIS_PID:

            try:
                pcmd = pid.cmdline( )
                pcmd = ' '.join( pcmd )

            except( psutil.NoSuchProcess, psutil.AccessDenied ) as err:

                log.info( "!!! Couldn't find pid in running processes."\
                                                            "Error: %s", err )

                pass

        # TODO: This should be a while loop in order to print all already running 
        # instances.
        #
        #

            if pname != None and pname in pcmd:

                runningPID = [ pid.pid ]

                log.info( "!!! Found a running RClone instance of Cloud Backup"
                            " with PID {}".format(pid.pid) )

    return runningPID 

#
#   Find RClone user configuration file.  The user should have gone through
#   initial RClone configuration specifying a unique name for the Google Drive
#   HPC configuration.
#   
#   TODO: Check that the script is being executed on the right compute node/queue.
#
def findRCloneConfig( ):

    global rc_conf_file

    log     = logging.getLogger( __name__ )

    if os.path.isfile(rc_conf_file):

        log.info( "Configuration file %s found." % rc_conf_file )

        if confname in open(rc_conf_file).read():
            log.info( "Found %s configuration for UCI HPC Cloud backup."\
                                                                % confname )

        else:
            log.info( "!!! RClone configuration name %s for UCI HPC Cloud backup "\
                                    "not found in %s" % (confname, rc_conf_file) )
            sys.exit( )

    else:
        log.info( "!!! RClone configuration file not found. :(" )
        log.info( "!!! Specify the RClone config path with --rc_conf_file=PATH" )

        sys.exit( )

#
#   Test to make sure tocken and config are valid by checking to see if UCIHPCBackup
#   directory exists in the user's remote drive.
#
def testRCloneConfig( ):

    log             = logging.getLogger( __name__ )

    #cmd             = ( ['/data/apps/rclone/1.35/bin/rclone', 'lsd',
    cmd             = ( [rc_exe_path, 'lsd',
                                                            str(confname)+":"] )
                                            #shell = True security hazard?
    result          = subprocess.Popen( cmd,    stdout = subprocess.PIPE, 
                                                stderr = subprocess.PIPE,
                                                shell = False ) 
    (dirs, errs)    = result.communicate( )

    if result.returncode != 0:
        
        log.info( "!!! Command {0} failed with returncode {1}".format(cmd,\
                                                            result.returncode) )

        sys.exit( )

    if remotebasedir in dirs:

        log.info( "Backup base directory %s:%s found on remote." % (confname,\
                                                                remotebasedir) )

    else:
        
        log.info( "!!! Cound't find base directory %s:%s on cloud." % (confname,\
                                                                remotebasedir) )
        sys.exit( )


#
#   Duplicating Joseph Farran's Selective Backup Paths parser to maintain
#   convention.  TODO: Replace dos2unix and sed, with a 1 liner dos2unix 
#   and replace sed with sub.re.  May also want to change subprocess.call() 
#   to Pcall()
#
def parseSourceFile( sourcefl ):

    log = logging.getLogger( __name__ )    

    with open( sourcefl, 'rb' ) as sfl:
        text = sfl.read().replace( '\r\n', '\n' )

    with open( sourcefl, 'wb' ) as ofl:
        ofl.write( text )

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

    log = logging.getLogger( __name__ )

    if os.path.isfile(sourcefl):
        
        if os.stat(sourcefl).st_size > 0:

            parseSourceFile( sourcefl )
            #excludePaths( )

            log.info( "Found file {0} with paths to backup.".format(sourcefl) )


        else:

            log.info( "!!! File {0} is empty.  Nothing to backup!..."\
                                                        .format(sourcefl) )

            sys.exit( )


    else:
        
        log.info( "!!! Couldn't find a file {0} containing paths for cloud backup."\
                    " Please crete one so we know what needs to be backuped up."\
                                                            .format(sourcefl) )

        sys.exit( )


#
#   Prepare final RClone argument string:
#       setsid rclone copy -vv [source] [destination] --exclude-from filesToExclude.txt --dump-filters --log-file ~/hpc_pubdir_cloud_backup.log --transfers=32 --checkers=16 --drive-chunk-size=16384k --drive-upload-cutoff=16384k --drive-use-trash &>/dev/null
#
#
def prepExecStrings( ):
    
    log = logging.getLogger( __name__ )

    if os.path.isfile(cleansourcefl):
        
        if os.stat(cleansourcefl).st_size > 0:

            with open(cleansourcefl) as fl:

                #spath = p.strip() for p in fl.readlines( )

                spath = [ p.strip() for p in fl.readlines( ) ]
                epath = [ "{0}:{1}{2}".format(confname, remotebasedir, sp)\
                                        for sp in spath ]
                
            # TODO: Check excludefl exists.
            # TODO: include --log-file 

            log.info( "Generating final RClone command string." )

            cmd = [ "{0} copy -vv {1} {2}"\
                        " --exclude-from {3} "\
                        "--dump-filters --transfers=32 "\
                        "--checkers=16 --drive-chunk-size=16384k "\
                        "--drive-upload-cutoff=16384k --drive-use-trash"\
                        .format(rc_exe_path, src, dest, excludefl) \
                                        for (src, dest) in zip(spath, epath) ]

            log.info( "{}".format(cmd) )

            # Write out all commands that will be executed to a file.
            with open(rclonecmdfl, "w") as cfl:

                cfl.write( '\n'.join(cmd) )
                cfl.close( )

            # Generate jobs queue.
            for i, c in enumerate( cmd, start = 1 ):

                global maxqjobs

                qflnm       = qjobsdir + "/cloudJob.{}".format( i ) 
                maxqjobs    += 1

                with open( qflnm, "w" ) as qfl:

                    qfl.write( "%s\n" % c )
                    qfl.close( )

            if maxqjobs > 0:
                log.info( "Job submission files generated." )

        else:

            log.info( "!!! Clean source file {0} is empty.  Nothing to backup!..."\
                                                            .format(sourcefl) )

            sys.exit( )

            
    else:

        log.info( "!!! Couldn't find a cleaned source file {0}."\
                                                            .format(cleansourcefl) )

        sys.exit( )

#
#   Count number of lines in a file.  (UNUSED)
#
def numNewLines( fl ):

    with open( fl, "r" ) as f:
        
        for i, l in enumerate(f):

            pass

        return i + 1

    fl.close( )


#
#   Given a file, return a list with file lines as elements
#
def flLineToList( fl ):

    lst = []    

    with open( fl, "r" ) as fl:

        lst = fl.read().splitlines()
        
    return lst


#
#   Submit RClone cmd by line number of file rclonecmdfl set to.
#
def subRCProc( proc, linenum ):

    log = logging.getLogger( __name__ )

    cmdList = [ p for p in proc.split(" ") ]
    
    fl = open( sesslogdir + "/RCloneCmdLine_{}.log".format(linenum), "w" )

    result  = subprocess.Popen( cmdList, stdout = fl, stderr = fl )

    log.info( "Initiating RClone session with PID {}".format(result.pid) )

    return result


#
#   Schedules and manages number of rclone commands to be run simultaneously.
#
def scheduleRCloneCmds( max_sess ):

    log = logging.getLogger( __name__ )

    rclonePID = getRCloneInstances( pname = "rclone" )

    if rclonePID != []:
        
        npids = len( rclonePID )

        log.info( "Found {} running RClone instance(s).".format(npids) )

    else:

        log.info( "Found no running RClone instances." )

        #nrclones = numNewLines( rclonecmdfl )
        procs    = deque( flLineToList(rclonecmdfl) )
        nprocs   = len( procs )

        log.info( "Number of RClone commands to process: %d" % (nprocs) )

        ln          = 0 # cmd line counter
        runningps   = { }

        while len(procs) > 0:
        
            #max_running = min( len(procs), max_sess )

            log.info( "Max # of simultaneous RClone sessions: {}"\
                                                    .format(max_sess) )

            log.info( "{}, {}, {}".format(len(runningps), max_sess, ln) )

            #if len(runningps) < max_running:
            if len(runningps) < max_sess:

                log.info( "Starting command line # {}".format(ln) )
                ps                  = subRCProc( procs.popleft(), ln )
                runningps[ps.pid]   = ps
                ln += 1

            else:

                log.info( "Max sessions (%d) open. "\
                            "Waiting for a session to end." % max_sess )
                (pid, status) = os.wait( )
                runningps.pop( pid )
                log.info( "RCLone session with PID {} ended with status {}"\
                                                            .format(pid, status) )

    #log.info( "All done!  Going to sleep." )

"""
                    r, e = result.communicate( )  # This calls communicate on first running process and doesn't return until the first process finishes.
                    result.wait( ) # exit all child processes when cloudBackup.py exists.

                     As is if stdout,stderr of a process is too big and I am not reading it, it is stored in buffer.  If the buffer is full or overloaded it can crash.  Use solution mentioned here: http://stackoverflow.com/questions/17190221/subprocess-popen-cloning-stdout-and-stderr-both-to-terminal-and-variables/25960956#25960956
                     Problem is described in detail here: http://stackoverflow.com/questions/36945580/redirect-the-output-of-multiple-parallel-processes-to-both-a-log-file-and-stdout
"""

#
#   Get log file handlers so they can be kept open after daemonizing.  Otherwise
#   logging to the log files stops.
#
def getLogFileHandles( log ):
    
    handles = [ ]

    for handler in log.handlers:
        
        handles.append( handler.stream.fileno() )

    if log.parent:
        
        handles += getLogFileHandles( log.parent )

    return handles


#
#   Get command line for a specific process.
#
def getCmdByPID( pid ):

    log = logging.getLogger( __name__ )

    try:
        with open( "/proc/%d/cmdline" % pid ) as fl:
            return fl.read( )

    except EnvironmentError as err:
        log.info( "!!! Error finding process command line. Error: {}".format(err) )
        return '' 

#
#   Look an executible (like RClone) in all $PATH dirs.
#
def findExe( exe ):

    log = logging.getLogger( __name__ )

    for path in os.environ["PATH"].split( os.pathsep ):

        path    = path.strip( '"' )
        exefl   = os.path.join( path, exe ) 

        if os.path.isfile( exefl ) and os.access( exefl, os.X_OK ):
            
            log.info( "Found RClone executible to use as default: {}"\
                                                                .format(exefl) )

            return exefl

    log.info( "Can't find an RClone executible to use!" )

    return None



#
#   Argument parser.
#
def parseOptions( argv ):

    log = logging.getLogger( __name__ )

    # config file parser (PARENT) 
    # Turn off -h/help in parent parser, so it doesn't print options twice (child)
    # the --config_file option has to be parsed first, if we want to be able to
    # overwrite config file options from command line.
    cnparser  = argparse.ArgumentParser(
                description = __doc__,
                formatter_class = argparse.ArgumentDefaultsHelpFormatter,
                add_help = False ) 

    cnparser.add_argument( "-c", "--conf_file",
                        dest        = "configfl",
                        required    = False,
                        help        = "Specify config file to use.",
                        metavar     = "FILE" )

    args, rem_args = cnparser.parse_known_args( ) # default taken from sys.argv[1:]

    defaults = {    "dt"            : 60,
                    "max_sess"      : 2,
                    "rc_exe_path"   : rc_exe_path,
                    "rc_conf_file"  : rc_conf_file }

    # If config file path is specified by user read the file.
    global configfl

    if args.configfl:

        configfl = args.configfl

        log.info( "Trying to load user specified config file {}.".format(configfl) )

    # If not specified by user, look for config file in default location.
    else:

        log.info( "Looking for config file in {}".format(configfl) )


    config = ConfigParser.SafeConfigParser( )
    config.read( [configfl] )
    # If config file reading is successful, overwrite defaults.
    defaults.update( dict(config.items(confname)) )

    # Create a child parser that inherits options from parents.
    # Not suppressing help here, so -h/--help will work.
    parser  = argparse.ArgumentParser( parents = [cnparser] )

    # Set (in order of priority) 1. defaults 2. config file 3. user specified
    # options.
    parser.set_defaults( **defaults )

    parser.add_argument( "-dt", "--delta_t",
                        type        = int,
                        dest        = "dt",
                        required    = False,
                        help        = "Time, in minutes, between backup restarts.",
                        metavar     = "NUMBER" )

    parser.add_argument( "--max_sess",
                        type        = int,
                        dest        = "max_sess",
                        required    = False,
                        help        = "Maximum number of simultaneous RClone sessions.  DO NOT EXCEED 2 (FOR NOW)",
                        metavar     = "NUMBER" )

    parser.add_argument( "-rc", "--rc_exe_path",
                        type        = str,
                        dest        = "rc_exe_path",
                        required    = False,
                        help        = "Specify RClone executible's path",
                        metavar     = "PATH" )

    parser.add_argument( "-rconf", "--rc_conf_file",
                        dest        = "rc_conf_file",
                        required    = False,
                        help        = "Specify path to RClone config file to use.",
                        metavar     = "FILE" )

    parser.add_argument( "-qsub",
                        nargs       = '?',
                        const       = 'qsub',
                        default     = 'qsub',
                        required    = False,
                        help        = "Create job submission files for queues" )

    parser.add_argument( "stop",
                        nargs       = '?',
                        help        = "Stop backup" )


    return parser.parse_args( rem_args )


#
#   Create dirs.
#
def mkdir( path ):

    log = logging.getLogger( __name__ )

    try:
        os.makedirs( path )

    except OSError as err:

        if err.errno != errno.EEXIST:
            log.info( "!!! Error trying to create dir {}. Error thrown: {}"\
                        " ... exiting ...".format(path, err) )

        else:
            log.info( "Dir {} exists.".format(path) )


#
#   Implementation of "cloudBackup.py stop" -- kill running cloudBackup.
#
def killCloudBackup( pidfl ):

    log = logging.getLogger( __name__ )

    pid = daemon.pidfile.TimeoutPIDLockFile(pidfl, -1).read_pid( )
    pid = int( pid )

    if pid:

        log.info( "Killing cloudBackup with pid: {}".format(pid) )
        os.kill( pid, signal.SIGTERM )

        sys.exit( )

#
#   Glue - put it all together.
#
def main( argv = None ):

    if argv is None:
        argv = sys.argv

    # Setup base dirs.  Can't use mkdir() it uses logger, but log dir not created.
    try:
        os.makedirs( clouddir )
        os.makedirs( logdir )

    except OSError: # If dir exists, pass.
        pass

    # Create RClone logs for each initiated RClone instance.
    mkdir( sesslogdir )

    # Configure Logging
    confLogging( )
    log     = logging.getLogger( __name__ )

    # Try to find RClone path and use it as default
    global rc_exe_path
    rc_exe_path = findExe( "rclone" )

    # Setting default RClone config file path.
    global rc_conf_file
    rc_conf_file    = basedir + "/.config/rclone/rclone.conf"

    # Configure option parsing
    config  = parseOptions( argv )

    if config.rc_exe_path:

        rc_exe_path = config.rc_exe_path

        log.info( "Using RClone: {}".format(config.rc_exe_path) )

    else:
        log.info( "Can't find a valid RClone executible. "\
                    "Please specify it in config file or set it using "\
                    "--rc_exe_path option." )

        sys.exit( )

    if config.rc_conf_file:
        
        rc_conf_file = config.rc_conf_file

        log.info( "Trying to load user specified RClone config file {}"\
                                                        .format(rc_conf_file) )
    else:
        
        log.info( "Looking for RClone config file in {}".format(rc_conf_file) )



    if config.stop == "stop":

        print "-> Stopping Cloud Backup..."

        killCloudBackup( cloudpidfl )
        sys.exit( )


    print "-> Staring Cloud Backup...\n  Check {} for status.".format( logfl )
    log.info( "Staring Cloud Backup." )

    # Check that a RClone configuration exists.
    findRCloneConfig( )

    # Daemonize.  From here on, stderr, stdout are redirected to log files.
    pf          = daemon.pidfile.TimeoutPIDLockFile( cloudpidfl, -1 )
    existing_pf = pf.read_pid( )

    # Check for previously existing Cloud Backup processes.
    if existing_pf:

        cmd = getCmdByPID( existing_pf )

        if not cmd.strip():
            pf.break_lock( )

        else:
            log.info( "!!! There is an already running instance with PID:"\
                        "%d. Exiting." % existing_pf )

            sys.exit( )

    dcontext = daemon.DaemonContext( pidfile = pf, detach_process = True,\
                files_preserve = getLogFileHandles(log) ) 

    log.info( "Detaching parent process." )

    # Main loop
    with dcontext:

        while True:
            # Check for existing Cloud Backup instances.
            findRCloneInstances( pname = "python cloudBackup.py" )

            # Test by checking the Google Drive directory for backups exists.
            testRCloneConfig( )

            # Clean user input dir and file strings 
            prepPaths( )

            # Prepare final RClone command.
            prepExecStrings( )

            if maxqjobs > 0:

                log.info( "Created scheduler submit scripts for {} serial jobs."\
                                                                .format(maxqjobs) )

                subscript = [   '#!/bin/bash\n',
                                '#$ -t 1-{}\n'.format(maxqjobs),
                                '#$ -N cloudbkp.{}\n'.format(username),
                                '#$ -q {}\n'.format(queues),
                                '#$ -V\n'
                                '#$ -o {}\n'.format(qlogsdir),
                                '#$ -j y\n',
                                '\n',
                                'bash {}/.${{SGE_TASK_ID}}\n'.format(qjobsdir) ]

                with open( qdir + "/sgeQsub.sh", 'w' ) as qfl:
                    for ln in subscript:
                        #log.info( "{}".format(ln) )
                        qfl.write( "{}".format(ln) )

            if config.qsub:

                sys.exit( )

            # Schedule RClone command for execution.
            scheduleRCloneCmds( config.max_sess )

            # Sleep between backups
            #time.sleep( 10 )
            if config.dt > 0:

                log.info( "All done!  Going to sleep for {} min."\
                                                            .format(config.dt) )
                time.sleep( config.dt * 60 ) # minutes
            else:
                
                log.info( "ciao ciao" )
                sys.exit( )



if __name__ == "__main__":

    main( )
