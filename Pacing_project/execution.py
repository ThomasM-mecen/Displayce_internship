from external_functions import main
import pandas as pd


if __name__ == '__main__':
    df = pd.read_pickle('data/br_clean.pkl')
    df.set_index('UTC_date', inplace=True)
    df.sort_index(inplace=True)
    df['id'] = range(len(df))
    df_slice = df['2020-07-08':'2020-07-10']
    pacing_results = main(df_slice, 5000, 8, 9)
