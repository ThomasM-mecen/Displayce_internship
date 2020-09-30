# Displayce internship

## Locations

1. The pacing algorithm is located in the folder Pacing_project

2. All steps to construct the algorithm are notebooks situated in the folder Pacing_notebooks

3. The Report folder contains the internship report and slides

4. The Miscellaneous folder contains miscellaneous things such as work on auction theory

## Pacing_project

This is the main folder of the project. It contains all useful scripts about the pacing algorithm. <br />
```pacing_class_tz.py``` is the script that contains the final algorithm. <br />
```external_functions_tz.py```is the script that contains functions used to simulate the algorithm. <br />
```execution_tz.py``` allows to simulate the algorithm on a dataframe (give any dataframe on the data folder). <br />
```api_rest.py``` is the script to generate the API of the algorithm. It allows to launch a local server. <br />
```exec_api.py``` is the script that simulates the API (with a dataframe of br situated in the data folder). <br />
```test_basics.py``` is basic unit tests on the API. <br />
<br />
Note: ```pacing_class.py```, ```external_functions.py``` and ```execution.py``` are the same that those with the suffix tz, but the algorithm doesn't allow multiple time zones. 


## How to use the API

To start a local server in order to use the API, launch on a terminal the following command:
```bash 
python api_rest.py
```

**POST method <br />**
1. Initialise a campaign: 
```bash 
curl --request POST \
  --url http://127.0.0.1:8000/campaign \
  --header 'content-type: application/json' \
  --data '{
	"cpid": String ID 
}'
```
2. Initialise a line item:
```bash
curl --request POST \
  --url http://127.0.0.1:8000/campaign/1/init \
  --header 'content-type: application/json' \
  --data '{
	"budget": Budget,
	"start": String date,
	"end": String date,
	"liid": String ID
}'
```

3. Send a bid request
```bash
curl --request POST \
  --url http://127.0.0.1:8000/li/1/br \
  --header 'content-type: application/json' \
  --data '{
	"tz": String time zone,
	"brid": ID of BR,
	"imps": Number of impressions,
	"cpm": CPM
}'
```
4. Send notification
```bash
curl --request POST \
  --url http://127.0.0.1:8000/li/1/notif \
  --header 'content-type: application/json' \
  --data '{
	"status": Status: must be 'win' or 'lose',
	"brid": ID of BR
}'
```
<br />

**GET method <br />**
Note that all output are in JSON format. <br />

1. Get campaigns list
```bash 
curl --request GET \
  --url http://127.0.0.1:8000/campaign
```
For example the if there is a campaign with the ID "1" and 3 line items for this campaign:
```json
{
  "campaigns": {
    "1": 3
  }
}
```

2. Get line items list
```bash 
curl --request GET \
  --url http://127.0.0.1:8000/li
```
The output for 3 line items would be the following:
```json
{
  "status": "ok",
  "LineItems": [
    "1",
    "2",
    "3"
  ]
}
```

3. Get general status
```bash
curl --request GET \
  --url http://127.0.0.1:8000/li/1/status
```
The general status of a line item returns the sum of expenditures and the total remaining budget:
```json
{
  "spent": 0,
  "remaining": 10000
}
```

4. Get status detailed by time zone
```bash
curl --request GET \
  --url http://127.0.0.1:8000/li/1/status/tz
```
The output is the expenditure per time zone. Assuming that we have spent $1 in the time zone America/New_York, the output would be:
```json
{
  "spent": {
    "Europe/Paris": 0,
    "America/New_york": 1.0
  },
  "remaining": {
    "Europe/Paris": 5000.0,
    "America/New_york": 4999.0
  }
}
```

5. Get status of a precised time zone
```bash
curl --request GET \
  --url http://127.0.0.1:8000/li/1/status/tz/STRING_TIMEZONE
```
Note: The `/` of the timezone in the URL should be replaced by `--`. For example if you want the time zone `America/New_York`:
```bash 
curl --request GET \
  --url http://127.0.0.1:8000/li/1/status/tz/America--New_York
```
The output would be then:
```json
{
  "spent": 1.0,
  "remaining": 4999.0
}
```

**Test the API<br />**
You can launch unit tests on the API by starting the local server and then execute the following command:
```bash
py.test .
```

To test the API in "real" conditions, you can start the local server, and if you have a br dataframe, just launch the ```exec_api.py``` script.
```bash
python exec_api.py
```


