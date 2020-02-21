Step 0: make a docker image compatible with the corresponding version of legacypipe

Step 1: seed_formation: get all the seed necessary to generate input randoms

Step 2: bricklist_generation: generate a list of bricks that needs to be processed

Step 3: radec_generation: generate all the radec region that will be made randoms on

Step 4: random_generation: generate the randoms in regions confined by the previous step

Step 5: random_division: divide the randoms into each brick

Step 6: obiwan_run: run obiwan with the input randoms and a list of bricks
        |
        | 
         --- meta: name_for_run; name_for_randoms metadata
        |
        |
         --- run_one_brick: run one test brick to see if everything works OK
        |
        |
         ---terminal_debug_run: run the obiwan code on terminal, for pdb debugging
        |
        |
         --- mpi4py_run: run a lot of bricks with multiple nodes
        |
        |
         --- brick_condition: 
             |
               --- list of finished, unfinished bricks for each name_for_run
             |
               --- brickstat.py: update finished, unfinished bricklist

directory needed for each production run:
name_for_run=XXXX
make a obiwan_out=$obiwan_run/$name_for_run/
$obiwan_out/run/name_for_run/output #for obiwan output
$obiwan_out/run/name_for_run/divided_randoms #brick-[brickname].fits
$obiwan_out/run/name_for_run/randoms_chunk  #whole chunk of randoms
$obiwan_code/brickstat/$name_for_run
