'''
give each seed a rhalf value matched from the dr7 tractor catalog
'''
dr7_topdir = '/global/project/projectdirs/cosmo/data/legacysurvey/dr7/tractor/'
SEED = '/global/cscratch1/sd/huikong/Obiwan/dr8/obiwan_out/test/elg_like.fits'
print("adding rhalf to seeds...")
import astropy.io.fits as fits
from astropy.table import Table
import os
import numpy as np
def seed_matching():
    seed = Table.read(SEED)
    bricknames = list(set(seed['brickname']))
    rhalf = np.zeros(len(seed))
    #e1 = np.zeros(len(seed))
    #e2 = np.zeros(len(seed))
    N = len(bricknames)
    count=1
    for brickname in bricknames:
        print("%d/%d"%(count,N))
        count+=1
        tractor = fits.getdata(os.path.join(dr7_topdir,brickname[:3],'tractor-'+brickname+'.fits'))
        seed_sel = (seed['brickname']==brickname)
        for i in range(seed_sel.sum()):
            objid = seed[seed_sel][i]['objid']
            tractor_match = tractor[np.where(tractor['objid']==objid)[0][0]]
            if tractor_match['type']=='DEV':
                rhalf_i = tractor_match['shapedev_r']
                #e1_i = tractor_match['shapedev_e1']
                #e2_i = tractor_match['shapedev_e2']
            else:
                rhalf_i = tractor_match['shapeexp_r']
                #e1_i = tractor_match['shapeexp_e1'] 
                #e2_i = tractor_match['shapeexp_e2']
            rhalf[seed_sel][i]=rhalf_i
            #e1[seed_sel][i]=e1_i
            #e2[seed_sel][i]=e2_i
    seed['rhalf'] = rhalf
    seed.write(os.environ['obiwan_out']+'/seed.fits',overwrite=True)

seed_matching()
