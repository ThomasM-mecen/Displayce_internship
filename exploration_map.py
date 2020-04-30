import json
from datetime import datetime
import pandas as pd
from plotly.graph_objs import Scattergeo, Layout
from plotly import offline

# Read the json
filename = 'sample_br.json'
all_dict = []
with open(filename) as infile:
    for line in infile:
        all_dict.append(json.loads(line))

# Create lists
lons, lats, cities = [], [], []
for line in all_dict:
    lons.append(line['_source']['Bidrequest']['device']['geo']['lon'])
    lats.append(line['_source']['Bidrequest']['device']['geo']['lat'])
    try:
        cities.append(line['_source']['Bidrequest']['device']['geo']['city'].title())
    except KeyError:
        cities.append('Paris')

# Create Dataframe
zippedList =  list(zip(lons,lats,cities))
df = pd.DataFrame(zippedList, columns = ['lons','lats','cities'])
df = df.groupby(['cities','lons','lats']).size().reset_index(name='counts')

# Function for the marker's size
def size_marker(number):
    """Return a good size for markers"""
    if number > 50:
        number = 50
    elif number < 10:
        number = 10
    return number

# Create map
data = [{
    'type' : 'scattergeo',
    'lon' : df.lons.tolist(),
    'lat' : df.lats.tolist(),
    'text' : [f'City: {x} <br> Number of BR: {y}' for x,y in list(zip(df.cities.tolist(), df.counts.tolist()))],
    'hovertemplate' : "%{text}",
    'marker' : {
        'size' : [size_marker(count/100) for count in df.counts.tolist()],
        'color': df.counts.tolist(),
        'colorscale': 'Viridis',
        'reversescale': True,
        'colorbar': {'title': 'Number'},
    },
}]
my_layout = Layout(title = 'Bid requests per localisation')
fig = {'data' : data, 'layout' : my_layout}
offline.plot(fig, filename='br_loc.html')