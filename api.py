import json
from flask import Flask, request, jsonify, abort
from flask_restful import Resource, Api


app = Flask(__name__)
api = Api(app)

# TODO: logging

routes_file = '/home/pi/trackman/GPS-Tracker/logs/gps_logs/routes.log'


def get_all_routes_data():
    results = []
    with open(routes_file) as rf:
        for line in rf:
            results.append(json.loads(line))
    return jsonify(results)


def get_routes_data_by_param(params_dict):
    results = []
    key, value = params_dict.popitem()
    with open(routes_file) as rf:
        for line in rf:
            if str(json.loads(line)[key]) == str(value):
                results.append(json.loads(line))
    if results == []:
        abort(404)
    return jsonify(results)



@app.route('/routes', methods=['GET'])
def get_routes():
    params_dict = request.args.to_dict()
    if len(params_dict) > 1:
        print(params_dict)
        raise TypeError('Too many parameters')
    try:
        if params_dict == {}:
            data = get_all_routes_data()
        else:
            data = get_routes_data_by_param(params_dict)
    except FileNotFoundError:
        abort(404)
    else:
        print(data)
        return data


if __name__ == '__main__':
    app.run(host='172.16.4.123', port='5000')
