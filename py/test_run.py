from legacypipe.runbrick import run_brick
from legacypipe.survey import LegacySurveyData
'''
run_brick('1273p255', LegacySurveyData, \
        #outdir = '.',\
        threads=1, \
        zoom="0 500 0 500", \
        wise=False, \
        #force-all=True, \
        hybridPsf=True, writePickles=False, do_calibs=True, \
        write_metrics=False, pixPsf=True, blobxy=None, early_coadds=False, \
        splinesky=True, ceres=False,  \
        plotbase='sim',\
        allbands='ugrizY', stages = ['writecat'], plots = False)
'''
from legacypipe.runbrick import main
#def main(args):
#    run_brick(args)

oytdir = './'
main(args=['--brick', '1102p240', '--zoom', '500', '600', '650', '750',\
                   '--force-all', '--no-write', '--no-wise',\
                               #'--rex', #'--plots',\
                                              '--survey-dir', surveydir,\
                                                             '--outdir', outdir])
