Goal:

Google provies unlimited storage to UCI affiliates through their Google Drive service.  Since data storage and capacity are a constant issue (along with long term maintenance and support), it would be great if we could utilize Google Drive as much as possible for data storage.

Approach:

The usefulness Google Drive mainly depends on the network speed we are able to achieve when transferring files between HPC and Google Drive.

Design:
Make design flexible so most of the code can be reused for services other than Google Drive (i.e: Amazon).

Accounts to backup from:
    - /etc/passwd > 500 && < 65500
    - csv file                                                      (TODO)

To Do:

Test network speed for a variety of file sizes, number of files and directories, file systems.
