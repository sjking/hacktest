#!/usr/bin/env python3

import sys, os, optparse, subprocess, multiprocessing, re, time

class bcolors:
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class HackTestResult:
  def __init__(self, number, execution_time, passed, actual_output, expected_output, error_message=None):
    self.number = number
    self.execution_time = execution_time
    self.passed = passed
    self.actual_output = actual_output
    self.expected_output = expected_output
    self.error_message = error_message

  def __str__(self):
    if self.passed:
      return bcolors.OKGREEN + "Test {0} Passed in {1:.2f} seconds".format(self.number, self.execution_time) + bcolors.ENDC
    else:
      failed_string = bcolors.FAIL + "Testcase {0} failed:\n\texpected output: {1}\n\tactual output: {2}\n\terror: {3}" + bcolors.ENDC
      return failed_string.format(self.number, self.expected_output, self.actual_output, self.error_message)

  __repr__ = __str__

class HackTestWorker(multiprocessing.Process):
  def __init__(self, task_queue, result_queue, executable):
    multiprocessing.Process.__init__(self)
    self.task_queue = task_queue
    self.result_queue = result_queue
    self.executable = executable

  def run(self):
    while True:
      test_case = self.task_queue.get()
      if test_case is None:
        self.task_queue.task_done()
        break
      try:
        input_file_name = test_case[0]
        output_file_name = test_case[1]
        test_number = int(re.search("^(.*\/input)([0-9]{2})(.txt)$", input_file_name).group(2))
  
        argv = self.executable
        input_file = open(input_file_name, 'r')
        start_time = time.clock()
        p = subprocess.run(argv, stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        end_time = time.clock()
        expected_output = open(output_file_name, 'r').read()
        
        if p.returncode == 0:
          elapsed_time = end_time - start_time
          if p.stdout == expected_output:
            result = HackTestResult(test_number, elapsed_time, True, p.stdout, expected_output)
          else:
            result = HackTestResult(test_number, elapsed_time, False, p.stdout, expected_output)
        else:
          result = HackTestResult(test_number, None, False, p.stdout, expected_output, p.stderr)
        self.task_queue.task_done()
        self.result_queue.put(result)
      except IndexError:
        print("Error", file=sys.stderr)
        break

class HackTest:
  def __init__(self, executable, opts=None):
    self.executable = executable
    self.testcase_dir = '../testcases'
    self.opt = opts and opts.testcase_dir

  def setup(self):
    try:
      directory = os.path.abspath('../testcases/input/')
      input_files = [os.path.abspath("../testcases/input/") + "/{0}".format(file) for file in os.listdir(directory)]
      directory = os.path.abspath('../testcases/output/')
      output_files = [os.path.abspath("../testcases/output/") + "/{0}".format(file) for file in os.listdir(directory)]
    except FileNotFoundError:
      print("Error: Testcases directory not found at path {0}".format(directory), file=sys.stderr)
      sys.exit(1)
    self.test_cases = [t for t in zip(input_files, output_files)]

  def run_all_tests(self):
    tasks = multiprocessing.JoinableQueue()
    results = multiprocessing.Queue()

    num_workers = multiprocessing.cpu_count() * 2
    workers = [HackTestWorker(tasks, results, self.executable) for w in range(num_workers)]
    for w in workers:
      w.start()

    for test_case in self.test_cases:
      tasks.put(test_case)

    for i in range(num_workers):
      tasks.put(None)

    tasks.join()
    results_list = []
    for i in range(len(self.test_cases)):
      result = results.get()
      results_list.append(result)

    self.process_results(results_list) 

  def process_results(self, results):
    results.sort(key=lambda result: result.number)
    passed = failed = 0
    for result in results:
      if result.passed:
        passed += 1
        print(result)
      else:
        print(result, file=sys.stderr)
        failed += 1
    summary = "{0}{1} Pass, {2}{3} Fail.{4}".format(bcolors.OKGREEN, passed, bcolors.FAIL, failed, bcolors.ENDC)
    print(summary)

def usage(program):
  print("Usage: {0} {1}".format(program, "<test_program>"), file=sys.stderr)

if __name__ == '__main__':
  try:
    executable = sys.argv[1]
    test = HackTest(executable)
    test.setup()
    test.run_all_tests()
  except IndexError:
    usage(sys.argv[0])
    sys.exit(1)
  except FileNotFoundError:
    print("Error: Testcases directory not found at path {0}".format(test.testcases_dir))
  except Exception as ex:
    sys.exit(1)
    print("exception: {0}, args: {1}".format(type(ex), ex.args))
