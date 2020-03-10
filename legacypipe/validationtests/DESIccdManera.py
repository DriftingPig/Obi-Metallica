#
import numpy as np
import healpy as hp
import astropy.io.fits as pyfits
from multiprocessing import Pool
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

from quicksipManera import *
import fitsio


### ------------ A couple of useful conversions -----------------------

def zeropointToScale(zp):
	return 10.**((zp - 22.5)/2.5)	

def nanomaggiesToMag(nm):
	return -2.5 * (log(nm,10.) - 9.)

def Magtonanomaggies(m):
	return 10.**(-m/2.5+9.)
	#-2.5 * (log(nm,10.) - 9.)

### ------------ SHARED CLASS: HARDCODED INPUTS GO HERE ------------------------
###    Please, add here your own harcoded values if any, so other may use them 

class mysample(object):
    """
    This class mantains the basic information of the sample
    to minimize hardcoded parameters in the test functions

    Everyone is meant to call mysample to obtain information like 
         - path to ccd-annotated files   : ccds
         - zero points                   : zp0
         - magnitude limits (recm)       : recm
         - photoz requirements           : phreq
         - extintion coefficient         : extc
         - extintion index               : be
         - mask var eqv. to blacklist_ok : maskname
         - predicted frac exposures      : FracExp   
    Current Inputs are: survey, DR, band, localdir) 
         survey: DECaLS, MZLS, BASS
         DR:     DR3, DR4
         band:   g,r,z
         localdir: output directory
    """                                  


    def __init__(self,survey,DR,band,localdir,verb):
        """ 
        Initialize image survey, data release, band, output path
        Calculate variables and paths
        """   
        self.survey = survey
        self.DR     = DR
        self.band   = band
        self.localdir = localdir 
        self.verbose =verb
        # Check bands
        if(self.band != 'g' and self.band !='r' and self.band!='z'): 
            raise RuntimeError("Band seems wrong options are 'g' 'r' 'z'")        
              
        # Check surveys
        if(self.survey !='DECaLS' and  self.survey !='BASS' and self.survey !='MZLS'):
            raise RuntimeError("Survey seems wrong options are 'DECAaLS' 'BASS' MZLS' ")

        # Annotated CCD paths  
        if(self.DR == 'DR3'):
            inputdir = '/global/project/projectdirs/cosmo/data/legacysurvey/dr3/'
            self.ccds =inputdir+'ccds-annotated-decals.fits.gz'
            self.catalog = 'DECaLS_DR3'
            if(self.survey != 'DECaLS'): raise RuntimeError("Survey name seems inconsistent")

        elif(self.DR == 'DR4'):
            inputdir = '/global/project/projectdirs/cosmo/data/legacysurvey/dr4/'
            if (band == 'g' or band == 'r'):
                #self.ccds = inputdir+'ccds-annotated-dr4-90prime.fits.gz'
                self.ccds = inputdir+'ccds-annotated-bass.fits.gz'
                self.catalog = 'BASS_DR4'
                if(self.survey != 'BASS'): raise RuntimeError("Survey name seems inconsistent")

            elif(band == 'z'):
                #self.ccds = inputdir+'ccds-annotated-dr4-mzls.fits.gz'
                self.ccds = inputdir+'ccds-annotated-mzls.fits.gz'
                self.catalog = 'MZLS_DR4'
                if(self.survey != 'MZLS'): raise RuntimeError("Survey name seems inconsistent")
            else: raise RuntimeError("Input sample band seems inconsisent")

        else: raise RuntimeError("Data Realease seems wrong") 


        # Predicted survey exposure fractions 
        if(self.survey =='DECaLS'):
             # DECALS final survey will be covered by 
             # 1, 2, 3, 4, and 5 exposures in the following fractions: 
             self.FracExp=[0.02,0.24,0.50,0.22,0.02]
        elif(self.survey == 'BASS'):
             # BASS coverage fractions for 1,2,3,4,5 exposures are:
             self.FracExp=[0.0014,0.0586,0.8124,0.1203,0.0054,0.0019]
        elif(self.survey == 'MZLS'):
             # For MzLS fill factors of 100% with a coverage of at least 1, 
             # 99.5% with a coverage of at least 2, and 85% with a coverage of 3.
             self.FracExp=[0.005,0.145,0.85,0,0]
        else:
             raise RuntimeError("Survey seems to have wrong options for fraction of exposures ")

        #Bands inputs
        if band == 'g':
            self.be = 1
            self.extc = 3.303  #/2.751
            self.zp0 = 25.08
            self.recm = 24.
            self.phreq = 0.01
        if band == 'r':
            self.be = 2
            self.extc = 2.285  #/2.751
            self.zp0 = 25.29
            self.recm = 23.4
            self.phreq = 0.01
        if band == 'z':
            self.be = 4
            self.extc = 1.263  #/2.751
            self.zp0 = 24.92
            self.recm = 22.5
            self.phreq = 0.02

# ------------------------------------------------------------------




# ------------------------------------------------------------------
# ------------ VALIDATION TESTS ------------------------------------
# ------------------------------------------------------------------
# Note: part of the name of the function should startw with number valXpX 

def val3p4c_depthfromIvar(sample):    
    """
       Requirement V3.4
       90% filled to g=24, r=23.4 and z=22.5 and 95% and 98% at 0.3/0.6 mag shallower.

       Produces extinction correction magnitude maps for visual inspection

       MARCM stable version, improved from AJR quick hack 
       This now included extinction from the exposures
       Uses quicksip subroutines from Boris, corrected 
       for a bug I found for BASS and MzLS ccd orientation
    """
    nside = 1024       # Resolution of output maps
    nsidesout = None   # if you want full sky degraded maps to be written
    ratiores = 1       # Superresolution/oversampling ratio, simp mode doesn't allow anything other than 1
    mode = 1           # 1: fully sequential, 2: parallel then sequential, 3: fully parallel
    pixoffset = 0      # How many pixels are being removed on the edge of each CCD? 15 for DES.
    oversamp='1'       # ratiores in string format
    nsideSTR='1024'    # same as nside but in string format
    
    band = sample.band
    catalogue_name = sample.catalog
    fname = sample.ccds    
    localdir = sample.localdir
    outroot = localdir
    extc = sample.extc

    #Read ccd file 
    tbdata = pyfits.open(fname)[1].data
    
    # ------------------------------------------------------
    # Obtain indices
    auxstr='band_'+band
    sample_names = [auxstr]
    if(sample.DR == 'DR3'):
        inds = np.where((tbdata['filter'] == band) & (tbdata['photometric'] == True) & (tbdata['blacklist_ok'] == True)) 
    elif(sample.DR == 'DR4'):
        inds = np.where((tbdata['filter'] == band) & (tbdata['photometric'] == True) & (tbdata['bitmask'] == 0)) 

    #Read data 
    #obtain invnoisesq here, including extinction 
    nmag = Magtonanomaggies(tbdata['galdepth']-extc*tbdata['EBV'])/5.
    ivar= 1./nmag**2.

    # What properties do you want mapped?
    # Each each tuple has [(quantity to be projected, weighting scheme, operation),(etc..)] 
    propertiesandoperations = [ ('ivar', '', 'total'), ]

 
    # What properties to keep when reading the images? 
    # Should at least contain propertiesandoperations and the image corners.
    # MARCM - actually no need for ra dec image corners.   
    # Only needs ra0 ra1 ra2 ra3 dec0 dec1 dec2 dec3 only if fast track appropriate quicksip subroutines were implemented 
    propertiesToKeep = [ 'filter', 'AIRMASS', 'FWHM','mjd_obs'] \
    	+ ['RA', 'DEC', 'crval1', 'crval2', 'crpix1', 'crpix2', 'cd1_1', 'cd1_2', 'cd2_1', 'cd2_2','width','height']
    
    # Create big table with all relevant properties. 

    tbdata = np.core.records.fromarrays([tbdata[prop] for prop in propertiesToKeep] + [ivar], names = propertiesToKeep + [ 'ivar'])
    
    # Read the table, create Healtree, project it into healpix maps, and write these maps.
    # Done with Quicksip library, note it has quite a few hardcoded values (use new version by MARCM for BASS and MzLS) 
    # project_and_write_maps_simp(mode, propertiesandoperations, tbdata, catalogue_name, outroot, sample_names, inds, nside)
    project_and_write_maps(mode, propertiesandoperations, tbdata, catalogue_name, outroot, sample_names, inds, nside, ratiores, pixoffset, nsidesout)
 
    # Read Haelpix maps from quicksip  
    prop='ivar'
    op='total'
    vmin=21.0
    vmax=24.0

    fname2=localdir+catalogue_name+'/nside'+nsideSTR+'_oversamp'+oversamp+'/'+\
           catalogue_name+'_band_'+band+'_nside'+nsideSTR+'_oversamp'+oversamp+'_'+prop+'__'+op+'.fits.gz'
    f = fitsio.read(fname2)

    # HEALPIX DEPTH MAPS 
    # convert ivar to depth 
    import healpy as hp
    from healpix import pix2ang_ring,thphi2radec

    ral = []
    decl = []
    val = f['SIGNAL']
    pix = f['PIXEL']
	
    # Obtain values to plot 
    if (prop == 'ivar'):
        myval = []
        mylabel='depth' 
            
        below=0 
        for i in range(0,len(val)):
            depth=nanomaggiesToMag(sqrt(1./val[i]) * 5.)
            if(depth < vmin):
                 below=below+1
            else:
                myval.append(depth)
                th,phi = hp.pix2ang(int(nside),pix[i])
	        ra,dec = thphi2radec(th,phi)
	        ral.append(ra)
	        decl.append(dec)

    npix=len(f)

    print 'Area is ', npix/(float(nside)**2.*12)*360*360./pi, ' sq. deg.'
    print  below, 'of ', npix, ' pixels are not plotted as their ', mylabel,' < ', vmin
    print 'Within the plot, min ', mylabel, '= ', min(myval), ' and max ', mylabel, ' = ', max(myval)


    # Plot depth 
    from matplotlib import pyplot as plt
    import matplotlib.cm as cm

    map = plt.scatter(ral,decl,c=myval, cmap=cm.rainbow,s=2., vmin=vmin, vmax=vmax, lw=0,edgecolors='none')
    cbar = plt.colorbar(map)
    plt.xlabel('r.a. (degrees)')
    plt.ylabel('declination (degrees)')
    plt.title('Map of '+ mylabel +' for '+catalogue_name+' '+band+'-band')
    plt.xlim(0,360)
    plt.ylim(-30,90)
    mapfile=localdir+mylabel+'_'+band+'_'+catalogue_name+str(nside)+'.png'
    print 'saving plot to ', mapfile
    plt.savefig(mapfile)
    plt.close()
    #plt.show()
    #cbar.set_label(r'5$\sigma$ galaxy depth', rotation=270,labelpad=1)
    #plt.xscale('log')

    return mapfile 

def val3p4b_maghist_pred(sample,ndraw=1e5, nbin=100, vmin=21.0, vmax=25.0):    
    """
       Requirement V3.4
       90% filled to g=24, r=23.4 and z=22.5 and 95% and 98% at 0.3/0.6 mag shallower.

       MARCM 
       Makes histogram of predicted magnitudes 
       by MonteCarlo from exposures converving fraction of number of exposures
       This produces the histogram for Dustin's processed galaxy depth
    """


    import fitsio
    from matplotlib import pyplot as plt
    from numpy import zeros,array
    from random import random

    # Check fraction of number of exposures adds to 1. 
    if( abs(sum(sample.FracExp) - 1.0) > 1e-5 ):
       raise ValueError("Fration of number of exposures don't add to one")

    # Survey inputs
    rel = sample.DR
    catalogue_name = sample.catalog
    band = sample.band
    be = sample.be
    zp0 = sample.zp0
    recm = sample.recm
    verbose = sample.verbose
		
    f = fitsio.read(sample.ccds)
    
    #read in magnitudes including extinction
    counts2014 = 0
    counts20 = 0
    nl = []
    for i in range(0,len(f)):
        year = int(f[i]['date_obs'].split('-')[0])
        if (year <= 2014): counts2014 = counts2014 + 1
        if f[i]['dec'] < -20 : counts20 = counts20 + 1
			

        if(sample.DR == 'DR3'): 

            if f[i]['filter'] == sample.band and f[i]['photometric'] == True and f[i]['blacklist_ok'] == True :   

                magext = f[i]['galdepth'] - f[i]['decam_extinction'][be]
                nmag = Magtonanomaggies(magext)/5. #total noise
                nl.append(nmag)


        if(sample.DR == 'DR4'): 
             if f[i]['filter'] == sample.band and f[i]['photometric'] == True and f[i]['bitmask'] == 0 :   

                 magext = f[i]['galdepth'] - f[i]['decam_extinction'][be]
                 nmag = Magtonanomaggies(magext)/5. #total noise
                 nl.append(nmag)


    ng = len(nl)
    print "-----------"
    if(verbose) : print "Number of objects = ", len(f)
    if(verbose) : print "Counts before or during 2014 = ", counts2014
    if(verbose) : print "Counts with dec < -20 = ", counts20
    print "Number of objects in the sample = ", ng 

    #Monte Carlo to predict magnitudes histogram 
    ndrawn = 0
    nbr = 0	
    NTl = []
    n = 0
    for indx, f in enumerate(sample.FracExp,1) : 
        Nexp = indx # indx starts at 1 bc argument on enumearate :-), thus is the number of exposures
        nd = int(round(ndraw * f))
        ndrawn=ndrawn+nd

        for i in range(0,nd):

            detsigtoti = 0
            for j in range(0,Nexp):
		ind = int(random()*ng)
		detsig1 = nl[ind]
		detsigtoti += 1./detsig1**2.

 	    detsigtot = sqrt(1./detsigtoti)
	    m = nanomaggiesToMag(detsigtot * 5.)
	    if m > recm: # pass requirement
	 	nbr += 1.	
	    NTl.append(m)
	    n += 1.
	
    # Run some statistics 
    NTl=np.array(NTl)
    mean = sum(NTl)/float(len(NTl))
    std = sqrt(sum(NTl**2.)/float(len(NTl))-mean**2.)

    NTl.sort()
    if len(NTl)/2. != len(NTl)/2:
        med = NTl[len(NTl)/2+1]
    else:
        med = (NTl[len(NTl)/2+1]+NTl[len(NTl)/2])/2.

    print "Total images drawn with either 1,2,3,4,5 exposures", ndrawn
    print "Mean = ", mean, "; Median = ", med ,"; Std = ", std
    print 'percentage better than requirements = '+str(nbr/float(ndrawn))

    # Prepare historgram 
    minN = max(min(NTl),vmin)
    maxN = max(NTl)+.0001
    hl = zeros((nbin)) # histogram counts
    lowcounts=0
    for i in range(0,len(NTl)):
        bin = int(nbin*(NTl[i]-minN)/(maxN-minN))
        if(bin >= 0) : 
            hl[bin] += 1
        else:
            lowcounts +=1

    Nl = []  # x bin centers
    for i in range(0,len(hl)):
        Nl.append(minN+i*(maxN-minN)/float(nbin)+0.5*(maxN-minN)/float(nbin))
    NTl = array(NTl)

    print "min,max depth = ",min(NTl), max(NTl) 
    print "counts below ", minN, " = ", lowcounts


    #### Ploting histogram 
    fname=sample.localdir+'validationplots/'+sample.catalog+sample.band+'_pred_exposures.png'
    print "saving histogram plot in", fname 

       #--- pdf version --- 
       #from matplotlib.backends.backend_pdf import PdfPages
       #pp = PdfPages(fname)	

    plt.clf()
    plt.plot(Nl,hl,'k-')
    plt.xlabel(r'5$\sigma$ '+sample.band+ ' depth')
    plt.ylabel('# of images')
    plt.title('MC combined exposure depth '+str(mean)[:5]+r'$\pm$'+str(std)[:4]+r', $f_{\rm pass}=$'+str(nbr/float(ndrawn))[:5]+'\n '+catalogue_name)
    #plt.xscale('log')     # --- pdf --- 
    plt.savefig(fname)       #pp.savefig()
    plt.close              #pp.close()
    return fname 


# -------------------------------------------------------------------
# -------------------------------------------------------------------
#         OLD STUFF 
# -------------------------------------------------------------------
dir = '$HOME/' # obviously needs to be changed
#inputdir = '/project/projectdirs/cosmo/data/legacysurvey/dr3/' # where I get my data 
inputdir= '/global/projecta/projectdirs/cosmo/work/dr4/'
localdir = '/global/homes/m/manera/DESI/validation-outputs/' #place for local DESI stuff

#extmap = np.loadtxt('/global/homes/m/manera/DESI/validation-outputs/healSFD_r_256_fullsky.dat') # extintion map remove it 



### Plotting facilities



def plotPhotometryMap(band,vmin=0.0,vmax=1.0,mjdmax='',prop='zptvar',op='min',rel='DR0',survey='surveyname',nside='1024',oversamp='1'):
        import fitsio
        from matplotlib import pyplot as plt
        import matplotlib.cm as cm
        from numpy import zeros,array
        import healpix

        from healpix import pix2ang_ring,thphi2radec
        import healpy as hp

        # Survey inputs
        mjdw=mjdmax
        if rel == 'DR2':
            fname =inputdir+'decals-ccds-annotated.fits'
            catalogue_name = 'DECaLS_DR2'+mjdw

        if rel == 'DR3':
            inputdir = '/project/projectdirs/cosmo/data/legacysurvey/dr3/' # where I get my data 
            fname =inputdir+'ccds-annotated-decals.fits.gz'
            catalogue_name = 'DECaLS_DR3'+mjdw

        if rel == 'DR4':
            inputdir= '/global/projecta/projectdirs/cosmo/work/dr4/'
            if (band == 'g' or band == 'r'):
                fname=inputdir+'ccds-annotated-dr4-90prime.fits.gz'
                catalogue_name = '90prime_DR4'+mjdw
            if band == 'z' :
                fname = inputdir+'ccds-annotated-dr4-mzls.fits.gz' 
                catalogue_name = 'MZLS_DR4'+mjdw



	
        fname=localdir+catalogue_name+'/nside'+nside+'_oversamp'+oversamp+'/'+catalogue_name+'_band_'+band+'_nside'+nside+'_oversamp'+oversamp+'_'+prop+'__'+op+'.fits.gz'
        f = fitsio.read(fname)

        ral = []
        decl = []
        val = f['SIGNAL']
        pix = f['PIXEL']

        # -------------- plot of values ------------------
        if( prop=='zptvar' and opt == 'min' ):

            print 'Plotting min zpt rms'
            myval = []
	    for i in range(0,len(val)):
             
                myval.append(1.086 * np.sqrt(val[i])) #1.086 converts dm into d(flux) 
                th,phi = hp.pix2ang(int(nside),pix[i])
	        ra,dec = thphi2radec(th,phi)
	        ral.append(ra)
	        decl.append(dec)
      
            mylabel = 'min-zpt-rms-flux'
            vmin = 0.0 #min(myval)
            vmax = 0.03 #max(myval) 
            npix = len(myval)
            below = 0
            print 'Min and Max values of ', mylabel, ' values is ', min(myval), max(myval)
            print 'Number of pixels is ', npix
            print 'Number of pixels offplot with ', mylabel,' < ', vmin, ' is', below
            print 'Area is ', npix/(float(nside)**2.*12)*360*360./pi, ' sq. deg.'


            map = plt.scatter(ral,decl,c=myval, cmap=cm.rainbow,s=2., vmin=vmin, vmax=vmax, lw=0,edgecolors='none')
            cbar = plt.colorbar(map)
            plt.xlabel('r.a. (degrees)')
            plt.ylabel('declination (degrees)')
            plt.title('Map of '+ mylabel +' for '+catalogue_name+' '+band+'-band')
            plt.xlim(0,360)
            plt.ylim(-30,90)
            plt.savefig(localdir+mylabel+'_'+band+'_'+catalogue_name+str(nside)+'.png')
            plt.close()


        # -------------- plot of status in udgrade maps of 1.406 deg pix size  ------------------

        #Bands inputs
        if band == 'g':
            phreq = 0.01
        if band == 'r':
            phreq = 0.01
        if band == 'z':
            phreq = 0.02

        # Obtain values to plot
        if( prop=='zptvar' and opt == 'min' ):

            nside2 = 64  # 1.40625 deg per pixel
            npix2 = hp.nside2npix(nside2)
            myreq = np.zeros(npix2)  # 0 off footprint, 1 at least one pass requirement, -1 none pass requirement
            ral = np.zeros(npix2)
            decl = np.zeros(npix2)
            mylabel = 'photometric-pixels'
            print 'Plotting photometric requirement'


            for i in range(0,len(val)):
                th,phi = hp.pix2ang(int(nside),pix[i])
                ipix = hp.ang2pix(nside2,th,phi)
                dF= 1.086 * (sqrt(val[i]))   # 1.086 converts d(magnitudes) into d(flux)

                if(dF < phreq):
                     myreq[ipix]=1
                else:
                     if(myreq[ipix] == 0): myreq[ipix]=-1

            for i in range(0,len(myreq)):
                th,phi = hp.pix2ang(int(nside2),pix[i])
	        ra,dec = thphi2radec(th,phi)
	        ral[i] = ra
	        decl[i] = dec

            #myval = np.zeros(npix2)
            #mycount = np.zeros(pix2)
            #myval[ipix] += dF
            #mycount[ipix] += 1.
           
            below=sum( x for x in myreq if x < phreq) 
            
            print 'Number of pixels offplot with ', mylabel,' < ', phreq, ' is', below

            vmin = min(myreq)
            vmax = max(myreq) 
            map = plt.scatter(ral,decl,c=myreq, cmap=cm.rainbow,s=5., vmin=vmin, vmax=vmax, lw=0,edgecolors='none')
            cbar = plt.colorbar(map)
            plt.xlabel('r.a. (degrees)')
            plt.ylabel('declination (degrees)')
            plt.title('Map of '+ mylabel +' for '+catalogue_name+' '+band+'-band')
            plt.xlim(0,360)
            plt.ylim(-30,90)
            plt.savefig(localdir+mylabel+'_'+band+'_'+catalogue_name+str(nside)+'.png')
            plt.close()
            #plt.show()
            #cbar.set_label(r'5$\sigma$ galaxy depth', rotation=270,labelpad=1)
            #plt.xscale('log')

        return True

		
def plotPropertyMap(band,vmin=21.0,vmax=24.0,mjdmax='',prop='ivar',op='total',survey='surveyname',nside='1024',oversamp='1'):
	import fitsio
	from matplotlib import pyplot as plt
	import matplotlib.cm as cm
	from numpy import zeros,array
	import healpix
	
	from healpix import pix2ang_ring,thphi2radec
	import healpy as hp

        fname=localdir+survey+mjdmax+'/nside'+nside+'_oversamp'+oversamp+'/'+survey+mjdmax+'_band_'+band+'_nside'+nside+'_oversamp'+oversamp+'_'+prop+'__'+op+'.fits.gz'
        f = fitsio.read(fname)

	ral = []
	decl = []
	val = f['SIGNAL']
        pix = f['PIXEL']
	
        # Obtain values to plot 
        if (prop == 'ivar'):
	    myval = []
            mylabel='depth' 
            print 'Converting ivar to depth.'
            print 'Plotting depth'
            
            below=0 
            for i in range(0,len(val)):
                depth=nanomaggiesToMag(sqrt(1./val[i]) * 5.)
                if(depth < vmin):
                     below=below+1
                else:
                    myval.append(depth)
                    th,phi = hp.pix2ang(int(nside),pix[i])
	            ra,dec = thphi2radec(th,phi)
	            ral.append(ra)
	            decl.append(dec)

        npix=len(f)
        print 'Min and Max values of ', mylabel, ' values is ', min(myval), max(myval)
        print 'Number of pixels is ', npix
        print 'Number of pixels offplot with ', mylabel,' < ', vmin, ' is', below 
        print 'Area is ', npix/(float(nside)**2.*12)*360*360./pi, ' sq. deg.'


	map = plt.scatter(ral,decl,c=myval, cmap=cm.rainbow,s=2., vmin=vmin, vmax=vmax, lw=0,edgecolors='none')
	cbar = plt.colorbar(map)
	plt.xlabel('r.a. (degrees)')
	plt.ylabel('declination (degrees)')
	plt.title('Map of '+ mylabel +' for '+survey+' '+band+'-band')
	plt.xlim(0,360)
	plt.ylim(-30,90)
	plt.savefig(localdir+mylabel+'_'+band+'_'+survey+str(nside)+'.png')
        plt.close()
	#plt.show()
	#cbar.set_label(r'5$\sigma$ galaxy depth', rotation=270,labelpad=1)
    	#plt.xscale('log')
	return True
		

def depthfromIvar(band,rel='DR3',survey='survename'):
    
    # ------------------------------------------------------
    # MARCM stable version, improved from AJR quick hack 
    # This now included extinction from the exposures
    # Uses quicksip subroutines from Boris 
    # (with a bug I corrected for BASS and MzLS ccd orientation) 
    # Produces depth maps from Dustin's annotated files 
    # ------------------------------------------------------
    
    nside = 1024 # Resolution of output maps
    nsidesout = None # if you want full sky degraded maps to be written
    ratiores = 1 # Superresolution/oversampling ratio, simp mode doesn't allow anything other than 1
    mode = 1 # 1: fully sequential, 2: parallel then sequential, 3: fully parallel
    
    pixoffset = 0 # How many pixels are being removed on the edge of each CCD? 15 for DES.
    
    mjd_max = 10e10
    mjdw = ''

    # Survey inputs
    if rel == 'DR2':
        fname =inputdir+'decals-ccds-annotated.fits'
        catalogue_name = 'DECaLS_DR2'+mjdw

    if rel == 'DR3':
        inputdir = '/project/projectdirs/cosmo/data/legacysurvey/dr3/' # where I get my data 
        fname =inputdir+'ccds-annotated-decals.fits.gz'
        catalogue_name = 'DECaLS_DR3'+mjdw

    if rel == 'DR4':
        inputdir= '/global/projecta/projectdirs/cosmo/work/dr4/'
        if (band == 'g' or band == 'r'):
            fname=inputdir+'ccds-annotated-dr4-90prime.fits.gz'
            catalogue_name = '90prime_DR4'+mjdw
        if band == 'z' :
            fname = inputdir+'ccds-annotated-dr4-mzls.fits.gz' 
            catalogue_name = 'MZLS_DR4'+mjdw
	
    #Bands inputs
    if band == 'g':
        be = 1
        extc = 3.303  #/2.751
    if band == 'r':
        be = 2
        extc = 2.285  #/2.751
    if band == 'z':
        be = 4
        extc = 1.263  #/2.751

    # Where to write the maps ? Make sure directory exists.
    outroot = localdir
    
    tbdata = pyfits.open(fname)[1].data
    
    # ------------------------------------------------------
    # Obtain indices
    if band == 'g':
        sample_names = ['band_g']
        indg = np.where((tbdata['filter'] == 'g') & (tbdata['photometric'] == True) & (tbdata['blacklist_ok'] == True)) 
        inds = indg #redundant
    if band == 'r':
        sample_names = ['band_r']
        indr = np.where((tbdata['filter'] == 'r') & (tbdata['photometric'] == True) & (tbdata['blacklist_ok'] == True))
        inds = indr #redundant
    if band == 'z':
        sample_names = ['band_z']
        indz = np.where((tbdata['filter'] == 'z') & (tbdata['photometric'] == True) & (tbdata['blacklist_ok'] == True))
        inds = indz # redundant
    
    #Read data 
    #obtain invnoisesq here, including extinction 
    nmag = Magtonanomaggies(tbdata['galdepth']-extc*tbdata['EBV'])/5.
    ivar= 1./nmag**2.

    # What properties do you want mapped?
    # Each each tuple has [(quantity to be projected, weighting scheme, operation),(etc..)] 
    propertiesandoperations = [ ('ivar', '', 'total'), ]

 
    # What properties to keep when reading the images? 
    #Should at least contain propertiesandoperations and the image corners.
    # MARCM - actually no need for ra dec image corners.   
    # Only needs ra0 ra1 ra2 ra3 dec0 dec1 dec2 dec3 only if fast track appropriate quicksip subroutines were implemented 
    propertiesToKeep = [ 'filter', 'AIRMASS', 'FWHM','mjd_obs'] \
    	+ ['RA', 'DEC', 'crval1', 'crval2', 'crpix1', 'crpix2', 'cd1_1', 'cd1_2', 'cd2_1', 'cd2_2','width','height']
    
    # Create big table with all relevant properties. 

    tbdata = np.core.records.fromarrays([tbdata[prop] for prop in propertiesToKeep] + [ivar], names = propertiesToKeep + [ 'ivar'])
    
    # Read the table, create Healtree, project it into healpix maps, and write these maps.
    # Done with Quicksip library, note it has quite a few hardcoded values (use new version by MARCM for BASS and MzLS) 
    # project_and_write_maps_simp(mode, propertiesandoperations, tbdata, catalogue_name, outroot, sample_names, inds, nside)
    project_and_write_maps(mode, propertiesandoperations, tbdata, catalogue_name, outroot, sample_names, inds, nside, ratiores, pixoffset, nsidesout)
 
    # ----- plot depth map -----
    prop='ivar'
    plotPropertyMap(band,survey=catalogue_name,prop=prop)

    return True


def plotMaghist_pred(band,FracExp=[0,0,0,0,0],ndraw = 1e5,nbin=100,rel='DR3',vmin=21.0):

    # MARCM Makes histogram of predicted magnitudes 
    # by MonteCarlo from exposures converving fraction of number of exposures
    # This produces the histogram for Dustin's processed galaxy depth

    import fitsio
    from matplotlib import pyplot as plt
    from numpy import zeros,array
    from random import random

    # Check fraction of number of exposures adds to 1. 
    if( abs(sum(FracExp) - 1.0) > 1e-5 ):
       print sum(FracExp)
       raise ValueError("Fration of number of exposures don't add to one")

    # Survey inputs
    mjdw='' 
    if rel == 'DR2':
        fname =inputdir+'decals-ccds-annotated.fits'
        catalogue_name = 'DECaLS_DR2'+mjdw

    if rel == 'DR3':
        inputdir = '/project/projectdirs/cosmo/data/legacysurvey/dr3/' # where I get my data 
        fname =inputdir+'ccds-annotated-decals.fits.gz'
        catalogue_name = 'DECaLS_DR3'+mjdw

    if rel == 'DR4':
        #inputdir= '/global/projecta/projectdirs/cosmo/work/dr4/'
        inputdir='/project/projectdirs/cosmo/data/legacysurvey/dr4'
        if (band == 'g' or band == 'r'):
            fname=inputdir+'ccds-annotated-bass.fits.gz'
            catalogue_name='BASS_DR4'+mjdw
            #fname=inputdir+'ccds-annotated-dr4-90prime.fits.gz'
            #catalogue_name = '90prime_DR4'+mjdw
        if band == 'z' :
            #fname = inputdir+'ccds-annotated-dr4-mzls.fits.gz' 
            fname = inputdir+'ccds-annotated-mzls.fits.gz' 
            catalogue_name = 'MZLS_DR4'+mjdw
		
    # Bands info 
    if band == 'g':
        be = 1
        zp0 = 25.08
        recm = 24.
    if band == 'r':
        be = 2
        zp0 = 25.29
        recm = 23.4
    if band == 'z':
        be = 4
        zp0 = 24.92
        recm = 22.5

    f = fitsio.read(fname)

    #read in magnitudes including extinction
    counts2014 =0
    n = 0
    nl = []
    for i in range(0,len(f)):
        DS = 0
        year = int(f[i]['date_obs'].split('-')[0])
        if (year <= 2014): counts2014=counts2014+1 
        if year > 2014:
            DS = 1 #enforce 2015 data

            if f[i]['filter'] == band:
			
                if DS == 1:
                    n += 1				
                    if f[i]['dec'] > -20 and f[i]['photometric'] == True and f[i]['blacklist_ok'] == True :   
		
                         magext = f[i]['galdepth'] - f[i]['decam_extinction'][be]
                         nmag = Magtonanomaggies(magext)/5. #total noise
                         nl.append(nmag)

    ng = len(nl)
    print "-----------"
    print "Number of objects with DS=1", n
    print "Number of objects in the sample", ng 
    print "Counts before or during 2014", counts2014

    #Monte Carlo to predict magnitudes histogram 
    ndrawn = 0
    nbr = 0	
    NTl = []
    for indx, f in enumerate(FracExp,1) : 
        Nexp = indx # indx starts at 1 bc argument on enumearate :-), thus is the number of exposures
        nd = int(round(ndraw * f))
        ndrawn=ndrawn+nd

        for i in range(0,nd):

            detsigtoti = 0
            for j in range(0,Nexp):
		ind = int(random()*ng)
		detsig1 = nl[ind]
		detsigtoti += 1./detsig1**2.

 	    detsigtot = sqrt(1./detsigtoti)
	    m = nanomaggiesToMag(detsigtot * 5.)
	    if m > recm: # pass requirement
	 	nbr += 1.	
	    NTl.append(m)
	    n += 1.
	
    # Run some statistics 

    NTl=np.array(NTl)
    mean = sum(NTl)/float(len(NTl))
    std = sqrt(sum(NTl**2.)/float(len(NTl))-mean**2.)
    NTl.sort()
    if len(NTl)/2. != len(NTl)/2:
        med = NTl[len(NTl)/2+1]
    else:
        med = (NTl[len(NTl)/2+1]+NTl[len(NTl)/2])/2.

    print "Mean ", mean
    print "Median ", med
    print "Std ", std
    print 'percentage better than requirements '+str(nbr/float(ndrawn))

    # Prepare historgram 
    minN = max(min(NTl),vmin)
    maxN = max(NTl)+.0001
    hl = zeros((nbin)) # histogram counts
    lowcounts=0
    for i in range(0,len(NTl)):
        bin = int(nbin*(NTl[i]-minN)/(maxN-minN))
        if(bin >= 0) : 
            hl[bin] += 1
        else:
            lowcounts +=1

    Nl = []  # x bin centers
    for i in range(0,len(hl)):
        Nl.append(minN+i*(maxN-minN)/float(nbin)+0.5*(maxN-minN)/float(nbin))
    NTl = array(NTl)

    #### Ploting histogram 
    print "Plotting the histogram now"
    print "min,max depth ",min(NTl), max(NTl) 
    print "counts below ", vmin, "are ", lowcounts

    from matplotlib.backends.backend_pdf import PdfPages
    plt.clf()
    pp = PdfPages(localdir+'validationplots/'+catalogue_name+band+'_pred_exposures.pdf')	

    plt.plot(Nl,hl,'k-')
    plt.xlabel(r'5$\sigma$ '+band+ ' depth')
    plt.ylabel('# of images')
    plt.title('MC combined exposure depth '+str(mean)[:5]+r'$\pm$'+str(std)[:4]+r', $f_{\rm pass}=$'+str(nbr/float(ndrawn))[:5]+'\n '+catalogue_name)
    #plt.xscale('log')
    pp.savefig()
    pp.close()
    return True

def photometricReq(band,rel='DR3',survey='survename'):
    
    # ------------------------------------------------------
    # ------------------------------------------------------
    
    nside = 1024 # Resolution of output maps
    nsidesout = None # if you want full sky degraded maps to be written
    ratiores = 1 # Superresolution/oversampling ratio, simp mode doesn't allow anything other than 1
    mode = 1 # 1: fully sequential, 2: parallel then sequential, 3: fully parallel
    
    pixoffset = 0 # How many pixels are being removed on the edge of each CCD? 15 for DES.
    
    mjd_max = 10e10
    mjdw = ''

    # Survey inputs
    if rel == 'DR2':
        fname =inputdir+'decals-ccds-annotated.fits'
        catalogue_name = 'DECaLS_DR2'+mjdw

    if rel == 'DR3':
        inputdir = '/project/projectdirs/cosmo/data/legacysurvey/dr3/' # where I get my data 
        fname =inputdir+'ccds-annotated-decals.fits.gz'
        catalogue_name = 'DECaLS_DR3'+mjdw

    if rel == 'DR4':
        inputdir= '/global/projecta/projectdirs/cosmo/work/dr4/'
        if (band == 'g' or band == 'r'):
            fname=inputdir+'ccds-annotated-dr4-90prime.fits.gz'
            catalogue_name = '90prime_DR4'+mjdw
        if band == 'z' :
            fname = inputdir+'ccds-annotated-dr4-mzls.fits.gz' 
            catalogue_name = 'MZLS_DR4'+mjdw
	
    # Where to write the maps ? Make sure directory exists.
    outroot = localdir
    
    tbdata = pyfits.open(fname)[1].data
    
    # ------------------------------------------------------
    # Obtain indices
    if band == 'g':
        sample_names = ['band_g']
        #indg = np.where((tbdata['filter'] == 'g') & (tbdata['photometric'] == True) & (tbdata['blacklist_ok'] == True)) 
        indg = np.where((tbdata['filter'] == 'g') & (tbdata['blacklist_ok'] == True)) 
        #indg = np.where((tbdata['filter'] == 'g') ) 
        inds = indg #redundant
    if band == 'r':
        sample_names = ['band_r']
        #indr = np.where((tbdata['filter'] == 'r') & (tbdata['photometric'] == True) & (tbdata['blacklist_ok'] == True))
        indr = np.where((tbdata['filter'] == 'r') & (tbdata['blacklist_ok'] == True))
        #indr = np.where((tbdata['filter'] == 'r') )
        inds = indr #redundant
    if band == 'z':
        sample_names = ['band_z']
        #indz = np.where((tbdata['filter'] == 'z') & (tbdata['photometric'] == True) & (tbdata['blacklist_ok'] == True))
        indz = np.where((tbdata['filter'] == 'z') & (tbdata['blacklist_ok'] == True))
        #indz = np.where((tbdata['filter'] == 'z') )
        inds = indz # redundant
    
    #Read data 
    #obtain invnoisesq here, including extinction 
    zptvar = tbdata['CCDPHRMS']**2/tbdata['CCDNMATCH']
    zptivar = 1./zptvar
    nccd = np.ones(len(tbdata))

    # What properties do you want mapped?
    # Each each tuple has [(quantity to be projected, weighting scheme, operation),(etc..)] 
    quicksipVerbose(sample.verbose)
    propertiesandoperations = [ ('zptvar', '', 'total') , ('zptvar','','min') , ('nccd','','total') , ('zptivar','','total')]

 
    # What properties to keep when reading the images? 
    #Should at least contain propertiesandoperations and the image corners.
    # MARCM - actually no need for ra dec image corners.   
    # Only needs ra0 ra1 ra2 ra3 dec0 dec1 dec2 dec3 only if fast track appropriate quicksip subroutines were implemented 
    propertiesToKeep = [ 'filter', 'AIRMASS', 'FWHM','mjd_obs'] \
    	+ ['RA', 'DEC', 'crval1', 'crval2', 'crpix1', 'crpix2', 'cd1_1', 'cd1_2', 'cd2_1', 'cd2_2','width','height']
    
    # Create big table with all relevant properties. 

    tbdata = np.core.records.fromarrays([tbdata[prop] for prop in propertiesToKeep] + [zptvar,zptivar,nccd], names = propertiesToKeep + [ 'zptvar','zptivar','nccd'])
    
    # Read the table, create Healtree, project it into healpix maps, and write these maps.
    # Done with Quicksip library, note it has quite a few hardcoded values (use new version by MARCM for BASS and MzLS) 
    # project_and_write_maps_simp(mode, propertiesandoperations, tbdata, catalogue_name, outroot, sample_names, inds, nside)
    project_and_write_maps(mode, propertiesandoperations, tbdata, catalogue_name, outroot, sample_names, inds, nside, ratiores, pixoffset, nsidesout)
 
    # ----- plot depth map -----
    #prop='ivar'
    #plotPropertyMap(band,survey=catalogue_name,prop=prop)

    return True


# ***********************************************************************
# ***********************************************************************

# --- run depth maps 
#band='r'
#depthfromIvar(band,rel='DR3')
#
#band='g'
#depthfromIvar(band,rel='DR3')
#
#band='z'
#depthfromIvar(band,rel='DR3')

#band='r'
#depthfromIvar(band,rel='DR4')

#band='g'
#depthfromIvar(band,rel='DR4')

#band='z'
#depthfromIvar(band,rel='DR4')



# DECALS (DR3) the final survey will be covered by 
# 1, 2, 3, 4, and 5 exposures in the following fractions: 
#FracExp=[0.02,0.24,0.50,0.22,0.02]

#print "DECaLS depth histogram r-band"
#band='r'
#plotMaghist_pred(band,FracExp=FracExp,ndraw = 1e5,nbin=100,rel='DR3')

#print "DECaLS depth histogram g-band"
#band='g'
#plotMaghist_pred(band,FracExp=FracExp,ndraw = 1e5,nbin=100,rel='DR3')

#print "DECaLS depth histogram z-band"
#band='z'
#plotMaghist_pred(band,FracExp=FracExp,ndraw = 1e5,nbin=100,rel='DR3')

# For BASS (DR4) the coverage fractions for 1,2,3,4,5 exposures are:
#FracExp=[0.0014,0.0586,0.8124,0.1203,0.0054,0.0019]

#print "BASS depth histogram r-band"
#band='r'
#plotMaghist_pred(band,FracExp=FracExp,ndraw = 1e5,nbin=100,rel='DR4')

#print "BASS depth histogram g-band"
#band='g'
#plotMaghist_pred(band,FracExp=FracExp,ndraw = 1e5,nbin=100,rel='DR4')

# For MzLS fill factors of 100% with a coverage of at least 1, 
# 99.5% with a coverage of at least 2, and 85% with a coverage of 3.
#FracExp=[0.005,0.145,0.85,0,0]

#print "MzLS depth histogram z-band"
#band='z'
#plotMaghist_pred(band,FracExp=FracExp,ndraw = 1e5,nbin=100,rel='DR4')

# --- run histogram deph peredictions
# prova
#photometricReq('g',rel='DR3',survey='survename')
#photometricReq('r',rel='DR3',survey='survename')
#photometricReq('z',rel='DR3',survey='survename')
#photometricReq('g',rel='DR4',survey='survename')
#photometricReq('r',rel='DR4',survey='survename')
#photometricReq('z',rel='DR4',survey='survename')

#prop = 'zptvar'
#opt  = 'min'

#rel  = 'DR3'
#band = 'g'
#plotPhotometryMap(band,prop=prop,op=opt,rel=rel)
#band = 'r'
#plotPhotometryMap(band,prop=prop,op=opt,rel=rel)
#band = 'z'
#plotPhotometryMap(band,prop=prop,op=opt,rel=rel)
#
#rel = 'DR4'
#band = 'g'
#plotPhotometryMap(band,prop=prop,op=opt,rel=rel)
#band = 'r'
#plotPhotometryMap(band,prop=prop,op=opt,rel=rel)
#band = 'z'
#plotPhotometryMap(band,prop=prop,op=opt,rel=rel)

