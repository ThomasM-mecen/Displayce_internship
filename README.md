# Displayce internship

## Locations

1. The pacing algorithm is located in the folder Pacing_project

2. All steps to construct the algorithm are notebooks situated in the folder Pacing_notebooks

3. The Report folder contains the internship report and slides

4. The Miscellaneous folder contains miscellaneous things such as work on auction theory

## Details Pacing_project

This is the main folder of the project. It contains all useful scripts about the pacing algorithm.
```pacing_class_tz.py``` is the script that contains the final algorithm.
```external_functions_tz.py```is the script that contains functions used to simulate the algorithm.
```execution_tz.py``` allows to simulate the algorithm on a dataframe (give any dataframe on the data folder).
```api_rest.py``` is the script to generate the API of the algorithm. It allows to launch a local server.
```exec_api.py``` is the script that simulates the API (with a dataframe of br situated in the data folder).
```test_basics.py``` is basic unit test on the API.

Note: ```pacing_class.py```, ```external_functions.py``` and ```execution.py``` are the same that those with the suffix tz, but the algorithm doesn't allow multiple time zones. 
