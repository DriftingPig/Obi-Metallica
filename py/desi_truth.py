#!/usr/bin/env python

import os
import numpy as np
import astropy.io.fits as fits
from astropy.coordinates import SkyCoord
from astropy import units as u
#import raichoorlib

# settings
ramin,ramax,decmin,decmax        = 34,38,-7,-3
depth_gmin,depth_rmin,depth_zmin = 4000,2000,500
sweep_fns = [	'/global/project/projectdirs/cosmo/data/legacysurvey/dr7/sweep/7.1/sweep-030m010-040m005.fits',
				'/global/project/projectdirs/cosmo/data/legacysurvey/dr7/sweep/7.1/sweep-030m005-040p000.fits']
hsc_fn    = '/global/cscratch1/sd/raichoor/HSC/pdr1.zphot.fits'
#outfits   = '/global/cscratch1/sd/raichoor/desi_mcsyst/desi_mcsyst_truth.dr7.34ra38.-7dec-3.fits'
outfits = '/global/cscratch1/sd/huikong/obiwan_Aug/repos_for_docker/obiwan_data/dr7_truth.fits'
print('start')
#print raichoorlib.get_date(), 'start'

# dr7 photometry
phot      = {}
phot_keys = ['brickname','objid','type','ra','dec','g','r','z','w1','w2','galdepth_g','galdepth_r','galdepth_z','shapeexp_r', 'shapeexp_e1', 'shapeexp_e2', 'shapedev_r', 'shapedev_e1', 'shapedev_e2']
for fn in sweep_fns:
	hdu = fits.open(fn)
	data= hdu[1].data
	# cutting
	keep = ((data['ra']>ramin) & (data['ra']<ramax) & (data['dec']>decmin) & (data['dec']<decmax) &
			(data['allmask_g']==0) & (data['allmask_r']==0) & (data['allmask_z']==0) & (~data['brightstarinblob']) &
			(data['galdepth_g']>depth_gmin) & (data['galdepth_r']>depth_rmin) & (data['galdepth_z']>depth_zmin) & (data['flux_g']>0) & (data['flux_r']>0) & (data['flux_z']>0) & (data['mw_transmission_g']>0) & (data['mw_transmission_r']>0) & (data['mw_transmission_z']>0)
			)
	data = data[keep]
        #print raichoorlib.get_date(), fn.split('/')[-1], 'keeping ', len(data), ' objects'
        #print(fn.split('/')[-1]+ 'keeping '+ str(len(data))+' objects')
        # appending + storing fmt
	for key in phot_keys:
		if (key in ['g','r','z','w1','w2']):
			tmparr = 22.5-2.5*np.log10(data['flux_'+key]/data['mw_transmission_'+key])
		else:
			tmparr = data[key]
		if (fn==sweep_fns[0]):
			if (key in ['g','r','z','w1','w2']):
				phot[key+'_fmt'] = 'E'
			else:
				phot[key+'_fmt'] = hdu[1].columns[key].format
			phot[key] = tmparr
		else:
			phot[key] = np.append(phot[key],tmparr)
#print raichoorlib.get_date(), 'selecting ', len(phot['ra']), ' objects from dr7'
print('selecting '+str(len(phot['ra']))+' objects from dr7')
# hsc/dr1 mizuki [taking mizuki because it has zphot=0 for stars]
hsc_keys= ['object_id','ra','dec','mizuki_photoz_best']
hdu     = fits.open(hsc_fn)
hsc     = hdu[1].data
keep    = (hsc['ra']>ramin) & (hsc['ra']<ramax) & (hsc['dec']>decmin) & (hsc['dec']<decmax) & (~hsc['mizuki_photoz_best_isnull'])
hsc     = hsc[keep]
#print raichoorlib.get_date(), len(hsc), ' hsc objects in that region'
print('%d hsc objects in that region'%len(hsc))
# matching
#print raichoorlib.get_date(), 'matching start'
print('matching start')
#photind,hscind,_,_,_ = raichoorlib.match_coord(phot['ra'],phot['dec'],hsc['ra'],hsc['dec'],search_radius=1.0)
c1 = SkyCoord(ra=phot['ra']*u.degree, dec=phot['dec']*u.degree)
c2 = SkyCoord(ra=hsc['ra']*u.degree, dec=hsc['dec']*u.degree)
idx, d2d, d3d = c1.match_to_catalog_sky(c2)
w = d2d.value <= 1./3600
idx[~w] = -1
idx1 = np.where(w)[0]
idx2 = idx[idx>-1]
#print(len(phot[idx1]), len(hsc[idx2]))
photind = idx1
hscind = idx2
#import pdb;pdb.set_trace()
for key in phot_keys:
	phot[key] = phot[key][photind]
#import pdb;pdb.set_trace()
hsc= hsc[hscind]
#print raichoorlib.get_date(), 'matching done'

# writing fits
collist = []
for key in phot_keys:
	collist.append(fits.Column(name=key,format=phot[key+'_fmt'],array=phot[key]))
for key in hsc_keys:
	collist.append(fits.Column(name='hsc_'+key,format=hdu[1].columns[key].format,array=hsc[key]))
hdu  = fits.BinTableHDU.from_columns(fits.ColDefs(collist))
hdu.writeto(outfits,overwrite=True)

#print raichoorlib.get_date(),' done'
