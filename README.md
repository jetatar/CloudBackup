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
PATH=$PATH:/pub/jtatar/tmp/git-annex.linux

Installing RClone:
http://rclone.org/downloads/
Download the AMD64 bit binary

Install git-annex-rclone:
https://github.com/DanielDent/git-annex-remote-rclone
Set path: PATH=$PATH:/pub/jtatar/tmp/git-annex-remote-rclone-master

1. Setting up Google Drive as a remote for git-annex-rclone:
Login to the interactive node with X11 forwarding, since rclone/google drive need to create unique security tockens for seemless authentication.
Mostly following instructions from: 
- https://github.com/DanielDent/git-annex-remote-rclone
- http://rclone.org/drive/

git-annex-rclone note: Password-protected rclone configurations are not supported at this time, so when running rclone config don't pick the "Set Configuration Password" option at the end of running rclone config.

2. Create a git-annex repository:
https://git-annex.branchable.com/walkthrough/#index1h2

3. Need to deal with locked files: https://git-annex.branchable.com/tips/unlocked_files/


ERRRR:  SHA-256 takes so long ... rclone may be faster.

Let's repeat somewhat the goal:  Back up all of HPC for free.

> Back up all of what I consider most important on HPC - the data.
    > Backup /pub + /data/users/ = 100TB
In phase 2:
    > Backup all of the individual groups' file systems.
In phase 3:
    > Have an option for individual HPC users to specify the backups themselves.

I am going to do all tests with rclone v1.35

Important numbers:

We are going to run rclone from fiona


The numbers seem to be in our favour with a few caviats:
James gets rclone transfer rates of 600MB/s if he opens many simultaneous sessions.  The theoretical max he should be able to push out is ~1.25GB/s.  I have hope that he can improve on that.  Even with 600MB/s, we can transfer 6TB in ~3 hours!!
* Caviat number 1:
That doesn't apply to large files since they can't be broken down and transferred in pieces (unless I make an option for that).

Important features that the transfer client should definitely (hopefully) have:
* Only sync changed segments of a file and not the whole file.
    > According to "Why doesn’t rclone support partial transfers / binary diffs like rsync?" on http://rclone.org/faq/, no cloud storage system supports diff like rsync does because that breaks the 1:1 mapping of FS to Cloud.

* Resume transfer where you left off.
Partial transfers on the other hands would take more metadata.  That would also break the 1:1 mapping.

* GUI
Yes.  Now there is a nice RCloneBrowser.

If we can get a sustained transfer rate of 50MB/s (currently James gets around 40MB/s) per file, it would take ~6h to transfer 1TB file.  It is not horrible, but not great either.

Potential Problems:
* The maximum file size that can be synced to google drive is 5TB (source: https://support.google.com/a/answer/172541?hl=en)


Generally Useful References:

https://github.com/swcarpentry/DEPRECATED-site/issues/797
http://udt.sourceforge.net/software.html
https://www.biostars.org/p/76628/
http://www.failureasaservice.com/2015/05/file-transfer-tool-performance-globus.html
http://pcbunn.cacr.caltech.edu/bbcp/using_bbcp.htm
https://news.ycombinator.com/item?id=12398303

- Git Annex RClone

- DVCS-Autosync

jjhhjj (Parasite) Backup Design:

- Use Joseph's rsync lines for rclone.
    > Problem with this is that users will have to backup the same stuff in both locations.  Can't backup more stuff than what's in their /sbak and they can't only backup to cloud.

- Partially re-used Joseph's script.
    > Reuse:
        - User list creation
        - Exclude and include file parsing.
    
    > Improve:
        - One user one job in a queue.
        - User interaction.  Display how the backup went for user on login.
        - If user doesn't have ongoing backup and there are file modifications, run backup.  Can utilize current logins for that and a global backup once a day.  Each user has an angel running.
        - Allow for multiple parallel streams per user.
        - Option for deleting accounts that are no longer active.
        - Option to optimize throughput on per user basis (break everything up into a file by file basis OR on per SIZE file/directory).

- Have the users learn rclone and post a command in a .file that will get collected and executed.  Post an example that is easily adaptable.  This would have to be made into a GUI, since HPC users can't be expected to even correctly type in options.


Code Structure:

I am writing a scheduling system that is queue friendly.
    - The problem with a very dynamic scheduling system is that I can't easily get a list of affected files, unless I edit the RClone source code.

    - RClone does multiple transfers efficiently by having asyncronous threads specified by the number of transfers configured.  The problem with threads instead of code that queues everything is scalability.  Unless there is a way to connect two nodes and have their total cores be visible.
    > Too much paralleizing doesn't make sense.  One must know what the individual parts of the backup process take the longest.
    > We can't transfer faster than we can load the data into RAM sequentially.
    > We can't transfer faster than the per rclone session speed with google drive.
    > We can't transfer faster than 1.25GB/s, since we have 10Gb/s link max.
    > We can't transfer faster than whatever throttling Google / Amazon, etc have.


    - Taylor a user's RClone configuration on the profile of the files they are trying to save.

Initialize one time things: log dirs
    - in user's own dir
    - they will have to run rclone config anyway to get a token
Initialize things periodically: log dirs, users to backup, etc
Parse user input
Create rclone string
