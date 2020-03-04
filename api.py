#!/usr/bin/env python3

import json
from flask import Flask, request, jsonify, abort
from flask_restful import Api
from subprocess import check_output

# From current directory (lcd_functions.py and buzzer_functions.py)
from lcd_functions import LCD
from buzzer_functions import Buzzer


app = Flask(__name__)
api = Api(app)

# TODO: logging

routes_file = '/home/pi/trackman/GPS-Tracker/logs/gps_logs/routes.log'
HOST_IP = check_output(['hostname', '--all-ip-addresses']).decode('ascii').strip()
PORT = '5000'


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
    if not results:
        abort(404)
    return jsonify(results)


@app.route('/routes', methods=['GET'])
def get_routes():
    params_dict = request.args.to_dict()
    if len(params_dict) > 1:
        raise TypeError('Too many parameters')
    try:
        if params_dict == {}:
            data = get_all_routes_data()
        else:
            data = get_routes_data_by_param(params_dict)
    except FileNotFoundError:
        abort(404)
    else:
        return data


if __name__ == '__main__':

    lcd = LCD()
    buzzer = Buzzer()

    buzzer.beep()

    # Display Connection Info
    lcd.display('API - PORT:{} '.format(PORT), 1)
    lcd.display(HOST_IP, 2)

    app.run(host=HOST_IP, port=PORT)
