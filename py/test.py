import  tractor
import  galsim
import  fitsio
import  numpy                 as      np
import  pylab                 as      plt

from    legacypipe.survey     import  RexGalaxy, LogRadius
from    astrometry.util.util  import  Tan
from    tractor.sky           import  ConstantSky
from tractor import *
from tractor.galaxy import *

seed                  = 2134
rng                   = galsim.BaseDeviate(seed)

if __name__ == '__main__':
    ra, dec           = 40., 10.
    H, W              = 100, 100

    pixscale          = 0.262                                             # [arcsec / pixel], DECAM. 
    ps                = pixscale / 3600.

    ##  Mean sky count level per pixel in the CP-processed frames measured (with iterative rejection) for each CCD in the image section.                                                                                           
    decam_accds       = fitsio.FITS('/global/cscratch1/sd/mjwilson/BGS/SV-ASSIGN/ccds/ccds-annotated-decam-dr8.fits')
    sky_levels_pixel  = decam_accds[1]['ccdskycounts'][:]

    ##  Median per-pixel error standard deviation, in nanomaggies.
    sky_levels_sigs   = decam_accds[1]['sig1'][:]
    sky_level_sig     = float(sky_levels_sigs[0])
    sky_level_sig     = tractor.NanoMaggies(**{'g': sky_level_sig, 'r': 0.0,  'z': 0.0})
    
    psf_fwhm_pixels   = decam_accds[1]['fwhm'][:]
    psf_fwhm          = psf_fwhm_pixels[0] * pixscale                     # arcsecond.                                                                                                                                              
    
    exptimes          = decam_accds[1]['exptime'][:]
    exptime           = exptimes[0]                                       # seconds.                                                                                                                                                

    zpts              = decam_accds[1]['zpt'][:]
    zpt               = zpts[0]

    psf_thetas        = decam_accds[1]['psf_theta'][:]                    # PSF position angle [deg.]                                                                                                                               
    psf_theta         = psf_thetas[0]

    psf_ells          = decam_accds[1]['psf_ell'][:]
    psf_ell           = psf_ells[0]

    psf               = galsim.Gaussian(flux=1.0, fwhm=psf_fwhm)

    ##  http://galsim-developers.github.io/GalSim/_build/html/_modules/galsim/shear.html                                                                                                                                              
    psf               = psf.shear(galsim.Shear(q=1.-psf_ell, beta=psf_theta * galsim.degrees))
    psf               = psf.drawImage(scale=pixscale, nx=W+1, ny=H+1)
    
    ##  psf           = tractor.GaussianMixturePSF(1., 0., 0., v, v, 0.)
    psf               = tractor.psf.PixelizedPSF(psf.array)
    
    # sky_level_pixel = sky_level * pixel_scale**2                                                                                                                                                                                  
    sky_level_pixel   = float(sky_levels_pixel[0])                        # [counts / pixel]                                                                                                                                        

    gmag              = 23.0
    ##  gflux         = exptime * 10.**((zpt - gmag) / 2.5)               # [Total counts on the image].
    gflux             = 10**(-0.4*(gmag-22.5))                            # [Nanomaggies].  

    gre               = 0.40                                              # [arcsec].                    

    ##  https://github.com/dstndstn/tractor/blob/13d3239500c5af873935c81d079c928f4cdf0b1d/doc/galsim.rst                                                                                                                             
    ##  _gflux        = tractor.Fluxes(g=gflux, r=0.0, z=0.0)
    _gflux            = tractor.NanoMaggies(**{'g': gflux, 'r': 0.0,  'z': 0.0})

    src               = RexGalaxy(tractor.RaDecPos(ra, dec), _gflux, LogRadius(gre))

    wcs               = Tan(ra, dec, W/2.+0.5, H/2.+0.5, -ps, 0., 0., ps, float(W), float(H))
    wcs               = tractor.ConstantFitsWcs(wcs)

    tims = []

    for band in ['g', 'r', 'z']:
        #photocal = FluxesPhotoCal(band)
        ##  photcal    = tractor.LinearPhotoCal(1., band=band)
        photocal        = tractor.MagsPhotoCal(band, zpt)

        csky_level_sig = photocal.brightnessToCounts(sky_level_sig)
        
        ##  The rms of the noise in ADU.                                                                                                                                                                                               
        ##  noise      = galsim.PoissonNoise(rng, sky_level=sky_level_pixel)                                                                                                                                                             
        ##  Gaussian approximation for large N.                                                                                                                                                                                        
        ##  noise      = galsim.GaussianNoise(rng, sigma=sky_level_sig)                                                                                                                                                                  
        ##  Rendered in counts.                                                                                                                                                                                                        
        noise          = np.random.normal(loc=csky_level_sig, scale=np.sqrt(csky_level_sig), size=(H,W))
        
        tim            = tractor.Image(data=np.zeros((H,W),  np.float32),
                                       inverr=np.ones((H,W), np.float32),
                                       psf=psf,
                                       wcs=wcs,
                                       photocal=photocal)

        ##  _tr            = tractor.Tractor([tim], [src])
        ##  mod            = _tr.getModelImage(0)

        tim.data       = tim.data + noise.data ##  + mod.data
        tims.append(tim)

    cat                 = tractor.Catalog(src)
    import pdb;pdb.set_trace()    
    ##
    tr                 = tractor.Tractor(tims, cat)

    # Evaluate likelihood.
    lnp                = tr.getLogProb()
    print('Logprob:', lnp)

    for nm,val in zip(tr.getParamNames(), tr.getParams()):
        print('  ', nm, val)

    exit(0)
    
    mod               = tr.getModelImage(0)

    np.savetxt('output/rex_noiseless.txt', mod)

    # Reset the source params.
    src.brightness.setParams([1.])

    tr.freezeParam('images')

    ##
    print('Fitting:')
    tr.printThawedParams()
    tr.optimize_loop()

    ##
    print('Fit:', src)

    # Take several linearized least squares steps.
    for i in range(20):
        dlnp, X, alpha = tr.optimize()
        print('dlnp', dlnp)

        if dlnp < 1e-3:
            break

    # Plot optimized models.
    mods = [tractor.getModelImage(i) for i in range(len(tims))]
    plt.clf()
    for i,band in enumerate(bands):
        for e in range(nepochs):
            plt.subplot(nepochs, len(bands), e*len(bands) + i +1)
            plt.imshow(mods[nepochs*i + e], **ima)
            plt.xticks([]); plt.yticks([])
            plt.title('%s #%i' % (band, e+1))

    plt.suptitle('Optimized models')
    plt.savefig('opt.png')

    # Plot optimized models + noise:
    plt.clf()
    for i,band in enumerate(bands):
        for e in range(nepochs):
            plt.subplot(nepochs, len(bands), e*len(bands) + i +1)
            mod = mods[nepochs*i + e]
            plt.imshow(mod + pixnoise * np.random.normal(size=mod.shape), **ima)
            plt.xticks([]); plt.yticks([])
            plt.title('%s #%i' % (band, e+1))
            
    plt.suptitle('Optimized models + noise')
    plt.savefig('opt_noise. png')
