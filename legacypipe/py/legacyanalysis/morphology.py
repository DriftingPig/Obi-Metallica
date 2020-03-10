from __future__ import print_function
import sys
import pylab as plt
import numpy as np
import os
from astrometry.util.plotutils import PlotSequence
from astrometry.util.util import Tan
from astrometry.libkd.spherematch import match_radec
from tractor.galaxy import *
from tractor import Tractor, Image, PixPos, Flux, PointSource, NullWCS, EllipseE, ConstantFitsWcs, LinearPhotoCal, RaDecPos, NanoMaggies
from tractor.psf import GaussianMixturePSF
from legacypipe.survey import SimpleGalaxy
from scipy.ndimage.filters import gaussian_filter

from legacypipe.oneblob import one_blob

'''
Investigate proposed change to our model selection cut of PSF/SIMP vs
EXP/DEV:

- for true EXP sources in the r_e vs S/N plane, what fraction of the
  time do we classify them as EXP / PSF / SIMP?  (As a function of
  seeing.)

- where do true EXP and PSF sources land in the DCHISQ(PSF) vs
  DCHISQ(EXP) plane?

'''

def scan_dchisq(seeing, target_dchisq, ps, e1=0.):
    pixscale = 0.262
    psfsigma = seeing / pixscale / 2.35
    print('PSF sigma:', psfsigma, 'pixels')
    psf = GaussianMixturePSF(1., 0., 0., psfsigma**2, psfsigma**2, 0.)

    sig1 = 0.01
    psfnorm = 1./(2. * np.sqrt(np.pi) * psfsigma)
    detsig1 = sig1 / psfnorm

    sz = 50
    cd = pixscale / 3600.
    wcs = Tan(0., 0., float(sz/2), float(sz/2), -cd, 0., 0., cd,
              float(sz), float(sz))
    band = 'r'

    tim = Image(data=np.zeros((sz,sz)), inverr=np.ones((sz,sz)) / sig1,
                psf=psf,
                wcs = ConstantFitsWcs(wcs),
                photocal = LinearPhotoCal(1., band=band))
    
    re_vals = np.logspace(-1., 0., 50)
    
    all_runs = []

    mods = []
    
    for i,re in enumerate(re_vals):
        true_src = ExpGalaxy(RaDecPos(0., 0.),
                             NanoMaggies(**{band: 1.}),
                             EllipseE(re, e1, 0.))
        print('True source:', true_src)
        tr = Tractor([tim], [true_src])
        tr.freezeParams('images')
        true_mod = tr.getModelImage(0)

        dchisq_none = np.sum((true_mod * tim.inverr)**2)
        scale = np.sqrt(target_dchisq / dchisq_none)

        true_src.brightness.setParams([scale])

        true_mod = tr.getModelImage(0)
        dchisq_none = np.sum((true_mod * tim.inverr)**2)

        mods.append(true_mod)
        
        tim.data = true_mod
        
        exp_src = true_src.copy()
        psf_src = PointSource(true_src.pos.copy(), true_src.brightness.copy())
        simp_src = SimpleGalaxy(true_src.pos.copy(), true_src.brightness.copy())

        dchisqs = []
        #for src in [psf_src, simp_src, exp_src]:
        for src in [psf_src, simp_src]:
            src.freezeParam('pos')
            #print('Fitting source:', src)
            #src.printThawedParams()
            tr.catalog[0] = src
            tr.optimize_loop()
            #print('Fitted:', src)
            mod = tr.getModelImage(0)
            dchisqs.append(dchisq_none - np.sum(((true_mod - mod) * tim.inverr)**2))
            #print('dchisq:', dchisqs[-1])
        dchisqs.append(dchisq_none)
        
        all_runs.append([re,] + dchisqs)

    all_runs = np.array(all_runs)

    re = all_runs[:,0]
    dchi_psf  = all_runs[:,1]
    dchi_simp = all_runs[:,2]
    dchi_exp  = all_runs[:,3]

    dchi_ps = np.maximum(dchi_psf, dchi_simp)
    dchi_cut1 = dchi_ps + 3+9
    dchi_cut2 = dchi_ps + dchi_psf * 0.02
    dchi_cut3 = dchi_ps + dchi_psf * 0.008
    
    plt.clf()
    plt.plot(re, dchi_psf, 'k-', label='PSF')
    plt.plot(re, dchi_simp, 'b-', label='SIMP')
    plt.plot(re, dchi_exp, 'r-', label='EXP')

    plt.plot(re, dchi_cut2, 'm--', alpha=0.5, lw=2, label='Cut: 2%')
    plt.plot(re, dchi_cut3, 'm:',  alpha=0.5, lw=2, label='Cut: 0.08%')
    plt.plot(re, dchi_cut1, 'm-',  alpha=0.5, lw=2, label='Cut: 12')

    plt.xlabel('True r_e (arcsec)')
    plt.ylabel('dchisq')
    #plt.legend(loc='lower left')
    plt.legend(loc='upper right')
    tt = 'Seeing = %g arcsec, S/N ~ %i' % (seeing, int(np.round(np.sqrt(target_dchisq))))
    if e1 != 0.:
        tt += ', Ellipticity %g' % e1
    plt.title(tt)
    plt.ylim(0.90 * target_dchisq, 1.05 * target_dchisq)

    # aspect = 1.2
    # ax = plt.axis()
    # dre  = (ax[1]-ax[0]) / 20 / aspect
    # dchi = (ax[3]-ax[2]) / 20
    # I = np.linspace(0, len(re_vals)-1, 8).astype(int)
    # for mod,re in [(mods[i], re_vals[i]) for i in I]:
    #     print('extent:', [re-dre, re+dre, ax[2], ax[2]+dchi])
    #     plt.imshow(mod, interpolation='nearest', origin='lower', aspect='auto',
    #                extent=[re-dre, re+dre, ax[2], ax[2]+dchi], cmap='gray')
    # plt.axis(ax)
        
    ps.savefig()


def stamps(T, I):
    NR,NC = 8,10
    for j,i in enumerate(I[:(NR*NC)]):
        fn = 'stamps/stamp-%.6f-%.6f.jpg' % (T.ra[i], T.dec[i])
        if not os.path.exists(fn):
            url = 'http://legacysurvey.org/viewer/jpeg-cutout/?ra=%.6f&dec=%.6f&layer=decals-dr3&size=100' % (T.ra[i], T.dec[i])
            cmd = 'wget -O %s "%s"' % (fn, url)
            print(cmd)
            os.system(cmd)
        img = plt.imread(fn)

        M = 20
        img = img[M:-M, M:-M, :]
        
        plt.subplot(NR, NC, j+1)
        plt.imshow(img, interpolation='nearest', origin='lower')
        plt.xticks([])
        plt.yticks([])

    
if __name__ == '__main__':
    ps = PlotSequence('morph')

    from glob import glob
    from astrometry.util.fits import merge_tables, fits_table

    HST = fits_table('acs-gc.fits')
    print(len(HST), 'ACS sources')
    HST.cut(HST.imaging == 'COSMOS ')
    print(len(HST), 'in COSMOS')
    HST.about()

    for dirnm in ['cosmos-50-rex', 'cosmos-51-rex', 'cosmos-52-rex']:
        fns = glob(os.path.join(dirnm, 'metrics', '*', 'all-models-*.fits'))
        T = merge_tables([fits_table(fn) for fn in fns])
        print(len(T), 'sources')
        T.about()
        #T.cut(T.primary)
        
        HI,HJ,d = match_radec(T.psf_ra, T.psf_dec, HST.raj2000, HST.dej2000,
                              1./3600.)
        print(len(HI), 'matched to HST')
        
        plt.clf()
        for t in ['PSF ', 'REX ', 'EXP ', 'DEV ']:
            K = np.flatnonzero(T.type[HI] == t)
            plt.plot(np.clip(T.rex_shapeexp_r[HI[K]], 1e-2, 1e2),
                     HST.s_g1[HJ[K]], '.', label=t,
                     alpha=0.1)
        plt.xlabel('REX radius (arcsec)')
        plt.ylabel('HST S/G')
        #plt.xscale('symlog')
        plt.xscale('log')
        plt.title(dirnm)
        plt.legend()
        ps.savefig()

        plt.clf()
        lo,hi = 0,1
        ha = dict(range=(lo,hi), bins=50, histtype='step')
        plt.subplot(2,1,1)
        for t in ['PSF ', 'REX ', 'EXP ', 'DEV ']:
            K = np.flatnonzero((T.type[HI] == t) * (HST.s_g1[HJ] < 0.5))
            plt.hist(np.clip(T.rex_shapeexp_r[HI[K]], lo, hi), label=t, **ha)
        plt.legend()
        plt.xlabel('REX radius (arcsec)')
        plt.title(dirnm + ': HST s_g1 < 0.5')
        plt.subplot(2,1,2)
        for t in ['PSF ', 'REX ', 'EXP ', 'DEV ']:
            K = np.flatnonzero((T.type[HI] == t) * (HST.s_g1[HJ] > 0.5))
            plt.hist(np.clip(T.rex_shapeexp_r[HI[K]], lo, hi), label=t, **ha)
        plt.legend()
        plt.xlabel('REX radius (arcsec)')
        plt.title(dirnm + ': HST s_g1 > 0.5')
        ps.savefig()


        plt.clf()
        #for t in ['PSF ', 'REX ', 'EXP ', 'DEV ']:
        #K = np.flatnonzero((HST.s_g1[HJ] > 0.5) * (T.type[HI] == t))

        K = np.flatnonzero((HST.s_g1[HJ] < 0.5))
        plt.plot(np.clip(T.rex_shapeexp_r[HI[K]], 1e-2, 1),
                 T.dchisq[HI[K],1] - T.dchisq[HI[K],0], 'r.', label='HST s_g1 < 0.5', alpha=0.25)

        K = np.flatnonzero((HST.s_g1[HJ] > 0.5))
        plt.plot(np.clip(T.rex_shapeexp_r[HI[K]], 1e-2, 1),
                 T.dchisq[HI[K],1] - T.dchisq[HI[K],0], 'b.', label='HST s_g1 > 0.5', alpha=0.25)

        plt.xlabel('REX radius (arcsec)')
        plt.ylabel('dchisq(REX - PSF)')
        plt.legend()
        plt.title(dirnm)
        plt.ylim(-5,15)
        plt.xscale('log')
        plt.xlim(0.98 * 1e-2, 1)
        ps.savefig()

        plt.clf()
        plt.scatter(np.clip(T.rex_shapeexp_r[HI], 1e-2, 1),
                    T.dchisq[HI,1] - T.dchisq[HI,0],
                    s=5, c=HST.s_g1[HJ], edgecolor='none')
        plt.xlabel('REX radius (arcsec)')
        plt.ylabel('dchisq(REX - PSF)')
        plt.legend()
        plt.title(dirnm + ': color = HST s_g1')
        plt.colorbar()
        plt.ylim(-5,15)
        plt.xscale('log')
        plt.xlim(0.98 * 1e-2, 1)
        ps.savefig()

        
    sys.exit(0)
        


    

    # From query of http://vizier.u-strasbg.fr/viz-bin/VizieR-3?-source=J/ApJS/200/9/acs-gc
    HST = fits_table('acs-gc.fits')
    print(len(HST), 'ACS sources')
    HST.cut(HST.imaging == 'COSMOS ')
    print(len(HST), 'in COSMOS')
    HST.about()
    
    # HST.class is all ""
    # HST.s_g2, HST.fwhm2 is all zero/nan
    # HST.s_g1 mostly 0, some 1, some in between.  star=1, gal=0
    # HST.fwhm1, re_s1,  does not correlate very well with s_g1

    for dirnm in ['cosmos-50', 'cosmos-51', 'cosmos-52']:
        fns = glob(os.path.join(dirnm, 'tractor', '*', 'tractor-*.fits'))
        T = merge_tables([fits_table(fn) for fn in fns])
        print(len(T), 'sources')

        # which sources have galaxy models computed
        dchiexp  = T.dchisq[:,3]
        I = np.flatnonzero(dchiexp)
        T.cut(I)
        print(len(T), 'have EXP models')

        dchipsf  = T.dchisq[:,0]
        dchisimp = T.dchisq[:,1]
        dchidev  = T.dchisq[:,2]
        dchiexp  = T.dchisq[:,3]
        #T.type0 = np.array([t[0] for t in T.type])

        x = np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp)
        y = x / dchipsf

        HI,HJ,d = match_radec(T.ra, T.dec, HST.raj2000, HST.dej2000, 1./3600.)
        print(len(HI), 'matched to HST')
        
        plt.clf()
        plt.scatter(x[HI], y[HI], c=HST.s_g1[HJ], edgecolors='none', s=10,
                    alpha=0.5)
        plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
        plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
        plt.title(dirnm + ' (color = HST star/gal)')
        plt.xscale('symlog')
        plt.axis([1e1, 1e7, 0, 0.04])
        plt.colorbar()

        xx = np.logspace(1, 7, 200)
        div = 0.001 + 1e-6 * xx
        plt.plot(xx, div, 'r--', lw=2)

        div2 = 0.003 + 1e-5 * xx
        plt.plot(xx, div2, 'r:', lw=2)
        
        ps.savefig()




        plt.clf()
        plt.scatter(x[HI], y[HI], c=HST.re_g1[HJ], edgecolors='none', s=10,
                    alpha=0.5, vmin=0, vmax=5)
        plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
        plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
        plt.title(dirnm + ' (color = HST re_g1)')
        plt.xscale('symlog')
        plt.axis([1e1, 1e7, 0, 0.04])
        plt.colorbar()
        xx = np.logspace(1, 7, 200)
        div = 0.001 + 1e-6 * xx
        plt.plot(xx, div, 'r--', lw=2)
        div2 = 0.003 + 1e-5 * xx
        plt.plot(xx, div2, 'r:', lw=2)
        ps.savefig()

        print('FWHM range:', HST.fwhm1[HJ].min(), HST.fwhm1[HJ].max())
        
        plt.clf()
        plt.scatter(x[HI], y[HI], c=HST.fwhm1[HJ], edgecolors='none', s=10,
                    alpha=0.5, vmin=0, vmax=10)
        plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
        plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
        plt.title(dirnm + ' (color = HST fwhm1)')
        plt.xscale('symlog')
        plt.axis([1e1, 1e7, 0, 0.04])
        plt.colorbar()
        xx = np.logspace(1, 7, 200)
        div = 0.001 + 1e-6 * xx
        plt.plot(xx, div, 'r--', lw=2)
        div2 = 0.003 + 1e-5 * xx
        plt.plot(xx, div2, 'r:', lw=2)
        ps.savefig()

        plt.clf()
        plt.scatter(x[HI], y[HI], c=HST.re_s1[HJ], edgecolors='none', s=10,
                    alpha=0.5, vmin=0, vmax=5)
        plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
        plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
        plt.title(dirnm + ' (color = HST re_s1)')
        plt.xscale('symlog')
        plt.axis([1e1, 1e7, 0, 0.04])
        plt.colorbar()
        xx = np.logspace(1, 7, 200)
        div = 0.001 + 1e-6 * xx
        plt.plot(xx, div, 'r--', lw=2)
        div2 = 0.003 + 1e-5 * xx
        plt.plot(xx, div2, 'r:', lw=2)
        ps.savefig()
        




        
    sys.exit(0)




    
    for dirnm in ['cosmos-50-rex', 'cosmos-51-rex', 'cosmos-52-rex']:
        fns = glob(os.path.join(dirnm, 'tractor', '*', 'tractor-*.fits'))
        T = merge_tables([fits_table(fn) for fn in fns])
        print(len(T), 'sources')

        print('PSF ', sum(T.type == 'PSF '))
        print('REX ', sum(T.type == 'REX '))
        print('EXP ', sum(T.type == 'EXP '))
        print('DEV ', sum(T.type == 'DEV '))
        print('COMP', sum(T.type == 'COMP'))

        plt.clf()
        R = np.flatnonzero(T.type == 'REX ')
        E = np.flatnonzero(T.type == 'EXP ')
        plt.hist(T.shapeexp_r[R], range=(0,2), bins=100, histtype='step', color='b', label='REX');
        plt.hist(T.shapeexp_r[E], range=(0,2), bins=100, histtype='step', color='r', label='EXP');
        plt.xlabel('Radius (arcsec)')
        plt.legend()
        plt.title(dirnm)
        plt.ylim(0, 2700)
        ps.savefig()

        I1 = np.flatnonzero((T.type == 'REX ') * (T.shapeexp_r < 0.1))
        I2 = np.flatnonzero((T.type == 'REX ') * (T.shapeexp_r > 0.3) *
                            (T.shapeexp_r < 0.5))
        I3 = np.flatnonzero(T.type == 'PSF ')
        I4 = np.flatnonzero((T.type == 'REX ') * (T.shapeexp_r > 0.1) *
                            (T.shapeexp_r < 0.3))
        I5 = np.flatnonzero(T.type == 'EXP ')
        
        print(len(I1), 'REX with r < 0.1')
        print(len(I2), 'REX with r between 0.3 and 0.5')
        print(len(I3), 'PSF')

        lab1 = 'REX r < 0.1'
        lab4 = 'REX r from 0.1 to 0.3'
        lab2 = 'REX r from 0.3 to 0.5'
        lab3 = 'PSF'
        lab5 = 'EXP'
        
        plt.clf()
        lo,hi = -10,10
        plt.hist(np.clip(T.dchisq[I1,1] - T.dchisq[I1,0], lo, hi), bins=100, range=(lo,hi), histtype='step', color='b', label=lab1)
        plt.hist(np.clip(T.dchisq[I4,1] - T.dchisq[I4,0], lo, hi), bins=100, range=(lo,hi), histtype='step', color='m', label=lab4)
        plt.hist(np.clip(T.dchisq[I2,1] - T.dchisq[I2,0], lo, hi), bins=100, range=(lo,hi), histtype='step', color='r', label=lab2)
        plt.hist(np.clip(T.dchisq[I3,1] - T.dchisq[I3,0], lo, hi), bins=100, range=(lo,hi), histtype='step', color='g', label=lab3)
        plt.xlabel('dchisq(REX - PSF)')
        plt.legend()
        plt.title(dirnm)
        plt.xlim(lo,hi)
        plt.ylim(0,4000)
        ps.savefig()

        T.rmag = -2.5 * (np.log10(T.decam_flux[:,2]) - 9.)
        
        plt.clf()
        lo,hi = 20,25
        plt.hist(np.clip(T.rmag[I1], lo, hi), bins=50, range=(lo,hi), histtype='step', color='b', label=lab1)
        #plt.hist(np.clip(T.rmag[I4], lo, hi), bins=50, range=(lo,hi), histtype='step', color='m', label=lab4)
        plt.hist(np.clip(T.rmag[I2], lo, hi), bins=50, range=(lo,hi), histtype='step', color='r', label=lab2)
        plt.hist(np.clip(T.rmag[I3], lo, hi), bins=50, range=(lo,hi), histtype='step', color='g', label=lab3)
        plt.xlabel('r mag')
        plt.legend()
        plt.title(dirnm)
        plt.xlim(lo,hi)
        ps.savefig()

        plt.clf()
        plt.plot(T.rmag[I1], T.dchisq[I1,1] - T.dchisq[I1,0], 'b.', alpha=0.2, label=lab1) 
        plt.plot(T.rmag[I4], T.dchisq[I4,1] - T.dchisq[I4,0], 'm.', alpha=0.2, label=lab4) 
        plt.plot(T.rmag[I2], T.dchisq[I2,1] - T.dchisq[I2,0], 'r.', alpha=0.2, label=lab2)
        plt.plot(T.rmag[I3], T.dchisq[I3,1] - T.dchisq[I3,0], 'g.', alpha=0.2, label=lab3)
        plt.plot(T.rmag[I5], T.dchisq[I5,1] - T.dchisq[I5,0], 'k.', alpha=0.2, label=lab5)
        plt.xlabel('r mag')
        plt.ylabel('dchisq(REX - PSF)')
        plt.legend()
        plt.title(dirnm)
        plt.ylim(-20, 60)
        plt.xlim(17, 27)
        ps.savefig()

        plt.clf()
        plt.plot(T.rmag[I1], T.shapeexp_r[I1], 'b.', alpha=0.2, label=lab1) 
        plt.plot(T.rmag[I4], T.shapeexp_r[I4], 'm.', alpha=0.2, label=lab4) 
        plt.plot(T.rmag[I2], T.shapeexp_r[I2], 'r.', alpha=0.2, label=lab2)
        #plt.plot(T.rmag[I3], T.shapeexp_r[I3], 'g.', alpha=0.2, label='PSF')
        plt.xlabel('r mag')
        plt.ylabel('radius (arcsec)')
        plt.legend()
        plt.title(dirnm)
        plt.ylim(0, 0.5)
        plt.xlim(17, 27)
        ps.savefig()

        plt.clf()
        plt.scatter(T.rmag, T.shapeexp_r, c=T.dchisq[:,1] - T.dchisq[:,0], s=5, edgecolor='none',
                    vmin=-4, vmax=10)
        plt.xlabel('r mag')
        plt.ylabel('radius (arcsec)')
        plt.colorbar()
        plt.title(dirnm + ': color: dchisq(REX - PSF)')
        plt.ylim(0, 0.5)
        plt.xlim(15, 27)
        ps.savefig()

        
        
    HST = fits_table('cosmos-acs-iphot-sub.fits')
    print(len(HST), 'ACS sources')

    for dirnm in ['cosmos-50', 'cosmos-51', 'cosmos-52']:
        fns = glob(os.path.join(dirnm, 'tractor', '*', 'tractor-*.fits'))
        T = merge_tables([fits_table(fn) for fn in fns])
        print(len(T), 'sources')

        # which sources have galaxy models computed
        dchiexp  = T.dchisq[:,3]
        I = np.flatnonzero(dchiexp)
        T.cut(I)
        print(len(T), 'have EXP models')

        dchipsf  = T.dchisq[:,0]
        dchisimp = T.dchisq[:,1]
        dchidev  = T.dchisq[:,2]
        dchiexp  = T.dchisq[:,3]

        x = np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp)
        y = x / dchipsf

        HI,HJ,d = match_radec(T.ra, T.dec, HST.ra, HST.dec, 1./3600.)
        print(len(HI), 'matched to HST')

        Kgal  = np.flatnonzero(HST.mu_class[HJ] == 1)
        Kstar = np.flatnonzero(HST.mu_class[HJ] == 2)

        Igal  = HI[Kgal]
        Istar = HI[Kstar]

        plt.clf()
        plt.plot(x[Igal],  y[Igal],  'bo', mec='none', mfc='b', ms=3, alpha=0.5)
        plt.plot(x[Istar], y[Istar], 'ro', mec='none', mfc='r', ms=3, alpha=0.5)
        plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
        plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
        plt.title(dirnm + ' (color = HST star/gal)')
        plt.xscale('symlog')
        plt.axis([1e1, 1e7, 0, 0.04])

        xx = np.logspace(1, 7, 200)
        div = 0.001 + 1e-6 * xx
        plt.plot(xx, div, 'r--', lw=2)

        div2 = 0.003 + 1e-5 * xx
        plt.plot(xx, div2, 'r:', lw=2)
        
        ps.savefig()
        
    sys.exit(0)

        
    
    if False:
        # glob doesn't understand {}
        #fns = glob('dr3/tractor/011/tractor-011?p0{02,05,07,10}.fits')
        fns = glob('dr3/tractor/011/tractor-011?p0*.fits')
        fns = [fn for fn in fns if fn[-7:-5] in ['02','05','07','10']]
        assert(len(fns) == 16)



    # wget "http://irsa.ipac.caltech.edu/data/COSMOS/tables/photometry/cosmos_acs_iphot_200709.tbl"
    # astrometry/bin/text2fits -S 124 -f jddddddddddddddddddddjddjjjjjjdddddddddddddddjdddddddsjdddjj -H "number mag_iso magerr_iso mag_isocor magerr_isocor mag_petro magerr_petro petro_radius mag_aper magerr_aper mag_auto magerr_auto mag_best magerr_best flux_auto fluxerr_auto kron_radius background threshold flux_max flux_radius isoarea_image x_image y_image xmin_image ymin_image xmax_image ymax_image xpeak_image ypeak_image alphapeak_j2000 deltapeak_j2000 a_image b_image ra dec theta_image mu_threshold mu_max isoarea_world x_world y_world a_world b_world theta_world flags fwhm_image fwhm_world cxx_image cyy_image cxy_image elongation class_star field mu_class x y z spt_ind cntr" cosmos_acs_iphot_200709.tbl cosmos-acs-iphot-200709.fits
    # fitscopy cosmos-acs-iphot-200709.fits"[col ra;dec;mu_class]" cosmos-acs-iphot-sub.fits


    for dirnm in ['cosmos-50', 'cosmos-51', 'cosmos-52']:
        fns = glob(os.path.join(dirnm, 'metrics', '*', '*', 'all-models-*.fits'))
        T = merge_tables([fits_table(fn) for fn in fns])
        print(len(T), 'sources')

        dchipsf  = T.dchisq[:,0]
        dchisimp = T.dchisq[:,1]
        dchidev  = T.dchisq[:,2]
        dchiexp  = T.dchisq[:,3]
        T.type0 = np.array([t[0] for t in T.type])
        # which sources have galaxy models computed
        I = np.flatnonzero(dchiexp)

        y = (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[I]/dchipsf[I]
        J = I[y < 0.001]
        K = I[y > 0.02]
        E = I[T.type0[I] == 'E']
        S = I[T.type0[I] == 'S']
        P = I[T.type0[I] == 'P']

        plt.clf()
        ha = dict(histtype='step', bins=100, range=(0,2))
        plt.hist(T.exp_shape_r[J], color='k', label='Frac < 0.001', **ha)
        plt.hist(T.exp_shape_r[K], color='g', label='Frac > 0.02',  **ha)
        plt.hist(T.exp_shape_r[E], color='r', label='EXP', **ha)
        plt.hist(T.exp_shape_r[S], color='m', label='SIMP', **ha)
        plt.hist(T.exp_shape_r[P], color='b', label='PSF', **ha)
        plt.xlabel('EXP radius')
        plt.legend()
        plt.title(dirnm)
        ps.savefig()

        
        
    for dirnm in ['cosmos-50', 'cosmos-51', 'cosmos-52']:
        fns = glob(os.path.join(dirnm, 'tractor', '*', 'tractor-*.fits'))
        
        T = merge_tables([fits_table(fn) for fn in fns])
        print(len(T), 'sources')
    
        dchipsf  = T.dchisq[:,0]
        dchisimp = T.dchisq[:,1]
        dchidev  = T.dchisq[:,2]
        dchiexp  = T.dchisq[:,3]

        T.type0 = np.array([t[0] for t in T.type])

        T.g = -2.5 * (np.log10(T.decam_flux[:,1]) - 9)
        T.r = -2.5 * (np.log10(T.decam_flux[:,2]) - 9)
        T.z = -2.5 * (np.log10(T.decam_flux[:,4]) - 9)

        from astrometry.util.plotutils import loghist
        
        model = np.array(['P' if p > s else 'S' for p,s in zip(dchipsf, dchisimp)])
        dchi = dchipsf * (model == 'P') + dchisimp * (model == 'S')
    
        # which sources have galaxy models computed
        I = np.flatnonzero(dchiexp)
        print(len(I), 'have EXP,DEV models')

        # plt.clf()
        # 
        # plt.plot(np.maximum(dchiexp, dchidev)[I] - np.maximum(dchipsf, dchisimp)[I],
        #          (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[I]/dchipsf[I],
        #          'k.', alpha=0.2)
        # 
        # # SATUR
        # J = I[np.flatnonzero(np.max(T.decam_anymask[I,:] == 2, axis=1))]
        # plt.plot(np.maximum(dchiexp, dchidev)[J] - np.maximum(dchipsf, dchisimp)[J],
        #          (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[J]/dchipsf[J],
        #          'rx', label='SAT')
        # 
        # plt.axhline(0.001, color='b', alpha=0.25)
        # plt.axhline(0.008, color='b', alpha=0.25)
        # plt.axhline(0.02 , color='b', alpha=0.25)
        # 
        # plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
        # plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
        # plt.legend()
        # 
        # plt.xscale('symlog')
        # 
        # plt.axis([1e1, 1e7, 0, 0.04])
        # plt.title(dirnm)
        # ps.savefig()


        plt.clf()

        ccmap = dict(P='b', S='m', E='r', D='c', C='k')
        for t in ['PSF','SIMP','EXP','DEV','COMP']:
            J = I[T.type0[I] == t[0]]
            plt.plot(np.maximum(dchiexp, dchidev)[J] - np.maximum(dchipsf, dchisimp)[J],
                     (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[J]/dchipsf[J],
                     '.', color=ccmap[t[0]], alpha=0.8, label=t)

        # SATUR
        J = I[np.flatnonzero(np.max(T.decam_anymask[I,:] == 2, axis=1))]
        plt.plot(np.maximum(dchiexp, dchidev)[J] - np.maximum(dchipsf, dchisimp)[J],
                 (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[J]/dchipsf[J],
                 'o', mec='k', mfc='none', label='Any SAT', alpha=0.2)

        xx = np.logspace(1, 7, 200)
        div = 0.001 + 1e-6 * xx

        plt.plot(xx, div, 'r--')
        
        plt.axhline(0.001, color='b', alpha=0.25)
        plt.axhline(0.008, color='b', alpha=0.25)
        plt.axhline(0.02 , color='b', alpha=0.25)
        plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
        plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
        plt.legend()
        plt.xscale('symlog')
        plt.axis([1e1, 1e7, 0, 0.04])
        plt.title(dirnm)
        ps.savefig()

        
        plt.clf()
        ax = [-2,5, -2,4]
        loghist(T.g - T.r, T.r - T.z, 200, range=((ax[0],ax[1]),(ax[2],ax[3])))
        plt.xlabel('g - r (mag)')
        plt.ylabel('r - z (mag)')
        plt.axis(ax)
        ps.savefig()

        plt.plot(T.g[J] - T.r[J], T.r[J] - T.z[J], 'g.', label='SAT')
        plt.legend()
        plt.axis(ax)
        ps.savefig()

        K = J[T.type0[J] != 'P']
        P = J[T.type0[J] == 'P']
        
        plt.clf()
        ax = [-2,5, -2,4]
        loghist(T.g - T.r, T.r - T.z, 200, range=((ax[0],ax[1]),(ax[2],ax[3])))
        plt.plot(T.g[K] - T.r[K], T.r[K] - T.z[K], 'g.', label='Non-PSF SAT')
        plt.xlabel('g - r (mag)')
        plt.ylabel('r - z (mag)')
        plt.axis(ax)
        plt.legend()
        ps.savefig()

        plt.clf()
        ax = [-2,5, -2,4]
        loghist(T.g - T.r, T.r - T.z, 200, range=((ax[0],ax[1]),(ax[2],ax[3])))
        plt.plot(T.g[P] - T.r[P], T.r[P] - T.z[P], 'g.', label='PSF SAT')
        plt.xlabel('g - r (mag)')
        plt.ylabel('r - z (mag)')
        plt.axis(ax)
        plt.legend()
        ps.savefig()

        
        
        
    sys.exit(0)

    galaxy_margin = 12.

    fcut1 = 0.02  * dchipsf
    fcut2 = 0.008 * dchipsf

    model1 = model.copy()
    model2 = model.copy()

    dchi1 = dchi.copy()
    dchi2 = dchi.copy()
    
    # Source we're going to convert to galaxy
    G = I[np.maximum(dchidev, dchiexp)[I] - dchi[I] >
          np.maximum(galaxy_margin, fcut1[I])]
    D = G[dchidev[G] > dchiexp[G]]
    model1[D] = 'D'
    dchi1 [D] = dchidev[D]
    E = G[dchiexp[G] >= dchidev[G]]
    model1[E] = 'E'
    dchi1 [E] = dchiexp[E]

    G = I[np.maximum(dchidev, dchiexp)[I] - dchi[I] >
          np.maximum(galaxy_margin, fcut2[I])]
    D = G[dchidev[G] > dchiexp[G]]
    model2[D] = 'D'
    dchi2 [D] = dchidev[D]
    E = G[dchiexp[G] >= dchidev[G]]
    model2[E] = 'E'
    dchi2 [E] = dchiexp[E]

    D = np.flatnonzero(model1 != model2)
    print(len(D), 'are classified differently')

    plt.clf()

    plt.plot(np.maximum(dchiexp, dchidev)[I] - np.maximum(dchipsf, dchisimp)[I],
             (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[I]/dchipsf[I],
             'k.', alpha=0.2)
             
    
    keys = ['P','S','D','E']
    for k1 in keys:
        J = D[model1[D] == k1]
        for k2 in keys:
            K = J[model2[J] == k2]
            print(len(K), 'switched from', k1, 'to', k2)

            if len(K) == 0:
                continue

            d1 = dict(P=dchipsf, S=dchisimp, D=dchidev, E=dchiexp)[k1][K]
            d2 = dict(P=dchipsf, S=dchisimp, D=dchidev, E=dchiexp)[k2][K]

            # For this change in cut, we switch only from P,S to D,E
            
            plt.plot(d2 - d1, (d2 - d1)/dchipsf[K], '.',
                     label='%s to %s' % (k1,k2))
    plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
    plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
    plt.legend()

    plt.xscale('symlog')

    plt.axis([1e1, 1e7, 0, 0.04])
    
    ps.savefig()


    plt.clf()

    plt.plot(np.maximum(dchiexp, dchidev)[I] - np.maximum(dchipsf, dchisimp)[I],
             (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[I]/dchipsf[I],
             'k.', alpha=0.2)

    #J = I[np.flatnonzero(np.max(T.decam_anymask[I,:], axis=1))]
    J = I[np.flatnonzero(np.max(T.decam_anymask[I,:] == 2, axis=1))]
    plt.plot(np.maximum(dchiexp, dchidev)[J] - np.maximum(dchipsf, dchisimp)[J],
             (np.maximum(dchiexp, dchidev) - np.maximum(dchipsf, dchisimp))[J]/dchipsf[J],
             'r.', alpha=0.8)
    plt.xlabel('dchi(EXP or DEV) - dchi(PSF or SIMP)')
    plt.ylabel('[ dchi(EXP or DEV) - dchi(PSF or SIMP) ] / dchipsf')
    plt.xscale('symlog')
    plt.axis([1e1, 1e7, 0, 0.04])
    ps.savefig()

    plt.clf()
    plt.plot(np.maximum(dchipsf, dchisimp)[I],
             np.maximum(dchiexp, dchidev)[I], 'k.', alpha=0.2)
    plt.plot(np.maximum(dchipsf, dchisimp)[J],
             np.maximum(dchiexp, dchidev)[J], 'r.')
    plt.xlabel('dchi(PSF or SIMP)')
    plt.ylabel('dchi(EXP or DEV)')
    plt.xscale('symlog')
    plt.yscale('symlog')
    plt.axis([1e1, 1e8, 1e1, 1e8])
    ps.savefig()
    
    
    d1 = np.maximum(dchipsf, dchisimp)
    d2 = np.maximum(dchiexp, dchidev)
    x = d2 - d1
    y = (d2 - d1) / dchipsf
    
    # Stars in right-hand locus
    I = np.flatnonzero((x > 3e4) * (y > 0.008) * (y < 0.02))
    T[I].writeto('locus.fits')

    plt.clf()
    plt.subplots_adjust(hspace=0, wspace=0)
    stamps(T, I)
    ps.savefig()
    
    T.g = -2.5 * (np.log10(T.decam_flux[:,1]) - 9)
    T.r = -2.5 * (np.log10(T.decam_flux[:,2]) - 9)
    T.z = -2.5 * (np.log10(T.decam_flux[:,4]) - 9)

    from astrometry.util.plotutils import loghist
    
    plt.clf()
    ax = [-2,5, -2,4]
    loghist(T.g - T.r, T.r - T.z, 200, range=((ax[0],ax[1]),(ax[2],ax[3])))
    plt.plot(T.g[I] - T.r[I], T.r[I] - T.z[I], 'go')
    plt.xlabel('g - r (mag)')
    plt.ylabel('r - z (mag)')
    plt.axis(ax)
    ps.savefig()
    
    # Pushing the cut even further down
    I = np.flatnonzero((x > 30) * (x < 1000) * (y > 0.002) * (y < 0.008))
    T[I].writeto('locus2.fits')

    plt.clf()
    stamps(T, I)
    ps.savefig()
    
    plt.clf()
    ax = [-2,5, -2,4]
    loghist(T.g - T.r, T.r - T.z, 200, range=((ax[0],ax[1]),(ax[2],ax[3])))
    plt.plot(T.g[I] - T.r[I], T.r[I] - T.z[I], 'go')
    plt.xlabel('g - r (mag)')
    plt.ylabel('r - z (mag)')
    plt.axis(ax)
    ps.savefig()

    # Bottom
    I = np.flatnonzero((x > 30) * (x < 1000) * (y < 0.001))
    T[I].writeto('locus3.fits')

    plt.clf()
    stamps(T, I)
    ps.savefig()
    
    plt.clf()
    ax = [-2,5, -2,4]
    loghist(T.g - T.r, T.r - T.z, 200, range=((ax[0],ax[1]),(ax[2],ax[3])))
    plt.plot(T.g[I] - T.r[I], T.r[I] - T.z[I], 'go')
    plt.xlabel('g - r (mag)')
    plt.ylabel('r - z (mag)')
    plt.axis(ax)
    ps.savefig()

    
    sys.exit(0)

    
    # Plots sent to the mailing list 2017-11-28
    dchisq = 1000.
    scan_dchisq(1.5, dchisq, ps)
    scan_dchisq(1.0, dchisq, ps)
    scan_dchisq(0.8, dchisq, ps)

    dchisq = 2500.
    scan_dchisq(1.0, dchisq, ps)
    dchisq = 10000.
    scan_dchisq(1.0, dchisq, ps)

    dchisq = 1000.
    scan_dchisq(1.0, dchisq, ps, e1=0.25)
    scan_dchisq(1.0, dchisq, ps, e1=0.5)
    
    sys.exit(0)
    
    seeing = 1.3

    pixscale = 0.262
    psfsigma = seeing / pixscale / 2.35
    print('PSF sigma:', psfsigma, 'pixels')
    psf = GaussianMixturePSF(1., 0., 0., psfsigma**2, psfsigma**2, 0.)

    sig1 = 0.01
    psfnorm = 1./(2. * np.sqrt(np.pi) * psfsigma)
    detsig1 = sig1 / psfnorm

    #sn_vals = np.linspace(8., 20., 5)
    #re_vals = np.logspace(-1., 0.5, 5)
    sn_vals = np.logspace(1.2, 2.5, 5)
    re_vals = np.logspace(-1., -0.5, 5)

    Nper = 10

    Nexp  = np.zeros((len(sn_vals), len(re_vals)), int)
    Nsimp = np.zeros_like(Nexp)
    Npsf  = np.zeros_like(Nexp)
    Nother= np.zeros_like(Nexp)

    np.random.seed(42)

    sz = 50
    cd = pixscale / 3600.
    wcs = Tan(0., 0., float(sz/2), float(sz/2), -cd, 0., 0., cd,
              float(sz), float(sz))
    band = 'r'

    #all_dchisqs = []

    all_runs = []

    tim = Image(data=np.zeros((sz,sz)), inverr=np.ones((sz,sz)) / sig1,
                psf=psf,
                wcs = ConstantFitsWcs(wcs),
                photocal = LinearPhotoCal(1., band=band))
    
    for i,sn in enumerate(sn_vals):
        for j,re in enumerate(re_vals):
            ## HACK -- this is the flux required for a PSF to be
            ## detected at target S/N... adjust for galaxy?
            flux = sn * detsig1
            # Create round EXP galaxy
            #PixPos(sz/2, sz/2),
            true_src = ExpGalaxy(RaDecPos(0., 0.),
                                 NanoMaggies(**{band: flux}),
                                 EllipseE(re, 0., 0.))
            
            tr = Tractor([tim], [true_src])
            tr.freezeParams('images')
            true_mod = tr.getModelImage(0)

            ima = dict(interpolation='nearest', origin='lower',
                       vmin=-2.*sig1, vmax=5.*sig1, cmap='hot')

            this_dchisqs = []
            flux_sns = []
            
            for k in range(Nper):
                noise = np.random.normal(scale=sig1, size=true_mod.shape)

                tim.data = true_mod + noise

                if k == 0 and False:
                    plt.clf()
                    plt.subplot(1,2,1)
                    plt.imshow(true_mod, **ima)
                    plt.subplot(1,2,2)
                    plt.imshow(tim.data, **ima)
                    plt.title('S/N %f, r_e %f' % (sn, re))
                    ps.savefig()
                
                ## run one_blob code?  Or shortcut?
                src = PointSource(RaDecPos(0., 0.),
                                  NanoMaggies(**{band: flux}))

                nblob,iblob,Isrcs = 0, 1, np.array([0])
                brickwcs = wcs
                bx0, by0, blobw, blobh = 0, 0, sz, sz
                blobmask = np.ones((sz,sz), bool)
                timargs = [(tim.data, tim.getInvError(), tim.wcs, tim.wcs.wcs,
                            tim.getPhotoCal(), tim.getSky(), tim.psf,
                            'tim', 0, sz, 0, sz, band, sig1,
                            tim.modelMinval, None)]
                srcs = [src]
                bands = band
                plots,psx = False, None
                simul_opt, use_ceres, hastycho = False, False, False
                
                X = (nblob, iblob, Isrcs, brickwcs, bx0, by0, blobw, blobh,
                     blobmask, timargs, srcs, bands, plots, psx, simul_opt,
                     use_ceres, hastycho)
                R = one_blob(X)
                #print('Got:', R)

                print('Sources:', R.sources)
                print('Dchisqs:', R.dchisqs)
                #R.about()
                psfflux_sn = 0.
                srctype = 'N'

                dchi_psf  = 0.
                dchi_simp = 0.
                dchi_exp  = 0.
                
                if len(R.sources) > 0:
                    assert(len(R.sources) == 1)
                    src = R.sources[0]
                    dchisq = R.dchisqs[0]
                    #print('srcs', src)
                    #print('ivs:', R.srcinvvars[0])

                    dchi_psf  = dchisq[0]
                    dchi_simp = dchisq[1]
                    dchi_exp  = dchisq[3]
                    
                    allmods = R.all_models[0]
                    allivs = R.all_model_ivs[0]
                    #print('All mods:', allmods)
                    psfmod = allmods['ptsrc']
                    psfflux = psfmod.getParams()[2]
                    psfiv = allivs['ptsrc'][2]
                    psfflux_sn = psfflux * np.sqrt(psfiv)
                    
                    # HACK...
                    
                    this_dchisqs.append(dchisq)
                    #flux_sns.append(
                    flux = src.getParams()[2]
                    fluxiv = R.srcinvvars[0][2]
                    flux_sns.append(flux * np.sqrt(fluxiv))
                    
                    if isinstance(src, PointSource):
                        Npsf[i, j] += 1
                        srctype = 'P'
                        # note, SimpleGalaxy is a subclass of ExpGalaxy
                    elif isinstance(src, SimpleGalaxy):
                        Nsimp[i, j] += 1
                        srctype = 'S'
                    elif isinstance(src, ExpGalaxy):
                        Nexp[i, j] += 1
                        srctype = 'E'
                    else:
                        Nother[i, j] += 1
                        print('Other:', src)
                        srctype = 'O'

                all_runs.append((srctype, sn, re, psfflux_sn,
                                 dchi_psf, dchi_simp, dchi_exp))
                        
            d = np.array(this_dchisqs)
            print('this_dchisqs shape', d.shape)
            if len(d) and False:
                plt.clf()
                plt.plot(d[:,0], d[:,1], 'b.')
                plt.xlabel('dchisq(PSF)')
                plt.ylabel('dchisq(SIMP)')
                ax = plt.axis()
                xx = np.array([0, 100000])
                plt.plot(xx, xx, 'b-', alpha=0.5)
                plt.axis(ax)
                plt.title('S/N %f, r_e %f' % (sn, re))
                ps.savefig()
    
                plt.clf()
                plt.plot(d[:,0], d[:,3], 'b.')
                plt.xlabel('dchisq(PSF)')
                plt.ylabel('dchisq(EXP)')
                ax = plt.axis()
                xx = np.array([0, 100000])
                fcut = 0.02
                plt.plot(xx, xx, 'b-', alpha=0.5)
                plt.plot(xx, xx + 3, 'r-', alpha=0.5)
                plt.plot(xx, (1. + fcut) * xx, 'r-', alpha=0.5)
                plt.axis(ax)
                plt.title('S/N %f, r_e %f' % (sn, re))
                ps.savefig()
            
            #all_dchisqs.append(this_dchisqs)
            print('Flux S/N values:', flux_sns)
            
    ima = dict(interpolation='nearest', origin='lower',
               extent=[np.log10(min(re_vals)), np.log10(max(re_vals)),
                       min(sn_vals), max(sn_vals),],
               aspect='auto', cmap='hot', vmin=0, vmax=Nper)

    types = np.array([a[0]  for a in all_runs])
    runs  = np.array([a[1:] for a in all_runs])

    re = runs[:,1]
    psfsn = runs[:,2]
    dchi_psf = runs[:,3]
    dchi_simp = runs[:,4]
    dchi_exp = runs[:,5]
    
    print('re:', re)
    
    plt.clf()
    syms = dict(N='s', P='.', S='o', E='x')
    for t in np.unique(types):
        I = np.flatnonzero(types == t)
        if len(I) == 0:
            continue
        plt.plot(re, psfsn, 'b.', marker=syms[t], label=t,
                 mec='b', mfc='none')
    plt.xlabel('r_e (arcsec)')
    plt.ylabel('PSF S/N')
    plt.legend()
    ps.savefig()

    plt.clf()
    plt.scatter(dchi_psf, dchi_simp, c=re, edgecolors='face')
    plt.colorbar()
    plt.xlabel('dchisq_psf')
    plt.ylabel('dchisq_simp')
    xx = np.array([0, 1000000])
    ax = plt.axis()
    plt.plot(xx, xx, 'k-', alpha=0.1)
    plt.axis(ax)
    plt.title('color: r_e')
    plt.xscale('symlog')
    plt.yscale('symlog')
    plt.axis([0,1e6,0,1e6])
    ps.savefig()    

    plt.clf()
    plt.scatter(dchi_psf, dchi_simp - dchi_psf, c=re, edgecolors='face')
    plt.colorbar()
    plt.xlabel('dchisq_psf')
    plt.ylabel('dchisq_simp - dchisq_psf')
    xx = np.array([0, 1000000])
    ax = plt.axis()
    plt.plot(xx, np.zeros_like(xx), 'k-', alpha=0.1)
    plt.axis(ax)
    plt.title('color: r_e')
    plt.xscale('symlog')
    plt.yscale('symlog')
    #plt.axis([1e1,1e6,0,1e6])
    plt.xlim(1e1, 1e6)
    ps.savefig()    

    plt.clf()
    plt.scatter(dchi_psf, dchi_exp - dchi_psf, c=re, edgecolors='face')
    plt.colorbar()
    plt.xlabel('dchisq_psf')
    plt.ylabel('dchisq_exp - dchisq_psf')
    xx = np.array([0, 1000000])
    ax = plt.axis()
    plt.plot(xx, np.zeros_like(xx), 'k-', alpha=0.1)
    plt.axis(ax)
    plt.title('color: r_e')
    plt.xscale('symlog')
    plt.yscale('symlog')
    #plt.axis([1e1,1e6,0,1e6])
    plt.xlim(1e1, 1e6)
    ps.savefig()    

    dchi_ps = np.maximum(dchi_psf, dchi_simp)
    
    plt.clf()
    plt.scatter(dchi_psf, dchi_exp - dchi_ps, c=re, edgecolors='face')
    plt.colorbar()
    plt.xlabel('dchisq_psf')
    plt.ylabel('dchisq_exp - max(dchisq_psf, dchisq_simp)')
    xx = np.array([0, 1000000])
    ax = plt.axis()
    plt.plot(xx, np.zeros_like(xx), 'k-', alpha=0.1)
    plt.axis(ax)
    plt.title('color: r_e')
    plt.xscale('symlog')
    plt.yscale('symlog')
    #plt.axis([1e1,1e6,0,1e6])
    plt.xlim(1e1, 1e6)
    ps.savefig()    

    xl,xh = plt.xlim()
    xx = np.logspace(np.log10(xl), np.log10(xh), 100)
    y1 = xx + 3
    y2 = xx * 1.02
    y3 = xx * 1.008
    plt.plot(xx, y1 - xx, 'r-', alpha=0.5)
    plt.plot(xx, y2 - xx, 'r--', alpha=0.5)
    plt.plot(xx, y3 - xx, 'r:', alpha=0.5)
    ps.savefig()    
    
    plt.clf()
    plt.imshow(Nexp, **ima)
    plt.colorbar()
    plt.xlabel('log_10 r_e (arcsec)')
    plt.ylabel('S/N (psf)')
    plt.title('Nexp')
    ps.savefig()

    plt.clf()
    plt.imshow(Nsimp, **ima)
    plt.colorbar()
    plt.xlabel('log_10 r_e (arcsec)')
    plt.ylabel('S/N (psf)')
    plt.title('Nsimp')
    ps.savefig()

    plt.clf()
    plt.imshow(Npsf, **ima)
    plt.colorbar()
    plt.xlabel('log_10 r_e (arcsec)')
    plt.ylabel('S/N (psf)')
    plt.title('Npsf')
    ps.savefig()
    
    plt.clf()
    plt.imshow(Nother, **ima)
    plt.colorbar()
    plt.xlabel('log_10 r_e (arcsec)')
    plt.ylabel('S/N (psf)')
    plt.title('Nother')
    ps.savefig()
