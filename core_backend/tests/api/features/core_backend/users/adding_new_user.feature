Feature: Generic Job Submission and Execution
    An example generic task list involving three tasks.

  Scenario Outline: Check job submission and execution
      Given a <generic_job_filepath>

      When I modify the job_file and submit the job

      Then the sequoia job outputs directory should exist
      And the experiment directory should exist
      And the session directory should exist
      And the job files directory should exist
      And a copy of the job file should exist in the job files directory
      And the submission script file should exist in the job files directory
      And output directories for each task should exist
      And task parameters should be saved for each task
      And at least one job log file should exist in the job files directory
      And the state dictionary for the job should exist in the job files directory
      And the last line in each job log file should be the finished task list string
      And and there should be a corresponding list of job filepaths and no job errors returned and from the job submission module

      Examples:
          | generic_job_filepath |
          | EXAMPLES_DIR/generic/generic.json |
          | EXAMPLES_DIR/generic/generic.jsonnet |
          | EXAMPLES_DIR/generic/generic.yaml |
          | FIXTURES_DIR/system/generic/generic_full_spec.json |
          | FIXTURES_DIR/system/generic/generic_min_spec.json |
          | FIXTURES_DIR/system/generic/generic_mixed_spec.json |
          | FIXTURES_DIR/system/generic/generic_mixed_spec.jsonnet |
          | FIXTURES_DIR/system/generic/generic.yml |
          | FIXTURES_DIR/system/generic/generic_multi_instantiation.jsonnet |
