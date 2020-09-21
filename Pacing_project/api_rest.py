import json
import falcon
from pacing_class_tz import GlobalPacing
from datetime import datetime
from loguru import logger
from wsgiref import simple_server

api = falcon.API()


class InitCampaign(object):

    def __init__(self):
        self.instances = {}

    def check_params(self, req):
        required_argument = {"budget", "start", "end", "cpid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)} in URL \n"
                           f"Possible arguments are: \n"
                           f"\t budget (integer) \n"
                           f"\t start (string format: %Y-%M-%d \n"
                           f"\t end (string format: %Y-%M-%d \n"
                           f"\t cpid")
        logger.info(f"Received arguments {req.keys()}")
        if req['cpid'] in self.instances.keys():
            raise ValueError(f"Campaign {req['cpid']} already created")
        try:
            int(req['budget'])
        except ValueError:
            raise ValueError(f"Unable to interpret budget={req['budget']}")
        try:
            datetime.strptime(req['start'], '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Unable to interpret start={req['start']}")
        try:
            datetime.strptime(req['end'], '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Unable to interpret start={req['end']}")

    def on_get(self, req, resp):
        data = req.params
        tz_list = ['America/Boise', 'America/Chicago', 'America/Denver', 'America/Detroit',
                   'America/Indiana/Indianapolis', 'America/Kentucky/Louisville', 'America/Los_Angeles',
                   'America/New_York', 'America/Phoenix', 'Europe/London', 'Europe/Paris']
        try:
            self.check_params(data)
        except Exception as e:
            resp.status = falcon.HTTP_500
            resp.body = json.dumps({
                'status': 'not ok',
                'error': str(e)
            })
            return

        try:
            pacing = GlobalPacing(total_budget=int(data['budget']),
                                  start_date=datetime.strptime(data['start'], '%Y-%m-%d'),
                                  end_date=datetime.strptime(data['end'], '%Y-%m-%d'),
                                  tz_list=tz_list)
            self.instances[data['cpid']] = pacing
            output = json.dumps({
                'status': 'ok'
            })
        except ValueError:
            resp.status = falcon.HTTP_400
            resp.body = json.dumps({
                'status': 'Not ok',
                'error': 'Budget could be negative OR start date superior to end date'
            })
            return
        resp.status = falcon.HTTP_200
        resp.body = output


class Campaign(object):

    def on_get(self, req, resp):
        cp_list = list(init_pacing.instances.keys())
        resp.body = json.dumps({
            'status': 'ok',
            'campaigns': cp_list
        })
        resp.status = falcon.HTTP_200

    def on_get_status(self, req, resp, cpid):
        try:
            good_instance = init_pacing.instances[cpid]
        except KeyError:
            resp.body = json.dumps({
                'error': f"campaign {cpid} doesn't exist"
            })
            resp.status = falcon.HTTP_500
            return
        spents = good_instance.pacing_performance()
        total_spent = sum(spents)
        remaining = good_instance.total_budget - total_spent
        resp.body = json.dumps({
            'spent': total_spent,
            'remaining': remaining
        })

    def on_get_status_tz(self, req, resp, cpid, tz):
        tz = tz.replace("--", "/")
        try:
            good_instance = init_pacing.instances[cpid]
        except KeyError:
            resp.body = json.dumps({
                'error': f"campaign {cpid} doesn't exist"
            })
            resp.status = falcon.HTTP_500
            return
        try:
            good_tz = good_instance.instances[tz]
        except KeyError:
            resp.body = json.dumps({
                'error': f"time zone {tz} doesn't exist"
            })
            resp.status = falcon.HTTP_500
            return
        resp.body = json.dumps({
            'spent': good_tz.budget_spent_total,
            'remaining': good_tz.budget_objective - good_tz.budget_spent_total
        })


class ReceiveBR(object):
    def check_and_parse_parameters(self, req):
        required_argument = {"tz", "cpm", "imps", "brid", "cpid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)} in URL")
        logger.info(f"Received arguments {req.keys()}")
        try:
            (float(req['imps']) * float(req['cpm'])) / 1000
        except ValueError:
            raise ValueError("Unable to interpret the price of the br")

    def on_post(self, req, resp):
        data = req.params
        ts = datetime.timestamp(datetime.utcnow())
        try:
            self.check_and_parse_parameters(data)
        except Exception as e:
            resp.status = falcon.HTTP_500
            resp.body = json.dumps({
                'status': 'not ok',
                'error': str(e)
            })
            return
        try:
            good_instance = init_pacing.instances[data['cpid']]
        except KeyError:
            resp.body = json.dumps({
                'status': 'not ok',
                'error': f"campaign {data['cpid']} doesn't exist"
            })
            resp.status = falcon.HTTP_500
            return
        try:
            price = (float(data['imps']) * float(data['cpm'])) / 1000
            buying, *_ = good_instance.choose_pacing(ts, data['tz'], price, float(data['imps']), int(data['brid']))
        except Exception as e:
            resp.body = json.dumps({
                'status': 'not ok',
                'error': str(e)
            })
            resp.status = falcon.HTTP_500
            return
        resp.body = json.dumps({
            'status': 'ok',
            'buying': buying
        })
        resp.status = falcon.HTTP_200


class ReceiveNotification(object):
    def check_params(self, req):
        required_argument = {"cpid", "status", "brid"}
        missing_argument = required_argument.difference(req.keys())
        if missing_argument:
            raise KeyError(f"Missing argument {str(missing_argument)} in URL")
        logger.info(f"Received arguments {req.keys()}")
        if req['status'] not in ["win", "lose"]:
            raise ValueError(f"Status should be win or lose. {req['status']} was given")

    def on_get(self, req, resp):
        data = req.params
        try:
            self.check_params(data)
        except Exception as e:
            resp.status = falcon.HTTP_500
            resp.body = json.dumps({
                'status': 'not ok',
                'error': str(e)
            })
            return
        try:
            good_instance = init_pacing.instances[data['cpid']]
        except KeyError:
            resp.body = json.dumps({
                'status': 'not ok',
                'error': f"campaign {data['cpid']} doesn't exist"
            })
            resp.status = falcon.HTTP_500
            return
        try:
            good_instance.dispatch_notifications(int(data['brid']), data['status'])
        except KeyError:
            resp.body = json.dumps({
                'status': 'not ok',
                'error': f"br with id {data['brid']} doesn't exist"
            })
            resp.status = falcon.HTTP_500
            return
        resp.body = json.dumps({
            'status': 'ok'
        })
        resp.status = falcon.HTTP_200


init_pacing = InitCampaign()
br = ReceiveBR()
notif = ReceiveNotification()
cp = Campaign()
api.add_route("/campaign", cp)
api.add_route("/campaign/{cpid}/status", cp, suffix="status")
api.add_route("/campaign/{cpid}/status/{tz}", cp, suffix="status_tz")
api.add_route("/init", init_pacing)
api.add_route("/br", br)
api.add_route("/notif", notif)

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, api)
    httpd.serve_forever()
