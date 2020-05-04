#!/usr/bin/env python
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from loguru import logger
import itertools

# global constants
filename = 'data/sample_br.json'
# N_LINES=5000
N_LINES=None

def parse_file(n_lines=None):
	with open(filename) as infile:
		if n_lines is not None: # only read at most n_lines
			file_iterator = itertools.islice(infile,0,n_lines)
		else:
			file_iterator = infile
		all_dict = list(map(json.loads,file_iterator))
		logger.info("Loaded {} rows",len(all_dict))
		return all_dict

# Create lists of variables
# ts_receive, imps = [], []
def map_impression(an_imp_object):
	record={
		'Ts':an_imp_object['_source']['Timestamp_status_receive_ms'],
		'imps':len(an_imp_object['_source']['Bidrequest']['imp'])
		}
	record['ts_string']=datetime.fromtimestamp(record['Ts']/1000.0).strftime("%H:%M")
	return record


def plot_impressions_by_time(df):
	logger.info("Preparing plot")
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

def main():
	all_dicts = parse_file(n_lines=N_LINES)
	records = map(map_impression,all_dicts)
	df = pd.DataFrame.from_records(records).sort_values("Ts",ascending=True,na_position="last")
	logger.info("Built dataframe with {} records :\n{}",len(df),df)
	plot_impressions_by_time(df)

if __name__ == '__main__':
	main()