#this code needs one node to get it running
#generate randoms from seeds
from astrometry.util.fits import fits_table, merge_tables
import astropy.io.fits as fits
import numpy as np
import os
import subprocess
topdir_dr8 = os.environ['obiwan_out']
SEED = fits.getdata(os.environ['obiwan_out']+'/seed.fits')
SEL = (SEED['type']!='COMP')&(SEED['type']!='DUP')
SEED = SEED[SEL]
TYPE_sel=SEED['TYPE']
ntype = np.zeros(len(SEED['TYPE']))
ntype[(SEED['TYPE']!='DEV')]=1
ntype[(SEED['TYPE']=='DEV')]=4

def get_radec(radec,\
              ndraws=1,random_state=np.random.RandomState()):
    """Draws ndraws samples of Ra,Dec from the unit sphere.

        Args:
                radec: dict with keys ra1,ra2,dec1,dec2
                        the ra,dec limits for the sample
                ndraws: number of samples
                randome_state: numpy random number generator

        Returns:
                ra,dec: tuple of arrays having length ndraws

        Note:
                Taken from
                https://github.com/desihub/imaginglss/blob/master/scripts/imglss-mpi-make-random.py#L55
        """
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


def draw_points_eboss(radec, seed, ndraws, outdir='./', startid=1):
        """
        Args:
                radec: dict with keys ra1,ra2,dec1,dec2
                        the ra,dec limits for the sample
                unique_ids: list of unique integers for each draw
                obj: star,elg,lrg,qso
                seed: to initialize random number generator
                outdir: dir to write randoms to

        Returns:
                Nothing, but write a fits_table containing the unique id, ra, dec
                        and color + redshift + morphology info for each source
        """
        print('entered draw_points')
        random_state = np.random.RandomState(seed)
        ra,dec = get_radec(radec,ndraws=ndraws,random_state=random_state)
        T = fits_table()
        T.set('id',np.arange(ndraws))
        T.set('ra',ra)
        T.set('dec',dec)
        #only chunk21 for now
        T.set('ba', np.random.uniform(0.2,1.,size=ndraws))
        T.set('pa', np.random.uniform(0.,180.,size=ndraws))
        ids = random_state.randint(low=0,high=len(SEED),size=ndraws)
        T.set('g',SEED['g'][ids])
        T.set('r',SEED['r'][ids])
        T.set('z',SEED['z'][ids])
        T.set('n',ntype[ids])
        T.set('rhalf',SEED['rhalf'][ids])
        T.set('id_sample', SEED['objid'][ids])
        T.set('redshift', SEED['redshift'][ids])
        #T.set('redshift', SEED['hsc_mizuki_photoz_best'][ids])
        fn = topdir_dr8+'randoms_chunk/randoms_ra1%.2fdec1%.2fra2%.2fdec2%.2f.fits'%(radec['ra1'],radec['dec1'],radec['ra2'],radec['dec2'])
        T.writeto(fn)
        print('Wrote %s' % fn)
#step 1
radecs = np.loadtxt(os.environ['obiwan_out']+'/radec.txt')
if len(radecs.shape)==1:
    radecs=[radecs]
N=len(radecs)
i=0
for radec in radecs:
    print('%d/%d'%(i,N))
    i+=1
    radec={'ra1':radec[0],'ra2':radec[1],'dec1':radec[2],'dec2':radec[3]}
    draw_points_eboss(radec,1,int(os.environ['TOTAL_POINTS']))

#step2 stack

SV_brick_topdir = topdir_dr8+'randoms_chunk/'
import glob
fns = glob.glob(SV_brick_topdir+'randoms_*')
t=None
from astropy.table import vstack,Table
for fn in fns:
    print(fn)
    t_i = Table.read(fn)
    if t is None:
       t=t_i
    else:
       t = vstack((t,t_i))
t.write(SV_brick_topdir+'stacked_randoms.fits',overwrite=True)
print('done')

