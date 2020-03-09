import sys
import os
from astropy.table import Table, vstack
#total splited files, it denpends on the size of all data
tot_seps = int(sys.argv[1])
#name of run, currently I have: elg_like_run, elg_ngc_run
name_for_run=sys.argv[2]


topdir_obiwan_out = os.environ['obiwan_out']


def fn_generator_sim(split_idx=0, N_splits=1):
        return os.path.join(topdir_obiwan_out,'subset','sim_%s_part%d_of_%d.fits' % (name_for_run, split_idx, N_splits))


tab = None
for i in range(0,tot_seps):
    fn_i = fn_generator_sim(split_idx=i, N_splits=tot_seps)
    print(fn_i)
    tab_i = Table.read(fn_i)
    if tab is None:
       tab = tab_i
    else:
       tab = vstack((tab, tab_i))
print('writing')
tab.write(os.path.join(topdir_obiwan_out,'subset','sim_%s.fits'%(name_for_run)),overwrite=True)

