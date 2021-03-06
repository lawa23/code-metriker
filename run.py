#!/usr/bin/python3
# coding: utf-8

import os
import sys
import datetime
import json
import random
import argparse
import asyncio
import time


from aiohttp import web

APP_VERSION = "001"

# exit codes for shell, failures can later be sub-devided
# if required and shell/user has benefit of this information
EXIT_OK      = 0
EXIT_FAILURE = 1



def set_config_defaults(app):
    # CAN be overwritten by config, will
    # be checked for sanity before webserver start
    app['MAX_REQUEST_SIZE'] = 5000000


def init_aiohttp(conf):
    app = web.Application()
    app["CONF"] = conf
    return app


async def handle_journal(request):
    root = request.app['path-root']
    full = os.path.join(root, "assets/webpage/journal.html")
    with open(full, 'r') as content_file:
        content = str.encode(content_file.read())
        return web.Response(body=content, content_type='text/html')


async def handle_utilization(request):
    root = request.app['path-root']
    full = os.path.join(root, "assets/webpage/utilization.html")
    with open(full, 'r') as content_file:
        content = str.encode(content_file.read())
        return web.Response(body=content, content_type='text/html')


async def handle_index(request):
    raise web.HTTPFound('journal')


def setup_routes(app, conf):
    app.router.add_route('GET', '/journal', handle_journal)
    app.router.add_route('GET', '/utilization', handle_utilization)

    path_assets = os.path.join(app['path-root'], "assets")
    app.router.add_static('/assets', path_assets, show_index=False)

    app.router.add_get('/', handle_index)


def timeout_daily_midnight(app):
    print("Execute daily execution handler")
    start_time = time.time()
    # do something
    end_time = time.time()
    print("Excuted in {:0.2f} seconds".format(end_time - start_time))


def seconds_to_midnight():
    now = datetime.datetime.now()
    deltatime = datetime.timedelta(days=1)
    tomorrow = datetime.datetime.replace(now + deltatime, hour=0, minute=0, second=0)
    seconds = (tomorrow - now).seconds
    if seconds < 60: return 60.0 # sanity checks
    if seconds > 60 * 60 * 24: return 60.0 * 60 * 24
    return seconds


def register_timeout_handler_daily(app):
    loop = asyncio.get_event_loop()
    midnight_sec = seconds_to_midnight()
    call_time = loop.time() + midnight_sec
    msg = "Register daily timeout [scheduled in {} seconds]".format(call_time)
    print(msg)
    loop.call_at(call_time, register_timeout_handler_daily, app)
    timeout_daily_midnight(app)


def register_timeout_handler(app):
    register_timeout_handler_daily(app)


def setup_db(app):
    app['path-root'] = os.path.dirname(os.path.realpath(__file__))

def init_debug(conf):
    pass


def main(conf):
    init_debug(conf)
    app = init_aiohttp(conf)
    setup_db(app)
    setup_routes(app, conf)
    register_timeout_handler(app)
    web.run_app(app, host="localhost", port=conf['port'])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--configuration", help="configuration", type=str, default=None)
    parser.add_argument("-v", "--verbose", help="verbose", action='store_true', default=False)
    args = parser.parse_args()
    if not args.configuration:
        emsg = "Configuration required, please specify a valid file path, exiting now"
        sys.stderr.write("{}\n".format(emsg))
        emsg = "E.g.: \"./run.py -f conf/code-metriker.conf\""
        sys.stderr.write("{}\n".format(emsg))
        sys.exit(EXIT_FAILURE)
    return args


def load_configuration_file(args):
    config = dict()
    exec(open(args.configuration).read(), config)
    return config

def configuration_check(conf):
    if not "port" in conf:
        conf['port'] = '8080'

def conf_init():
    args = parse_args()
    conf = load_configuration_file(args)
    configuration_check(conf)
    return conf


if __name__ == '__main__':
    info_str = sys.version.replace('\n', ' ')
    print("Starting code-metriker (python: {})".format(info_str))
    conf = conf_init()
    main(conf)
