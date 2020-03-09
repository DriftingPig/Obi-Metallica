import os
import glob
import numpy as n
import numpy as np
from astropy.io import fits
from math import *
from astropy.table import Column, Table
from astropy.coordinates import SkyCoord
from astropy import units as u
import subprocess
from astropy.table import hstack,Table

def SV_brick_match(brickname, name_for_run, rs_type, name_for_randoms = None, startid = None, nobj = None, angle = 1.5/3600):
    
    assert(name_for_randoms is not None);assert(startid is not None);assert(nobj is not None)
    topdir_tractor = os.environ['obiwan_out']+'/output/'
    sim_topdir = os.environ['obiwan_out']+'/divided_randoms/'
    print(brickname,rs_type)
    fn_tractor = os.path.join(topdir_tractor,'tractor',brickname[:3],brickname,rs_type,'tractor-%s.fits' %brickname)
    fn_sim = os.path.join(topdir_tractor,'obiwan',brickname[:3],brickname,rs_type,'simcat-elg-%s.fits' %brickname)
    fn_original_sim = sim_topdir+'/brick_'+brickname+'.fits'
    
    tractor = Table.read(fn_tractor)
    sim = Table.read(fn_sim)
    
    original_sim = Table.read(fn_original_sim)[startid:startid+nobj] 
    
    #import pdb;pdb.set_trace()
    c1 = SkyCoord(ra=sim['ra']*u.degree, dec=sim['dec']*u.degree)
    c2 = SkyCoord(ra=np.array(tractor['ra'])*u.degree, dec=np.array(tractor['dec'])*u.degree)
    c3 = SkyCoord(ra=original_sim['ra']*u.degree, dec=original_sim['dec']*u.degree)

    idx1, d2d, d3d = c1.match_to_catalog_sky(c2)
    idx2, d2d2, d3d2 = c1.match_to_catalog_sky(c3)

    matched = d2d.value <= angle
    distance = d2d.value
    tc = tractor[idx1]

    ors = original_sim[idx2]
    
    tc.add_column(sim['gflux'],name = 'sim_gflux')
    tc.add_column(sim['rflux'],name='sim_rflux')
    tc.add_column(sim['zflux'],name='sim_zflux')
    tc.add_column(ors['redshift'],name='sim_redshift')
    tc.add_column(sim['rhalf'],name='sim_rhalf')
    tc.add_column(sim['e1'],name='sim_e1')
    tc.add_column(sim['e2'],name='sim_e2')
    tc.add_column(sim['x'],name='sim_bx')
    tc.add_column(sim['y'],name='sim_by')
    
    tc['detected'] = np.array(matched,dtype=np.bool)
    tc.add_column(sim['n'],name='sim_sersic_n')
    return tc

#SV_brick_match('2283p115', 'dr8_SV','rs0', name_for_randoms='SV_dr8', startid = 0, nobj = 200)
