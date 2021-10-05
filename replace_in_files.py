# -*- coding: utf-8 -*-
"""

"""

import os 

TOP = "."

REPLACE_MAP = dict(
        DOGGIES = 'HOGS',
        FOOBAR = 'RANDY'
        )

def fileNameMatch(fname):
    return fname.endswith(".spud") # (".java")
    

def walker():
    for r, dz, fz in os.walk(TOP):
        for fn in fz:
            if not fileNameMatch(fn):
                continue
            fpath = os.path.sep.join((r,fn))
            substitute(fpath)

def substitute(fpath):
    print ('Substitute: %s' % fpath)
    with open(fpath,'r+') as f:
        nlz = []
        for lin in f.readlines():
           for k,v in REPLACE_MAP.items():
              lin = lin.replace(k,v)
           nlz.append(lin)
        f.seek(0)
        f.truncate()
        f.writelines(nlz)
        f.close()
        
if __name__ == '__main__':
    walker()
                    
                
        
    
    
    