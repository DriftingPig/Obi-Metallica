'''
generate a fits file for randoms of a brick (#TODO more bricks within one fits file)
'''
import astropy.io.fits as fits
import numpy as np
import logging
import sys
import multiprocessing
import sys
import os
NUM=int(sys.argv[1])
print(NUM)
node_tot = int(os.environ['NODE_NUM'])
bricklist = os.environ['obiwan_out']+'/bricklist.txt'
bricks = np.loadtxt(bricklist, dtype = np.str)
randoms_chunk = os.environ['obiwan_out']+'/randoms_chunk/stacked_randoms.fits'
outdir = os.environ['obiwan_out']+'/divided_randoms/'
surveybricks = fits.getdata(os.environ['obiwan_data']+'/survey-bricks.fits.gz')
sel = np.zeros(len(surveybricks),dtype=bool)

for i in range(len(surveybricks)):
    if surveybricks['BRICKNAME'][i] in bricks:
        sel[i]=True

sub_surveybricks = surveybricks[sel]

N_tot = len(sub_surveybricks)
unit = int(N_tot/node_tot)



if NUM<node_tot-1:
    sub_surveybricks = sub_surveybricks[NUM*unit:(NUM+1)*unit]
else:
    sub_surveybricks = sub_surveybricks[NUM*unit:]


def GetBrickSrcs(index, write=True):
    from os.path import isfile
    #if isfile(outdir+'brick_%s.fits' % (sub_surveybricks['BRICKNAME'][index])):
    #    print('file exists for index %d' % index)
    #    return True
    log = logging.getLogger('brick_stats')
    log.info('sub_surveybricks[%d] brickname:%s ra1 %f ra2 %f dec1 %f dec2 %f' %(index, sub_surveybricks['BRICKNAME'][index], sub_surveybricks['RA1'][index], sub_surveybricks['RA2'][index], sub_surveybricks['DEC1'][index], sub_surveybricks['DEC2'][index]))
    
    ra1 = sub_surveybricks['RA1'][index]
    ra2 = sub_surveybricks['RA2'][index]
    dec1 = sub_surveybricks['DEC1'][index]
    dec2 = sub_surveybricks['DEC2'][index]
    flag = True
    TOTAL_COUNT=0
    if True:
        hdu = fits.open(randoms_chunk)
        dat_i = hdu[1].data
        hdu.close()
        TOTAL_COUNT+=len(dat_i)
        dat_ra = dat_i['ra']
        dat_dec = dat_i['dec']
        dat_sel = (dat_ra>ra1)&(dat_ra<ra2)&(dat_dec>dec1)&(dat_dec<dec2)
        dat_i_brick = dat_i[dat_sel]
        if flag:
           dat_brick = dat_i_brick
           if len(dat_brick)>0:
               flag=False
               log.debug(len(dat_brick))
        else:
           dat_brick = np.hstack((dat_brick, dat_i_brick))
           log.debug(len(dat_i_brick))
           log.debug(len(dat_brick))
    #log.info('Total points here are: %d total number of bricks: %d' % (TOTAL_COUNT, len(sub_surveybricks)))
    if write is True and len(np.array(dat_brick))>0:
        log.info('brick %s length %d' %(sub_surveybricks['BRICKNAME'][index], len(dat_brick)))
        cols = fits.ColDefs(np.array(dat_brick))
        HDU = fits.BinTableHDU.from_columns(cols)
        HDU.writeto(outdir+'brick_%s.fits' % (sub_surveybricks['BRICKNAME'][index]), overwrite = True)
    return np.array(dat_brick)

#main
def GetBrickStats():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    log = logging.getLogger('brick_stats')
    log.info('entering GetBrickStats...')
    CPU_COUNT = 32 #multiprocessing.cpu_count()
    log.info('CPU_COUNT %d' %(CPU_COUNT))
    
    p = multiprocessing.Pool(CPU_COUNT)
    tasks=range(len(sub_surveybricks))
    outputs = p.map(GetBrickSrcs, tasks)
    
    #output_len = [len(outputs[i]) for i in range(len(outputs))]
    #bricknames = sub_surveybricks['BRICKNAME']
    #bricks_len_list = np.array(zip(bricknames, output_len))
    #FAILED: #np.savetxt(outdir+'brick_list.out',bricks_len_list)
    GetBrickInfoFile()
    log.info('exiting GetBrickStats...')

def GetBrickInfoFile():
    f = open(outdir+'brick_list.out',"w")
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    log = logging.getLogger('bgrick_stats')
    for brick_i in sub_surveybricks['BRICKNAME']:
        log.info("writing %s" % brick_i)
        try:
        	hdu = fits.open(outdir+'brick_%s.fits' % brick_i)
        	dat = hdu[1].data
        	hdu.close()
        	f.write("%s %d\n" % (brick_i, len(dat)))
        except:
               pass
    f.close()

def run_one_brick():
    print('test run')
    for i in range(1):
        final_array = GetBrickSrcs(i)
        print('brick:%s length:%d' % (sub_surveybricks['BRICKNAME'][i], len(final_array)))
    #    brickname_array = np.array([sub_surveybricks['BRICKNAME'][i] for k in range(len(final_array))])
    #    brickname_cols = fits.Column(name='brickname',array=brickname_array,format='20A')
        cols = fits.ColDefs(final_array)
        print(type(cols))
    #    cols.add_col(brickname_cols)
        HDU = fits.BinTableHDU.from_columns(cols)
        HDU.writeto(outdir+'brick_%s.fits' % (sub_surveybricks['BRICKNAME'][i]), overwrite=True)

if __name__ == '__main__':
    GetBrickStats()
