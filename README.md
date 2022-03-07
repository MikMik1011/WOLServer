# Intro


## This is a REST server that can send WOL packets and also update your DDNS hostname. 

### One of the use-cases is ie. if your router flushes your computer's MAC instantly, so you can't send the WOL packet to your computer regularly, but instead you need to use some kind of a server on the local network which can do that for you.


# Usage


### Firstly, you need to install the required modules. List of them is in the `requirements.txt` file.
### You also need to make a `.env` file. There you have to declare and initialize the following variables:


```
DEBUG=False
TARGET_MAC=
SERVER_PORT=
WOL_PORT=
WEBHOOK_URL=
USE_NOIP=True
NOIP_CHECK_PERIOD=
NOIP_USERNAME=
NOIP_PASSWORD=
NOIP_HOSTNAME=
SERVER_USERNAME=
SERVER_PASSWORD=
```

### The variable names are pretty much self-explanatory. 


### Note: If you don't want to use NOIP then change the USE_NOIP variable to anything other than "True" (it is case sensitive). Also you can turn debug on if you want.


## Enjoy the script I guess!
