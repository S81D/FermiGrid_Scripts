#########################################################################################
# Automatically send jobs to the grid, using the container-within-a-container method
# --> specifically designed for building events (w/out LAPPDs) using the DataDecoder TC
#
# Thanks to James Minock for finding a working solution to the grid incompatibility issue 
# and for developing the backbone for the various submission and execution scripts.
# Thanks to Marvin Ascencio and Paul Hackspacher for their help as well.
#
# Author: Steven Doran, May 2023
#########################################################################################

import sys, os
import submit_jobs     # other py script for generating the job submission scripts

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Modify:

TA_tar_name = 'MyToolAnalysis_grid.tar.gz'                    # name of toolanalysis tar-ball
name_TA = 'MyToolAnalysis_5_15_23'                            # name of the TA directory (within tar-ball)

user = 'doran'                                                # annie username

input_path = '/pnfs/annie/scratch/users/doran/'               # path to your grid input location (submit_job_grid.sh, run_container_job.sh, grid_job.sh and necessary submission files)
output_path = '/pnfs/annie/scratch/users/doran/output/'       # grid output location

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
print('\n------- Please ensure you have a produced a <RUN_NUMBER>_beamdb file prior to job submission -------')
print("\n*********************** Don't forget about Daylight Savings!! **************************\n")
run = input('\nRun number:  ')
process_all = input('\nWould you like to submit the entire run? (y/n)   ')

if process_all == 'y':
    process_all = True
elif process_all == 'n':
    process_all = False
else:
    print('\n### ERROR: Please type y or n ###\n')
    exit()


# sort and find the highest numbered part file from that run (need for breaking up the jobs)

all_files = os.listdir('/pnfs/annie/persistent/raw/raw/' + run + '/')

all_files.sort(key=lambda file: int(file.split('p')[-1]))
last_file = all_files[-1]
final_part = int(last_file.split('p')[-1])

if process_all == True:
    print('\nThere are ' + str(final_part+1) + ' part files in this run. Proceeding with job submissions...')
    first_part = int(0)
    last_part = final_part

if process_all == False:
    first_part = int(input('\nPlease specify the first part file of the batch:  '))
    last_part = int(input('\nPlease specify the final part file of the batch:  '))


step_size = int(input('\nPlease specify how many part files per job you would like to submit:   '))
print('\n')

if (step_size > (last_part-first_part + 1)):
    print('\n### ERROR: Stepsize larger than the number of part files selected or first part file > last part file ###\n')
    exit()


# We need to break the batch into seperate jobs. Unless the batch size is evenly divisible by
# the step size, the last job will be smaller than the other ones.

# Also (recent change) for the PreProcessTrigOverlap ToolChain, the trigoverlap files that are produced
# may contain trigger data from the part before or after. For instance, if running over p1, the trigoverlap file 
# for p1 may contain info from p0 and/or p2. To remedy this, we actually copy the raw data files before and after
# the user input request, producing trig overlap files that cover each side. Since (in this code) the PreProcessTrigOverlap
# and DataDecoder ToolChain share the same my_files.txt, we will produce two more files than the user requested. We then 
# have to delete those processed data files after, before copying the "true" processed data back to /scratch.


# this isn't trivial since we could be processing p0 or the final part file
fudge_factor = [[], []]  # [0] = whether to include file before first part, [1] = whether to include one after

part_list = [[], []]     # [0] = first,  [1] = final
for i in range(first_part, last_part + 1, step_size):
    part_list[0].append(i)
    if ((i+step_size-1) > last_part):    # the last job (will be smaller than the others)
        part_list[1].append(last_part)
    else:
        part_list[1].append(i+step_size-1)
    
    if i == 0:                  # if the first part is 0, no fudge factor needed before
        fudge_factor[0].append(0)
    else:
        fudge_factor[0].append(1)
        
    if i == final_part:          # if the last part of the job is the last part file in the run, no fudge factor needed after
        fudge_factor[1].append(0)
    else:
        fudge_factor[1].append(1)


# Submit the entire batch through multiple jobs, based on the user input (above)

for i in range(len(part_list[0])):     # loop over number of jobs

    # grid_job doesn't need the fudge_factor information, the other two do
    
    # create the run_container_job and grid_job scripts
    os.system('rm ' + input_path + 'grid_job.sh')
    submit_jobs.grid_job(run, user, input_path, TA_tar_name, part_list[0][i], part_list[1][i])
    os.system('rm run_container_job.sh')
    submit_jobs.run_container_job(run, name_TA, part_list[0][i], part_list[1][i], fudge_factor[0][i], fudge_factor[1][i])

    # For the DataDecoder TC, we first must produce "my_files.txt", which contains the paths to the raw data files
    # For some reason, when submitting my_files.txt from the input to the worker node, the job could not locate it, aside
    # from the final job in a batch. Therefore, if you submitted 5 jobs in total, only the last one could find the file. 
    # To remedy this, we produce my_files.txt on the worker node based on the input RAWData files in /srv.


    # We can then create the job_submit script that will send our job (with files) to the grid

    os.system('rm submit_grid_job.sh')
    submit_jobs.submit_grid_job(run, part_list[0][i], part_list[1][i], input_path, output_path, TA_tar_name, fudge_factor[0][i], fudge_factor[1][i])


    # Lastly, we can execute the job submission script and send the job to the grid

    os.system('sh submit_grid_job.sh')
    print('\n# # # # # # # # # # # # # # # # # # # # #')
    print('Run ' + run + ' p' + str(part_list[0][i]) + '-' + str(part_list[1][i]) + ' sent')
    print('# # # # # # # # # # # # # # # # # # # # #\n')


print('\nJobs successfully submitted!\n')
