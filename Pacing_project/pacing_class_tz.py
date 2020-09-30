from datetime import datetime
from datetime import timedelta
import pandas as pd
import pytz
import itertools
from statsmodels.formula.api import ols


# Temporal pacing class
class Pacing:
    """ The temporal pacing algorithm class
    """

    def __init__(self, total_budget, start_date, end_date, timezone):
        """Class constructor"""

        # Fixed attributes
        self.tz = pytz.timezone(timezone)
        self.start_date = self.tz.localize(start_date)
        self.end_date = self.tz.localize(end_date + timedelta(days=1))
        self.total_days = (self.end_date - self.start_date).days
        # data for the linear regression
        self.buffer = list()
        self.buffer_data = pd.DataFrame()
        # Initialise variables
        self.remaining_days = (self.end_date - self.start_date).days
        self.budget_objective = total_budget
        self.budget_engaged = 0
        self.budget_spent_total = 0
        self.budget_remaining = self.budget_objective - (
                self.budget_engaged + self.budget_spent_total)
        self.current_hour = -1
        self.budget_remaining_hourly = 0
        self.budget_daily = self.budget_remaining / self.remaining_days
        self.surplus_hour = 0
        self.bs_history = [0]
        self.ongoing_br = {}
        self.acceleration = [{'ts': self.start_date,
                              'A': 0}]
        self.speed = [{'ts': self.start_date,
                       'S': 0}]
        self.size_acceleration = 1
        self.sum_acceleration = 0
        self.size_speed = 1
        self.sum_speed = 0
        self.prop_table, self.unif, self.without_weekday = self.meta_prop(self.buffer_data)
        # Setup variables to begin pacing
        self.day = self.start_date.day
        self.nb_br = 0
        self.nb_buy = 0
        self.prop_purchase = 0
        self.spent_per_sec = 0
        self.surplus_hour = 0
        self.spent_hour = 0
        # Flag variables
        self.new_objective = None
        self.trigger_count = False
        self.block_increase = False
        self.first_br = True
        self.first_day = True

    # Functions for the linear regression
    @staticmethod
    def gen_prop_lr(br_object):
        """Linear regression with hours and weekdays

        :param br_object: historical data about bid requests to perform linear regression
        :return: Dataframe
        """
        aggr = br_object.imps.groupby([br_object.index.date, br_object.index.weekday, br_object.index.hour]).sum()
        aggr.index.names = ['date', 'weekday', 'hour']
        # Here we keep the date column but note that it is irrelevant.
        aggr = aggr.reset_index()
        model = ols('imps ~ C(weekday) + C(hour)', data=aggr).fit()
        weekday_list = range(7)
        weekday_list = list(itertools.chain.from_iterable(itertools.repeat(x, 24) for x in weekday_list))
        hour_list = list()
        for i in range(7):
            for z in range(24):
                hour_list.append(z)
        df_fitting = pd.DataFrame({'weekday': weekday_list, 'hour': hour_list})
        prediction = model.predict(df_fitting)
        df_fitting['fitted'] = prediction
        pattern = df_fitting.pivot_table('fitted', index=df_fitting.hour, columns=df_fitting.weekday)
        line, col = pattern.shape
        for i in range(col):
            pattern.iloc[:, i] = pattern.iloc[:, i] * 100 / pattern.iloc[:, i].sum()
        return pattern

    @staticmethod
    def gen_prop_lr_hour(br_object):
        """Linear regression with only hours

        :param br_object: historical data about bid requests to perform linear regression
        :return: Dataframe
        """
        aggr = br_object.imps.groupby([br_object.index.date, br_object.index.hour]).sum().reset_index()
        aggr.columns = ['date', 'hour', 'imps']
        model = ols('imps ~ C(hour)', data=aggr).fit()
        hour_list = list()
        for z in range(24):
            hour_list.append(z)
        df_fitting = pd.DataFrame({'hour': hour_list})
        prediction = model.predict(df_fitting)
        df_fitting['fitted'] = prediction
        df_fitting.index = df_fitting.hour
        del df_fitting['hour']
        df_fitting.iloc[:, 0] = df_fitting.iloc[:, 0] * 100 / df_fitting.iloc[:, 0].sum()
        return df_fitting

    def meta_prop(self, data):
        """ Give the proportion of impressions per hour. The output type depends on the input.

        :param data: a dataframe with a datetime as index
        :return: an  integer, a Serie or a Dataframe
        """
        if data.empty or set(data.index.hour.unique()) != set(range(24)):
            unif = True
            without_weekday = True
            prop = 1 / 24
        else:
            if set(data.index.weekday.unique()) != set(range(7)):
                unif = False
                without_weekday = True
                prop = self.gen_prop_lr_hour(data)
            else:
                unif = False
                without_weekday = False
                prop = self.gen_prop_lr(data)
        return prop, unif, without_weekday

    # Function to reset variables when we start a new day
    def day_reset(self, ts):
        """ Reset variables when there is a new day

        :param ts: timestamp
        """
        day = ts.day
        month = ts.month
        year = ts.year
        self.remaining_days = (self.end_date - ts).days + 1  # +1 because we have to take the end of the day
        if not self.buffer:
            self.buffer_data = pd.DataFrame.from_records(self.buffer)
        else:
            self.first_day = False
            self.buffer_data = pd.DataFrame.from_records(self.buffer, index='Date')
        # Reinitialise some variables
        self.current_hour = -1
        self.budget_remaining_hourly = 0
        self.budget_daily = self.budget_remaining / self.remaining_days
        self.surplus_hour = 0
        self.bs_history = [0]
        self.acceleration = [{'ts': self.tz.localize(datetime(year, month, day, 0, 0, 0)),
                              'A': 0}]
        self.speed = [{'ts': self.tz.localize(datetime(year, month, day, 0, 0, 0)),
                       'S': 0}]
        self.size_acceleration = 1
        self.sum_acceleration = 0
        self.size_speed = 1
        self.sum_speed = 0
        self.prop_table, self.unif, self.without_weekday = self.meta_prop(self.buffer_data)

    # Function when we change hour
    def change_hour(self, weekday):
        """ Reset budget for the following hour

        :param weekday: week day integer
        """
        self.current_hour += 1
        self.remaining_hours = 24 - self.current_hour
        # Evolutive target
        self.surplus_hour += self.budget_remaining_hourly / self.remaining_hours
        if self.unif:
            self.budget_hour = (self.prop_table * self.budget_daily) + self.surplus_hour
        elif self.without_weekday and not self.unif:
            self.budget_hour = (self.prop_table.iloc[
                                    self.current_hour, 0] / 100) * self.budget_daily + self.surplus_hour
        else:
            self.budget_hour = (self.prop_table.iloc[
                                    self.current_hour, weekday] / 100) * self.budget_daily + self.surplus_hour
        self.target = self.budget_hour / 3600
        self.spent_hour = 0
        self.budget_remaining_hourly = self.budget_hour - self.spent_hour

    # Mean of budget variation the last 30 minutes
    def gen_mean_speed(self):
        """ Return the moving average of variation of the budget per second over 30 minutes
        """
        created_time = self.speed[-1]['ts'] - timedelta(minutes=30)
        while self.speed[0]['ts'] < created_time:
            self.size_speed -= 1
            self.sum_speed += self.speed[0]['S']
            del self.speed[0]
        try:
            average = self.sum_speed / self.size_speed
        except ZeroDivisionError:
            average = 0
        return average

    # Mean of speed of variation the last 30 minutes
    def gen_mean_acceleration(self):
        """ Return the moving average of the speed of variation of the budget per second over 30 minutes
        """
        created_time = self.acceleration[-1]['ts'] - timedelta(minutes=30)
        while self.acceleration[0]['ts'] < created_time:
            self.size_acceleration -= 1
            self.sum_acceleration += self.acceleration[0]['A']
            del self.acceleration[0]
        try:
            average = self.sum_acceleration / self.size_acceleration
        except ZeroDivisionError:
            average = 0
        return average

    # Build the dataframe for the linear regression
    def build_data_prop(self, ts, imps):
        """ Build Dataframe for the proportion per hour linear regression

        :param ts: current timestamp
        :param imps: number of impressions
        """
        self.buffer.append({'Date': ts, 'imps': imps})

    def bs_calculation(self, average_acceleration, average_speed, remaining_time, coef=1):
        """ Calculate the available budget per second

        :param average_acceleration: mean of acceleration over 30 min
        :param average_speed: mean of speed over 30 min
        :param remaining_time: remaining time in seconds before the end of the hour
        :param coef: importance of speed and variation in the formula (default is one)
        """
        alpha = average_acceleration * coef
        try:
            bs = self.budget_remaining_hourly * ((1 + alpha * average_speed) / remaining_time)
        except ZeroDivisionError:
            bs = 1
        if bs < 0:
            bs = 1
        return bs

    # Function to make the buying decision. This the main function of the pacing class algorithm
    def buying_decision(self, ts, price, imps, br_id):
        """From a BR, decide whether to buy or not

        :param ts: timestamp of the BR
        :param price: price of the BR
        :param imps: number of impressions
        :param br_id: id of bid request
        :return: Boolean
        """

        # If we have spent all budget then we will never buy
        if self.budget_remaining <= 0:
            buying = False
            return buying

        # Check problem in br
        if price < 0:
            return False
        if imps < 0:
            return False

        if self.first_br:
            self.first_br = False
            self.ts_first_br = datetime.timestamp(ts)

            # Enough time to check proportion
        if datetime.timestamp(ts) - self.ts_first_br >= 3600:
            self.trigger_count = True

        # TS de la BR
        self.weekday = ts.weekday()
        day = ts.day
        month = ts.month
        year = ts.year
        hour = ts.hour

        # If we begin a new day, we reset variables
        if self.day != day:
            self.day_reset(ts)
        self.day = day

        # Changement of hour
        while hour != self.current_hour:
            self.change_hour(self.weekday)

        # Build data for proportion lr
        self.build_data_prop(ts, imps)

        # Remaining time before the end of the hour
        end_hour = self.tz.localize(datetime(year, month, day, hour, 59, 59, 999999))
        remaining_time = datetime.timestamp(end_hour) - datetime.timestamp(ts)

        # Calculation of the budget per second (bs)
        average_acceleration = self.gen_mean_acceleration()
        average_speed = self.gen_mean_speed()
        self.bs = self.bs_calculation(average_acceleration, average_speed, remaining_time)

        # Calculation of vt and at
        self.bs_history.append(self.bs)
        vt = self.bs_history[-1] - self.bs_history[-2]
        self.speed.append({'ts': ts,
                           'S': vt})
        self.size_speed += 1  # We calculate the size without using len() for micro optimisation
        at = self.speed[-1]['S'] - self.speed[-2]['S']
        self.acceleration.append({'ts': ts,
                                  'A': at})
        self.size_acceleration += 1  # We calculate the size without using len() for micro optimisation

        # Buying decision
        if (self.bs >= self.target) and (self.budget_remaining_hourly - price) >= 0:
            buying = True
            self.budget_engaged += price
            self.spent_hour += price
            self.nb_buy += 1
            self.ongoing_br[br_id] = price
        else:
            buying = False
        self.budget_remaining_hourly = self.budget_hour - self.spent_hour
        self.budget_remaining = self.budget_objective - (
                self.budget_engaged + self.budget_spent_total)
        if self.budget_remaining < 0:
            self.budget_remaining = 0
        self.nb_br += 1

        # Check proportion of bought br
        self.new_objective = self.check_proportion(ts)

        return buying

    # Proportion of buying
    def check_proportion(self, ts):
        """ Check if the algorithm needs to buy a high volume of bid requests to reach the objective

        :param ts: current timestamp
        :return: New objective if we have to lower the budget or none if it is already ok
        """
        self.prop_purchase = self.nb_buy / self.nb_br
        if not self.first_day and self.trigger_count and self.prop_purchase >= 0.7:
            elapsed_time = datetime.timestamp(ts) - datetime.timestamp(self.start_date)
            spent_per_sec = self.budget_spent_total / elapsed_time
            remaining_time = datetime.timestamp(self.end_date) - datetime.timestamp(ts)
            new_objective = (spent_per_sec * remaining_time) * 0.85
            if (self.budget_spent_total + self.budget_engaged) < new_objective < self.budget_objective:
                self.block_increase = True
                self.trigger_count = False
                self.ts_first_br = datetime.timestamp(ts)
                return new_objective

    # Function to reset the spend objective
    def reallocate_budget(self, new_budget):
        """ This function handle a reset of the budget that needs to be spent

        :param new_budget: budget
        """
        self.budget_objective = new_budget
        self.budget_remaining = self.budget_objective - (
                self.budget_engaged + self.budget_spent_total)
        if self.budget_remaining < 0:
            self.budget_remaining = 0
        self.budget_daily = self.budget_remaining / self.remaining_days
        if self.unif:
            self.budget_hour = (self.prop_table * self.budget_daily) + self.surplus_hour
        elif self.without_weekday and not self.unif:
            self.budget_hour = (self.prop_table.iloc[
                                    self.current_hour, 0] / 100) * self.budget_daily + self.surplus_hour
        else:
            self.budget_hour = (self.prop_table.iloc[
                                    self.current_hour, self.weekday] / 100) * self.budget_daily + self.surplus_hour
        self.target = self.budget_hour / 3600
        self.spent_hour = 0
        self.budget_remaining_hourly = self.budget_hour - self.spent_hour

    # Function to handle the reception of a notification
    def receive_notification(self, status, br_id):
        """ From a notification, take into account the status (win/lose)

        :param status: 'win' or 'lose'
        :param br_id: id of the bid request
        """
        br_price = self.ongoing_br[br_id]
        if status == 'win':
            self.budget_engaged -= br_price
            self.budget_spent_total += br_price
        elif status == 'lose':
            self.budget_engaged -= br_price
            self.spent_hour -= br_price
        self.budget_remaining = self.budget_objective - (
                self.budget_engaged + self.budget_spent_total)
        del self.ongoing_br[br_id]


# Class to create handle  different time zones. It allows a dynamic budget reallocation between instances
class GlobalPacing(object):
    def __init__(self, total_budget, start_date, end_date):

        # Raise errors in parameters
        if total_budget < 0:
            raise ValueError("Budget cannot be negative!")
        if start_date > end_date:
            raise ValueError("Start date cannot be later than end date!")

        self.total_budget = total_budget
        self.start_date = start_date
        self.end_date = end_date
        self.tz_list = []
        self.tz_objective = []
        self.timezones = {}
        self.instances = {}

    # If we need to change the setup
    def update_budget(self, new_budget):
        """This function allows to change the budget allocated initially to the line item

        :param new_budget: new budget to be spent
        :return:
        """
        self.total_budget = new_budget
        budget_tz = self.total_budget / len(self.tz_list)
        for key in self.tz_list:
            self.instances[key].reallocate_budget(budget_tz)

    # When we receive a bid request from a timezone that we have never met
    def new_instance(self, new_tz):
        """ Generate a new instance of the temporal pacing class when there is a new time zone

        :param new_tz: name of the new timezone
        """
        if len(self.instances) == 0:
            self.tz_list.append(new_tz)
            self.tz_objective.append(new_tz)
            self.instances[new_tz] = Pacing(total_budget=self.total_budget,
                                            start_date=self.start_date,
                                            end_date=self.end_date, timezone=new_tz)
        else:
            budget_tz = self.total_budget / (len(self.tz_list) + 1)
            self.instances[new_tz] = Pacing(total_budget=budget_tz,
                                            start_date=self.start_date,
                                            end_date=self.end_date, timezone=new_tz)
            for key in self.tz_list:
                self.instances[key].reallocate_budget(budget_tz)
            self.tz_list.append(new_tz)
            self.tz_objective.append(new_tz)

    # Main function to select the good pacing instance and make the buying decision
    def choose_pacing(self, ts, tz, cpm, imps, br_id):
        """ Function to select the good pacing instance and return the buying decision

        :param ts: timestamp of the br
        :param tz: time zone of the br
        :param cpm: Cost per mile of the br
        :param imps: number of impressions
        :param br_id: id of the br
        :return: buying decision with some statistics
        """
        price = (imps * cpm) / 1000
        local_date = datetime.fromtimestamp(ts, tz=pytz.timezone(tz))
        # Before the campaign?
        if local_date < pytz.timezone(tz).localize(self.start_date):
            raise ValueError("BR before campaign start date")
        # End of the campaign?
        if local_date > pytz.timezone(tz).localize(self.end_date + timedelta(days=1)):
            raise ValueError("BR after campaign end date")
        if tz not in self.instances.keys():
            self.new_instance(tz)
        buying = self.instances[tz].buying_decision(local_date, price, imps, br_id)
        if buying:
            self.timezones[br_id] = tz
        budget_remaining = self.instances[tz].budget_remaining
        spent_budget = self.instances[tz].budget_spent_total
        budget_engaged = self.instances[tz].budget_engaged
        prop = self.instances[tz].prop_purchase
        if self.instances[tz].new_objective is not None:
            self.set_new_objectives(self.instances[tz].budget_objective,
                                    self.instances[tz].new_objective, tz)
        objective = self.instances[tz].budget_objective
        return buying, budget_remaining, spent_budget, budget_engaged, objective, prop

    # Function called when we have to set new objectives of spend
    def set_new_objectives(self, old_budget, new_budget, tz):
        """ Allow to dynamically reallocate budget between time zones

        :param old_budget: budget objective before
        :param new_budget: new budget objective
        :param tz: timezone related to the changement
        """
        for key in self.tz_list:
            # We delete the tz from the list to block the increase
            if self.instances[key].block_increase:
                try:
                    self.tz_objective.remove(key)
                except ValueError:
                    pass
        # We check if there is at least one timezone to dispatch the surplus budget
        if len(self.tz_objective) > 0:
            surplus_budget = (old_budget - new_budget) / len(self.tz_objective)
            self.instances[tz].reallocate_budget(new_budget)
            for key in self.tz_objective:
                self.instances[key].reallocate_budget(self.instances[key].budget_objective +
                                                      surplus_budget)

    # Function to call the good instance when we receive a notification
    def dispatch_notifications(self, br_id, status):
        """Dispatch notifications to the good instances of pacing

        :param br_id: id of the br
        :param status: 'win' or 'lose'
        """
        tz = self.timezones[br_id]
        del self.timezones[br_id]
        self.instances[tz].receive_notification(status, br_id)

    # Function to see the current spent of all time zones
    def pacing_performance(self):
        """Function that return a list of expenditure of each time zone

        """
        spents = []
        for key in self.tz_list:
            spents.append(self.instances[key].budget_spent_total)
        return spents
