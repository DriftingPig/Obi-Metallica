'''
make seed from anand's truth table
'''
import astropy.io.fits as fits
import numpy as np
from astropy.table import Table
import os
fn_truth = os.environ['seed_truth']
truth = fits.getdata(fn_truth)
def ELG_cut(g,r,z,south=False):
    elg = np.ones_like(g,dtype='?')
    elg &= g > 20                       # bright cut.
    elg &= r - z > 0.3                  # blue cut.
    elg &= r - z < 1.6                  # red cut.
    elg &= g - r < -1.2*(r - z) + 1.6   # OII flux cut.
    # ADM cuts that are unique to the north or south.
    if south:
        elg &= g < 23.5  # faint cut.
    # ADM south has the FDR cut to remove stars and low-z galaxies.
        elg &= g - r < 1.15*(r - z) - 0.15
    else:
        elg &= g < 23.6  # faint cut.
        elg &= g - r < 1.15*(r - z) - 0.35  # remove stars and low-z galaxies.
    return elg
ttruth = Table(truth)
ttruth['iselg']=ELG_cut(ttruth['g'],ttruth['r'],ttruth['z'])
print('total source:%d total elg:%d ratio:%.4f'
      %(len(ttruth),ttruth['iselg'].sum(),ttruth['iselg'].sum()/len(ttruth)))

def ELG_like_cut(g,r,z,scale=0.2,south=False):
    elg = np.ones_like(g,dtype='?')
    elg &= g > 20-scale                       # bright cut.
    elg &= r - z > 0.3-scale                 # blue cut.
    elg &= r - z < 1.6+scale                  # red cut.
    elg &= g - r < -1.2*(r - z) + 1.6+scale   # OII flux cut.
    # ADM cuts that are unique to the north or south.
    if south:
        elg &= g < 23.5+scale  # faint cut.
    # ADM south has the FDR cut to remove stars and low-z galaxies.
        elg &= g - r < 1.15*(r - z) - 0.15 +scale
    else:
        elg &= g < 23.8  # faint cut.
        elg &= g - r < 1.15*(r - z) - 0.35 +scale  # remove stars and low-z galaxies.
    return elg


ttruth['iselglike']=ELG_like_cut(ttruth['g'],ttruth['r'],ttruth['z'],scale=0.3)
print('total source:%d total elg_like:%d ratio:%.4f'
      %(len(ttruth),ttruth['iselglike'].sum(),ttruth['iselglike'].sum()/len(ttruth)))
print('ratio of elg/elg_like:%.4f'
        %(ttruth['iselg'].sum()/ttruth['iselglike'].sum()))
ttruth_elg_like = ttruth[ttruth['iselglike']]
ttruth_elg_like.write(os.environ['obiwan_out']+'elg_like.fits',overwrite=True)


