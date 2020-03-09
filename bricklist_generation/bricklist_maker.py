'''
http://legacysurvey.org/dr8/description/
Sources are resolved as distinct by only counting BASS and MzLS sources if they are both at Declination > 32.375 and north of the Galactic Plane, or, otherwise counting DECam sources.
'''

import os
import astropy.io.fits as fits
import numpy as np
import glob
def SV_south_bricklist():
    '''
    bricklist made for SV south
    '''
    bricknames=set([])
    tiles_dir = os.environ['SV_tiles']
    fns = glob.glob(tiles_dir+'/tile-*')
    for fn in fns:
        dat = fits.getdata(fn)
        sel = (dat['PHOTSYS']=='S')
        if sel.sum()>0:
             bricknames=bricknames|set(dat[sel]['BRICKNAME'])
    bricknames=list(bricknames)
    f=open(os.environ['obiwan_out']+'/bricklist.txt','w')
    for bricknames in bricknames:
        f.write(bricknames+'\n')
    f.close()

def cosmos_repeat_bricklist(sub_num):
    fns = glob.glob('/global/cscratch1/sd/desiproc/dr8-cosmos/decam-sub%d/tractor/*/tractor-*.fits'%sub_num)
    bricklist=[]
    for fn in fns:
        brickname=os.path.basename(fn).replace('tractor-','').replace('.fits','')
        bricklist.append(brickname)
    f=open(os.environ['obiwan_out']+'/bricklist.txt','w')
    for bricknames in bricklist:
        f.write(bricknames+'\n')
    f.close()

def cosmos_repeat_bricklist_intersected():
    #bircks that exist in all subs
    brickset=None
    for i in range(0,10):
        fns = glob.glob('/global/cscratch1/sd/desiproc/dr8-cosmos/decam-sub%d/tractor/*/tractor-*.fits'%i)
        bricklist=[]
        for fn in fns:
            brickname=os.path.basename(fn).replace('tractor-','').replace('.fits','')
            bricklist.append(brickname)
        bricklist=np.array(bricklist,dtype=np.str)
        if brickset is None:
            brickset=set(bricklist)
        else:
            brickset=brickset&set(bricklist)
    bricklist = list(brickset)
    f=open(os.environ['obiwan_out']+'/bricklist.txt','w')
    for bricknames in bricklist:
        f.write(bricknames+'\n')
    f.close()
    

cosmos_repeat_bricklist_intersected()

