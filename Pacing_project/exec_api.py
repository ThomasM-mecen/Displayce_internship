import requests as req
import pandas as pd
from datetime import datetime
import pytz


# Main function to simulate the API
def main(data, budget):
    """Function to simulate the API

    :param data: Dataframe of br
    :param budget: budget allocated to the line item
    :return:
    """
    # Initialise the campaign and the line item
    req.post("http://127.0.0.1:8000/campaign", json={"cpid": "1"})
    req.post("http://127.0.0.1:8000/campaign/1/init", json={
        "budget": budget,
        "start": "2020-07-09",
        "end": "2020-07-12",
        "liid": "1"
    })
    i = True
    for utc, row in data.iterrows():
        if i and utc > datetime(2020, 7, 9):
            i = False
            # Simulate a reset in the budget
            req.post("http://127.0.0.1:8000/li/1/reset", json={
                "new_budget": budget + 1000
            })
        tz = row['TZ']
        ts = row['ts']
        local = datetime.fromtimestamp(ts, tz=pytz.timezone(tz))

        # Before the campaign?
        if local < pytz.timezone(tz).localize(datetime(2020, 7, 9)):
            continue

        # End of the campaign?
        if local > pytz.timezone(tz).localize(datetime(2020, 7, 13)):
            continue

        # Receive BR and make a decision
        req.post("http://127.0.0.1:8000/li/1/br", json={
            "ts": ts,
            "tz": tz,
            "brid": row['id'],
            "imps": row['imps'],
            "cpm": row['CPM']
        })
        # Receive a notification
        req.post("http://127.0.0.1:8000/li/1/notif", json={
            "status": "win" if row['win'] else "lose",
            "brid": row['id']
        })
    return


if __name__ == '__main__':
    df = pd.read_pickle('data/br_clean.pkl')
    df.set_index('UTC_date', inplace=True)
    df.sort_index(inplace=True)
    df['id'] = range(len(df))
    databis = df['2020-07-08':'2020-07-13']
    main(databis, 10000)
    req.get("http://127.0.0.1:8000/li/1/status/tz")
    req.get("http://127.0.0.1:8000/li/1/status")
