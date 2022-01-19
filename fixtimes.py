import os, win32con, win32api, win32file, stat, sys
from pywintypes import Time
from pathlib import WindowsPath

# moving files between volumes and in other scenarios on Windows
# changes the times on the files, which I find unhelpful
# this script sets the oldest known timestamp as created/modified

# this script is currently Windows-specific because I haven't yet
# had time to test the os/stat functionality used here
# if you absolutely want to try it on Linux, replace all
# WindowsPath with Path
# ex: file_list.append(WindowsPath(item[0])) -> file_list.append(Path(item[0]))

# you can enter a root directory here if you don't want to use the command-line
# ex: BASE_DIR = r"C:\Users"
BASE_DIR = r"" 
# if you only want to process certain subdirectories, replace '.'
# ex: SUBDIRS = ['dir1', 'dir2', 'dir3', ]
SUBDIRS = ['.']


def set_oldest_time(file, flags_and_attr=win32con.FILE_FLAG_BACKUP_SEMANTICS):
    # get the oldest time by getting the smallest value out of
    # the modified, accessed and created times from the file attributes
    newtime = Time(min(file.stat().st_mtime, file.stat().st_atime, file.stat().st_ctime))

    # remove (or ignore?) read-only flag if necessary
    is_writable = os.access(str(file), os.W_OK)
    if not is_writable:
        # I have no idea what stat.S_IWRITE is or how it works
        # but I found it in the os.chmod() documentation
        os.chmod(str(file), stat.S_IWRITE)

    # open existing file, change the time and close the file
    # 256 character max limit on Windows which can only be ignored
    # by prefixing \\?\ to an absolute file path
    # ... but it doesn't work and I'm not sure why
    # https://bugs.python.org/issue18199
    file = "\\\\?\\" + str(file)
    winfile = win32file.CreateFile(
        file, win32con.GENERIC_WRITE,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None, win32con.OPEN_EXISTING,
        flags_and_attr, None)
    win32file.SetFileTime(winfile, newtime, newtime, newtime)
    winfile.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_DIR = sys.argv[1]
    os.chdir(str(BASE_DIR))

    if BASE_DIR == "":
        print("No BASE_DIR defined or command-line argument given")
        print(r"ex: python fixtimes.py C:\Users")
        sys.exit(1)

    processed_files = 0
    failed_files_num = 0
    failed_files = []

    for subd in SUBDIRS:
        # get full list of all files/dirs in the given directory
        files = os.walk(str(subd))

        # parses the tuple returned by walk to create valid 
        # WindowsPath objects for every file/dir and store them
        file_list = []
        for item in files:
            # add directories so they're also processed
            file_list.append(WindowsPath(os.path.join(BASE_DIR, item[0])))
            for filename in item[2]:
                # create file path from directory and one of the filenames inside said dir
                file_list.append(WindowsPath(os.path.join(BASE_DIR, item[0], filename)))

        for index, file in enumerate(file_list):
            try:
                set_oldest_time(file)
                processed_files += 1
            except Exception as inst:
                print(" ".join(["\n", str(index), str(file), " failed"]))
                print(str(type(inst)) + " - " + str(inst.args))
                failed_files_num += 1
                failed_files.append([file, inst])

    print("Following files failed: ")
    for file in file_list:
        print("{}: {}".format(file[0], str(type(file[1])))) # 0 for file itself and 1 for the exception

    print("Completed successefully, processed {} files. {} files failed"
        .format(processed_files, failed_files_num))
