import json
import falcon
from pacing_class_tz import GlobalPacing
from datetime import datetime
from loguru import logger
from wsgiref import simple_server

api = falcon.API()


# Store data
class DataBase(object):
    def __init__(self):
        self.campaigns = {}
        self.instances = {}


# Controller to initialise a campaign
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
            raise falcon.HTTPUnprocessableEntity(description=str(e))
        self.bdd.campaigns[data['cpid']] = []
        resp.body = json.dumps({
            "status": "ok",
        })

    def on_get(self, req, resp):
        length_dict = {key: len(value) for key, value in self.bdd.campaigns.items()}
        resp.body = json.dumps({
            "campaigns": length_dict
        })

    def on_delete(self, req, resp):
        data = json.loads(req.bounded_stream.read())
        try:
            del self.bdd.campaigns[data['cpid']]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"Campaign {data['cpid']} doesn't exist")
        resp.body = json.dumps({
            "status": "ok",
        })
        resp.status = falcon.HTTP_200


# Controller to initialise a line item
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
        try:
            self.check_params(data)
        except Exception as e:
            raise falcon.HTTPUnprocessableEntity(description=str(e))
        try:
            pacing = GlobalPacing(total_budget=int(data['budget']),
                                  start_date=datetime.strptime(data['start'], '%Y-%m-%d'),
                                  end_date=datetime.strptime(data['end'], '%Y-%m-%d'))
            self.bdd.instances[data['liid']] = pacing
            self.bdd.campaigns[cpid].append(data['liid'])
            output = json.dumps({
                "status": "ok",
            })
        except ValueError:
            raise falcon.HTTPUnprocessableEntity(description='Budget could be negative OR start date superior to end '
                                                             'date')
        resp.status = falcon.HTTP_200
        resp.body = output

    def on_delete(self, req, resp, cpid):
        data = json.loads(req.bounded_stream.read())
        if cpid not in self.bdd.campaigns.keys():
            raise falcon.HTTPNotFound(description=f"Campaign {cpid} doesn't exist")
        try:
            del self.bdd.instances[data['liid']]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {data['liid']} doesn't exist")
        self.bdd.campaigns[cpid].remove(data['liid'])
        resp.body = json.dumps({
            "status": "ok",
        })
        resp.status = falcon.HTTP_200


# Controller to have the status of a line item
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


# Controller to handle the reception of a bid request (make a buying decision)
class ReceiveBR(object):
    def __init__(self, bdd):
        self.bdd = bdd

    def check_and_parse_parameters(self, req):
        required_argument = {"tz", "cpm", "imps", "brid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)} in URL")
        logger.info(f"Received arguments {req.keys()}")

    def on_post(self, req, resp, liid):
        data = json.loads(req.bounded_stream.read())
        ts = datetime.timestamp(datetime.utcnow())
        # ts = data['ts']
        try:
            self.check_and_parse_parameters(data)
        except Exception as e:
            raise falcon.HTTPUnprocessableEntity(description=str(e))
        try:
            good_instance = self.bdd.instances[liid]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {liid} doesn't exist")
        try:
            buying, *_ = good_instance.choose_pacing(ts, data['tz'], data['cpm'], data['imps'], data['brid'])
        except Exception as e:
            raise falcon.HTTPUnprocessableEntity(description=str(e))
        resp.body = json.dumps({
            'status': 'ok',
            'buying': buying
        })
        resp.status = falcon.HTTP_200


# Controller to change the setup of a campaign
class ChangeSetup(object):
    def __init__(self, bdd):
        self.bdd = bdd

    def check_params(self, req):
        required_argument = {"new_budget"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)} in URL")
        logger.info(f"Received arguments {req.keys()}")
        if req['new_budget'] < 0:
            raise ValueError(f"New budget cannot be negative")

    def on_post(self, req, resp, liid):
        data = json.loads(req.bounded_stream.read())
        try:
            good_instance = self.bdd.instances[liid]
        except KeyError:
            raise falcon.HTTPNotFound(description=f"line item {liid} doesn't exist")
        try:
            good_instance.change_setup(data['new_budget'])
        except Exception as e:
            raise falcon.HTTPUnprocessableEntity(description=f"Exception {e}")
        resp.body = json.dumps({
            'status': 'ok'
        })
        resp.status = falcon.HTTP_200


# Controller to take into account the notification (win or lose)
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
            raise falcon.HTTPUnprocessableEntity(description=str(e))
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
reset_setup = ChangeSetup(bdd)
api.add_route("/campaign", init_campaign)
api.add_route("/campaign/{cpid}/init", init_pacing)
api.add_route("/li", li)
api.add_route("/li/{liid}/status", li, suffix="status")
api.add_route("/li/{liid}/status/tz", li, suffix="status_all")
api.add_route("/li/{liid}/status/tz/{tz}", li, suffix="status_tz")
api.add_route("/li/{liid}/br", br)
api.add_route("/li/{liid}/notif", notif)
api.add_route("/li/{liid}/reset", reset_setup)

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, api)
    httpd.serve_forever()
