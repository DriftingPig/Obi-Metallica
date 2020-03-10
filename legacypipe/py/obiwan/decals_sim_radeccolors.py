#!/usr/bin/env python

"""
"""
from __future__ import division, print_function

import matplotlib.pyplot as plt
import matplotlib as mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
import os
import argparse
import numpy as np
from glob import glob
from astrometry.util.ttime import Time
import datetime
import sys
import pickle

from astrometry.util.fits import fits_table, merge_tables
from theValidator.catalogues import CatalogueFuncs

from legacypipe.survey import LegacySurveyData, wcs_for_brick

######## 
## Ted's
import time
from contextlib import contextmanager

@contextmanager
def stdouterr_redirected(to=os.devnull, comm=None):
    '''
    Based on http://stackoverflow.com/questions/5081657
    import os
    with stdouterr_redirected(to=filename):
        print("from Python")
        os.system("echo non-Python applications are also supported")
    '''
    sys.stdout.flush()
    sys.stderr.flush()
    fd = sys.stdout.fileno()
    fde = sys.stderr.fileno()

    ##### assert that Python and C stdio write using the same file descriptor
    ####assert libc.fileno(ctypes.c_void_p.in_dll(libc, "stdout")) == fd == 1

    def _redirect_stdout(to):
        sys.stdout.close() # + implicit flush()
        os.dup2(to.fileno(), fd) # fd writes to 'to' file
        sys.stdout = os.fdopen(fd, 'w') # Python writes to fd
        sys.stderr.close() # + implicit flush()
        os.dup2(to.fileno(), fde) # fd writes to 'to' file
        sys.stderr = os.fdopen(fde, 'w') # Python writes to fd
        
    with os.fdopen(os.dup(fd), 'w') as old_stdout:
        if (comm is None) or (comm.rank == 0):
            print("Begin log redirection to {} at {}".format(to, time.asctime()))
        sys.stdout.flush()
        sys.stderr.flush()
        pto = to
        if comm is None:
            if not os.path.exists(os.path.dirname(pto)):
                os.makedirs(os.path.dirname(pto))
            with open(pto, 'w') as file:
                _redirect_stdout(to=file)
        else:
            pto = "{}_{}".format(to, comm.rank)
            with open(pto, 'w') as file:
                _redirect_stdout(to=file)
        try:
            yield # allow code to be run with the redirected stdout
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            _redirect_stdout(to=old_stdout) # restore stdout.
                                            # buffering and flags such as
                                            # CLOEXEC may be different
            if comm is not None:
                # concatenate per-process files
                comm.barrier()
                if comm.rank == 0:
                    with open(to, 'w') as outfile:
                        for p in range(comm.size):
                            outfile.write("================= Process {} =================\n".format(p))
                            fname = "{}_{}".format(to, p)
                            with open(fname) as infile:
                                outfile.write(infile.read())
                            os.remove(fname)
                comm.barrier()

            if (comm is None) or (comm.rank == 0):
                print("End log redirection to {} at {}".format(to, time.asctime()))
            sys.stdout.flush()
            sys.stderr.flush()
            
    return
##############

def ptime(text,t0):
    tnow=Time()
    print('TIMING:%s ' % text,tnow-t0)
    return tnow

def read_lines(fn):
    fin=open(fn,'r')
    lines=fin.readlines()
    fin.close()
    if len(lines) < 1: raise ValueError('lines not read properly from %s' % fn)
    return np.array( list(np.char.strip(lines)) )

def dobash(cmd):
    print('UNIX cmd: %s' % cmd)
    if os.system(cmd): raise ValueError

def get_area(radec):
    '''returns area on sphere between ra1,ra2,dec2,dec1
    https://github.com/desihub/imaginglss/model/brick.py#L64, self.area=...
    '''
    deg = np.pi / 180.
    # Wrap around
    if radec['ra2'] < radec['ra1']:
        ra2=radec['ra2']+360.
    else:
        ra2=radec['ra2']
    
    area= (np.sin(radec['dec2']*deg)- np.sin(radec['dec1']*deg)) * \
          (ra2 - radec['ra1']) * \
          deg* 129600 / np.pi / (4*np.pi)
    approx_area= (radec['dec2']-radec['dec1'])*(ra2-radec['ra1'])
    print('approx area=%.2f deg2, actual area=%.2f deg2' % (approx_area,area))
    return area

def get_radec(radec,\
              ndraws=1,random_state=np.random.RandomState()):
    '''https://github.com/desihub/imaginglss/blob/master/scripts/imglss-mpi-make-random.py#L55'''
    ramin,ramax= radec['ra1'],radec['ra2']
    dcmin,dcmax= radec['dec1'],radec['dec2']
    u1,u2= random_state.uniform(size=(2, ndraws) )
    #
    cmin = np.sin(dcmin*np.pi/180)
    cmax = np.sin(dcmax*np.pi/180)
    #
    RA   = ramin + u1*(ramax-ramin)
    DEC  = 90-np.arccos(cmin+u2*(cmax-cmin))*180./np.pi
    return RA,DEC

class KDEColors(object):
    def __init__(self,objtype='star',pickle_dir='./'):
        self.objtype= objtype
        self.kdefn=os.path.join(pickle_dir,'%s-kde.pickle' % self.objtype)
        self.kde= self.get_kde()

    def get_kde(self):
        fout=open(self.kdefn,'r')
        kde= pickle.load(fout)
        fout.close()
        return kde

    def get_colors(self,ndraws=1,random_state=np.random.RandomState()):
        samp= self.kde.sample(n_samples=ndraws,random_state=random_state)
        if self.objtype == 'star':
            #labels=['r wdust','r-z','g-r']
            r= samp[:,0]
            z= r- samp[:,1]
            g= r+ samp[:,2]
            return g,r,z
        elif self.objtype == 'qso':
            #labels=['r wdust','r-z','g-r']
            r= samp[:,0]
            z= r- samp[:,1]
            g= r+ samp[:,2]
            redshift= samp[:,3]
            return g,r,z,redshift
        elif self.objtype == 'elg':
            #labels=['r wdust','r-z','g-r'] 
            r= samp[:,0]
            z= r- samp[:,1]
            g= r+ samp[:,2]
            redshift= samp[:,3]
            return g,r,z,redshift
        elif self.objtype == 'lrg':
            #labels=['z wdust','r-z','r-W1','g wdust']
            z= samp[:,0]
            r= z+ samp[:,1]
            redshift= samp[:,3]
            g= samp[:,4]
            return g,r,z,redshift
        else: 
            raise ValueError('objecttype= %s, not supported' % self.objtype)

class KDEshapes(object):
    def __init__(self,objtype='elg',pickle_dir='./'):
        assert(objtype in ['lrg','elg'])
        self.objtype= objtype
        self.kdefn=os.path.join(pickle_dir,'%s-shapes-kde.pickle' % self.objtype)
        self.kde= self.get_kde()

    def get_kde(self):
        fout=open(self.kdefn,'r')
        kde= pickle.load(fout)
        fout.close()
        return kde

    def get_shapes(self,ndraws=1,random_state=np.random.RandomState()):
        samp= self.kde.sample(n_samples=ndraws,random_state=random_state)
        # Same for elg,lrg
        re= samp[:,0]
        n=  samp[:,1]
        ba= samp[:,2]
        pa= samp[:,3]
        # pa ~ flat PDF
        pa=  random_state.uniform(0., 180., ndraws)
        # ba can be [1,1.2] due to KDE algorithm, make these 1
        ba[ ba < 0.1 ]= 0.1
        ba[ ba > 1 ]= 1.
        # Sanity Check
        assert(np.all(re > 0))
        assert(np.all((n > 0)*\
                      (n < 10)))
        assert(np.all((ba > 0)*\
                      (ba <= 1.)))
        assert(np.all((pa >= 0)*\
                      (pa <= 180)))
        
        return re,n,ba,pa

def get_sample_dir(outdir=None):
    return os.path.join(outdir,'input_sample')

def get_bybrick_dir(outdir='.'): 
    dr= get_sample_dir(outdir=outdir)
    return os.path.join(dr,'bybrick')

def get_sample_fn(seed=None,prefix=''):
    return '%ssample_%d.fits' % (prefix,seed)

def get_sample_fns(outdir=None,prefix=''):
    dr= get_sample_dir(outdir=outdir)
    fn= get_sample_fn(seed=1,prefix=prefix)
    fn= fn.replace('sample_1.fits','sample_*.fits')
    fns=glob(os.path.join(dr,fn) )
    if not len(fns) > 0: raise ValueError('no fns found')
    return fns

def get_brick_sample_fn(brickname=None,seed=None,prefix=None):
    fn= get_sample_fn(seed=seed,prefix=prefix)
    return fn.replace('sample_','sample_%s_' % brickname)

def get_brick_sample_fns(brickname=None,outdir='./',prefix=None):
    dr= get_bybrick_dir(outdir=outdir)
    fn= get_brick_sample_fn(brickname=brickname,seed=239,prefix=prefix)
    fn= os.path.join(dr,fn)
    if os.path.exists(fn):
        # Haven't been deleted yet, so glob for all of them
        fn= os.path.join(dr,fn.replace('239.fits','*.fits') )
        fns=glob(fn )
    else: return None
    if not len(fns) > 0: 
        print('no fns found with wildcard: %s' % fn)
        with open(os.path.join(outdir,'nofns_wildcard.txt'),'a') as foo:
            foo.write('%s\n' % fn)
        return None
    return fns

def get_brick_merged_fn(brickname=None,outdir='./',prefix=None):
    dr= get_bybrick_dir(outdir=outdir)
    fn= get_brick_sample_fn(brickname=brickname,seed=1,prefix=prefix)
    fn= os.path.join(dr,fn.replace('_1.fits','.fits') )
    return fn


def survey_bricks_cut2radec(radec):
    #fn=os.path.join(os.getenv('LEGACY_SURVEY_DIR'),'survey-bricks-5rows-eboss-ngc.fits.gz')
    fn=os.path.join(os.getenv('LEGACY_SURVEY_DIR'),'survey-bricks.fits.gz')
    tab= fits_table(fn)
    tab.cut( (tab.ra >= radec['ra1'])*(tab.ra <= radec['ra2'])*\
             (tab.dec >= radec['dec1'])*(tab.dec <= radec['dec2'])
           )
    print('%d bricks, cutting to radec' % len(tab))
    return tab
            
def draw_points(radec,unique_ids,seed=1,outdir='./',prefix=''):
    '''unique_ids -- ids assigned to this mpi task
    writes ra,dec,grz qso,lrg,elg,star to fits file
    for given seed'''
    ndraws= len(unique_ids)
    random_state= np.random.RandomState(seed)
    ra,dec= get_radec(radec,ndraws=ndraws,random_state=random_state)
    # Mags
    mags={}
    for typ in ['star','lrg','elg','qso']:
        kde_obj= KDEColors(objtype=typ,pickle_dir=outdir)
        if typ == 'star':
            mags['%s_g'%typ],mags['%s_r'%typ],mags['%s_z'%typ]= \
                        kde_obj.get_colors(ndraws=ndraws,random_state=random_state)
        else:
            mags['%s_g'%typ],mags['%s_r'%typ],mags['%s_z'%typ],mags['%s_redshift'%typ]= \
                        kde_obj.get_colors(ndraws=ndraws,random_state=random_state)
    # Shapes
    gfit={}
    for typ in ['lrg','elg']:
        kde_obj= KDEshapes(objtype=typ,pickle_dir=outdir)
        gfit['%s_re'%typ],gfit['%s_n'%typ],gfit['%s_ba'%typ],gfit['%s_pa'%typ]= \
                    kde_obj.get_shapes(ndraws=ndraws,random_state=random_state)
    # Create Sample table
    T=fits_table()
    T.set('id',unique_ids)
    T.set('seed',np.zeros(ndraws).astype(int)+seed)
    T.set('ra',ra)
    T.set('dec',dec)
    for key in mags.keys():
        T.set(key,mags[key])
    for key in gfit.keys():
        T.set(key,gfit[key])
    # Save table
    fn= os.path.join(get_sample_dir(outdir),get_sample_fn(seed,prefix=prefix) )
    if os.path.exists(fn):
        os.remove(fn)
        print('Overwriting %s' % fn)
    T.writeto(fn)
    print('Wrote %s' % fn)

def organize_by_brick(sample_fns,sbricks,outdir=None,seed=None,prefix=None):
    '''
    For each sample_fn, split into bricks
    get  brick sample fn for that brick and sample
    write it if does not exist
    sample_fn -- sample_seed.fits file assigned to that mpi task
    sbricks -- survey bricks table cut to radec region
    '''
    dr= get_bybrick_dir(outdir=outdir)
    for sample_fn in sample_fns:
        # Skip if already looped over bricks for this sample
        check_done= os.path.join(dr, get_sample_fn(seed=seed,prefix=prefix) )
        check_done= check_done.replace('.fits','_done.txt')
        if os.path.exists(check_done):
            print('check_done exists: %s' % check_done)
            continue
        # 
        sample= fits_table(sample_fn)
        print('sample min,max ra,dec= %f %f %f %f' % (sample.ra.min(),sample.ra.max(),\
                                                      sample.dec.min(),sample.dec.max()))
        # Loop over survey bricks
        survey = LegacySurveyData()
        for sbrick in sbricks:
            # Get output fn for this brick and sample
            fn= os.path.join(dr, get_brick_sample_fn(brickname=sbrick.brickname,seed=seed,prefix=prefix) )
            if os.path.exists(fn):
                continue
            # Cut sample by brick's bounds
            brickinfo = survey.get_brick_by_name(sbrick.brickname)
            brickwcs = wcs_for_brick(brickinfo)
            ra1,ra2,dec1,dec2= brickwcs.radec_bounds()
            keep=  (sample.ra >= ra1)*(sample.ra <= ra2)*\
                   (sample.dec >= dec1)*(sample.dec <= dec2)
            sample2= sample.copy()
            if np.where(keep)[0].size > 0:
                sample2.cut(keep)
                sample2.writeto(fn)
                print('Wrote %s' % fn)
            else: 
                print('WARNING: sample=%s has no ra,dec in brick=%s' % (sample_fn,sbrick.brickname))
        # This sample is done
        with open(check_done,'w') as foo:
            foo.write('done')

def merge_bybrick(bricks,outdir='',prefix='',cleanup=False):
    for brick in bricks:
        outfn= get_brick_merged_fn(brickname=brick,outdir=outdir,prefix=prefix) 
        if cleanup:
            if os.path.exists(outfn):
                # Safe to remove the pieces that went into outfn
                rm_fns= get_brick_sample_fns(brickname=brick,outdir=outdir,prefix=prefix)
                if not rm_fns is None:
                    print('removing files like: %s' % rm_fns[0])
                    try:
                        for rm_fn in rm_fns: os.remove(rm_fn)
                    except OSError:
                        pass
            continue 
        elif os.path.exists(outfn):
            # We are creating outfn, don't spend time deleting
            continue
        else:
            print('outfn=%s' % outfn)
            fns= get_brick_sample_fns(brickname=brick,outdir=outdir,prefix=prefix)
            if fns is None:
                # Wildcard found nothing see outdir/nofns_wildcard.txt
                continue 
            cats=[]
            for i,fn in enumerate(fns):
                print('reading %d/%d' % (i+1,len(fns)))
                try: 
                    tab= fits_table(fn) 
                    cats.append( tab )
                except IOError:
                    print('Fits file does not exist: %s' % fn)
            cat= merge_tables(cats, columns='fillzero') 
            cat.writeto(outfn)
            print('Wrote %s' % outfn)
        
        

#def merge_draws(outdir='./',prefix=''):
#    '''merges all fits tables created by draw_points()'''
#    # Btable has 5 rows: bricks for the run,ra1,ra2,dec1,dec2 
#    btable= get_bricks_fn(outdir)
#    print('Merging sample tables for %d brick directories' % len(btable))
#    for brick in btable.brickname:
#        T= CatalogueFuncs().stack(fns,textfile=False)
#        # Save
#        name= get_merged_fn(brick,outdir,prefix=prefix)
#        if os.path.exists(name):
#            os.remove(name)
#            print('Overwriting %s' % name)
#        T.writeto(name)
#        print('wrote %s' % name)
       

class PlotTable(object):
    def __init__(self,outdir='./',prefix=''):
        print('Plotting Tabulated Quantities')
        self.outdir= outdir
        self.prefix= prefix
        # Table 
        merge_fn= get_merge_fn(self.outdir,prefix=self.prefix) 
        print('Reading %s' % merge_fn)
        tab= fits_table( merge_fn )
        # RA, DEC
        self.radec(tab)
        # Source Properties
        xyrange=dict(x_star=[-0.5,2.2],\
                 y_star=[-0.3,2.],\
                 x_elg=[-0.5,2.2],\
                 y_elg=[-0.3,2.],\
                 x_lrg= [0, 3.],\
                 y_lrg= [-2, 6],\
                 x1_qso= [-0.5,3.],\
                 y1_qso= [-0.5,2.5],\
                 x2_qso= [-0.5,4.5],\
                 y2_qso= [-2.5,3.5])
        for obj in ['star','lrg','elg','qso']:
            # Colors, redshift
            if obj == 'star':
                x= tab.star_r
                y= tab.star_r - tab.star_z
                z= tab.star_g - tab.star_r
                labels=['r','r-z','g-r']
                xylims=dict(x1=(15,24),y1=(0,0.3),\
                            x2=(-1,3.5),y2=(-0.5,2))
                X= np.array([x,y,z]).T
            elif obj == 'elg':
                x= tab.elg_r
                y= tab.elg_r - tab.elg_z
                z= tab.elg_g - tab.elg_r
                d4= tab.elg_redshift
                labels=['r','r-z','g-r','redshift']
                xylims=dict(x1=(20.5,25.5),y1=(0,0.8),\
                            x2=xyrange['x_elg'],y2=xyrange['y_elg'],\
                            x3=(0.6,1.6),y3=(0.,1.0))
                X= np.array([x,y,z,d4]).T
            elif obj == 'lrg':
                x= tab.lrg_z
                y= tab.lrg_r - tab.lrg_z
                z= np.zeros(len(x)) #rW1['red_galaxy']
                d4= tab.lrg_redshift
                M= tab.lrg_g
                labels=['z','r-z','r-W1','redshift','g']
                xylims=dict(x1=(17.,22.),y1=(0,0.7),\
                            x2=xyrange['x_lrg'],y2=xyrange['y_lrg'],\
                            x3=(0.,1.6),y3=(0,1.),\
                            x4=(17.,29),y4=(0,0.7))
                X= np.array([x,y,z,d4,M]).T
            elif obj == 'qso':
                x= tab.qso_r
                y= tab.qso_r - tab.qso_z
                z= tab.qso_g - tab.qso_r
                d4= tab.qso_redshift
                labels=['r','r-z','g-r','redshift']
                hiz=2.1
                xylims=dict(x1=(15.,24),y1=(0,0.5),\
                            x2=xyrange['x1_qso'],y2=xyrange['y1_qso'],\
                            x3=(0.,hiz+0.2),y3=(0.,1.))
                X= np.array([x,y,z,d4]).T
 
            # Shapes
            if obj in ['elg','lrg']:
                re,n,ba,pa= tab.get('%s_re'%obj),tab.get('%s_n'%obj),tab.get('%s_ba'%obj),tab.get('%s_pa'%obj) 
                shape_labels=['re','n','ba','pa']
                shape_xylims=dict(x1=(-10,100),\
                            x2=(-2,10),\
                            x3=(-0.2,1.2),\
                            x4=(-20,200))
                X_shapes= np.array([re,n,ba,pa]).T
            
            # Plots
            if obj == 'star':
                self.plot_1band_and_color(X,labels,obj=obj,xylims=xylims)
            elif obj == 'qso':
                self.plot_1band_color_and_redshift(X,labels,obj=obj,xylims=xylims)
            elif obj in ['lrg','elg']:
                self.plot_1band_color_and_redshift(X,labels,obj=obj,xylims=xylims)
                self.plot_galaxy_shapes(X_shapes,shape_labels,obj=obj,xylims=shape_xylims)

    def radec(self,tab):
        plt.scatter(tab.ra,tab.dec,\
                    c='b',edgecolors='none',marker='o',s=1.,rasterized=True,alpha=0.2)
        xlab=plt.xlabel('RA (deg)')
        ylab=plt.ylabel('DEC (deg)')
        fn=os.path.join(self.outdir,'%ssample-merged-radec.png' % (self.prefix))
        plt.savefig(fn,bbox_extra_artists=[xlab,ylab], bbox_inches='tight',dpi=150)
        plt.close()
        print('Wrote %s' % fn)



    def plot_1band_and_color(self,X,labels,obj='star',xylims=None):
        '''xylims -- dict of x1,y1,x2,y2,... where x1 is tuple of low,hi for first plot xaxis'''
        if obj == 'lrg':
            fig,ax= plt.subplots(1,3,figsize=(15,3))
        else:
            fig,ax= plt.subplots(1,2,figsize=(12,5))
        plt.subplots_adjust(wspace=0.2)
        # Data
        ax[0].hist(X[:,0],normed=True)
        ax[1].scatter(X[:,1],X[:,2],\
                      c='b',edgecolors='none',marker='o',s=10.,rasterized=True,alpha=0.2)
        if xylims is not None:
            ax[0].set_xlim(xylims['x1'])
            ax[0].set_ylim(xylims['y1'])
            ax[1].set_xlim(xylims['x2'])
            ax[1].set_ylim(xylims['y2'])
        xlab=ax[0].set_xlabel(labels[0],fontsize='x-large')
        xlab=ax[1].set_xlabel(labels[1],fontsize='x-large')
        ylab=ax[1].set_ylabel(labels[2],fontsize='x-large')
        if obj == 'lrg':
            # G distribution even though no Targeting cuts on g
            ax[0,2].hist(X[:,3],normed=True)
            if xylims is not None:
                ax[2].set_xlim(xylims['x3'])
                ax[2].set_ylim(xylims['y3'])
            xlab=ax[2].set_xlabel(labels[3],fontsize='x-large')
        fn=os.path.join(self.outdir,'%ssample-merged-colors-%s.png' % (self.prefix,obj))
        plt.savefig(fn,bbox_extra_artists=[xlab], bbox_inches='tight',dpi=150)
        plt.close()
        print('Wrote %s' % fn)

    def plot_1band_color_and_redshift(self,X,labels,obj='elg',xylims=None):
        '''xylims -- dict of x1,y1,x2,y2,... where x1 is tuple of low,hi for first plot xaxis'''
        # Colormap the color-color plot by redshift
        cmap = mpl.colors.ListedColormap(['m','r', 'y', 'g','b', 'c'])
        bounds= np.linspace(xylims['x3'][0],xylims['x3'][1],num=6)
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
        if obj == 'lrg':
            fig,ax= plt.subplots(1,4,figsize=(15,3))
        else:
            fig,ax= plt.subplots(1,3,figsize=(12,3))
        plt.subplots_adjust(wspace=0.2)
        # Data
        ax[0].hist(X[:,0],normed=True)
        # color bar with color plot
        axobj= ax[1].scatter(X[:,1],X[:,2],c=X[:,3],\
                                 marker='o',s=10.,rasterized=True,lw=0,\
                                 cmap=cmap,norm=norm,\
                                 vmin=bounds.min(),vmax=bounds.max())
        divider3 = make_axes_locatable(ax[1])
        cax3 = divider3.append_axes("right", size="5%", pad=0.1)
        cbar3 = plt.colorbar(axobj, cax=cax3,\
                             cmap=cmap, norm=norm, boundaries=bounds, ticks=bounds)
        cbar3.set_label('redshift')
        ax[2].hist(X[:,3],normed=True)
        if xylims is not None:
            ax[0].set_xlim(xylims['x1'])
            ax[0].set_ylim(xylims['y1'])
            ax[1].set_xlim(xylims['x2'])
            ax[1].set_ylim(xylims['y2'])
            ax[2].set_xlim(xylims['x3'])
            ax[2].set_ylim(xylims['y3'])
        xlab=ax[0].set_xlabel(labels[0],fontsize='x-large')
        xlab=ax[1].set_xlabel(labels[1],fontsize='x-large')
        ylab=ax[1].set_ylabel(labels[2],fontsize='x-large')
        xlab=ax[2].set_xlabel(labels[3],fontsize='x-large')
        if obj == 'lrg':
            # G distribution even though no Targeting cuts on g
            ax[3].hist(X[:,4],normed=True)
            if xylims is not None:
                ax[3].set_xlim(xylims['x4'])
                ax[3].set_ylim(xylims['y4'])
            xlab=ax[3].set_xlabel(labels[4],fontsize='x-large')
        fn=os.path.join(self.outdir,'%ssample-merged-colors-redshift-%s.png' % (self.prefix,obj))
        plt.savefig(fn,bbox_extra_artists=[xlab], bbox_inches='tight',dpi=150)
        plt.close()
        print('Wrote %s' % fn)


    def plot_galaxy_shapes(self,X,labels,obj='elg',xylims=None):
        '''xylims -- dict of x1,y1,x2,y2,... where x1 is tuple of low,hi for first plot xaxis'''
        fig,ax= plt.subplots(1,4,figsize=(15,3))
        plt.subplots_adjust(wspace=0.2)
        # ba,pa can be slightly greater 1.,180
        assert(np.all(X[:,0] > 0))
        assert(np.all((X[:,1] > 0)*\
                      (X[:,1] < 10)))
        assert(np.all((X[:,2] > 0)*\
                      (X[:,2] <= 1.)))
        assert(np.all((X[:,3] >= 0)*\
                      (X[:,3] <= 180)))
        # plot
        for cnt in range(4):
            # Bin Re
            if cnt == 0:
                bins=np.linspace(0,80,num=20)
                ax[0].hist(X[:,cnt],bins=bins,normed=True)
            else:
                ax[cnt].hist(X[:,cnt],normed=True)
        # lims
        for col in range(4):
            if xylims is not None:
                ax[col].set_xlim(xylims['x%s' % str(col+1)])
                #ax[cnt,1].set_xlim(xylims['x2'])
                #ax[cnt,2].set_xlim(xylims['x3'])
                xlab=ax[col].set_xlabel(labels[col],fontsize='x-large')
                #xlab=ax[cnt,1].set_xlabel(labels[1],fontsize='x-large')
        fn=os.path.join(self.outdir,'%ssample-merged-shapes-%s.png' % (self.prefix,obj))
        plt.savefig(fn,bbox_extra_artists=[xlab], bbox_inches='tight',dpi=150)
        plt.close()
        print('Wrote %s' % fn)

def combine(fns):
    cat=np.array([])
    for i,fn in enumerate(fns): 
        print('reading %d/%d' % (i+1,len(fns)))
        try: 
            tab= fits_table(fn) 
            cat= np.concatenate( (cat,tab.id) )
        except IOError:
            print('Fits file does not exist: %s' % fn)
    return cat


if __name__ == "__main__":
    t0 = Time()
    tbegin=t0
    print('TIMING:after-imports ',datetime.datetime.now())
    parser = argparse.ArgumentParser(description='Generate a legacypipe-compatible CCDs file from a set of reduced imaging.')
    parser.add_argument('--dowhat',choices=['sample','bybrick','merge','cleanup','check'],action='store',help='slurm jobid',default='001',required=True)
    parser.add_argument('--ra1',type=float,action='store',help='bigbox',required=True)
    parser.add_argument('--ra2',type=float,action='store',help='bigbox',required=True)
    parser.add_argument('--dec1',type=float,action='store',help='bigbox',required=True)
    parser.add_argument('--dec2',type=float,action='store',help='bigbox',required=True)
    parser.add_argument('--spacing',type=float,action='store',default=10.,help='choosing N radec pionts so points have spacingxspacing arcsec spacing',required=False)
    parser.add_argument('--ndraws',type=int,action='store',help='default space by 10x10 arcsec, number of draws for all mpi tasks',required=False)
    parser.add_argument('--jobid',action='store',help='slurm jobid',default='001',required=False)
    parser.add_argument('--prefix', type=str, default='', help='Prefix to prepend to the output files.')
    parser.add_argument('--outdir', type=str, default='./radec_points_dir', help='Output directory.')
    parser.add_argument('--nproc', type=int, default=1, help='Number of CPUs to use.')
    args = parser.parse_args()

    radec={}
    radec['ra1']=args.ra1
    radec['ra2']=args.ra2
    radec['dec1']=args.dec1
    radec['dec2']=args.dec2
    if args.ndraws is None:
        # Number that could fill a grid with 5x5 arcsec spacing
        ndraws= int( get_area(radec)/args.spacing**2 * 3600.**2 ) + 1
    else:
        ndraws= args.ndraws
    print('ndraws= %d' % ndraws)
    unique_ids= np.arange(1,ndraws+1)

    # Draws per mpi task
    if args.nproc > 1:
        from mpi4py.MPI import COMM_WORLD as comm
        unique_ids= np.array_split(unique_ids,comm.size)[comm.rank] 
        #nper= len(unique_ids) #int(ndraws/float(comm.size))
    #else: 
    #    nper= ndraws
    t0=ptime('parse-args',t0)

    if args.nproc > 1:
        if comm.rank == 0:
            print('using mpi')
            if not os.path.exists(args.outdir):
                os.makedirs(args.outdir)
        seed = comm.rank
        #cnt=0
        #while os.path.exists(get_fn(args.outdir,seed)):
        #    print('skipping, exists: %s' % get_fn(args.outdir,seed))
        #    cnt+=1
        #    seed= comm.rank+ comm.size*cnt
        # Divide and conquer: each task saves a sample
        if args.dowhat == 'sample':
            # Write {outdir}/input_sample/{prefix}sample_{seed}.fits files
            # Root 0 makes dirs
            #if comm.rank == 0:
            #    dr= get_sample_dir(outdir=args.outdir)
            #    if not os.path.exists(dr):
            #        os.makedirs(dr)
            #    data=dict(dr=dr)
            #else: 
            #    data=None
            # Bcast the dir
            #comm.bcast(data, root=0)
            #print('rank=%d, data["dr"]= ' % comm.rank,data['dr'])
            draw_points(radec,unique_ids, seed=seed,outdir=args.outdir,prefix=args.prefix)
        elif args.dowhat == 'bybrick':
            # Write {outdir}/input_sample/bybrick/{prefix}sample_{brick}_{seed}.fits files
            # Root 0 reads survey bricks, makes dirs
            #if comm.rank == 0:
            #    d= dict(btable= survey_bricks_cut2radec(radec) )
            #    # Root 0 makes all dirs could need    
            #    dr= get_bybrick_dir(outdir=args.outdir)
            #    if not os.path.exists(dr):
            #        os.makedirs(dr)
            #else:
            #    d=None
            # Bcast survey bricks
            #if comm.rank == 1:
            #    print('rank 1 before bcast')
            #comm.bcast(d, root=0)
            #if comm.rank == 1:
            #    print('rank 1 after bcast')
            # All workers
            # Assign list of samples to each worker
            sample_fns= get_sample_fns(outdir=args.outdir,prefix=args.prefix)
            sample_fns= np.array_split(sample_fns,comm.size)[comm.rank] 
            print('rank %d, sample_fns=' % comm.rank,sample_fns)
            # Loop over survey bricks, write brick sample files
            print('before read table: rank=%d' % comm.rank)
            btable= survey_bricks_cut2radec(radec) 
            print('after read table: rank=%d' % comm.rank)
            organize_by_brick(sample_fns,btable,outdir=args.outdir,seed=seed,prefix=args.prefix)
            # DONE at this point        
            #Each task gets its sample file
            ## Divide and conquer: 15k bricks in eBOSS NGC
            #inds= np.arange(len(btable))
            #inds= np.array_split(inds,comm.size)[comm.rank]
            #btable.cut(inds)
            # Gather, done
        elif args.dowhat in ['merge','cleanup']:
            brickfn= os.path.join(args.outdir,'bricks_for_sample.txt')
            # See if we can read text file as opposed to entire fits table
            if os.path.exists(brickfn):
                bricks= np.loadtxt(brickfn,dtype=str)
                bricks= np.array_split(bricks,comm.size)[comm.rank] 
            else:
                btable= survey_bricks_cut2radec(radec)
                bricks= np.array_split(btable.brickname,comm.size)[comm.rank]
                if comm.rank == 0:
                    if not os.path.exists(brickfn):
                        with open(brickfn,'w') as foo:
                            for b in btable.brickname:
                                foo.write('%s\n' % b)
                        print('Wrote %s' % brickfn) 
            # Either create brick samples or remove them if all have been created and concatenated
            cleanup=False 
            if args.dowhat == 'cleanup':
                cleanup=True
            merge_bybrick(bricks,outdir=args.outdir,prefix=args.prefix,cleanup=cleanup)
        elif args.dowhat == 'check':
            fns=glob(os.path.join(args.outdir,'input_sample/bybrick/%ssample_*[0-9][0-9].fits' % args.prefix))
            if len(fns) == 0: raise ValueError
            fns= np.array_split(fns,comm.size)[comm.rank] 
            ids= combine(fns)
            all_ids= comm.gather(ids, root=0)
            if comm.rank == 0:
                print('number of unique ids=%d, total number ra,dec pts=%d' % \
                        (len(set(all_ids)),len(all_ids)))
        #if comm.rank == 0:
        #    merge_draws(outdir=args.outdir,prefix=args.prefix)
            #plotobj= PlotTable(outdir=args.outdir,prefix=args.prefix)
        #images_split= np.array_split(images, comm.size)
        # HACK, not sure if need to wait for all proc to finish 
        #confirm_files = comm.gather( images_split[comm.rank], root=0 )
        #if comm.rank == 0:
        #    print('Rank 0 gathered the results:')
        #    print('len(images)=%d, len(gathered)=%d' % (len(images),len(confirm_files)))
        #    tnow= Time()
        #    print("TIMING:total %s" % (tnow-tbegin,))
        #    print("Done")
    else:
        if not os.path.exists(args.outdir):
            os.makedirs(args.outdir)
        seed= 1
        #cnt=1
        #while os.path.exists(get_fn(args.outdir,seed)):
        #    print('skipping, exists: %s' % get_fn(args.outdir,seed))
        #    cnt+=1
        #    seed= cnt
        if args.dowhat == 'sample':
            # Write {outdir}/input_sample/{prefix}sample_{seed}.fits files
            dr= get_sample_dir(outdir=args.outdir)
            if not os.path.exists(dr):
                os.makedirs(dr)
            draw_points(radec,unique_ids, seed=seed,outdir=args.outdir,prefix=args.prefix)
        elif args.dowhat == 'bybrick':
            # Assign list of samples to each worker
            sample_fns= get_sample_fns(outdir=args.outdir,prefix=args.prefix)
            sample_fns= np.array_split(sample_fns,1)[0] 
            print('sample_fns=',sample_fns)
            # Loop over survey bricks, write brick sample files
            print('before read table:')
            btable= survey_bricks_cut2radec(radec) 
            print('after read table:')
            organize_by_brick(sample_fns,btable,outdir=args.outdir,seed=154,prefix=args.prefix)
            # DEPRECATED:
            ## Write {outdir}/input_sample/bybrick/{prefix}sample_{brick}_{seed}.fits files
            #btable= survey_bricks_cut2radec(radec)
            #with open('eboss_ngc_bricks.txt','w') as foo:
            #    for brick in btable.brickname:
            #        foo.write('%s\n' % brick)
            #dr= get_bybrick_dir(outdir=args.outdir)
            #if not os.path.exists(dr):
            #    os.makedirs(dr)
            ## split each sample into its bricks
            #sample_fns= get_sample_fns(outdir=args.outdir,prefix=args.prefix)
            #sample_fns= np.array_split(sample_fns,1)[0] 
            ## Loop over survey bricks, write brick sample files
            #organize_by_brick(sample_fns,btable,outdir=args.outdir,seed=seed,prefix=args.prefix)
        elif args.dowhat in ['merge','cleanup']:
            brickfn= os.path.join(args.outdir,'bricks_for_sample.txt')
            if os.path.exists(brickfn):
                # Quicker to read 1 column text file
                bricks= np.loadtxt(brickfn,dtype=str)
                bricks= np.array_split(bricks,1)[0] 
            else:
                btable= survey_bricks_cut2radec(radec)
                bricks= np.array_split(btable.brickname,1)[0]
                if not os.path.exists(brickfn):
                    with open(brickfn,'w') as foo:
                        for b in btable.brickname:
                            foo.write('%s\n' % b)
                    print('Wrote %s' % brickfn) 
            # Each task gets a list of bricks, merges sample for each brick, removes indiv brick samps 
            cleanup=False 
            if args.dowhat == 'cleanup':
                cleanup=True
            print('cleanup=',cleanup)
            merge_bybrick(bricks,outdir=args.outdir,prefix=args.prefix,cleanup=cleanup)
        elif args.dowhat == 'check':
            fns=glob(os.path.join(args.outdir,'input_sample/bybrick/%ssample_*[0-9][0-9].fits' % args.prefix))
            if len(fns) == 0: raise ValueError
            fns= np.array_split(fns,1)[0]
            print("len(fns)=",len(fns)) 
            all_ids= combine(fns)
            print('number of unique ids=%d, total number ra,dec pts=%d' % \
                    (len(set(all_ids)),len(all_ids)))
        #
        # Gather, done
        #merge_draws(outdir=args.outdir,prefix=args.prefix)
        #plotobj= PlotTable(outdir=args.outdir,prefix=args.prefix)
        # Plot table for sanity check
        
        ## Create the file
        #t0=ptime('b4-run',t0)
        #runit(image_fn, measureargs,\
        #      zptsfile=zptsfile,zptstarsfile=zptstarsfile)
        #t0=ptime('after-run',t0)
        #tnow= Time()
        #print("TIMING:total %s" % (tnow-tbegin,))
        #print("Done")

