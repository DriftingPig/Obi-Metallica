'''
This is a little script for comparing DECaLS to Pan-STARRS magnitudes for
investigating zeropoint and other issues.
'''
if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Agg')
import pylab as plt
import numpy as np
import sys
import os

import scipy.ndimage
from scipy.stats import sigmaclip

from tractor.brightness import NanoMaggies
from astrometry.util.fits import fits_table, merge_tables
from astrometry.util.miscutils import *
from astrometry.util.plotutils import *

from legacyanalysis.ps1cat import *
from legacypipe.survey import *
from astrometry.libkd.spherematch import *
import photutils

def apphot_ps1stars(ccd, ps,
                    apertures,
                    survey,
                    sky_inner_r=40,
                    sky_outer_r=50):
    im = survey.get_image_object(ccd)

    tim = im.get_tractor_image(gaussPsf=True, splinesky=True)
    img = tim.getImage()

    wcs = tim.subwcs
    
    magrange = (15,21)
    ps1 = ps1cat(ccdwcs=wcs)
    ps1 = ps1.get_stars(magrange=magrange)
    print 'Got', len(ps1), 'PS1 stars'
    band = ccd.filter
    piband = ps1cat.ps1band[band]
    print 'band:', band

    ps1.cut(ps1.nmag_ok[:,piband] > 0)
    print 'Keeping', len(ps1), 'stars with nmag_ok'
    
    ok,x,y = wcs.radec2pixelxy(ps1.ra, ps1.dec)
    apxy = np.vstack((x - 1., y - 1.)).T

    ap = []
    aperr = []
    nmasked = []
    with np.errstate(divide='ignore'):
        ie = tim.getInvError()
        imsigma = 1. / ie
        imsigma[ie == 0] = 0
    mask = (imsigma == 0)
    for rad in apertures:
        aper = photutils.CircularAperture(apxy, rad)
        p = photutils.aperture_photometry(img, aper, error=imsigma, mask=mask)
        aperr.append(p.field('aperture_sum_err'))
        ap.append(p.field('aperture_sum'))
        p = photutils.aperture_photometry((ie == 0), aper)
        nmasked.append(p.field('aperture_sum'))
    ap = np.vstack(ap).T
    aperr = np.vstack(aperr).T
    nmasked = np.vstack(nmasked).T

    print 'Aperture fluxes:', ap[:5]
    print 'Aperture flux errors:', aperr[:5]
    print 'Nmasked:', nmasked[:5]
    
    H,W = img.shape
    sky = []
    skysigma = []
    skymed = []
    skynmasked = []
    for xi,yi in zip(x,y):
        ix = int(np.round(xi))
        iy = int(np.round(yi))
        skyR = sky_outer_r
        xlo = max(0, ix-skyR)
        xhi = min(W, ix+skyR+1)
        ylo = max(0, iy-skyR)
        yhi = min(H, iy+skyR+1)
        xx,yy = np.meshgrid(np.arange(xlo,xhi), np.arange(ylo,yhi))
        r2 = (xx - xi)**2 + (yy - yi)**2
        inannulus = ((r2 >= sky_inner_r**2) * (r2 < sky_outer_r**2))
        unmasked = (ie[ylo:yhi, xlo:xhi] > 0)
        
        #sky.append(np.median(img[ylo:yhi, xlo:xhi][inannulus * unmasked]))

        skypix = img[ylo:yhi, xlo:xhi][inannulus * unmasked]
        # this is the default value...
        nsigma = 4.
        goodpix,lo,hi = sigmaclip(skypix, low=nsigma, high=nsigma)
        # sigmaclip returns unclipped pixels, lo,hi, where lo,hi are
        # mean(goodpix) +- nsigma * sigma
        meansky = np.mean(goodpix)
        sky.append(meansky)
        skysigma.append((meansky - lo) / nsigma)
        skymed.append(np.median(skypix))
        skynmasked.append(np.sum(inannulus * np.logical_not(unmasked)))
    sky = np.array(sky)
    skysigma = np.array(skysigma)
    skymed = np.array(skymed)
    skynmasked = np.array(skynmasked)

    print 'sky', sky[:5]
    print 'median sky', skymed[:5]
    print 'sky sigma', skysigma[:5]

    psmag = ps1.median[:,piband]

    ap2 = ap - sky[:,np.newaxis] * (np.pi * apertures**2)[np.newaxis,:]
    
    if ps is not None:
        plt.clf()
        nstars,naps = ap.shape
        for iap in range(naps):
            plt.plot(psmag, ap[:,iap], 'b.')
        #for iap in range(naps):
        #    plt.plot(psmag, ap2[:,iap], 'r.')
        plt.yscale('symlog')
        plt.xlabel('PS1 %s mag' % band)
        plt.ylabel('DECam Aperture Flux')
    
        #plt.plot(psmag, nmasked[:,-1], 'ro')
        plt.plot(np.vstack((psmag,psmag)), np.vstack((np.zeros_like(psmag),nmasked[:,-1])), 'r-', alpha=0.5)
        plt.ylim(0, 1e3)
        ps.savefig()    
    
        plt.clf()
        plt.plot(ap.T / np.max(ap, axis=1), '.')
        plt.ylim(0, 1)
        ps.savefig()
    
        plt.clf()
        dimshow(tim.getImage(), **tim.ima)
        ax = plt.axis()
        plt.plot(x, y, 'o', mec='r', mfc='none', ms=10)
        plt.axis(ax)
        ps.savefig()

    color = ps1_to_decam(ps1.median, band)
    print 'Color terms:', color

    
    T = fits_table()
    T.apflux = ap.astype(np.float32)
    T.apfluxerr = aperr.astype(np.float32)
    T.apnmasked = nmasked.astype(np.int16)

    # Zero out the errors when pixels are masked
    T.apfluxerr[T.apnmasked > 0] = 0.

    #T.apflux2 = ap2.astype(np.float32)
    T.sky = sky.astype(np.float32)
    T.skysigma = skysigma.astype(np.float32)
    T.expnum = np.array([ccd.expnum] * len(T))
    T.ccdname = np.array([ccd.ccdname] * len(T)).astype('S3')
    T.band = np.array([band] * len(T))
    T.ps1_objid = ps1.obj_id
    T.ps1_mag = psmag + color
    T.ra  = ps1.ra
    T.dec = ps1.dec
    T.tai = np.array([tim.time.toMjd()] * len(T)).astype(np.float32)
    T.airmass = np.array([tim.primhdr['AIRMASS']] * len(T)).astype(np.float32)
    T.x = (x + tim.x0).astype(np.float32)
    T.y = (y + tim.y0).astype(np.float32)

    if False:
        plt.clf()
        plt.plot(skymed, sky, 'b.')
        plt.xlabel('sky median')
        plt.ylabel('sigma-clipped sky')
        ax = plt.axis()
        lo,hi = min(ax),max(ax)
        plt.plot([lo,hi],[lo,hi],'k-', alpha=0.25)
        plt.axis(ax)
        ps.savefig()
    
    return T, tim.primhdr
        
if __name__ == '__main__':

    survey = LegacySurveyData()
    ps = None
    pixscale = 0.262
    apertures = apertures_arcsec / pixscale

    #ps = PlotSequence('uber')
    if False:
        C = fits_table('coadd/000/0001p000/decals-0001p000-ccds.fits')
        for c in C:
            T,hdr = apphot_ps1stars(c, ps, apertures, survey)
            T.writeto('apphot-%08i-%s.fits' % (c.expnum, c.ccdname), header=hdr)
        sys.exit(0)
        
    C = survey.get_ccds_readonly()

    exps = [ 346352, 347460, 347721 ]

    for e in exps:
        print
        print
        print 'Exposure', e
        print
        E = C[C.expnum == e]
        TT = []
        for i,c in enumerate(E):
            print
            print 'Exposure', e, 'chip', i, 'of', len(E)
            print
            T,hdr = apphot_ps1stars(c, ps, apertures, survey)
            TT.append(T)
        T = merge_tables(TT)
        T.writeto('apphot-%08i.fits' % e, primheader=hdr)
