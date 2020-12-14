import os,sys
import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

# required arg
parser.add_argument("sub_file_name",type=str,help="Name of submission file that we should write to.")
parser.add_argument("-c","--config",required=True,type=str,help="Config script to run.")
parser.add_argument("-o","--out_dir",required=True,type=str,help="Directory to copy output to.")
environment = parser.add_mutually_exclusive_group(required=True)
environment.add_argument("--env_script",type=str,default=None,help="Environment script to run before running fire.")
environment.add_argument("--ldmx_version",type=str,default=None,help="LDMX Version to pick a pre-made environment script.")

# optional arg
parser.add_argument("--input_dir",default=None,type=str,help="Directory containing input files to run over.")
parser.add_argument("--num_jobs",type=int,default=None,help="Number of jobs to run (if not input directory given).")
parser.add_argument("--config_args",type=str,default='',help="Extra arguments to be passed to the configuration script.")
parser.add_argument("--start_job",type=int,default=0,help="Starting number to use when counting jobs (and run numbers)")

# rarely-used optional args
parser.add_argument("-t","--test",action='store_true',dest='test',help="Don't submit the job to the batch.")
parser.add_argument("--nonice",action='store_true',dest="nonice",help="Do not run this at nice priority.")
parser.add_argument("--run_script",type=str,help="Script to run jobs on worker nodes with.",default='%s/run_fire.sh'%os.path.dirname(os.path.realpath(__file__)))
parser.add_argument("--scratch_root",type=str,help="Directory to create any working directories inside of.",default='/export/scratch/user/%s'%os.environ['USER'])
parser.add_argument("--sleep",type=int,help="Time in seconds to sleep before starting the next job.",default=60)

arg = parser.parse_args()

jobs = 0
if arg.input_dir is not None :
    full_input_dir = os.path.realpath(arg.input_dir)
    input_file_list = [ os.path.join(full_input_dir,f) for f in os.listdir(arg.input_dir) ]
    if arg.num_jobs is not None :
        jobs = min(arg.num_jobs,len(input_file_list))
    else :
        jobs = len(input_file_list)
elif arg.num_jobs is not None :
    jobs = arg.num_jobs
else :
    parser.error("Either an input directory of files or a number of jobs needs to be given.")

# make the output directory
full_out_dir_path = os.path.realpath(arg.out_dir)
if not os.path.exists(full_out_dir_path):
    os.makedirs(full_out_dir_path)

if not os.path.exists(full_out_dir_path):
    raise Exception('Unable to create output directory "%s"'%full_out_dir_path)

full_config_path = os.path.realpath(arg.config)
if not os.path.exists(full_config_path) :
    raise Exception('Config script "%s" does not exist.'%full_config_path)

if arg.env_script is not None :
    env_script = os.path.realpath(arg.env_script)
elif arg.ldmx_version is not None :
    env_script = "/local/cms/user/%s/ldmx/stable-installs/%s/setup.sh"%(os.environ['USER'],arg.ldmx_version)
else :
    parser.error('Either a full env script \'--env_script\' or a ldmx_version \'--ldmx_version\' must be specified.')

if not os.path.exists(env_script) :
    raise Exception('Environment script "%s" does not exist.'%env_script)

header_template="""
# Header for Jobs, defines global options and variables for use in this condor submission
executable          =  {executable}
universe            =  vanilla
requirements        =  Arch==\"X86_64\" && (Machine  !=  \"zebra01.spa.umn.edu\") && (Machine  !=  \"zebra02.spa.umn.edu\") && (Machine  !=  \"zebra03.spa.umn.edu\") && (Machine  !=  \"zebra04.spa.umn.edu\") && (Machine  !=  \"caffeine.spa.umn.edu\")
+CondorGroup        =  \"cmsfarm\"
nice_user           = {nice}
request_memory      =  4 Gb
on_exit_hold        = (ExitCode != 0)
env_script          = {env_script}
scratch_root        = {scratch_root}
config_script       = {config}
output_dir          = {out_dir}

"""

with open(arg.sub_file_name,'w') as submission_file :
    submission_file.write(header_template.format(
          executable=os.path.realpath(arg.run_script),
          nice=str(not arg.nonice),
          env_script = env_script,
          scratch_root = arg.scratch_root,
          config = full_config_path,
          out_dir = full_out_dir_path
          ))

    if arg.test :
        submission_file.write('output = %s/$(Cluster)-$(Process).out\n'%(full_out_dir_path))
        submission_file.write('error  = %s/$(Cluster)-$(Process).out\n'%(full_out_dir_path))

    # This needs to match the correct order of the arguments in the run_fire.sh script
    #   The input file and any extra config arguments are optional and come after the
    #   three required arguments
    arguments = '$(scratch_root)/$(Cluster)-$(Process) $(env_script) $(config_script) $(output_dir)'

    if arg.input_dir is not None :
        arguments += ' $(input_file)'

    arguments += ' --run_number %(run_number) ' + arg.config_args

    submission_file.write('arguments = %s\n'%arguments)
    submission_file.write('next_job_start_delay = %d\n'%arg.sleep)

    if arg.input_dir is not None :
        if jobs != len(input_file_list) :
            # need special listing
            #  -> construct list of input files and run numbers
            submission_file.write('queue run_number, input_file from (\n')
            for run in range(jobs) :
                submission_file.write('\t%d, %s\n'%(arg.start_job+run,input_file_list[run]))
            submission_file.write(')\n')
        else :
            # submitting the whole directory
            submission_file.write('run_number=$(Process)\n')
            submission_file.write('queue input_file matching files %s/*\n'%(full_input_dir))
    else :
        # submitting a range of run numbers
        submission_file.write('queue run_number from seq %d %d\n'%(arg.start_job,arg.start_job+arg.num_jobs-1))

