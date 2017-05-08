#   
#   Effectively create a deamon that users can run ON:
#                                                       * the interactive node
#                                                       * on a queue
#                                                       * executed as user
#


#rclone copy -vv --include-from filesToSave.txt --exclude-from filesToExclude.txt gDrive:hpc_backup

# copy vs copyto (copyto can specify a different name for file to be saved as)

#setsid rclone copy -vv --include-from pubDirFilesToSave.txt --exclude-from filesToExclude.txt /pub/jtatar gDrive:uci_hpc_pubdir_backup --dump-filters --log-file ~/hpc_pubdir_cloud_backup.log --transfers=32 --checkers=16 --drive-chunk-size=16384k --drive-upload-cutoff=16384k --drive-use-trash &>/dev/null

setsid rclone copy -vv --include-from homeDirFilesToSave.txt --exclude-from filesToExclude.txt /data/users/jtatar gDrive:uci_hpc_homedir_backup --dump-filters --log-file ~/hpc_homedir_cloud_backup.log --transfers=32 --checkers=16 --drive-chunk-size=16384k --drive-upload-cutoff=16384k --drive-use-trash &>/dev/null


### This works
#setsid rclone copy -vv --include-from filesToSave.txt --exclude-from filesToExclude.txt /pub/jtatar gDrive:hpc_backup --dump-filters --log-file /pub/jtatar/Work/CloudBackup/hpc_cloud_backup.log --transfers=32 --checkers=16 --drive-chunk-size=16384k --drive-upload-cutoff=16384k --drive-use-trash &>/dev/null
