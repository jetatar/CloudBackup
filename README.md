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

Notes:

- Git Annex: 
https://writequit.org/articles/getting-started-with-git-annex.html

* Allows managing large files with git, without checking the contents into git.  Only a symlink is checked into git.  The symlink contains the SHA-1 of the file.
* Syncs files between various storage services (cloud, personal cloud, removable HDs).
* Has a drag and drop client/web app as well as a CLI.  It also has an Android version?
* Written in Haskell.
* Uses inotify.
* Git annex uses rsync == scp for data transfers that are not custom, like many cloud services.
* rsync 
* Use -d option to see exactly what git annex executes so one can figure out what transfer protocol is used.
* Info on tmp files being locked in the event of a git-annex interruption.
* Git annex GUI (assistant): https://www.kickstarter.com/projects/joeyh/git-annex-assistant-like-dropbox-but-with-your-own

I just wrote a post (http://mattshirley.com/Benchmarking-BitTorrent-for-large-transfers-of-next-generation-sequencing-data) benchmarking BitTorrent vs scp. I'm not going to benchmark against Aspera, since I don't have a server license, but I think as far as throughput it would go aspera,unison,udt > BitTorrent > scp,netcat,http,ftp,scp. The main benefit to using BitTorrent would be lightweight infrastructure and good, stable tools, as well as scalable distribution if you are sending data to more than one collaborator.

Installing Git-Annex:

Downloaded tarball with all dependencies included from:
https://git-annex.branchable.com/install/Linux_standalone/

Set path to:
PATH=$PATH:/pub/jtatar/tmp/git-annex.linux/bin (note to include /bin, and not top level dir)

Installing RClone:
http://rclone.org/downloads/
Download the AMD64 bit binary

Install git-annex-rclone:
https://github.com/DanielDent/git-annex-remote-rclone
Set path: PATH=$PATH:/pub/jtatar/tmp/git-annex-remote-rclone-master

Generally Useful References:

https://github.com/swcarpentry/DEPRECATED-site/issues/797
http://udt.sourceforge.net/software.html
https://www.biostars.org/p/76628/
http://www.failureasaservice.com/2015/05/file-transfer-tool-performance-globus.html
http://pcbunn.cacr.caltech.edu/bbcp/using_bbcp.htm
https://news.ycombinator.com/item?id=12398303

- Git Annex RClone

- DVCS-Autosync
