#!/usr/bin/python3
import os, sys
import json
import argparse

out = {}

HELP = \
"""
deepo PATH1 PATH2

deep compare of two folders. 
name and file size match only.
"""

def main():
    if len(sys.argv) < 3:
        raise SystemExit("deepo PATH1 PATH2")
    
    path1,path2 = sys.argv[1:3]
    
    files1 = scan("L",path1)
    files2 = scan("R",path2)
    
    print("L - not R")    
    
    d1 = list(files1.difference(files2))
    d1.sort()
    for dif in d1:
        print(dif)
    
    print("\n\n")
    
    print("R - not L")        
    
    d2 = list(files2.difference(files1))
    d2.sort()
    for dif in d2:
        print(dif)
    
    
def scan(idx, path):
        files = set()
        
        for r, dz, fz in os.walk(path):
            
            pdir = r[len(path):]
            for fn in fz:
                fpath = os.path.sep.join((r,fn))
                      
                # links 
                if os.path.islink(fpath):
                    continue  # we do not care about links.
                
                fsiz = fsize_calc(fpath)
            
                files.add(("%s/%s" % (pdir,fn), fsiz))
        
        return files
                
def fsize_calc(filepath):
    try:
       return os.stat(filepath)[6]
    except OSError:
       print("stat error %s" % filepath)
       return -1
        
        
    
if __name__ == '__main__':
    main()