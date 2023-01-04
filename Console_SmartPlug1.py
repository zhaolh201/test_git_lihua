'''
Created on 19 aôut 2022
author: Lihua Zhao
Fonction: Il affiche l'heure actuelle et la météo actuelle avec l'image dans Console. Il peut controle les etats de
          l'alarme, la lumière du salon, la lumière de l'entrée par deux façons: click le bouton et dire le commande.
          Il y a deux tk interfaces: Historique montre les events et Commande montre les commandes et responses.
Référence: https://support.asplhosting.com/t/working-myqtthub-com-python-paho-examples/43
'''
from tkinter import *
import paho.mqtt.client as mqtt 
import pymongo
from datetime import datetime
from threading import Thread
import time
from pyowm import OWM
from pyowm.utils.config import get_default_config
from PIL import Image, ImageTk
from speech_recognition import Recognizer, Microphone
from gtts import gTTS
import subprocess

import threading

""" Quitter proprement """
def fermer():
    print("Quitter proprement")
    alarmClient.loop_stop()
    alarmClient.disconnect()

    light_enter_client.loop_stop()
    light_enter_client.disconnect()
    
    light_salon_client.loop_stop()
    light_salon_client.disconnect()


    port_enter_client.loop_stop()
    port_enter_client.disconnect()


    speechRecongnizer.terminate()

    fen1.destroy()

def cmd_alarm_on():
    alarmClient.publish("Alarm/Commandes", "on")

def cmd_alarm_off():
    alarmClient.publish("Alarm/Commandes", "off")

def cmd_light_enter_on():
    light_enter_client.publish("LightEnter/Commandes", "on")

def cmd_light_enter_off():
    light_enter_client.publish("LightEnter/Commandes", "off")

def cmd_light_salon_on():
    light_salon_client.publish("LightSalon/Commandes", "on")

def cmd_light_salon_off():
    light_salon_client.publish("LightSalon/Commandes", "off")

def cmd_port_enter_on():
    light_salon_client.publish("PortEnter/Commandes", "on")

def cmd_port_enter_off():
    light_salon_client.publish("PortEnter/Commandes", "off")
    
def on_alarm_Message(client, userdata, message):
    print("alarm received message: " ,str(message.payload.decode("utf-8")))
    alarmEtat.configure(text=str(message.payload.decode("utf-8")))
    if handle['control']==0:
        history_update()

def on_light_enter_message(client, userdata, message):
    print("light enter received message: " ,str(message.payload.decode("utf-8")))
    lightEnterEtat.configure(text=str(message.payload.decode("utf-8")))
    if handle['control']==0:
        history_update()

def on_light_salon_message(client, userdata, message):
    print("light salon received message: " ,str(message.payload.decode("utf-8")))
    lightSalonEtat.configure(text=str(message.payload.decode("utf-8")))
    if handle['control']==0:
        history_update()

def on_port_enter_message(client, userdata, message):
    print("Port enter received message: " ,str(message.payload.decode("utf-8")))
    portEnterEtat.configure(text=str(message.payload.decode("utf-8")))
    if handle['control']==0:
        history_update()

def history_update():
    global recordframe
    global collection
    resultstr = ''
    #datarecords = [{'date': '22/06/29', 'heure': '20:45:30', 'event': 'Lumiere Salon:OFF'},
    #               {'date': '22/06/29', 'heure': '03:45:30', 'event': 'Alarme:ARME'},
    #               {'date': '22/06/30', 'heure': '22:45:30', 'event': 'Lumiere Entree:ON'}]
    #for item in datarecords:
    recordsum = len(list(collection.find()))
    if recordsum >= 10:
        for item in collection.find().skip(recordsum-10):
            resultstr += item['date'] + '    ' + item['heure'] + '    ' + item['event'] + '\n'
    else:
        for item in collection.find():
            resultstr += item['date'] + '    ' + item['heure'] + '    ' + item['event'] + '\n'
        for i in range(10 - recordsum):
            resultstr += '\n'
    resultlabel = Label(recordframe, text=resultstr, font="Helvetica 16", justify='left')
    resultlabel.grid(row=2, column=0)

def weather_init():
    global observation
    config_dict = get_default_config()
    config_dict['language'] = 'fr'
    owm = OWM('66342ecbbade1fdccc2c4cde8600eb85', config_dict)
    mgr = owm.weather_manager()
    observation = mgr.weather_at_place('Montreal,CA')
    fetch()

def fetch():
    global tempertureValue
    global weather_icon_name
    w = observation.weather
    tempertureValue = w.temperature('celsius')['temp']
    weather_icon_name = w.weather_icon_name

def update_weather():
    tempertureEtat.configure(text=str(int(round(tempertureValue))) + chr(176) + "C")
    img = Image.open("Icon/" + weather_icon_name + ".png")
    photo = ImageTk.PhotoImage(img)
    imglabel.configure(image=photo)
    imglabel.bm = photo
    imglabel.grid(row=1, column=0)


def time_update():
    global timeCount
    timeCount +=1
    heure = datetime.now().strftime("%H:%M:%S")
    timeEtat.configure(text=heure)
    if (timeCount ==90):
        timeCount=0
        fetch()
        update_weather()
    fen1.after(1000, time_update)


class speechRecongnizerTask:
    def __init__(self):
        self._running = True
        self.threadRun = False
        print('true')
        self.hotwords = ["ouvrir la lumière de l'entrée", "allumer la lumière de l'entrée",
                         "fermer la lumière de l'entrée", "éteindre la lumière de l'entrée",
                         "ouvrir la lumière du salon", "allumer la lumière du salon", "fermer la lumière du salon",
                         "éteindre la lumière du salon", "quelle heure est-il", "il est quelle heure",
                         "quel temps fait-il", "ouvrir la porte de l'entrée", "fermer la porte de l'entrée",
                         "ouvrir l'alarme", "activer l'alarme", "fermer l'alarme", "désactiver l'alarme"]
        self.repondes = ["La lumière de l'entrée est allumé", "La lumière de l'entrée est allumé",
                         "La lumière de l'entrée est éteinte", "La lumière de l'entrée est éteinte",
                         "La lumière du salon est allumé", "La lumière du salon est allumé",
                         "La lumière du salon est éteinte", "La lumière du salon est éteinte",
                         "Il est ", "Il est ", "Il fait ", "La porte de l'entrée est ouverte",
                         "La porte de l'entrée est fermée", "L'alarme est activée", "L'alarme est activée",
                         "L'alarme est désactivée", "L'alarme est désactivée"]
        #self.speechrecord =[]

    def terminate(self):
        self._running = False

    def reset(self):
        self._running = True

    def run(self):
        recognizer = Recognizer()
        self.threadRun = True
        while self._running:
            with Microphone() as source:
                print("Réglage du bruit ambiant... Patientez...")
                recognizer.adjust_for_ambient_noise(source)
                print("Vous pouvez parler...")
                recorded_audio = recognizer.listen(source, phrase_time_limit=15)
                print("Enregistrement terminé !")

                # Reconnaissance de l'audio

                try:
                    print("Reconnaissance du texte...")
                    text = recognizer.recognize_google(
                        recorded_audio,
                        language="fr-FR"
                    )
                    print("Vous avez dit : {}".format(text))


                    flag = False
                    for i in range(len(self.hotwords)):
                        if self.hotwords[i] in text:
                            outstr = self.repondes[i]
                            if ((i==0) or (i ==1)):
                                cmd_light_enter_on()
                            elif ((i==2) or (i ==3)):
                                cmd_light_enter_off()
                            elif ((i==4) or (i ==5)):
                                cmd_light_salon_on()
                            elif ((i==6) or (i ==7)):
                                cmd_light_salon_off()
                            elif ((i==8) or (i==9)):
                                outstr = self.repondes[i] + datetime.now().strftime("%H:%M:%S")
                            elif (i == 10):
                                outstr = self.repondes[i] + str(int(round(tempertureValue)))+" degrée"
                            elif (i ==11):
                                cmd_port_enter_on()
                            elif (i ==12):
                                cmd_port_enter_off()
                            elif ((i==13) or (i ==14)):
                                cmd_alarm_on()
                            elif ((i==15) or (i ==16)):
                                cmd_alarm_off()

                            # if (len(self.speechrecord) ==10):
                            #     self.speechrecord.pop(0)
                            # self.speechrecord.append({'command':self.hotwords[i],'response': outstr})
                            self.command = self.hotwords[i]
                            self.response = outstr
                            speechrecord_update()
                            tts = gTTS(text=outstr, lang="fr")
                            tts.save('out.mp3')
                            cmd = ['mpg321', '-q', 'out.mp3']
                            subprocess.call(cmd)
                            print(outstr)
                            flag = True
                    if (not flag):
                        print("aucune commande détectée")
                        tts = gTTS(u"aucune commandes detecter", lang="fr")
                        tts.save('out.mp3')
                        cmd = ['mpg321', '-q', 'out.mp3']
                        subprocess.call(cmd)
                except Exception as ex:
                    print(ex)
        self.threadRun = False



def history_close():
    global handle
    global history
    handle['control']=1
    history.destroy()

def speech_close():
    global handle
    global speech

    speechRecongnizer.terminate()
    handle['speech']=1
    speech.destroy()

def speech_onclick():
    global speechframe
    global handle
    global speech
    global sumrow
    if handle['speech']:
        speech = Toplevel()
        speech.protocol("WM_DELETE_WINDOW", speech_close)
        speechframe = LabelFrame(speech)
        speechframe.grid(row=0, column=0, padx=20, pady=10)
        titlelabel = Label(speechframe, text='commande', font="Helvetica 18 bold")
        titlelabel.grid(row=0,column=0)
        titlelabel = Label(speechframe, text='response', font="Helvetica 18 bold")
        titlelabel.grid(row=0, column=1)
        signlabel = Label(speechframe,  text='===========================', font="Helvetica 18 bold")
        signlabel.grid(row=1,column=0,columnspan=2)
        sumrow = 2

        #speechrecord_update()
        exitbtn = Button(speech, text="Quitter", font="Helvetica 18 bold", command=speech_close)
        exitbtn.grid(row=1,column=0)
        while speechRecongnizer.threadRun:
            { }
        speechRecongnizer.reset()
        thread = Thread(target=speechRecongnizer.run, args=())
        thread.start()

        handle['speech'] = 0

def speechrecord_update():
    global speechframe
    global sumrow
    #resultstr = ''
    # count=0
    commandLable = Label(speechframe, text=speechRecongnizer.command, font="Helvetica 16", justify='left', padx=10)
    commandLable.grid(row=sumrow, column=0)
    responseLable = Label(speechframe, text=speechRecongnizer.response, font="Helvetica 16", justify='left',padx=10)
    responseLable.grid(row=sumrow, column=1)
    sumrow += 1

    # for record in speechRecongnizer.speechrecord:
    #     commandLable = Label(speechframe, text=record['command'], font="Helvetica 16", justify='left',padx=10)
    #     commandLable.grid(row=2+count, column=0)
    #     responseLable = Label(speechframe, text=record['response'], font="Helvetica 16", justify='left',padx=10)
    #     responseLable.grid(row=2 + count, column=1)
    #     count +=1
    # for i in range(10 - len(speechRecongnizer.speechrecord)):
    #     commandLable = Label(speechframe, text='', font="Helvetica 16", justify='left', padx=10)
    #     commandLable.grid(row=2 + count, column=0)
    #     responseLable = Label(speechframe, text='', font="Helvetica 16", justify='left', padx=10)
    #     responseLable.grid(row=2 + count, column=1)
    #     count +=1


def history_onclick():
    global recordframe
    global handle
    global history

    if handle['control']:
        history = Toplevel()
        history.protocol("WM_DELETE_WINDOW", history_close)
        recordframe = LabelFrame(history)
        recordframe.grid(row=0, column=0, padx=20, pady=10)
        titlelabel = Label(recordframe, text='Date    Heure    Evennement', font="Helvetica 18 bold")
        titlelabel.grid(row=0,column=0)
        signlabel = Label(recordframe,  text='===========================', font="Helvetica 18 bold")
        signlabel.grid(row=1,column=0)
        history_update()
        exitbtn = Button(history, text="Quitter", font="Helvetica 18 bold", command=history_close)
        exitbtn.grid(row=1,column=0)
        handle['control'] = 0

""" MQTT """

host          = "node02.myqtthub.com"
port          = 1883
clean_session = True
alarmClient_id     = "systemAlarm"
light_enter_client_id     = "lampEnter"
light_salon_client_id     = "lampSalon"
port_enter_client_id       = "porteEnter"
user_name     = "zhaolh201"
password      = "test1234"

dbclient = pymongo.MongoClient("localhost")
db = dbclient.project1 # La base de donnée project 1
collection = db.eventrecord

handle = {}
handle['control'] = 1
handle['speech'] = 1

alarmClient = mqtt.Client(client_id = alarmClient_id, clean_session = clean_session)
alarmClient.username_pw_set (user_name, password)
alarmClient.connect (host, port)

light_enter_client = mqtt.Client(client_id = light_enter_client_id, clean_session = clean_session)
light_enter_client.username_pw_set (user_name, password)
light_enter_client.connect (host, port)

light_salon_client = mqtt.Client(client_id = light_salon_client_id, clean_session = clean_session)
light_salon_client.username_pw_set (user_name, password)
light_salon_client.connect (host, port)

port_enter_client = mqtt.Client(client_id = port_enter_client_id, clean_session = clean_session)
port_enter_client.username_pw_set (user_name, password)
port_enter_client.connect (host, port)

alarmClient.loop_start()

alarmClient.subscribe("Alarm/Etats")
alarmClient.on_message=on_alarm_Message

light_enter_client.loop_start()

light_enter_client.subscribe("LightEnter/Etats")
light_enter_client.on_message=on_light_enter_message

light_salon_client.loop_start()

light_salon_client.subscribe("LightSalon/Etats")
light_salon_client.on_message=on_light_salon_message


port_enter_client.loop_start()

port_enter_client.subscribe("PortEnter/Etats")
port_enter_client.on_message=on_port_enter_message

weather_init()
timeCount =0
""" Interface Tk """
fen1 = Tk()
fen1.protocol("WM_DELETE_WINDOW", fermer)

leftFrame = LabelFrame(fen1, font="Helvetica 20 bold", padx=10, pady=10)
leftFrame.grid(row=0, column=0)

timeEtat = Label(leftFrame, font="Helvetica 18 bold",padx=20, width=10)
timeEtat.grid(row=0, column=0)

img = Image.open("Icon/"+weather_icon_name+".png")
photo = ImageTk.PhotoImage(img)
imglabel = Label(leftFrame, image=photo)
imglabel.grid(row=1, column=0)

tempertureEtat = Label(leftFrame, text=str(int(round(tempertureValue)))+ chr(176) +"C", font="Helvetica 18 bold",padx=20, width=10)
tempertureEtat.grid(row=2, column=0)

Label(leftFrame, text="", font="Helvetica 18 bold",padx=20,pady=5).grid(row=3, column=0)


speechFrame = LabelFrame(leftFrame, text='Commande', font="Helvetica 20 bold", padx=10, pady=10)
speechFrame.grid(row=4, column=0)
speechBtn = Button(speechFrame, text='Vocale', font="Helvetica 18 bold", command=speech_onclick)
speechBtn.grid(row=0, column=0)

Label(leftFrame, text="", font="Helvetica 18 bold",padx=20,pady=5).grid(row=5, column=0)

historyFrame = LabelFrame(leftFrame, text='Historique', font="Helvetica 20 bold",padx=10, pady=10)
historyFrame.grid(row=6, column=0)
historyBtn = Button(historyFrame, text='Afficher', font="Helvetica 18 bold", command=history_onclick)
historyBtn.grid(row=0, column=0)

rightFrame = LabelFrame(fen1, font="Helvetica 20 bold", padx=10, pady=10)
rightFrame.grid(row=0, column=1)

alarmFrame = LabelFrame(rightFrame, text='Alarme', font="Helvetica 20 bold",padx=10, pady=10)
alarmFrame.pack(padx=10, pady=10)
alarmONBtn = Button(alarmFrame, text='ON', font="Helvetica 18 bold", command = cmd_alarm_on)
alarmONBtn.grid(row=0, column=0)
alarmOFFBtn = Button(alarmFrame, text='OFF', font="Helvetica 18 bold", command = cmd_alarm_off)
alarmOFFBtn.grid(row=0, column=1)
alarmEtat = Label(alarmFrame, text="Etat", fg='red', font="Helvetica 18 bold",padx=20,width=10)
alarmEtat.grid(row = 0, column = 2)

lightEnterFrame = LabelFrame(rightFrame, text='Lumiere entree', font="Helvetica 20 bold",padx=10, pady=10)
lightEnterFrame.pack(padx=10, pady=10)
lightEnterONBtn = Button(lightEnterFrame, text='ON', font="Helvetica 18 bold", command = cmd_light_enter_on)
lightEnterONBtn.grid(row=0, column=0)
lightEnterOFFBtn = Button(lightEnterFrame, text='OFF', font="Helvetica 18 bold", command = cmd_light_enter_off)
lightEnterOFFBtn.grid(row=0, column=1)
lightEnterEtat = Label(lightEnterFrame, text="Etat", fg='red', font="Helvetica 18 bold",padx=20,width=10)
lightEnterEtat.grid(row = 0, column = 2)

lightSalonFrame = LabelFrame(rightFrame, text='Lumiere salon', font="Helvetica 20 bold",padx=10, pady=10)
lightSalonFrame.pack(padx=10, pady=10)
lightSalonONBtn = Button(lightSalonFrame, text='ON', font="Helvetica 18 bold", command = cmd_light_salon_on)
lightSalonONBtn.grid(row=0, column=0)
lightSalonOFFBtn = Button(lightSalonFrame, text='OFF', font="Helvetica 18 bold", command = cmd_light_salon_off)
lightSalonOFFBtn.grid(row=0, column=1)
lightSalonEtat = Label(lightSalonFrame, text="Etat", fg='red', font="Helvetica 18 bold",padx=20,width=10)
lightSalonEtat.grid(row = 0, column = 2)

portEnterFrame = LabelFrame(rightFrame, text='Porte Enter', font="Helvetica 20 bold",padx=10, pady=10)
portEnterFrame.pack(padx=10, pady=10)
portEnterONBtn = Button(portEnterFrame, text='ON', font="Helvetica 18 bold", command = cmd_port_enter_on)
portEnterONBtn.grid(row=0, column=0)
portEnterOFFBtn = Button(portEnterFrame, text='OFF', font="Helvetica 18 bold", command = cmd_port_enter_off)
portEnterOFFBtn.grid(row=0, column=1)
portEnterEtat = Label(portEnterFrame, text="Etat", fg='red', font="Helvetica 18 bold",padx=20,width=10)
portEnterEtat.grid(row = 0, column = 2)


fen1.after(1000,time_update())
speechRecongnizer = speechRecongnizerTask()

fen1.mainloop()
