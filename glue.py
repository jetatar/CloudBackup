#!/bin/env python

import pwd # Needed to get /etc/passwd info
import sys 
'''
Modes:
    Test
    Selective Backup
    Archive
    All?
'''
'''
Get list of users to backup:
    /etc/passwd > 500 && < 65500 && cloud backup turned on
'''

# Load user info from:
#                       /etc/passwd
def loadUsers( ):
    
    try:
        allUsers = pwd.getpwall( )

    except Exception as err:
        print "!!! Error: ", err
        sys.exit( 1 )

    for u in allUsers:
        print u, "\n"

    #print allUsers


# Main function.  Define so function can be called from other scripts.
#
def main( ):
    loadUsers( )


if __name__ == "__main__":
    main( )
