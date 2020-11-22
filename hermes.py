#!/usr/bin/python
import os
import sys
import time
import shutil
import filecmp
import subprocess
import hashlib
import cPickle as pickle
import argparse
import textwrap
import collections
import json

"""
This version of hermes is the one that will be DONE!! by dadgummit 
Eliminate confusing and excessive feature ideas
NO HISTORY, NO TRACKING OF SCANS. 

1. Exactly ONE copy of each file by hash. No more.
2. Read in and/or Write out a pickle.   
3. All reporting done to sysout..  capture it if you want, or don't
4. treat dupes found in current scan exactly the same as dupes matching current to previous. 
    move em, or leave em. 
5. stdout report parsable, but no object output.. make more tools if you must. 

POINT IS TO MAKE A USEFUL TOOL FOR CURRENT PROBLEM.. NOT A SWISS ARMY KNIFE FOR ANY POSSIBLE PROBLEM IN FUTURE

"""
# ==============================================================================

PS    = os.path.sep
HOME  = os.getenv('HOME')
CWD   = os.getcwd() 
if CWD == PS:
    raise SystemExit("don't run from /. just don't")
    
DEFAULT_PICKLE=PS.join((HOME,"hermes.pickle"))

def Say(x):
    sys.stderr.write("%s\n" % x)
Bug=lambda x:None
# ==============================================================================
# hostname
p = subprocess.Popen("hostname",shell=True,stdout=subprocess.PIPE)
p.wait()
HOSTNAME = p.stdout.read().strip()

# ==============================================================================

start_time = time.time()

CurrentScan = dict(
    host = HOSTNAME,
    base = CWD,
    start = time.ctime(),
    comment =''
)

Scans = [] 
Bhash = {} # key: fash  val: toop or [toop,..]
Bfold = {} # key: relative folder path

# REPORTING - in order of shown
dup_folders = [] # highest level possible
new_unique = [] #  all 'new' unique files. added to Bhash and Bfold of course.
dup_files  = [] #  all duplicates

FILE_TUPLE = collections.namedtuple("FileTuple",('scan', 'path', 'size', 'fash'))  
tut = lambda path, size, fash: (CurrentScan, path, size, fash)
# ##############################################################################


HELP = \
"""
Hermes
   scan directory structure, report on duplicates.
   if entire folder is duplicates.. only report on the folder.
   move duplicates to a special folder
   
"""




def main():
    global Conf, Say, Bug
  
    par = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=HELP)
    
    par.add_argument('-r', '--read',    action='store',    help="store file read path. use '.' for default" )
    par.add_argument('-w', '--write',   action='store',    help="store file write path. if read not specificied, read from here if exists. use '.' for default" )
    par.add_argument('-c', '--comment', action='store',    help="scan comment  optional")
    
    par.add_argument('-m', '--move'   ,action='store',      help='move duplicates to location - relative to PWD')
    par.add_argument('-l', '--list'   ,action='store_true', help='list scans. without --read, wont show much')
    
    par.add_argument('-n', '--hidden', action='store_true', help='scan hidden dirs' )     
    par.add_argument('-d', '--debug',  action='store_true', help='show debugging lines')
    par.add_argument('-q', '--quiet',  action='store_true', help='silence!')   
   
    Conf = par.parse_args()
    
    if Conf.quiet:
        Say = lambda x:None
    elif Conf.debug:
        Bug = Say
        
    CurrentScan['comment'] = Conf.comment or ''
    # -------------------------------------------------------------------------    
    if Conf.read:
        if not os.path.exists(Conf.read):
            raise SystemExit("Cant read - file not found:%s" % Conf.read )
        if Conf.read == '.':
            if not os.path.exists(DEFAULT_PICKLE):
                raise SystemExit("Default not found:%s" % DEFAULT_PICKLE)
            load(DEFAULT_PICKLE)
        else:
            load(Conf.read) 
    elif Conf.write:
        if os.path.exists(Conf.write):
            if Conf.write == '.':
                if os.path.exists(DEFAULT_PICKLE):
                    load(DEFAULT_PICKLE)
                else:
                   raise SystemExit("Default not found:%s" % DEFAULT_PICKLE)
            else:
                load(Conf.write)

    # -------------------------------------------------------------------------    
    Scans.insert(0,CurrentScan) # reverse order 
    
    if Conf.list: 
        dump_scans()
        return
        
    if Conf.move:
        if os.path.exists(Conf.move):
            raise SystemExit("Move to folder already exists:%s" % Conf.move)
        os.makedirs(Conf.move,0777)
     
    scan_folder(".")
    
    if Conf.write:
        if Conf.write == '.':
            write(DEFAULT_PICKLE)
        else:
            write(Conf.write)
    
    json.dump({'matched_folders':dup_folders, 
               'new_files': new_unique,
               'matched files':dup_files},
               sys.stdout,
               indent=3)
   
    Say("FINI")
    
# =======================================================================

def scan_folder(currDir):
    """
    
    shallow ( local ) first; so shallow files are first priority as "official"
    
    matched files moved to folders with identical structure to those in scan, as that arrangement will accomodate all duplicates for examinatino.
    ( had thought moving to official structure might be nice.. but with report, not needed. )
    
    fully matched subtrees will be reported *first*.. their contents will be at end of the report as not as interesting. 
    
    at any level, if the total unmatched > 0,  *all* duplicates, including folders, are moved at that level. 
    only if total match ( unmatched ==0 ) is the case will the moving be left to the parent level. 
    
    returns hasNovelFiles - indicates the subtree is not "bulk movable".. and it's matched contents have already been moved. 
    """
    Bug("scan_folder(%s)" % currDir)
    
    folders = []
    matched = [] # duplicate files in this path.
    matched_sub = [] # subfolders with nothing but matches.. 
    
    hasNovelFiles = False # *any* novel files exist. 
    
    # SCAN - WIDE FIRST ( shallow )
    # =========================
    for entry in os.listdir(currDir):
        
        # hidden        
        if entry.startswith(".") and not Conf.hidden:
            continue
        
        fpath = PS.join((currDir,entry))

        # links 
        if os.path.islink(fpath):
            continue  # we do not care about links.
            
        # folders
        if os.path.isdir(fpath):
            if currDir == "." and entry == Conf.move:
                continue # do not scan the move to. 
            folders.append(fpath)
            continue
        
        #TODO - check for devices and pipes?  
        
        # ============= FILE STATS AND COMPARE ==============
        fsize = fsize_calc(fpath)
        fash =  fash_calc(fpath)
        
        ofp = Bhash.get(fash)
        if ofp:
            # simple test of md5's reliability
            if fsize != ofp[2]: # an extreme reaction
                raise SystemExit("md5 collision!  %s and %s " % ( fpath, ofp))
            # Matched/Duplicate
            matched.append(fpath)
            # Report
            dup_files.append((ofp, (fpath,fsize,fash)))
        else:
            # UNIQUE, NOVEL FILE - "I gotta be me!!!"
            hasNovelFiles = True
            
            # Store.. 
            toop = tut(fpath,fsize,fash)
            Bhash.setdefault(currDir,[]).append(toop)
            Bhash[fash] = toop
            # Report
            new_unique.append(fpath)
    
    # ============= Recurse now ======================
    
    for fpath in folders:
        novel = scan_folder(fpath)
        if novel:
            hasNovelFiles = True
        else:
            matched_sub.append(fpath)
        
    # report at highest level
    dup_folders.extend(matched_sub)
    
    # ============= If we have either fully matched ( unmatched==0 ) folders,
    # ============= or matched files.. or are in the lowest level 
    # ============= then move everything here and now. 
    
    
    if Conf.move and ( hasNovelFiles or currDir == "." ):
        
        
        whereTo = PS.join((Conf.move,currDir))  
        if ( currDir != "."):
            Bug("Make Match(Dupe) folder: makedirs(%s)" % whereTo)
            if not os.path.exists(whereTo):
                os.makedirs(whereTo, 0777)
        
        
        # local (currDir) matched files first.
        Bug("MATCH: %s" % matched)
        for fpath in matched:  # files
            new_path = PS.join((Conf.move,fpath))
            Bug("rename %s to %s" % (fpath, new_path))
            try:
                os.rename(fpath, new_path)
            except OSError, e:
                print ("from %s to %s" % ( fpath, new_path ))
                raise e       
        
        Bug("MFOLD: %s" % matched_sub)
        # only subfolders with pure matches will be moved
        for fpath in matched_sub:
            new_path = PS.join((Conf.move,fpath))
            new_dir = os.path.dirname(new_path)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
            try:
                Bug("rename %s to %s" % (fpath, new_path))
                os.rename(fpath, new_path)
            except OSError, e:
                print ("from %s to %s" % ( fpath, new_path ))
                raise e
            
    return hasNovelFiles
# ==============================================================================
        

def fash_calc(filepath):
    md5 = hashlib.md5()
    with open(filepath,'rb') as f:
        for chunk in iter(lambda: f.read(8192), ''):
            md5.update(chunk)
        return md5.hexdigest()
        
def fsize_calc(filepath):
    try:
       return os.stat(filepath)[6]
    except OSError:
       Say("stat error %s" % filepath)
       return -1
            

def load(read_from_path):
    global Scans, Bhash, Bfold
    Bug("read from %s" % read_from_path)
    with open(read_from_path, 'r') as f:
            Scans, Bhash, Bfold = pickle.load(f)

def write(store_to_path):
    with open(store_to_path,'w') as f:
        pickle.dump((Scans, Bhash, Bfold),f)
    Bug("stored to %s" % store_to_path)
        
def dump_scans():
    import json
    json.dump(Scans, sys.stdout, indent=2)
    
    
################################################################################
if __name__ == '__main__':
    main()
