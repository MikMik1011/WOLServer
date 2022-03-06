import os
import requests
import json
from flask import Flask, request, jsonify
from wakeonlan import send_magic_packet
from discord_webhook import DiscordWebhook

from threading import Event, Thread

def call_repeatedly(interval, func, *args):
    stopped = Event()
    def loop():
        while not stopped.wait(interval): # the first call is in `interval` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set

mac = "YOUR MAC HERE" 
serverPort = 1234 #YOUR PORT HERE
wolPort = 4343 #YOUR WOL PORT HERE
webhookURL = "YOUR DISCORD WEBHOOK URL HERE"

oldIP = ""

def updateNOIP():
    try: 
        print("pokrenut update")
        global oldIP, webhookURL
        
        response = requests.get("https://api.myip.com/")
        newIP = response.json()["ip"]

        if newIP != oldIP:
            oldIP = newIP
            os.system("noipy -u your_nick_here -p your_pw_here -n your_ddns_url_here --provider noip")
            DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'DDNS IP azuriran, novi IP je: {newIP}').execute()
        else: 
            print("nije novi ip")

    except:
        print("offline")


call_repeatedly(10, updateNOIP)

app = Flask(__name__)


@app.route('/wol', methods=['GET'])
def sendWOL():
    if request.args.get("sifra") == "YourPassHere":
        send_magic_packet(mac, port = wolPort)
        DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'WOL paket poslat sa IPa: {request.environ["REMOTE_ADDR"]}').execute()
        return "WOL paket poslat!" 
    else:
        DiscordWebhook(url=webhookURL, rate_limit_retry=True, content=f'IP: {request.environ["REMOTE_ADDR"]} je pokusao da posalje WOL paket al se uvatio za kurac').execute()
        return "ne znas sifru od fice"

app.run(host = '0.0.0.0', port = serverPort )



