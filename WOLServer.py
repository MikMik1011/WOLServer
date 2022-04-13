import subprocess
import time
startTime = time.time()

import os
import requests
from datetime import datetime, timedelta 
from flask import Flask, request, make_response, jsonify
from wakeonlan import send_magic_packet
import logging
from discord_handler import DiscordHandler
from threading import Event, Thread
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


mac = os.getenv("TARGET_MAC").replace(":", ".")
serverPort = int(os.getenv("SERVER_PORT")) 
wolPort = int(os.getenv("WOL_PORT"))
webhookURL = os.getenv("WEBHOOK_URL")

debug = os.getenv("DEBUG") == 'True'


app = Flask(__name__)

werkzeugLogger = logging.getLogger('werkzeug')
formatter = logging.Formatter("[%(asctime)s] %(levelname)s : %(message)s", "%d.%m.%Y %H:%M:%S")

handlers = []
handlers.append(logging.StreamHandler())
handlers.append(logging.FileHandler('wolserver.log', mode='a'))
handlers.append(DiscordHandler(webhookURL, "WOLServer"))

for handler in handlers:
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    werkzeugLogger.addHandler(handler)

if (debug):
    app.logger.setLevel(logging.DEBUG)
    werkzeugLogger.setLevel(logging.DEBUG)
else:
    app.logger.setLevel(logging.INFO)
    werkzeugLogger.setLevel(logging.INFO)

oldIP = ""
def updateNOIP():
    try: 
        werkzeugLogger.debug("IP update check started!")
        global oldIP, webhookURL
        
        response = requests.get("https://api.ipify.org?format=json")
        newIP = response.json()["ip"]

        if newIP != oldIP:
            oldIP = newIP
            noipyOutput = subprocess.check_output("noipy -u {0} -p {1} -n {2} --provider noip".format(os.getenv("NOIP_USERNAME"), os.getenv("NOIP_PASSWORD"), os.getenv("NOIP_HOSTNAME")), shell=True)
            werkzeugLogger.info(noipyOutput.decode("utf-8"))
        else: 
            werkzeugLogger.debug("IP hasn't changed!")

    except:
        werkzeugLogger.exception("Failed to fetch your IP, maybe you are offline! (or maybe the ipify.org API is down)")


def call_repeatedly(interval, func, *args):
    stopped = Event()
    def loop():
        while not stopped.wait(interval): # the first call is in `interval` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set

if os.getenv("USE_NOIP") == "True":
    call_repeatedly(int(os.getenv("NOIP_CHECK_PERIOD")), updateNOIP) 
    updateNOIP()

call_repeatedly(int(os.getenv("RUNNING_LOG_PERIOD")), werkzeugLogger.info, "Server is up and running!")


def srvResp(success):
    return make_response(jsonify({
            "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "success": success, 
            }), 
            200 if success else 401, 
            {'WWW-Authenticate' : 'Basic realm="Enter credentials in order to send a WOL packet!"'} if not success else {}) 


@app.route('/')
def helloWorld():
    return jsonify({"status": "online",
    "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    "uptime": str(timedelta(seconds = time.time() - startTime)),
    }) 

@app.route('/termux')
def termuxEndpoint():
    return subprocess.check_output(["termux-battery-status"]).decode("utf-8")

@app.route('/wol', methods=['GET'])
def sendWOL():
    if not request.authorization:
        return srvResp(False)
    elif request.authorization.username == os.getenv("SERVER_USERNAME") and request.authorization.password == os.getenv("SERVER_PASSWORD"): 
        send_magic_packet(mac, port = wolPort)
        try:
            werkzeugLogger.info(f'{request.authorization.username} sent an WOL packet from the following IP: {request.environ["REMOTE_ADDR"]}')
        except:
            pass
        return srvResp(True) 
    else:
        try:
            werkzeugLogger.critical(f'IP: {request.environ["REMOTE_ADDR"]} didn\'t type the right password!')
        except:
            pass
        return srvResp(False)


werkzeugLogger.info("Starting Flask server!")
app.run(host = '0.0.0.0', port = serverPort, debug = debug)


