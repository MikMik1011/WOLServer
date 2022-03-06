import os
import requests
import json
from flask import Flask, request, jsonify, make_response
from wakeonlan import send_magic_packet
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv, find_dotenv
from threading import Event, Thread

def debugPrint(args):
    if os.getenv("DEBUG") == "True":
        print(args)
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
        
        response = requests.get("https://api.myip.com/")
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
        debugPrint("The server is offline!")

if os.getenv("USE_NOIP") == "True":
    call_repeatedly(int(os.getenv("NOIP_CHECK_PERIOD")), updateNOIP)

app = Flask(__name__)


@app.route('/wol', methods=['GET'])
def sendWOL():
    if not request.authorization:
        return make_response("Hello!", 401, {'WWW-Authenticate' : 'Basic realm="Enter credentials in order to send a WOL packet!"'})
    elif request.authorization.username == os.getenv("SERVER_USERNAME") and request.authorization.password == os.getenv("SERVER_PASSWORD"):
        send_magic_packet(mac, port = wolPort)
        try:
            DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'{request.authorization.username} sent an WOL packet from the following IP: {request.environ["REMOTE_ADDR"]}').execute()
        except:
            pass
        return "<h1>WOL packet sent successfully!<h1>" 
    else:
        try:
            DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'IP: {request.environ["REMOTE_ADDR"]} didn\'t type the right password!').execute()
        except:
            pass
        return make_response("Invalid password!", 401, {'WWW-Authenticate' : 'Basic realm="Enter credentials in order to send a WOL packet!"'})

app.run(host = '0.0.0.0', port = serverPort)



