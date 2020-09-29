# Displayce internship

## Locations

1. The pacing algorithm is located in the folder Pacing_project

2. All steps to construct the algorithm are notebooks situated in the folder Pacing_notebooks

3. The Report folder contains the internship report and slides

4. The Miscellaneous folder contains miscellaneous things such as work on auction theory

## Details Pacing_project

This is the main folder of the project. It contains all useful scripts about the pacing algorithm. <br />
```pacing_class_tz.py``` is the script that contains the final algorithm. <br />
```external_functions_tz.py```is the script that contains functions used to simulate the algorithm. <br />
```execution_tz.py``` allows to simulate the algorithm on a dataframe (give any dataframe on the data folder). <br />
```api_rest.py``` is the script to generate the API of the algorithm. It allows to launch a local server. <br />
```exec_api.py``` is the script that simulates the API (with a dataframe of br situated in the data folder). <br />
```test_basics.py``` is basic unit test on the API. <br />
<br />
Note: ```pacing_class.py```, ```external_functions.py``` and ```execution.py``` are the same that those with the suffix tz, but the algorithm doesn't allow multiple time zones. 


## How to use the API
POST method 
1. Initialise a campaign: 
```bash 
curl --request POST \
  --url http://127.0.0.1:8000/campaign \
  --header 'content-type: application/json' \
  --data '{
	"cpid": string ID 
}'
```

