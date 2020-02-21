'''
http://legacysurvey.org/dr8/description/
Sources are resolved as distinct by only counting BASS and MzLS sources if they are both at Declination > 32.375° and north of the Galactic Plane, or, otherwise counting DECam sources.
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

SV_south_bricklist()

