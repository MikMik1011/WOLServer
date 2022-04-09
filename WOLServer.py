import time
startTime = time.time()

import os
import requests
from datetime import datetime, timedelta 
from flask import Flask, request, make_response, jsonify
from wakeonlan import send_magic_packet
from discord_webhook import DiscordWebhook
from threading import Event, Thread

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

def call_repeatedly(interval, func, *args):
    stopped = Event()
    def loop():
        while not stopped.wait(interval): # the first call is in `interval` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set

mac = os.getenv("TARGET_MAC").replace(":", ".")
serverPort = int(os.getenv("SERVER_PORT")) 
wolPort = int(os.getenv("WOL_PORT"))
webhookURL = os.getenv("WEBHOOK_URL")

oldIP = ""

def log(args):
    currTime = datetime.now().strftime("%H:%M:%S") 

    print(f"[{currTime}] {args}") 

    if os.getenv("LOG_TO_FILE") == "True":
        try:
            with open("wolserver.log", "a") as logFile: 
                logFile.write(f"[{currTime}] {args}\n") 
        except:
            pass

    try:
        DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f"[{currTime}] {args}").execute() 
    except:
        pass

def debugPrint(args):
    if os.getenv("DEBUG") == "True": 
        log(args)

def resetLog():
    if os.getenv("LOG_TO_FILE") == "True": 
        try:
            with open("wolserver.log", "w") as logFile:
                logFile.write("")
        except:
            pass

    try:
        DiscordWebhook(url=webhookURL, rate_limit_retry=True, content="** **").execute() # ** ** sends a blank message to discord
    except:
        pass

resetLog()


def updateNOIP():
    try: 
        debugPrint("IP update check started!")
        global oldIP, webhookURL
        
        response = requests.get("https://api.ipify.org?format=json")
        newIP = response.json()["ip"]

        if newIP != oldIP:
            oldIP = newIP
            os.system("noipy -u {0} -p {1} -n {2} --provider noip".format(os.getenv("NOIP_USERNAME"), os.getenv("NOIP_PASSWORD"), os.getenv("NOIP_HOSTNAME")))
            try:
                log(f'DDNS IP updated, new IP is: {newIP}')
            except:
                pass
        else: 
            debugPrint("IP hasn't changed!")

    except:
        log("Failed to fetch your IP, maybe you are offline! (or maybe the ipify.org API is down)")

if os.getenv("USE_NOIP") == "True":
    call_repeatedly(int(os.getenv("NOIP_CHECK_PERIOD")), updateNOIP) 
    updateNOIP()

call_repeatedly(int(os.getenv("RUNNING_LOG_PERIOD")), log, "Server is up and running!")


def srvResp(success):
    return make_response(jsonify({
            "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "success": success, 
            }), 
            200 if success else 401, 
            {'WWW-Authenticate' : 'Basic realm="Enter credentials in order to send a WOL packet!"'} if not success else {}) 

app = Flask(__name__)

@app.route('/')
def helloWorld():
    return jsonify({"status": "online",
    "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    "uptime": str(timedelta(seconds = time.time() - startTime)),
    }) 

@app.route('/wol', methods=['GET'])
def sendWOL():
    if not request.authorization:
        return srvResp(False)
    elif request.authorization.username == os.getenv("SERVER_USERNAME") and request.authorization.password == os.getenv("SERVER_PASSWORD"): 
        send_magic_packet(mac, port = wolPort)
        try:
            log(f'{request.authorization.username} sent an WOL packet from the following IP: {request.environ["REMOTE_ADDR"]}')
        except:
            pass
        return srvResp(True) 
    else:
        try:
            log(f'IP: {request.environ["REMOTE_ADDR"]} didn\'t type the right password!')
        except:
            pass
        return srvResp(False)


log("Flask server is starting!")
app.run(host = '0.0.0.0', port = serverPort)
