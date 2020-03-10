import matplotlib
matplotlib.use('Agg')
import pylab as plt
from glob import glob

from astrometry.util.fits import *
from astrometry.libkd.spherematch import *

from tractor import *

dataset = 'DR2m'
fns = glob('dr2m/tractor/*/tractor-*.fits')
fns.sort()
fns = fns[:10]

T = merge_tables([fits_table(fn) for fn in fns])

print len(T), 'total'
T.cut(T.brick_primary)
print len(T), 'primary'

T.mags = NanoMaggies.nanomaggiesToMag(T.decam_flux)
T.gmag = T.mags[:,1]
T.rmag = T.mags[:,2]
T.zmag = T.mags[:,4]
T.grzbright = reduce(np.logical_and,
                     [T.decam_flux[:,1] * np.sqrt(T.decam_flux_ivar[:,1]) > 5.,
                      T.decam_flux[:,2] * np.sqrt(T.decam_flux_ivar[:,2]) > 5.,
                      T.decam_flux[:,4] * np.sqrt(T.decam_flux_ivar[:,4]) > 5.,
                      ])

print 'Checking finite-ness of decam_fracflux'
#assert(np.all(np.isfinite(T.decam_fracflux)))
I,B = np.nonzero(np.logical_not(np.isfinite(T.decam_fracflux)))
print len(I), 'infinite DECAM_FRACFLUX'
i = I[0]
b = B[0]
t = T[i]
print 'Example:', repr(t)
print 'band', b


sys.exit(0)


T.t0 = np.array([t[0] for t in T.type])

P = T[T.t0 == 'P']
S = T[T.t0 == 'S']
E = T[T.t0 == 'E']
D = T[T.t0 == 'D']
C = T[T.t0 == 'C']
G = T[np.array([t in 'EDC' for t in T.t0])]

print len(P), 'PSF'
print len(S), 'Simple'
print len(E), 'Exp'
print len(D), 'Dev'
print len(C), 'Comp'

plt.clf()
plt.hist(np.clip(C.fracdev, -0.2, 1.2), range=(-0.1,1.1), bins=50)
plt.xlabel('FracDev')
plt.title('Composite galaxies')
plt.savefig('fracdev.png')

print 'Checking finite-ness of shapes'
assert(np.all(np.isfinite(E.shapeexp_r)))
assert(np.all(np.isfinite(E.shapeexp_e1)))
assert(np.all(np.isfinite(E.shapeexp_e2)))

assert(np.all(np.isfinite(D.shapedev_r)))
assert(np.all(np.isfinite(D.shapedev_e1)))
assert(np.all(np.isfinite(D.shapedev_e2)))

assert(np.all(np.isfinite(C.shapeexp_r)))
assert(np.all(np.isfinite(C.shapeexp_e1)))
assert(np.all(np.isfinite(C.shapeexp_e2)))
assert(np.all(np.isfinite(C.shapedev_r)))
assert(np.all(np.isfinite(C.shapedev_e1)))
assert(np.all(np.isfinite(C.shapedev_e2)))

assert(np.all(E.shapeexp_r > 0.))
assert(np.all(D.shapedev_r > 0.))
assert(np.all(C.shapeexp_r > 0.))
assert(np.all(C.shapedev_r > 0.))

print 'Checking flux distributions'
plt.clf()
lo,hi = -1, 20
plt.hist(np.clip(T.decam_flux[:,1], lo, hi), range=(lo,hi), bins=50,
         histtype='step', color='g')
plt.hist(np.clip(T.decam_flux[:,2], lo, hi), range=(lo,hi), bins=50,
         histtype='step', color='r')
plt.hist(np.clip(T.decam_flux[:,4], lo, hi), range=(lo,hi), bins=50,
         histtype='step', color='m')
plt.savefig('flux.png')

plt.clf()
lo,hi = 13,26
plt.hist(np.clip(T.mags[:,1], lo, hi), range=(lo,hi), bins=50,
         histtype='step', color='g')
plt.hist(np.clip(T.mags[:,2], lo, hi), range=(lo,hi), bins=50,
         histtype='step', color='r')
plt.hist(np.clip(T.mags[:,4], lo, hi), range=(lo,hi), bins=50,
         histtype='step', color='m')
plt.savefig('mags.png')

plt.clf()
plt.hist(T.rmag, range=(lo,hi), bins=50, histtype='step', color='k')
n,b,pp = plt.hist(P.rmag, range=(lo,hi), bins=50, histtype='step', color='g')
n,b,ps = plt.hist(S.rmag, range=(lo,hi), bins=50, histtype='step', color='0.5')
n,b,pe = plt.hist(E.rmag, range=(lo,hi), bins=50, histtype='step', color='b')
n,b,pd = plt.hist(D.rmag, range=(lo,hi), bins=50, histtype='step', color='r')
n,b,pc = plt.hist(C.rmag, range=(lo,hi), bins=50, histtype='step', color='m')
plt.legend((pp[0],ps[0],pe[0],pd[0],pc[0]),
           ('Point src', 'Simple', 'Exp', 'deV', 'Comp'),
           'upper left')
plt.xlabel('r mag')
plt.title('Mag distribution by classification')
plt.savefig('mags2.png')

ax = [-0.5, 2.5, -1, 3]
I = P.grzbright
plt.clf()
plt.plot(P.gmag[I] - P.rmag[I], P.rmag[I] - P.zmag[I], 'b.', alpha=0.1)
plt.xlabel('g - r (mag)')
plt.ylabel('r - z (mag)')
plt.title('Point sources')
plt.axis(ax)
plt.savefig('cc-p.png')

I = S.grzbright
plt.clf()
plt.plot(S.gmag[I] - S.rmag[I], S.rmag[I] - S.zmag[I], 'b.', alpha=0.1)
plt.xlabel('g - r (mag)')
plt.ylabel('r - z (mag)')
plt.title('Simple galaxies')
plt.axis(ax)
plt.savefig('cc-s.png')

plt.clf()
I = E.grzbright
plt.plot(E.gmag[I] - E.rmag[I], E.rmag[I] - E.zmag[I], 'b.', alpha=0.1)
I = D.grzbright
plt.plot(D.gmag[I] - D.rmag[I], D.rmag[I] - D.zmag[I], 'r.', alpha=0.1)
I = C.grzbright
plt.plot(C.gmag[I] - C.rmag[I], C.rmag[I] - C.zmag[I], 'm.', alpha=0.1)
plt.xlabel('g - r (mag)')
plt.ylabel('r - z (mag)')
plt.title('Galaxies')
plt.axis(ax)
plt.savefig('cc-g.png')


# At least one flux should be positive...
I = np.flatnonzero(np.all(T.decam_flux <= 0, axis=1))
print 'Sources with all fluxes not positive:', len(I)
T[I].writeto('neg.fits')
assert(np.all(np.any(T.decam_flux > 0, axis=1)))

# Match distances
I,J,d = match_radec(T.ra, T.dec, T.ra, T.dec, 10./3600., notself=True)
K = np.flatnonzero(I < J)
I,J,d = I[K],J[K],d[K]

plt.clf()
plt.hist(d*3600., range=(0,10), bins=50)
plt.xlabel('Arcsec between pairs')
plt.title('%s -- close pairs' % dataset)
plt.savefig('dists.png')

I,J,d = match_radec(T.ra, T.dec, T.ra, T.dec, 1./3600., notself=True)
K = np.flatnonzero(I < J)
I,J,d = I[K],J[K],d[K]

print 'Fracflux for nearby pairs:'
B = np.array([1,2,4])
for i,j in zip(I,J)[:10]:
    print T.decam_fracflux[i,B], T.decam_fracflux[j,B]
    

print 'r-band fluxes and fracfluxes:'
b = 2
for i,j in zip(I,J)[:10]:
    print 'fluxes', T.decam_flux[i,b], T.decam_flux[j, b], 'fracs', T.decam_fracflux[i,b], T.decam_fracflux[j,b]

plt.clf()
#plt.plot(T.decam_flux[:,2], T.dchisq[:,1] - T.dchisq[:,0], 'b.')
#
plt.plot(P.rmag, P.dchisq[:,1] - P.dchisq[:,0], 'b.', alpha=0.1)
plt.plot(S.rmag, S.dchisq[:,1] - S.dchisq[:,0], 'g.', alpha=0.1)
p1 = plt.plot([],[],'b.')
p2 = plt.plot([],[],'g.')
plt.ylabel('dchisq_simple - dchisq_pointsource')
plt.xlabel('r mag')
plt.legend((p2[0],p1[0]), ('Simple','PointSource'), 'upper right')
plt.xlim(18,26)
plt.yscale('symlog', linthreshy = 1, linscaley = 0.5)
plt.ylim(-1e5, 1e5)
plt.title(dataset)
plt.savefig('dchi.png')

ax1 = plt.axis()

plt.ylim(-100, 100)
plt.xlim(20, 26)
ax2 = plt.axis()
plt.savefig('dchi2.png')

plt.plot(G.rmag, G.dchisq[:,1] - G.dchisq[:,0], 'r.', alpha=0.1)
p3 = plt.plot([],[],'r.')
plt.legend((p3[0], p2[0],p1[0]), ('Galaxies', 'Simple','PointSource'),
           'upper right')
plt.axis(ax1)
plt.savefig('dchi3.png')

plt.axis(ax2)
plt.savefig('dchi4.png')

plt.clf()
plt.hist(T.dchisq[:,1] - T.dchisq[:,0], range=(-30, 30), bins=50,
         histtype='step', color='b')
plt.xlabel('dchisq_simple - dchisq_psf')
plt.savefig('dchi5.png')
