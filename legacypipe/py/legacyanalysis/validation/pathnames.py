import os

def bash(cmd):
    ret= os.system('%s' % cmd)
    if ret:
        print 'command failed: %s' % cmd
        raise ValueError 

def make_dir(dir):
    if not os.path.exists(dir): bash('mkdir -p %s' % dir)

def get_outdir(comparison):
    '''
    Returns the relative path (to legacypipe/py) for desired comparison
    *comparison* : string, which comparison you are doing: bmd (bass,mosaic,decals), cosmos (Johans/Jeffs comparisons), dr23 (Johans dr2 dr3 comparison) 
    '''
    if 'VALIDATION_DIR' in os.environ:
        outdir = os.getenv('VALIDATION_DIR')
    else:
        outdir = 'validation'
    # Add appropriate dir
    if comparison == 'test':
        dir= os.path.join(outdir,'test/')
    elif comparison == 'bmd':
        dir= os.path.join(outdir,'bass-mosaic-decals/')
    elif comparison == 'cosmos':
        dir= os.path.join(outdir,'cosmos/')
    elif comparison == 'dr23':
        dir= os.path.join(outdir,'dr2dr3/')
    else: raise ValueError
    make_dir(dir)
    return dir

def get_indir(comparison,indir='/project/projectdirs/desi/imaging/data/validation'):
    '''
    Returns the absolute path to data for desired comparison
    *comparison* : string, which comparison you are doing: bmd (bass,mosaic,decals), cosmos (Johans/Jeffs comparisons), dr23 (Johans dr2 dr3 comparison) 
    '''
    if comparison == 'bmd':
        dir= os.path.join(indir,'bass-mosaic-decals/')
    elif comparison == 'cosmos':
        dir= os.path.join(indir,'cosmos/')
    elif comparison == 'dr23':
        dir= os.path.join(indir,'dr2dr3/')
    else: raise ValueError
    return dir


