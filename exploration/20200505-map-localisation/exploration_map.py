import json
import pandas as pd
from plotly.graph_objs import Scattergeo, Layout
from plotly import offline
from loguru import logger
import itertools

# Global constants
filename = 'data/sample_br.json'
# N_LINES=5000
N_LINES = None

# Parse json file
def parse_file(n_lines=None):
    """ Function to parse a json file and slice by the number of line we want (default: no slice)"""
    with open(filename) as infile:
        if n_lines is not None:
            file_iterator = itertools.islice(infile, n_lines)
        else:
            file_iterator = infile
        all_dict = list(map(json.loads, file_iterator))
    logger.info(f"Loaded {len(all_dict)} rows")
    return all_dict


# Create records
def map_localisation(coord_object):
    """Function to create a dictionary of our variables"""
    # Avoid error with empty city name (namely Paris)
    try:
        city = coord_object['_source']['Bidrequest']['device']['geo']['city'].title()
    except KeyError:
        city = 'Paris'
    record = {
        'lons': coord_object['_source']['Bidrequest']['device']['geo']['lon'],
        'lats': coord_object['_source']['Bidrequest']['device']['geo']['lat'],
        'cities': city
    }
    return record


# Function for the marker's size
def size_marker(number):
    """Return a good size for markers"""
    if number > 50:
        number = 50
    elif number < 10:
        number = 10
    return number

def plot_map(df):
    logger.info("Preparing plot")
    # Create map
    data = [{
        'type': 'scattergeo',
        'lon': df.lons.tolist(),
        'lat': df.lats.tolist(),
        'text': [f'City: {x} <br> Number of BR: {y}' for x, y in list(zip(df.cities.tolist(), df.counts.tolist()))],
        'hovertemplate': "%{text}",
        'marker': {
            'size': [size_marker(count / 100) for count in df.counts.tolist()],
            'color': df.counts.tolist(),
            'colorscale': 'Viridis',
            'reversescale': True,
            'colorbar': {'title': 'Number'},
        },
    }]
    my_layout = Layout(title='Bid requests per localisation')
    fig = {'data': data, 'layout': my_layout}
    offline.plot(fig, filename='br_loc.html')


# Execute script
def main():
    all_dicts = parse_file()
    records = map(map_localisation, all_dicts)
    df = pd.DataFrame.from_records(records)
    df = df.groupby(['cities', 'lons', 'lats']).size().reset_index(name='counts')
    logger.info(f"Built dataframe with {len(df)} records :\n{df}")
    plot_map(df)


if __name__ == '__main__':
    main()




