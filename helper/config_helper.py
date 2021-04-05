import json


def get_config():
    with open('config.json') as json_file:
        data = json.load(json_file)
        return data
