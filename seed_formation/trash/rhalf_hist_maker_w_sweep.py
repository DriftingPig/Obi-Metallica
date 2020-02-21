#collect all the rhalf in north dr8 sweep files
#COMP is ~0.5%, DUP is ~1e-5, so I dump them (I don't know how to model and they donnot seem important)
'''
collect rhalf info from all the dr8 sweep files
'''
import glob
import astropy.io.fits as fits
import numpy as np
import os

def elg_like_selection(dat,south=True):
    '''
    select desi ELG-like sample
    refer to: https://github.com/desihub/desitarget/blob/33d622d01110e75e8093d5f472d188cd83059261/py/desitarget/cuts.py#L362
    0.2 mag wider in every selection
    '''
    g = 22.5 - 2.5*np.log10(dat['flux_g'].clip(1e-16))
    r = 22.5 - 2.5*np.log10(dat['flux_r'].clip(1e-16))
    z = 22.5 - 2.5*np.log10(dat['flux_z'].clip(1e-16))
    elg = np.ones_like(g,dtype='?')
    elg &= g > 19.8                       # bright cut.
    elg &= r - z > 0.1                  # blue cut.
    elg &= r - z < 1.8                  # red cut.
    elg &= g - r < -1.2*(r - z) + 1.8   # OII flux cut.
    # ADM cuts that are unique to the north or south.
    if south:
        elg &= g < 23.7  # faint cut.
        # ADM south has the FDR cut to remove stars and low-z galaxies.
        elg &= g - r < 1.15*(r - z) + 0.05
    else:
        elg &= g < 23.8  # faint cut.
        elg &= g - r < 1.15*(r - z) - 0.15  # remove stars and low-z galaxies.
    return elg

def sub_param_generator(X):
    (fns,idx)=X
    topdir = '/global/project/projectdirs/cosmo/data/legacysurvey/dr8/south/sweep/8.0/'
    all_stuff = None
    N = len(fns)
    count=0
    for fn in fns:
        dat = fits.getdata(fn)
        #step1: get it masked
        l1 = len(dat)
        dat = dat[dat['MASKBITS']==0]
        l2 = len(dat)
        sel = elg_like_selection(dat)
        dat = dat[sel]
        l3 = len(dat)
        if l1*l2*l3==0:
            continue
        print('%d/%d %s %f sources remaining %f'%(count,N,os.path.basename(fn),l2/l1,l3/l2))
        EXP = (dat['type']=='EXP')
        REX = (dat['type']=='REX')
        PSF = (dat['type']=='PSF')
        DEV = (dat['type']=='DEV')
        sub_exp = np.vstack((np.repeat('EXP',EXP.sum()),dat[EXP]['SHAPEEXP_R'],dat[EXP]['SHAPEEXP_E1'],dat[EXP]['SHAPEEXP_E2']))
        sub_rex = np.vstack((np.repeat('REX',REX.sum()),dat[REX]['SHAPEEXP_R'],dat[REX]['SHAPEEXP_E1'],dat[REX]['SHAPEEXP_E2']))
        sub_psf = np.vstack((np.repeat('PSF',PSF.sum()),np.repeat(0.001,PSF.sum()),dat[PSF]['SHAPEEXP_E1'],dat[PSF]['SHAPEEXP_E2']))
        sub_dev = np.vstack((np.repeat('DEV',DEV.sum()),dat[DEV]['SHAPEDEV_R'],dat[DEV]['SHAPEDEV_E1'],dat[DEV]['SHAPEDEV_E2']))
        sub_all = np.hstack((sub_exp,sub_rex,sub_psf,sub_dev))
        np.savetxt('./param_subs/params_sub_%d_%d.txt'%(idx,count),sub_all.transpose(),fmt = '%s')
        count+=1
        del sub_all

def param_generatir():
    topdir = '/global/project/projectdirs/cosmo/data/legacysurvey/dr8/south/sweep/8.0/'
    fn_arrays = glob.glob(topdir+'*.fits')
    import multiprocessing as mp
    p = mp.Pool(10)
    fn_arrays = np.array_split(fn_arrays,10)
    params = []
    for i in range(10):
        params.append((fn_arrays[i],i))
    p.map(sub_param_generator,params)

#param_generatir()
def stack():
    fns = glob.glob('./param_subs/params*')
    dat = None
    count = 0
    N = len(fns)
    NN=0
    for fn in fns:
        print('%d/%d'%(count,N))
        sub_dat = np.loadtxt(fn,dtype=np.str)
        if dat is not None:
            dat = np.vstack((dat,sub_dat))
        else:
            dat = sub_dat
        count+=1
        if count%100==0:
            np.savetxt('./param_subs/all_dat%d.txt'%NN,dat,fmt='%s')
            NN+=1
            dat = None
    np.savetxt('./param_subs/all_dat%d.txt'%NN,dat,fmt='%s')

stack()

def stack_all():
    fns = glob.glob('./param_subs/all_dat*')
    dat = None
    for fn in fns:
        print(fn)
        sub_dat = np.loadtxt(fn,dtype=np.str)
    if dat is not None:
            dat = np.vstack((dat,sub_dat))
    else:
            dat = sub_dat
    np.savetxt('./param_subs/all_dat.txt',fmt='%s')

#stack_all()
