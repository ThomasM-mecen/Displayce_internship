import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

# Read the json
filename = 'sample_br.json'
all_dict = []
with open(filename) as infile:
    for line in infile:
        all_dict.append(json.loads(line))

# Create lists of variables
ts_receive, imps = [], []
for line in all_dict:
    ts_receive.append(line['_source']['Timestamp_status_receive_ms'])
    imp = line['_source']['Bidrequest']['imp']
    imps.append(len(imp))
ts_receive_modified = [datetime.fromtimestamp(ts/1000.0).strftime("%H:%M") for ts in ts_receive]

# Create the dataframe
zippedList =  list(zip(ts_receive, ts_receive_modified, imps))
df = pd.DataFrame(zippedList, columns = ['Ts' , 'ts_string', 'imps'])
df.sort_values("Ts", axis = 0, ascending = True,
                 inplace = True, na_position ='last')

# Create the plot
plt.style.use('seaborn')
fig, ax = plt.subplots()
df.groupby(['ts_string'])['imps'].sum().plot(x='ts_string', y='imps', ax=ax, legend=False)
# Format plot.
plt.title("Evolution of impressions per minute", fontsize=24)
plt.xlabel('', fontsize=5)
plt.ylabel("Impressions", fontsize=16)
plt.tick_params(axis='both', which='major', labelsize=10)
fig.autofmt_xdate()
plt.show()