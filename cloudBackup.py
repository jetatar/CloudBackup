#!/bin/env python

import sys
import os.path

basedir     = "/data/users/jtatar"
rconfdir    = basedir + "/.config/rclone/rclone.conf"
confname    = "gDrive"

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

def main( ):
    findRCloneConfig( )

if __name__ == "__main__":
    main( )
