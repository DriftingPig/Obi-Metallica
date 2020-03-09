import astropy.io.fits as fits
import os
import numpy as np
def all_blob_test():
    #test bricks that have bright stars for checking if the updated halo subtraction is accurate enough (from Rongpu)
    bricklist = ["1316m002", "1313m002", "1505p315", "1503p305", "1587p317"]
    surveybrick = os.environ['obiwan_data']+'/survey-bricks.fits.gz'
    surveyB = fits.getdata(surveybrick)
    f = open(os.environ['obiwan_out']+"/radec.txt","w")
    for brick in bricklist:
        sel = (surveyB['BRICKNAME']==brick)
        assert(sel.sum()==1)
        ra1 = surveyB[sel]['RA1']
        ra2 = surveyB[sel]['RA2']
        dec1 = surveyB[sel]['DEC1']
        dec2 = surveyB[sel]['DEC2']
        #ra1 ra2 dec1 dec2 0.1 degree wider
        f.write("%f %f %f %f\n"%(ra1-0.1,ra2+0.1,dec1-0.1,dec2+0.1))
    f.close()

def SV_south_test():
    #radec boundries for SV_south,dr8
    f = open(os.environ['obiwan_out']+"/radec.txt","w")
    tile_topdir = os.environ['SV_tiles']
    tileids = np.arange(72000,72050)
    def fn(i):
        return tile_topdir+'tile-%06d.fits'%i
    for tileid in tileids:
        dat = fits.getdata(fn(tileid))
        ra1 = dat['TARGET_RA'].min()-0.1
        ra2 = dat['TARGET_RA'].max()+0.1
        dec1 = dat['TARGET_DEC'].min()-0.1
        dec2 = dat['TARGET_DEC'].max()+0.1
        f.write("%.2f %.2f %.2f %.2f\n"%(ra1,ra2,dec1,dec2))
    #two extras because they are at the edge, I need to split it in half
    radec={'ra1':0,'ra2':5,'dec1':-1.71,'dec2':1.72}
    f.write("%.2f %.2f %.2f %.2f\n"%(radec['ra1'],radec['ra2'],radec['dec1'],radec['dec2']))
    radec={'ra1':355,'ra2':360,'dec1':-1.71,'dec2':1.72}
    f.write("%.2f %.2f %.2f %.2f\n"%(radec['ra1'],radec['ra2'],radec['dec1'],radec['dec2']))
    f.close()

def cosmos_repeat():
    f = open(os.environ['obiwan_out']+"/radec.txt","w")
    f.write("%f %f %f %f\n"%(149,151,1.4,2.6))

cosmos_repeat()
