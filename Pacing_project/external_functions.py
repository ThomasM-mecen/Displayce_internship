from pacing_class import GlobalPacing
from datetime import datetime, timedelta
import pandas as pd
import pytz
from loguru import logger


def send_pending_notifications(instance_obj, pending_notif, current_ts=None):
    """ Send notifications

    :param instance_obj: instance of the algorithm class
    :param pending_notif: list of notifications
    :param current_ts: if None: will send all notifications, else send before current_ts
    """
    while len(pending_notif) > 0 and (pending_notif[0]['timestamp'] <= current_ts if current_ts else True):
        ev = pending_notif.pop(0)
        instance_obj.dispatch_notifications(ev['id'], ev['status'], ev['br_price'])


def main(data, budget, day_start, day_end):
    logger.info(f"Start pacing on {len(data)} bid requests")
    tz_list = data.TZ.unique().tolist()
    prop_tz = (data.groupby(data['TZ']).size() / len(data))
    pacing = GlobalPacing(total_budget=budget, start_date=datetime(2020, 7, day_start),
                          end_date=datetime(2020, 7, day_end), tz_list=tz_list, prop_tz=prop_tz)
    records = []
    pending_notifications = []
    for utc, row in data.iterrows():
        tz = row['TZ']
        ts = row['ts']
        local = datetime.fromtimestamp(ts, tz=pytz.timezone(tz))

        # Before the campaign?
        if local < pytz.timezone(tz).localize(pacing.start_date):
            continue

        # End of the campaign?
        if local > pytz.timezone(tz).localize(pacing.end_date + timedelta(days=1)):
            continue

        # Send current notifications
        send_pending_notifications(pacing, pending_notifications, utc)

        # Receive BR and make a decision
        buying, remaining_budget, spent_budget, engaged_budget = pacing.choose_pacing(
            ts, tz, row['price'], row['imps'], row['id'])

        # Create notification
        if buying:
            next_notif_ts = utc + timedelta(seconds=row['seconds_notif'])
            status = "win" if row['win'] else "lose"
            br_id = row['id']
            pending_notifications.append(
                {"timestamp": next_notif_ts, "status": status,
                 "br_price": row['price'], "id": br_id})
            pending_notifications.sort(key=lambda x: x["timestamp"])
        record = {
            'utc_date': utc,
            'local_date': local,
            'tz': tz,
            'buying': buying,
            'remaining': remaining_budget,
            'spent': spent_budget,
            'engaged': engaged_budget
        }
        records.append(record)
    # Send remaining notifications
    send_pending_notifications(pacing, pending_notifications)

    # Get pacing performances
    remainings, spents = pacing.pacing_performance()

    # Generate result DataFrame
    pacing_df = pd.DataFrame.from_records(records)
    pacing_df.set_index('utc_date', inplace=True)
    logger.info("End of the campaign")
    logger.info(f"Total budget spent: {sum(spents.values())}")
    logger.info(f"Remaining budget: {sum(remainings.values())}")
    return pacing_df
