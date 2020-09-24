import json
import falcon
from pacing_class_tz import GlobalPacing
from datetime import datetime
from loguru import logger
from wsgiref import simple_server

api = falcon.API()


class DataBase(object):
    def __init__(self):
        self.campaigns = {}
        self.instances = {}


class InitCampaign(object):
    def __init__(self, bdd):
        self.bdd = bdd

    def check_params(self, req):
        required_argument = {"cpid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)}")
        logger.info(f"Received argument {req.keys()}")
        if req['cpid'] in bdd.campaigns.keys():
            raise ValueError(f"Campaign {req['cpid']} already created")

    def on_post(self, req, resp):
        data = json.loads(req.bounded_stream.read())
        try:
            self.check_params(data)
        except Exception as e:
            raise falcon.HTTPNotFound(description=str(e))
        self.bdd.campaigns[data['cpid']] = []
        resp.body = json.dumps({
            "status": "ok",
        })

    def on_get(self, req, resp):
        length_dict = {key: len(value) for key, value in self.bdd.campaigns.items()}
        resp.body = json.dumps({
            "campaigns": length_dict
        })


class InitLineItem(object):

    def __init__(self, bdd):
        self.bdd = bdd

    def check_params(self, req):
        required_argument = {"budget", "start", "end", "liid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)}\n"
                           f"Possible arguments are: \n"
                           f"\t budget (integer) \n"
                           f"\t start (string format: %Y-%M-%d \n"
                           f"\t end (string format: %Y-%M-%d \n"
                           f"\t cpid")
        logger.info(f"Received arguments {req.keys()}")
        if req['liid'] in self.bdd.instances.keys():
            raise ValueError(f"Line item {req['liid']} already created")
        try:
            int(req['budget'])
        except SyntaxError:
            raise ValueError(f"Unable to interpret budget={req['budget']}")
        try:
            datetime.strptime(req['start'], '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Unable to interpret start={req['start']}")
        try:
            datetime.strptime(req['end'], '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Unable to interpret start={req['end']}")

    def on_post(self, req, resp, cpid):
        data = json.loads(req.bounded_stream.read())
        if cpid not in self.bdd.campaigns.keys():
            raise falcon.HTTPNotFound(description=f"Campaign {cpid} doesn't exist")
        tz_list = ['America/Boise', 'America/Chicago', 'America/Denver', 'America/Detroit',
                   'America/Indiana/Indianapolis', 'America/Kentucky/Louisville', 'America/Los_Angeles',
                   'America/New_York', 'America/Phoenix', 'Europe/London', 'Europe/Paris']
        try:
            self.check_params(data)
        except Exception as e:
            raise falcon.HTTPNotFound(description=str(e))

        try:
            pacing = GlobalPacing(total_budget=int(data['budget']),
                                  start_date=datetime.strptime(data['start'], '%Y-%m-%d'),
                                  end_date=datetime.strptime(data['end'], '%Y-%m-%d'),
                                  tz_list=tz_list)
            self.bdd.instances[data['liid']] = pacing
            self.bdd.campaigns[cpid].append(data['liid'])
            output = json.dumps({
                "status": "ok",
            })
        except ValueError:
            raise falcon.HTTPNotFound(description='Budget could be negative OR start date superior to end date')
        resp.status = falcon.HTTP_200
        resp.body = output


class LineItem(object):
    def __init__(self, bdd):
        self.bdd = bdd

    def on_get(self, req, resp):
        li_list = list(self.bdd.instances.keys())
        resp.body = json.dumps({
            'status': 'ok',
            'LineItems': li_list
        })
        resp.status = falcon.HTTP_200

    def on_get_status(self, req, resp, liid):
        try:
            good_instance = self.bdd.instances[liid]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {liid} doesn't exist")
        spents = good_instance.pacing_performance()
        total_spent = sum(spents)
        remaining = good_instance.total_budget - total_spent
        resp.body = json.dumps({
            'spent': total_spent,
            'remaining': remaining
        })

    def on_get_status_all(self, req, resp, liid):
        try:
            good_instance = self.bdd.instances[liid]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {liid} doesn't exist")
        spents = {}
        remainings = {}
        for tz in good_instance.tz_list:
            good_tz = good_instance.instances[tz]
            spents[tz] = good_tz.budget_spent_total
            remainings[tz] = good_tz.budget_objective - good_tz.budget_spent_total
        resp.body = json.dumps({
            'spent': spents,
            'remaining': remainings
        })

    def on_get_status_tz(self, req, resp, liid, tz):
        tz = tz.replace("--", "/")
        try:
            good_instance = self.bdd.instances[liid]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {liid} doesn't exist")
        try:
            good_tz = good_instance.instances[tz]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"time zone {tz} doesn't exist")
        resp.body = json.dumps({
            'spent': good_tz.budget_spent_total,
            'remaining': good_tz.budget_objective - good_tz.budget_spent_total
        })


class ReceiveBR(object):
    def __init__(self, bdd):
        self.bdd = bdd
    def check_and_parse_parameters(self, req):
        required_argument = {"tz", "cpm", "imps", "brid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)} in URL")
        logger.info(f"Received arguments {req.keys()}")
        try:
            (req['imps'] * req['cpm']) / 1000
        except ValueError:
            raise ValueError("Unable to interpret the price of the br")

    def on_post(self, req, resp, liid):
        data = json.loads(req.bounded_stream.read())
        ts = datetime.timestamp(datetime.utcnow())
        try:
            self.check_and_parse_parameters(data)
        except Exception as e:
            raise falcon.HTTPNotFound(description=str(e))
        try:
            good_instance = self.bdd.instances[liid]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {liid} doesn't exist")
        try:
            price = (data['imps'] * data['cpm']) / 1000
            buying, *_ = good_instance.choose_pacing(ts, data['tz'], price, data['imps'], data['brid'])
        except Exception as e:
            raise falcon.HTTPNotFound(description=str(e))
        resp.body = json.dumps({
            'status': 'ok',
            'buying': buying
        })
        resp.status = falcon.HTTP_200


class ReceiveNotification(object):
    def __init__(self, bdd):
        self.bdd = bdd
    def check_params(self, req):
        required_argument = {"status", "brid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)} in URL")
        logger.info(f"Received arguments {req.keys()}")
        if req['status'] not in ["win", "lose"]:
            raise ValueError(f"Status should be win or lose. {req['status']} was given")

    def on_post(self, req, resp, liid):
        data = json.loads(req.bounded_stream.read())
        try:
            self.check_params(data)
        except Exception as e:
            raise falcon.HTTPNotFound(description=str(e))
        try:
            good_instance = self.bdd.instances[liid]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {liid} doesn't exist")
        try:
            good_instance.dispatch_notifications(data['brid'], data['status'])
        except KeyError:
            raise falcon.HTTPNotFound(description=f"br with id {data['brid']} doesn't exist")
        resp.body = json.dumps({
            'status': 'ok'
        })
        resp.status = falcon.HTTP_200


bdd = DataBase()
init_campaign = InitCampaign(bdd)
init_pacing = InitLineItem(bdd)
br = ReceiveBR(bdd)
notif = ReceiveNotification(bdd)
li = LineItem(bdd)
api.add_route("/campaign", init_campaign)
api.add_route("/campaign/{cpid}/init", init_pacing)
api.add_route("/li", li)
api.add_route("/li/{liid}/status", li, suffix="status")
api.add_route("/li/{liid}/status/tz", li, suffix="status_all")
api.add_route("/li/{liid}/status/tz/{tz}", li, suffix="status_tz")
api.add_route("/li/{liid}/br", br)
api.add_route("/li/{liid}/notif", notif)

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, api)
    httpd.serve_forever()
