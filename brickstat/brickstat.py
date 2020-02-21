#e.g. python brickstat.py --name_for_run elg_like_run --rs more_rs0 --real_bricks_fn real_bricks_chunk21.txt
# python brickstat.py --name_for_run chunk23_final --rs rs0 --real_bricks_fn real_bricks_chunk23.txt
#  python brickstat.py --name_for_run dr8_SV --rs rs0 --real_bricks_fn SV_bricks.txt
import os
NAME_FOR_RUN=None
RS=None
REAL_BRICKS_FN=None

def mkdir(fn):
    if os.path.exists(fn):
       pass
    else:
       import subprocess
       subprocess.call(["mkdir","-p",fn])

def OneBrickClassify(brickname):
    print(brickname)
    global NAME_FOR_RUN
    global RS
    global REAL_BRICKS_FN
    log_dir = os.environ['obiwan_out']+'/output/logs/%s/%s/log.%s'%(brickname[:3],RS,brickname)
    if os.path.isfile(log_dir) is False:
        f1 = open('./%s/UnfinishedBricks.txt'%NAME_FOR_RUN, 'a')
        f1.write(str(brickname)+'\n')
        f1.close()
        return -1
    flag = False
    if "decals_sim:All done!" in open(log_dir).read():
        f2 = open('./%s/FinishedBricks.txt'%NAME_FOR_RUN, 'a')
        f2.write(str(brickname)+'\n')
        f2.close()
        return 1
    f4 = open('./%s/UnfinishedBricks.txt'%NAME_FOR_RUN, 'a')
    f4.write(str(brickname)+'\n')
    f4.close()
    return 2

def BrickClassify():
    import numpy as np
    import multiprocessing as mp
    N=16
    p = mp.Pool(N)
    global NAME_FOR_RUN
    f1 = open('./%s/FinishedBricks.txt'%NAME_FOR_RUN, 'w')
    f1.close
    f2 = open('./%s/UnfinishedBricks.txt'%NAME_FOR_RUN, 'w')
    f2.close()
    bricks = np.loadtxt('./real_brick_lists/%s'%REAL_BRICKS_FN, dtype=np.str)
    p.map(OneBrickClassify,bricks)

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,description='brickstat')
    parser.add_argument('--name_for_run', type=str, required=True, help='name of production run')#currently: elg_like_run,elg_ngc_run
    parser.add_argument('--rs', type=str, required=True, help='e.g. rs0, more_rs0,rs200')
    parser.add_argument('--real_bricks_fn', type=str, required=True, help='bricks processed in this run')
    return parser
if __name__ == '__main__':
    parser= get_parser()
    args = parser.parse_args()
    #import pdb;pdb.set_trace()
    #global NAME_FOR_RUN
    #global RS
    #global REAL_BRICKS_FN
    NAME_FOR_RUN = args.name_for_run
    RS = args.rs
    REAL_BRICKS_FN = args.real_bricks_fn   
    mkdir(NAME_FOR_RUN) 
    BrickClassify()
