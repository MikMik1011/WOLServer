import os
import requests
from datetime import datetime
from flask import Flask, request, make_response, jsonify
from wakeonlan import send_magic_packet
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv, find_dotenv
from threading import Event, Thread

def debugPrint(args):
    if os.getenv("DEBUG") == "True":
        print(args)

def srvResp(success):
    return make_response(jsonify({
            "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "success": success, 
            }), 200 if success else 401, 
            {'WWW-Authenticate' : 'Basic realm="Enter credentials in order to send a WOL packet!"'} if not success else {})

def call_repeatedly(interval, func, *args):
    stopped = Event()
    def loop():
        while not stopped.wait(interval): # the first call is in `interval` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set

load_dotenv(find_dotenv())

mac = os.getenv("TARGET_MAC").replace(":", ".")
serverPort = int(os.getenv("SERVER_PORT")) 
wolPort = int(os.getenv("WOL_PORT"))
webhookURL = os.getenv("WEBHOOK_URL")

oldIP = ""

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
                DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'DDNS IP updated, new IP is: {newIP}').execute()
            except:
                pass
        else: 
            debugPrint("IP hasn't changed!")

    except:
        print("Failed to fetch your IP, maybe you are offline! (or maybe the ipify.org API is down)")

if os.getenv("USE_NOIP") == "True":
    call_repeatedly(int(os.getenv("NOIP_CHECK_PERIOD")), updateNOIP)

app = Flask(__name__)


@app.route('/wol', methods=['GET'])
def sendWOL():
    if not request.authorization:
        return srvResp(False)
    elif request.authorization.username == os.getenv("SERVER_USERNAME") and request.authorization.password == os.getenv("SERVER_PASSWORD"):
        send_magic_packet(mac, port = wolPort)
        try:
            DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'{request.authorization.username} sent an WOL packet from the following IP: {request.environ["REMOTE_ADDR"]}').execute()
        except:
            pass
        return srvResp(True) 
    else:
        try:
            DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'IP: {request.environ["REMOTE_ADDR"]} didn\'t type the right password!').execute()
        except:
            pass
        return srvResp(False)

app.run(host = '0.0.0.0', port = serverPort)



