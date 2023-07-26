import csv
import math
import subprocess
import logging
import sys
import os
import xml.etree.ElementTree as ET
import pandas as pd
import shutil
from collections import OrderedDict
from collections import defaultdict

#return_codes
#0 : Success
#-1: Failure (Defined in the Toolbox)
#1: Infeasible or unbounded problem (not implemented in the toolbox, functionally same as -1. For a possiblity of a graphical depiction)

class FlexToolRunner:
    """
    Define Class to run the model and read and recreate the required config files:
    """

    def __init__(self) -> None:
        logging.basicConfig(
            stream=sys.stderr,
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        translation = {39: None}
        # make a directory for model unit tests
        if not os.path.exists("./tests"):
            os.makedirs("./tests")
        # read the data in
        self.timelines = self.get_timelines()
        self.model_solve = self.get_solves()
        self.solve_modes = self.get_solve_modes("solve_mode")
        self.highs_presolve = self.get_solve_modes("highs_presolve")
        self.highs_method = self.get_solve_modes("highs_method")
        self.highs_parallel = self.get_solve_modes("highs_parallel")
        self.solve_period_years_represented = self.get_solve_period_years_represented()
        self.solvers = self.get_solver()
        self.timeblocks = self.get_timeblocks()
        self.timeblocks__timeline = self.get_timeblocks_timelines()
        self.timeblocks_used_by_solves = self.get_timeblocks_used_by_solves()
        self.invest_periods = self.get_list_of_tuples('input/solve__invest_period.csv')
        self.realized_periods = self.get_list_of_tuples('input/solve__realized_period.csv')
        self.invest_realized_periods =  self.get_list_of_tuples('input/solve__invest_realized_period.csv')
        self.fix_storage_periods = self.get_list_of_tuples('input/solve__fix_storage_period.csv')
        self.solver_precommand = self.get_solver_precommand()
        self.solver_arguments = self.get_solver_arguments()
        self.included_solves = self.get_included_solves()
        self.rolling_times = self.get_rolling_times()
        self.new_step_durations=self.get_new_step_durations()
        self.create_timeline_from_timestep_duration()
        #self.write_full_timelines(self.timelines, 'steps.csv')
    
    def get_solves(self):
        """
        read in
        the list of solves, return it as a list of strings
        :return:
        """
        with open("input/model__solve.csv", 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            model__solve = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    model__solve[datain[0]].append((datain[1]))
                except StopIteration:
                    break
        return model__solve

    def get_solve_modes(self, parameter):
        """
        read in
        the list of solve modes, return it as a list of strings
        :return:
        """
        with open("input/solve_mode.csv", 'r') as solvefile:
            header = solvefile.readline()
            solves = solvefile.readlines()
            params = []
            right_params = {}
            for solve in solves:
                solve_stripped = solve.rstrip()
                params.append(solve_stripped.split(","))
            for param in params:
                if param[0] == parameter:
                    right_params[param[1]] = param[2]
        return right_params

    def get_solve_period_years_represented(self):
        """
        read the years presented by each period in a solve
        :return: dict : (period name, years represented)
        """
        with open('input/solve__period__years_represented.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            years_represented = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    years_represented[datain[0]].append((datain[1], datain[2]))
                except StopIteration:
                    break
        return years_represented

    def get_solver(self):
        """
        read in
        the list of solvers for each solve. return it as a list of strings
        :return:
        """
        with open('input/solver.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            solver_dict = defaultdict()
            while True:
                try:
                    datain = next(filereader)
                    solver_dict[datain[0]] = datain[1]
                except StopIteration:
                    break

        #with open("input/solver.csv", 'r') as solvefile:
        #    header = solvefile.readline()
        #    solvers = solvefile.readlines()
        #    for solver in solvers:
        #        solve__period = solver.split(",")
        #        solver_dict[solve__period[0]] = solve__period[1]
        return solver_dict

    def get_solver_precommand(self):
        """
        read in
        the solver_precommand for each solve. return it as a list of strings
        :return:
        """
        with open('input/solver_precommand.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            solver_precommand_dict = defaultdict()
            while True:
                try:
                    datain = next(filereader)
                    solver_precommand_dict[datain[0]] = datain[1]
                except StopIteration:
                    break
        return solver_precommand_dict
        
    def get_solver_arguments(self):
        """
        read in
        the solver commands for each solve. return it as a list of strings
        :return:
        """
        with open('input/solver_arguments.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            solver_arguments_dict = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    solver_arguments_dict[datain[0]].append((datain[1]))
                except StopIteration:
                    break
        return solver_arguments_dict

    def get_included_solves(self):
        """
        read in
        the included_solves for each solve. return it as a dict of list of strings
        :return:
        """
        with open('input/solve__include_solve.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            included_solves_dict = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    included_solves_dict[datain[0]]= datain[1]
                except StopIteration:
                    break
        return included_solves_dict

    def get_rolling_times(self):
        """
        read in
        the rolling_times for each solve. return it as a dict of list of ints
        :return:
        """
        with open('input/solve__rolling_times.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            rolling_parameters = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    rolling_parameters[datain[0]].append((datain[1],datain[2]))
                except StopIteration:
                    break
        rolling_times=defaultdict(list)
        for solve, data in list(rolling_parameters.items()):
            start = None
            horizon = 0
            jump = 0
            duration = -1
            for param_value in data:
                if "rolling_start_time" == param_value[0]:
                    #timestamp
                    start = param_value[1]
                if "rolling_duration" in param_value[0]:
                    duration = float(param_value[1])
                if "rolling_solve_horizon" in param_value[0]:
                    horizon = float(param_value[1])
                if "rolling_solve_jump" in param_value[0]:
                    jump = float(param_value[1])
            
            if self.solve_modes[solve] == 'rolling_window' and (horizon == 0 or jump == 0):
                logging.error("When using rolling_window solve mode, rolling_solve_horizon and rolling_solve_jump have to defined and not be 0")
                exit(-1)
            rolling_times[solve] = [start,jump,horizon,duration]

        return rolling_times

    def create_timeline_from_timestep_duration(self):
        for timeblockSet_name, timeblockSet in list(self.timeblocks.items()):
            if timeblockSet_name in self.new_step_durations.keys():
                step_duration= float(self.new_step_durations[timeblockSet_name])
                #create the new timeline
                timeline_name = self.timeblocks__timeline[timeblockSet_name][0]
                old_steps = self.timelines[timeline_name]
                new_steps = []
                new_timeblocks = []
                for timeblock in timeblockSet:
                    first_step = timeblock[0]
                    first_index = [step[0] for step in old_steps].index(timeblock[0])
                    step_counter = float(old_steps[first_index][1])
                    last_index = first_index + int(float(timeblock[1]))
                    added_steps = 0
                    for step in old_steps[first_index:last_index]:
                        if step_counter >= step_duration:
                            new_steps.append((first_step,str(step_counter)))
                            first_step = step[0]
                            step_counter=0
                            added_steps += 1
                            if step_counter> step_duration:
                                logging.warning("Warning: All new steps are not the size of the given step duration. The new step duration has to be multiple of old step durations for this to happen.")
                        step_counter += float(step[1])
                    new_steps.append((first_step,str(step_counter)))
                    new_timeblocks.append((timeblock[0], added_steps))
                self.timeblocks[timeblockSet_name] = new_timeblocks 
                new_timeline_name = timeline_name+ "_"+ timeblockSet_name 
                self.timelines[new_timeline_name] = new_steps
                self.timeblocks__timeline[timeblockSet_name] = [new_timeline_name]

    def create_averaged_timeseries(self,solve):
        timeseries_list=['pt_node.csv','pt_process.csv','pt_profile.csv','pt_process_source.csv','pt_process_sink.csv','pt_reserve__upDown__group.csv']
        if not any(self.timeblocks_used_by_solves[solve]) in self.new_step_durations.keys():
            for timeseries in timeseries_list:
                shutil.copy('input/'+timeseries,'solve_data/'+timeseries)
        else:
            for timeseries in timeseries_list:
                with open('input/'+ timeseries,'r') as blk:
                    filereader = csv.reader(blk, delimiter=',')
                    with open('solve_data/'+timeseries,'w', newline='') as solve_file:
                        filewriter = csv.writer(solve_file,delimiter=',')
                        headers = next(filereader)
                        filewriter.writerow(headers)
                        #assumes that the data is in the format:
                        #[group1, group2, ... group_last, time, numeric_value]
                        #ie. the numeric data is the last column and the timestep is the one before it.
                        #and that there are rows from other groups between the rows of one group 
                        time_index = headers.index('time')
                        timelines=[]
                        for period, timeblockSet in self.timeblocks_used_by_solves[solve]:
                            timeline = self.timeblocks__timeline[timeblockSet][0]
                            if timeline not in timelines:
                                if len(timelines) != 0:
                                    logging.error("Error: More than one timeline in the solve or the same timeline with different step durations in different timeblockSets")
                                    exit(-1)
                                timelines.append(timeline)

                        for timeline in timelines:
                            new_timeline = self.timelines[timeline]    
                            started = False
                            last_timestamp = new_timeline[-1][0]
                            last_timestep_length = float(new_timeline[-1][1])
                            last = False
                            while True:
                                try:
                                    datain = next(filereader)
                                    if not started:
                                        row = datain[0:time_index+1]
                                        next_index = 1
                                        values = []
                                        started = True
                                        values.append(float(datain[time_index+1]))

                                    elif datain[time_index] == new_timeline[next_index][0]:
                                        #write row
                                        out_value = sum(values)/len(values)
                                        row.append(out_value)
                                        filewriter.writerow(row)

                                        #new start values
                                        row = datain[0:time_index+1]
                                        values = [float(datain[time_index+1])]
                                        next_index += 1
                                        if next_index > len(new_timeline)-1:
                                            next_index = 0

                                        if datain[time_index] == last_timestamp:
                                            last = True
                                            counter = 0

                                    elif last:
                                        if counter >= last_timestep_length:
                                            #write row
                                            out_value = sum(values)/len(values)
                                            row.append(out_value)
                                            filewriter.writerow(row)
                                            break
                                        values.append(float(datain[time_index+1]))
                                        counter += 1
                                    else:
                                        values.append(float(datain[time_index+1]))
                                except StopIteration:
                                    break
                    

    
    def get_new_step_durations(self):
        """
        read the new step duration for each solve
        :return: dict : (period name, step_duration (hours))
        """
        with open('input/timeblockSet__timeline_with_new_stepduration.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            step_durations = defaultdict()
            while True:
                try:
                    datain = next(filereader)
                    step_durations[datain[0]]=datain[1]
                except StopIteration:
                    break
        return step_durations 

    def get_timeblocks_used_by_solves(self):
        """
        timeblocks_in_use.csv contains three columns
        solve: name of the solve
        period: name of the time periods used for a particular solve
        timeblocks: timeblocks used by the period

        :return list of tuples in a dict of solves : (period name, timeblock name)
        """
        with open('input/timeblocks_in_use.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            timeblocks_used_by_solves = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    timeblocks_used_by_solves[datain[0]].append((datain[1], datain[2]))
                    # blockname needs to be in both block_start and timeblock_lengths.csv
                    # assert datain[1] in self.starts.keys(), "Block {0} not in block_starts.csv".format(datain[1])
                    # assert datain[1] in self.steps.keys(), "Block {0} not in block_steps.csv".format(datain[1])
                except StopIteration:
                    break
                #except AssertionError as e:
                #    logging.error(e)
                #    sys.exit(-1)
        return timeblocks_used_by_solves

    def get_timelines(self):
        """
        read in the timelines including step durations for all simulation steps
        timeline is the only inputfile that contains the full timelines for all timeblocks.
        :return: list of tuples in a dict timeblocks : (timestep name, duration)
        """
        with open('input/timeline.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            timelines = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    timelines[datain[0]].append((datain[1], datain[2]))
                except StopIteration:
                    break
        return timelines

    def get_timeblocks_timelines(self):
        """
        read in the timelines including step durations for all simulation steps
        timeline is the only inputfile that contains the full timelines for all timeblocks.
        :return: list of tuples in a dict timeblocks : (timestep name, duration)
        """
        with open('input/timeblocks__timeline.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            timeblocks__timeline = defaultdict(list)
            while True:
                try:
                    datain = next(filereader)
                    timeblocks__timeline[datain[0]].append((datain[1]))
                except StopIteration:
                    break
        return timeblocks__timeline

    def get_timeblocks(self):
        """
        read in the timeblock definitions that say what each set of timeblock contains (timeblock start and length)
        :return: list of tuples in a dict of timeblocks : (start timestep name, timeblock length in timesteps)
        :return: list of tuples that hold the timeblock length in timesteps
        """
        with open('input/timeblocks.csv', 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            timeblocks = defaultdict(list)
            #timeblock_lengths = []
            while True:
                try:
                    datain = next(filereader)
                    timeblocks[datain[0]].append((datain[1], datain[2]))
                    """ This assert should check the list of timelines inside the dict, but didn't have time to formulate it yet
                    assert timeblocks[datain[0]] in self.timelines[datain[0]], "Block {0} start time {1} not found in timelines".format(
                        datain[0], datain[1])
                    """
                    #timeblock_lengths.append[(datain[0], datain[1])] = datain[2]
                except StopIteration:
                    break
                """ Once the assert works, this can be included
                except AssertionError as e:
                    logging.error(e)
                    sys.exit(-1)
                """
        return timeblocks

    def get_list_of_tuples(self, filename):
        """
        read in invest_period
        :return  a list of tuples that say when it's ok to invest (solve, period):
        """
        with open(filename, 'r') as blk:
            filereader = csv.reader(blk, delimiter=',')
            headers = next(filereader)
            tuple_list = []
            while True:
                try:
                    datain = next(filereader)
                    tuple_list.append((datain[0], datain[1]))
                except StopIteration:
                    break
        return tuple_list

    def make_steps(self, start, stop):
        """
        make a list of timesteps available
        :param start: Start index of of the block
        :param stop: Stop index of the block
        :param steplist: list of steps, read from steps.csv
        :return: list of timesteps
        """

        active_step = start
        steps = []
        while active_step <= stop:
            steps.append(self.steplist[active_step])
            active_step += 1
        return steps

    def write_full_timelines(self, period__timeblocks_in_this_solve, timeblocks__timeline, timelines, filename):
        """
        write to file a list of timestep as defined in timelines.
        :param filename: filename to write to
        :param steplist: list of timestep indexes
        :return:
        """
        with open(filename, 'w') as outfile:
            # prepend with a header
            outfile.write('period,step\n')
            for period__timeblock in period__timeblocks_in_this_solve:
                for timeline in timelines:
                    for timeblock_in_timeline, tt in timeblocks__timeline.items():
                        if period__timeblock[1] == timeblock_in_timeline:
                            if timeline == tt[0]:
                                for item in timelines[timeline]:
                                    outfile.write(period__timeblock[0] + ',' + item[0] + '\n')

    def write_active_timelines(self, timeline, filename, scaling = False):
        """
        write to file a list of timesteps as defined by the active timeline of the current solve
        :param filename: filename to write to
        :param timeline: list of tuples containing the period and the timestep
        :return: nothing
        """
        if not scaling:
            with open(filename, 'w') as outfile:
                # prepend with a header
                outfile.write('period,step,step_duration\n')
                for period_name, period in timeline.items():
                    for item in period:
                        outfile.write(period_name + ',' + item[0] + ',' + item[2] + '\n')
        else: 
            with open(filename, 'w') as outfile:
                # prepend with a header
                outfile.write('period,step,scaling_step_duration\n')
                for period_name, period in timeline.items():
                    for item in period:
                        outfile.write(period_name + ',' + item[0] + ',' + item[2] + '\n')

    def write_years_represented(self, years_represented, filename):
        """
        write to file a list of periods with the number of years the period represents before the next period starts
        :param filename: filename to write to
        :param years_represented: dict of periods with the number of years represented
        :return: nothing
        """
        with open(filename, 'w') as outfile:
            # prepend with a header
            outfile.write('period,years_from_solve,p_years_from_solve,p_years_represented\n')
            year_count = 0
            for period__years in years_represented:
                for i in range(int(max(1.0, float(period__years[1])))):
                    years_to_cover_within_year = min(1, float(period__years[1]))
                    outfile.write(period__years[0] + ',y' + str(year_count) + ',' + str(year_count) + ','
                            + str(years_to_cover_within_year) + '\n')
                    year_count = year_count + years_to_cover_within_year

    def write_period_years(self, years_represented, filename):
        """
        write to file a list of timesteps as defined by the active timeline of the current solve
        :param filename: filename to write to
        :param timeline: list of tuples containing the period and the timestep
        :return: nothing
        """
        with open(filename, 'w') as outfile:
            # prepend with a header
            outfile.write('period,param\n')
            year_count = 0
            for period__year in years_represented:
                outfile.write(period__year[0] + ',' + str(year_count) + '\n')
                year_count += float(period__year[1])

    def make_block_timeline(self, start, length):
        """
        make a block timeline, there might be multiple blocks per solve so these blocks might need to be combined for a run
        :param start: start of block
        :param length: length of block
        :return: block timeline
        """
        steplist = []
        startnum = self.steplist.index(start)
        for i in range(startnum, math.ceil(startnum + float(length))):
            steplist.append(self.steplist[i])
        return steplist

    def model_run(self, current_solve):
        """
        run the model executable once
        :return the output of glpsol.exe:
        """
        try:
            solver = self.solvers[current_solve]
        except KeyError:
            logging.warning(f"No solver defined for {current_solve}. Defaulting to highs.")
            solver = "highs"
        if solver == "glpsol":
            only_glpsol = ['glpsol', '--model', 'flexModel3.mod', '-d', 'FlexTool3_base_sets.dat', '--cbg','-w', 'glpsol_solution.txt'] + sys.argv[1:]
            completed = subprocess.run(only_glpsol)
            if completed.returncode != 0:
                logging.error(f'glpsol failed: {completed.returncode}')
                exit(completed.returncode)
            
            #checking if solution is infeasible. This is quite clumsy way of doing this, but the solvers do not give infeasible exitstatus
            with open('glpsol_solution.txt','r') as inf_file:
                inf_content = inf_file.read() 
                if 'INFEASIBLE' in inf_content:
                    logging.error(f"The model is infeasible. Check the constraints.")
                    exit(1)

        elif solver == "highs" or solver == "cplex":
            highs_step1 = ['glpsol', '--check', '--model', 'flexModel3.mod', '-d', 'FlexTool3_base_sets.dat',
                           '--wfreemps', 'flexModel3.mps'] + sys.argv[1:]
            completed = subprocess.run(highs_step1)
            if completed.returncode != 0:
                logging.error(f'glpsol mps writing failed: {completed.returncode}')
                exit(completed.returncode)
            print("GLPSOL wrote the problem as MPS file\n")

            #check if the problem has columns(nodes)
            with open('flexModel3.mps','r') as mps_file:
                mps_content = mps_file.read() 
                if 'Columns:    0' in mps_content:
                    logging.error(f"The problem has no columns. Check that the model has nodes.")
                    exit(-1)


            if solver == "highs":
                highs_step2 = "highs flexModel3.mps --options_file=highs.opt --presolve=" \
                    + self.highs_presolve.get(current_solve, "on") + " --solver=" \
                    + self.highs_method.get(current_solve, "choose") + " --parallel=" \
                    + self.highs_parallel.get(current_solve, "off")
                completed = subprocess.run(highs_step2)
                if completed.returncode != 0:
                    logging.error(f'Highs solver failed: {completed.returncode}')
                    exit(completed.returncode)
                print("HiGHS solved the problem\n")
                
                #checking if solution is infeasible. This is quite clumsy way of doing this, but the solvers do not give infeasible exitstatus
                with open('HiGHS.log','r') as inf_file:
                    inf_content = inf_file.read() 
                    if 'Infeasible' in inf_content:
                        logging.error(f"The model is infeasible. Check the storage constraints.")
                        exit(1)
            
            elif solver == "cplex": #or gurobi
                if current_solve not in self.solver_precommand.keys():
                    s_wrapper = ''
                else:
                    s_wrapper = self.solver_precommand[current_solve]

                if solver == "cplex":
                    if current_solve not in self.solver_arguments.keys():
                        cplex_step = [s_wrapper, 'cplex', '-c', 'read flexModel3.mps','opt', 'write flexModel3_cplex.sol', 'quit']  + sys.argv[1:]
                    else:
                        cplex_step = [s_wrapper, 'cplex', '-c', 'read flexModel3.mps']
                        cplex_step += self.solver_arguments[current_solve]
                        cplex_step += ['opt', 'write flexModel3_cplex.sol', 'quit']
                        cplex_step += sys.argv[1:]

                    completed = subprocess.run(cplex_step)
                    if completed.returncode != 0:
                        logging.error(f'Cplex solver failed: {completed.returncode}')
                        exit(completed.returncode) 
                    
                    completed = self.cplex_to_glpsol("flexModel3_cplex.sol","flexModel3.sol")


            highs_step3 = ['glpsol', '--model', 'flexModel3.mod', '-d', 'FlexTool3_base_sets.dat', '-r',
                        'flexModel3.sol'] + sys.argv[1:]
            completed = subprocess.run(highs_step3)
            if completed.returncode == 0:
                print("GLPSOL wrote the results into csv files\n")
        else:
            logging.error(f"Unknown solver '{solver}'. Currently supported options: highs, glpsol, cplex.")
            exit(-1)
        return completed.returncode

    def cplex_to_glpsol(self,cplexfile,solutionfile): 
        
        try:
            tree = ET.parse(cplexfile)
        except (OSError):
            logging.error('The CPLEX solver does not produce a solution file if the problem is infeasible. Check the constraints, more info at cplex.log')
            exit(-1)
        root = tree.getroot()

        if root.find('header').get('solutionStatusString') == "optimal":
            with open(solutionfile,'w') as glpsol_file:
                
                obj = root.find('header').get('objectiveValue')

                for constraint in root.iter('constraint'):
                    rows = constraint.get('index')
                rows = int(rows) + 2

                for variable in root.iter('variable'):
                    col = variable.get('index')
                col = int(col) + 1
                
                glpsol_file.write("s bas "+str(rows)+" "+str(col)+" f f "+obj+"\n")
                
                #For some reason the glpsol constraint the first variable row to be the objective function value.
                #This is not stated anywhere in the glpk documentation
                glpsol_file.write("i 1 b "+obj+" 0\n")
            
                for constraint in root.iter("constraint"):
                    slack = constraint.get('slack')
                    index = int(constraint.get('index')) + 2
                    status = constraint.get('status')
                    dual = constraint.get('dual')
                    
                    if status == "BS":
                        status = 'b'
                    elif status == "LL":
                        status = 'l'
                    elif status == "UL":
                        status = 'u'
                    
                    glpsol_file.write("i"+" "+str(index)+" "+status+" "+slack+" "+dual+"\n")

                for variable in root.iter('variable'):
                    val = variable.get('value')
                    index = int(variable.get('index')) +1
                    status = variable.get('status')
                    reduced = variable.get('reducedCost')
                    
                    if status == "BS":
                        status = 'b'
                    elif status == "LL":
                        status = 'l'
                    elif status == "UL":
                        status = 'u'

                    glpsol_file.write("j"+" "+str(index)+" "+status+" "+val+" "+reduced+"\n")
                
                glpsol_file.write("e o f")
        elif root.find('header').get('solutionStatusString') == "integer optimal solution":
            with open(solutionfile,'w') as glpsol_file:
                
                obj = root.find('header').get('objectiveValue')

                for constraint in root.iter('constraint'):
                    rows = constraint.get('index')
                rows = int(rows) + 2

                for variable in root.iter('variable'):
                    col = variable.get('index')
                col = int(col) + 1
                
                glpsol_file.write("s mip "+str(rows)+" "+str(col)+" o "+obj+"\n")
                
                #For some reason the glpsol requires the first constraint row to be the objective function value.
                #This is not stated anywhere in the glpk documentation
                glpsol_file.write("i 1 "+obj+"\n")
            
                for constraint in root.iter("constraint"):
                    slack = constraint.get('slack')
                    index = int(constraint.get('index')) + 2
                    
                    glpsol_file.write("i"+" "+str(index)+" "+slack+"\n")

                for variable in root.iter('variable'):
                    val = variable.get('value')
                    index = int(variable.get('index')) +1

                    glpsol_file.write("j"+" "+str(index)+" "+val+"\n")
                
                glpsol_file.write("e o f")
        else:
            logging.error(f"Optimality could not be reached. Check the flexModel3_cplex.sol file for more")
            exit(1)
        
        return 0


    def get_active_time(self, current_solve, timeblocks_used_by_solves, timeblocks, timelines, timeblocks__timelines):
        """
        retunr all block codes that are included in solve
        :param solve:
        :param blocklist:
        :return:
        """ 
        active_time = defaultdict(list)
        for solve in timeblocks_used_by_solves:
            if solve == current_solve:
                for period_timeblock in timeblocks_used_by_solves[solve]:
                    for timeblocks__timeline_key, timeblocks__timeline_value in timeblocks__timelines.items():
                        if timeblocks__timeline_key == period_timeblock[1]:
                            for timeline in timelines:
                                if timeline == timeblocks__timeline_value[0]:
                                    for single_timeblock_def in timeblocks[timeblocks__timeline_key]:
                                        for index, timestep in enumerate(timelines[timeline]):
                                            if timestep[0] == single_timeblock_def[0]:
                                                for block_step in range(int(float(single_timeblock_def[1]))):
                                                    active_time[period_timeblock[0]].append((
                                                                        timelines[timeline][index + block_step][0],
                                                                        index + block_step,
                                                                        timelines[timeline][index + block_step][1]))
                                                break
        if len(active_time.keys()) == 0:
            logging.error(current_solve + " could not connect to timeline. Check that object solve has period_timeblockSet [Map], objects timeblockSet [Map] and timeline [Map] are defined and that relation timeblockSet_timeline exists")
            exit(-1)
        return active_time

    def make_step_jump(self, active_time_list):
        """
        make a file that indicates the length of jump from one simulation step to next one.
        the final line should always contain a jump to the first line.

        length of jump is the number of lines needed to advance in the timeline specified in step_duration.csv

        :param steplist: active steps used in the solve
        :param duration: duration of every timestep
        :return:
        """
        step_lengths = []
        period_start_pos = 0
        period_counter = -1
        first_period_name = list(active_time_list)[0]
        last_period_name = list(active_time_list)[-1]
        for period, active_time in reversed(active_time_list.items()):
            period_counter -= 1
            period_last = len(active_time)
            block_last = len(active_time) - 1
            if period == first_period_name:
                previous_period_name = last_period_name
            else:
                previous_period_name = list(active_time_list)[period_counter]
            for i, step in enumerate(reversed(active_time)):
                j = period_last - i - 1
                if j > 0:  # handle the first element of the period separately below
                    jump = active_time[j][1] - active_time[j - 1][1]
                    if jump > 1:
                        step_lengths.insert(period_start_pos, (period, step[0], active_time[j - 1][0], active_time[block_last][0], period, active_time[j - 1][0], jump))
                        block_last = j - 1
                    else:
                        step_lengths.insert(period_start_pos, (period, step[0], active_time[j - 1][0], active_time[j - 1][0], period, active_time[j - 1][0], jump))
                else:  # first time step of the period is handled here
                    jump = active_time[j][1] - active_time_list[previous_period_name][-1][1]
                    step_lengths.insert(period_start_pos, (period, step[0], active_time[j - 1][0], active_time[block_last][0], previous_period_name, active_time_list[previous_period_name][-1][0], jump))
        return step_lengths

    def write_step_jump(self, step_lengths):
        """
        write step_jump.csv according to spec.

        :param step_lengths:
        :return:
        """

        headers = ("period", "time", "previous", "previous_within_block", "previous_period", "previous_within_solve", "jump")
        with open("solve_data/step_previous.csv", 'w', newline='\n') as stepfile:
            writer = csv.writer(stepfile, delimiter=',')
            writer.writerow(headers)
            writer.writerows(step_lengths)

    def get_first_steps(self, steplists):
        """
        get the first step of the current solve and the next solve in execution order.
        :param steplists: Dictionary containg steplist for each solve, in order
        :return: Return a dictionary containing tuples of current_first, next first
        """
        solve_names = list(steplists.keys())
        starts = OrderedDict()
        for index, name in enumerate(solve_names):
            # last key is a different case
            if index == (len(solve_names) - 1):
                starts[name] = (steplists[name][0],)
            else:
                starts[name] = (steplists[solve_names[index]][0], steplists[solve_names[index + 1]][0])
        return starts

    def write_first_steps(self, timeline, filename):
        """
        write to file the first step of each period
        
        :param steps: a tuple containing the period and the timestep
        """
        with open(filename, 'w') as outfile:
            # prepend with a header
            outfile.write('period,step\n')
            for period_name, period in timeline.items():
                for item in period[:1]:
                    outfile.write(period_name + ',' + item[0] + '\n')

    def write_last_steps(self, timeline, filename):
        """
        write to file the last step of each period

        :param steps: a tuple containing the period and the timestep
        """
        with open(filename, 'w') as outfile:
            # prepend with a header
            outfile.write('period,step\n')
            for period_name, period in timeline.items():
                for item in period[-1:]:
                    outfile.write(period_name + ',' + item[0] + '\n')

    def write_periods(self, solve, periods, filename):
        """
        write to file a list of periods based on the current solve and
        a list of tuples with the solve as the first element in the tuple
        :param solve: current solve
        :param filename: filename to write to
        :param periods: list of tuples with solve and periods to be printed to the file
        :return: nothing
        """
        with open(filename, 'w') as outfile:
            # prepend with a header
            outfile.write('period\n')
            for item in periods:
                if item[0] == solve:
                    outfile.write(item[1] + '\n')

    def write_solve_status(self, first_state, last_state, nested = False):
        """
        make a file solve_first.csv that contains information if the current solve is the first to be run

        :param first_state: boolean if the current run is the first

        """
        if not nested:
            with open("input/p_model.csv", 'w') as p_model_file:
                p_model_file.write("modelParam,p_model\n")
                if first_state:
                    p_model_file.write("solveFirst,1\n")
                else:
                    p_model_file.write("solveFirst,0\n")
                if last_state:
                    p_model_file.write("solveLast,1\n")
                else:
                    p_model_file.write("solveLast,0\n")
        else:
            with open("solve_data/p_nested_model.csv", 'w') as p_model_file:
                p_model_file.write("modelParam,p_nested_model\n")
                if first_state:
                    p_model_file.write("solveFirst,1\n")
                else:
                    p_model_file.write("solveFirst,0\n")
                if last_state:
                    p_model_file.write("solveLast,1\n")
                else:
                    p_model_file.write("solveLast,0\n")

    def write_currentSolve(self, solve, filename):
        """
        make a file with the current solve name
        """
        with open(filename, 'w') as solvefile:
            solvefile.write("solve\n")
            solvefile.write(solve + "\n")

    def write_empty_investment_file(self):
        """
        make a file p_entity_invested.csv that will contain capacities of invested and divested processes. For the first solve it will be empty.
        """
        with open("solve_data/p_entity_invested.csv", 'w') as firstfile:
            firstfile.write("entity,p_entity_invested\n")
        with open("solve_data/p_entity_divested.csv", 'w') as firstfile:
            firstfile.write("entity,p_entity_divested\n")
        with open("solve_data/p_entity_period_existing_capacity.csv", 'w') as firstfile:
            firstfile.write("entity,period,p_entity_period_existing_capacity,p_entity_period_invested_capacity\n")

    def write_empty_storage_fix_file(self):
        with open("solve_data/fix_storage_price.csv", 'w') as firstfile:
            firstfile.write("node, period, step, ndt_fix_storage_price\n")
        with open("solve_data/fix_storage_quantity.csv", 'w') as firstfile:
            firstfile.write("node, period, step, ndt_fix_storage_quantity\n")

    def write_headers_for_empty_output_files(self, filename, header):
        """
        make an empty output file with headers
        """
        with open(filename, 'w') as firstfile:
            firstfile.write(header+"\n")

    def write_realized_dispatch(self,active_time_list,solve):

        with open("solve_data/realized_dispatch.csv", 'w') as realfile:
            realfile.write("period,step\n")
            for period, active_time in active_time_list.items():
                if (solve,period) in self.realized_periods:
                    for i in active_time:
                        realfile.write(period+","+i[0]+"\n")

    def write_fixed_storage_timesteps(self,active_time_list,solve):

        with open("solve_data/fix_storage_timesteps.csv", 'w') as realfile:
            realfile.write("period,step\n")
            for period, active_time in active_time_list.items():
                if (solve,period) in self.fix_storage_periods:
                    for i in active_time:
                        realfile.write(period+","+i[0]+"\n")


    def create_rolling_solves(self, solve, full_active_time, jump, horizon, start = None, duration = -1):
        #can the steps be assumed to be constant?
        #period/timeblock jumps?
        
        active_time_lists= OrderedDict()    
        jump_lists = OrderedDict()
        realized_time_lists = OrderedDict()
        solves=[]
        starts=[]
        jumps= []
        horizons= []
        duration_counter = 0
        horizon_counter = 0
        jump_counter = 0
        started = False
        ended = False
        #if start time is given and not generated by parent. Given is just a timestamp. Generated is [period,timestamp]
        if start != None and len(start) == 1:
            start = [list(full_active_time.items())[0][0],start]
        
        for period, active_time in list(full_active_time.items()):
            for i, step in enumerate(active_time):
                if started and not ended:
                    if duration_counter >= duration and duration != -1:
                        jumps.append(last_index)
                        horizons.append(last_index)
                        ended = True
                        break
                    if jump_counter >= jump:
                        jumps.append(last_index)
                        starts.append([period,i])
                        jump_counter -= jump
                    if horizon_counter >= horizon:
                        horizons.append(last_index)
                        horizon_counter -= jump
                    horizon_counter += float(step[2])
                    jump_counter += float(step[2])
                    duration_counter += float(step[2])
                    last_index = [period,i]
                else:
                    if start == None or start == [period,step[0]]:
                        starts.append([period,i])
                        started = True
                        horizon_counter += float(step[2])
                        jump_counter += float(step[2])
                        duration_counter += float(step[2])
                        last_index=[period,i]
        #if there is start of the roll but not end, the end is the last index of the active time
        diff = len(starts)-len(horizons)
        for i in range(0,diff):
            horizons.append(last_index)
        diff = len(starts)-len(jumps)
        for i in range(0,diff):
            jumps.append(last_index)
        for index, start in enumerate(starts): 
            active = OrderedDict()
            realized = OrderedDict()
            solve_name= solve+"_roll_"+str(index)
            solves.append(solve_name) 
            if start[0]==horizons[index][0]: #if the whole roll is in the same period
                active[start[0]] = full_active_time[start[0]][start[1]:horizons[index][1]+1]
            else:
                started = False
                for period, active_time in list(full_active_time.items()):
                    if started:
                        if period == horizons[index][0]:
                            active[period] = full_active_time[period][0:horizons[index][1]+1]
                            break
                        else:
                            active[period] = full_active_time[period]
                    elif period == start[0]:
                        active[start[0]] = full_active_time[period][start[1]:]
                        started = True
            
            if start[0]==jumps[index][0]:
                realized[start[0]] = full_active_time[start[0]][start[1]:jumps[index][1]+1]
            else:
                started = False
                for period, active_time in list(full_active_time.items()):
                    print(period, jumps[index][0])
                    if started:
                        if period == jumps[index][0]:
                            realized[period] = full_active_time[period][0:jumps[index][1]+1]
                            break
                        else:
                            realized[period] = full_active_time[period]
                    elif period == start[0]:
                        realized[period] = full_active_time[period][start[1]:]
                        started = True

            jump= self.make_step_jump(active)
            active_time_lists[solve_name] = active
            realized_time_lists[solve_name] = realized
            jump_lists[solve_name] = jump

        return solves, active_time_lists, jump_lists, realized_time_lists

    def define_solve(self, solve, combined_name, start = None, duration = -1):
        parent_solves= OrderedDict() #parent_solve is for rolling, so that the rolls inherit the parameters of the solve
        active_time_lists= OrderedDict()    
        jump_lists = OrderedDict()
        realized_time_lists = OrderedDict()
        fix_storage_time_lists = OrderedDict()
        solves=[]

        full_active_time = self.get_active_time(solve, self.timeblocks_used_by_solves, self.timeblocks,self.timelines, self.timeblocks__timeline)
        if solve in self.included_solves.keys():
            include_solve = self.included_solves[solve]
        else:
            include_solve = None
        
        if solve not in self.solve_modes.keys():
            self.solve_modes[solve] = "single_solve"

        if self.solve_modes[solve] == "rolling_window":
            #rolling_times: 0:start, 1:jump, 2:horizon, 3:duration
            rolling_times = self.rolling_times[solve]
            if duration == -1:
                duration = rolling_times[3]
            roll_solves, roll_active_time_lists, roll_jump_lists, roll_realized_time_lists = self.create_rolling_solves(combined_name+solve, full_active_time, rolling_times[1], rolling_times[2], start, duration)
            for i in roll_solves:
                parent_solves[i] = solve    
            
            active_time_lists.update(roll_active_time_lists)
            jump_lists.update(roll_jump_lists)
            realized_time_lists.update(roll_realized_time_lists)
            fix_storage_time_lists.update(roll_realized_time_lists)

            if include_solve != None:
                for index, roll in enumerate(roll_solves):
                    solves.append(roll)
                    #creating the start time for the rolling. This is the first [period, timestamp] of the active time of the parent roll 
                    start = [list(roll_active_time_lists[roll].items())[0][0],list(roll_active_time_lists[roll].items())[0][1][0][0]]
                    #upper_jump = lower_duration 
                    duration = rolling_times[1]
                    inner_solves, inner_parent_solve, inner_active_time_lists, inner_jump_lists, inner_realized_time_lists, inner_fix_storage_time_lists = self.define_solve(include_solve,roll,start,duration)
                    solves += inner_solves
                    parent_solves.update(inner_parent_solve)
                    active_time_lists.update(inner_active_time_lists)
                    jump_lists.update(inner_jump_lists)
                    realized_time_lists.update(inner_realized_time_lists)
                    fix_storage_time_lists.update(inner_fix_storage_time_lists)
            else:
                solves += roll_solves
        
        else:
            solves.append(solve)
            parent_solves[solve]= solve #parent_solve is for rolling, so that the rolls inherit the parameters of the solve. If not rolling, the solve is its own parent
            active_time_lists[solve] = full_active_time
            jumps = self.make_step_jump(full_active_time)
            jump_lists[solve] = jumps
            realized_time_lists[solve]=full_active_time
            fix_storage_time_lists[solve] = full_active_time 

            if include_solve != None:
                inner_solves, inner_parent_solve, inner_active_time_lists, inner_jump_lists, inner_realized_time_lists, inner_fix_storage_time_lists = self.define_solve(include_solve,include_solve)
                solves += inner_solves
                parent_solves.update(inner_parent_solve)
                active_time_lists.update(inner_active_time_lists)
                jump_lists.update(inner_jump_lists)
                realized_time_lists.update(inner_realized_time_lists)
                fix_storage_time_lists.update(inner_fix_storage_time_lists)


        return solves, parent_solves, active_time_lists, jump_lists, realized_time_lists, fix_storage_time_lists

    def periodic_postprocess(self,groupby_map, method = None):
        for key, group in list(groupby_map.items()):
            if method == "timewise":
                filepath = 'output/' + key + '__t.csv'
            else:
                filepath = 'output/' + key + '.csv'
                #get the relationship indicators from the start of the file
            if group[1]>1:
                relationship_start_df=pd.read_csv(filepath, header = 0, nrows=group[1]-1)
                if method == "timewise":
                    relationship_start_df.drop(["time"],axis = 1, inplace=True)
                timestep_df = pd.read_csv(filepath,header = 0,skiprows=range(1,group[1]))
            else:
                timestep_df = pd.read_csv(filepath,header = 0)
            if method == "timewise":
                timestep_df.drop(["time"],axis = 1, inplace=True)
            
            #create a df with only group,solve,period cols, where the solve is the first of the group,period combo
            solve_period = timestep_df.filter(items= group[0] +["solve","period"])
            solve_first = solve_period.groupby(group[0] +["period"]).first().reset_index()
            cols = list(solve_first.columns)
            a,b = cols.index('period'),cols.index('solve')
            cols[a], cols[b] = cols[b], cols[a]
            solve_first= solve_first[cols]
            
            #group_by with group and period, sum numeric columns, other columns are removed
            modified= timestep_df.groupby(group[0]+["period"],group_keys=False).sum(numeric_only=True).reset_index()
            #combine with the solve name df
            combined = pd.merge(solve_first,modified)
            #put the relationship indicators back to the start of the file
            if group[1]>1:
                combined = pd.concat([relationship_start_df,combined])

            combined.to_csv('output/' + key + '.csv',index=False)

    def combine_result_tables(self, inputfile1, inputfile2, outputfile, combine_headers = None, move_column = []):
        input1 = pd.read_csv(inputfile1,header = 0)
        input2 = pd.read_csv(inputfile2,header = 0)
        combined = pd.concat([input1,input2])
        #move columns to desired locations
        for column in move_column:
            name = combined.columns[column[0]]
            col = combined.pop(name)
            combined.insert(column[1],name,col)
        combined.to_csv(outputfile, index= False)

def main():
    """
    first read the solve configuration from the input files, then for each solve write the files that are needed
    By that solve into disk. separate the reading into a separate step since the input files need knowledge of multiple solves.
    """
    runner = FlexToolRunner()
    active_time_lists = OrderedDict()
    jump_lists = OrderedDict()
    solve_period_history = defaultdict(list)
    realized_time_lists = OrderedDict()
    parent_solve= OrderedDict()
    fix_storage_time_lists= OrderedDict()
    all_solves=[]

    try:
        os.mkdir('solve_data')
    except FileExistsError:
        print("solve_data folder existed")

    if not runner.model_solve:
        logging.error("No model. Make sure the 'model' class defines solves [Array].")
        sys.exit(-1)
    solves = next(iter(runner.model_solve.values()))
    if not solves:
        logging.error("No solves in model.")
        sys.exit(-1)
    
    for solve in solves:
        solve_solves, solve_parent_solve, solve_active_time_lists, solve_jump_lists, solve_realized_time_lists, solve_fix_storage_timesteps = runner.define_solve(solve,solve)
        all_solves += solve_solves
        parent_solve.update(solve_parent_solve)
        active_time_lists.update(solve_active_time_lists)
        jump_lists.update(solve_jump_lists)
        realized_time_lists.update(solve_realized_time_lists)
        fix_storage_time_lists.update(solve_fix_storage_timesteps)

    real_solves = [] 
    for solve in solves: #real solves are the defined solves not including the individual rolls
        real_solves.append(solve)
    for solve, inner_solve in list(runner.included_solves.items()):
        real_solves.append(inner_solve)

    for solve in real_solves:
        for solve_2 in real_solves:
            if solve_2 == solve:
                break
            for solve__period in (runner.realized_periods+runner.invest_realized_periods+runner.fix_storage_periods):
                if solve__period[0] == solve_2:
                    this_solve = runner.solve_period_years_represented[solve_2]
                    for period in this_solve:
                        if period[0] == solve__period[1] and not any(period[0]== sublist[0] for sublist in solve_period_history[solve]):
                            solve_period_history[solve].append((period[0], period[1]))
        for period__year in runner.solve_period_years_represented[solve]:
            if not any(period__year[0]== sublist[0] for sublist in solve_period_history[solve]):
                solve_period_history[solve].append((period__year[0], period__year[1]))
        if not runner.solve_period_years_represented[solve]:
            for solve__period in (runner.realized_periods+runner.invest_realized_periods+runner.fix_storage_periods):
                if solve__period[0] == solve and not any(solve__period[1]== sublist[0] for sublist in solve_period_history[solve]):
                    solve_period_history[solve].append((solve__period[1], 1))

    real_solves_index = defaultdict(list)
    for i, solve in enumerate(all_solves):
        real_solves_index[parent_solve[solve]].append(i)
    first_of_nested_level_list = []
    last_of_nested_level_list = []
    for solve in real_solves:
        first_of_nested_level_list.append(real_solves_index[solve][0])
        last_of_nested_level_list.append(real_solves_index[solve][-1])
    
    first = True
    for i, solve in enumerate(all_solves):
        parent_active_time_lists = runner.get_active_time(parent_solve[solve], runner.timeblocks_used_by_solves, runner.timeblocks, runner.timelines, runner.timeblocks__timeline)
        runner.write_full_timelines(runner.timeblocks_used_by_solves[parent_solve[solve]], runner.timeblocks__timeline, runner.timelines, 'solve_data/steps_in_timeline.csv')
        runner.write_active_timelines(active_time_lists[solve], 'solve_data/steps_in_use.csv')
        runner.write_active_timelines(parent_active_time_lists, 'solve_data/steps_for_scaling.csv', scaling = True)
        runner.write_step_jump(jump_lists[solve])
        runner.write_period_years(solve_period_history[parent_solve[solve]], 'solve_data/period_with_history.csv')
        runner.write_periods(parent_solve[solve], runner.invest_realized_periods, 'solve_data/invest_realized_periods_of_current_solve.csv')
        #assume that if invest_realized_periods is not defined,but the invest_periods and realized_periods are defined, use realized_periods also as the invest_realized_periods
        if (not any(parent_solve[solve] == step[0] for step in runner.invest_realized_periods)) and any(parent_solve[solve] == step[0] for step in runner.invest_periods) and any(parent_solve[solve] == step[0] for step in runner.realized_periods):
             runner.write_periods(parent_solve[solve], runner.realized_periods, 'solve_data/invest_realized_periods_of_current_solve.csv')
        runner.write_periods(parent_solve[solve], runner.invest_periods, 'solve_data/invest_periods_of_current_solve.csv')
        runner.write_years_represented(runner.solve_period_years_represented[parent_solve[solve]],'solve_data/p_years_represented.csv')
        runner.write_period_years(runner.solve_period_years_represented[parent_solve[solve]],'solve_data/p_discount_years.csv')
        runner.write_currentSolve(solve, 'solve_data/solve_current.csv')
        runner.write_first_steps(active_time_lists[solve], 'solve_data/first_timesteps.csv')
        runner.write_last_steps(active_time_lists[solve], 'solve_data/last_timesteps.csv')
        runner.write_realized_dispatch(realized_time_lists[solve],parent_solve[solve])
        runner.write_fixed_storage_timesteps(fix_storage_time_lists[solve],parent_solve[solve])
        runner.create_averaged_timeseries(parent_solve[solve])
        if i in first_of_nested_level_list:
            first_of_nested_level = True
        else:
            first_of_nested_level = False
        if i in last_of_nested_level_list:
            last_of_nested_level = True
        else:
            last_of_nested_level = False
        runner.write_solve_status(first_of_nested_level,last_of_nested_level, nested = True)
        last = i == len(solves) - 1
        runner.write_solve_status(first, last)
        if i == 0:
            first = False
            runner.write_empty_investment_file()
            runner.write_empty_storage_fix_file()
            runner.write_headers_for_empty_output_files('output/costs_discounted.csv', 'param_costs,costs_discounted')
        exit_status = runner.model_run(solve)
        if exit_status == 0:
            logging.info('Success!')
        else:
            logging.error(f'Error: {exit_status}')
            exit(-1)

    if "rolling_window" in runner.solve_modes.values():
        #group by name and relation dimension
        period_only = {
        "group__process__node__period": [[],1],
        "unit_online__period_average": [[],1],
        "unit__inputNode__period": [[],2],
        "unit__outputNode__period": [[],2],
        "connection__period": [[],3],
        "process__reserve__upDown__node__period_average": [[],6],
        }

        timewise_groupby = {
        "annualized_dispatch_costs__period": [[],1],
        "node__period": [["node"],1],
        "group_node__period": [["group"],1] #väärin
        }

        runner.periodic_postprocess(period_only, method = "periodic")
        runner.periodic_postprocess(timewise_groupby, method = "timewise")
        runner.combine_result_tables("output/annualized_investment_costs__period.csv","output/annualized_dispatch_costs__period.csv", "output/annualized_costs__period.csv",move_column =[(6,14)])
    
    if len(runner.model_solve) > 1:
        logging.error(
            f'Trying to run more than one model - not supported. The results of the first model are retained.')
        sys.exit(-1)


if __name__ == '__main__':
    main()
