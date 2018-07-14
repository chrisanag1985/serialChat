from PySide.QtCore import *
from PySide.QtGui import *
import time
import serial
import sys
import json
import base64
import re

#sport = sys.argv[1] 
#ser = serial.Serial(port=sport)
#print(ser)

#text2 = "a"*2330
#
#interval_time = 4
"""
possible types:
msg - message
file - file
resend - request to resend chunks that were damaged
"""




class Send(QThread):
    
    """
    before you start() you must enter the self.text 
    """

    sendData = Signal(int)
    totalData = Signal(int)
    endData = Signal()

    def __init__(self,parent):
        QThread.__init__(self)
        self.counter = 0
        self.text = None
        self.nickname = parent.nickname 
        self.filename = None
        self.type = 'msg'
        self.ser = parent.serial_port 
        self.interval_time = parent.intervaltime
        self.progressbar = parent.progressBar
        self.parent = parent


    def run(self):
        if type(self.text) == unicode:
            self.text = self.text.encode('utf-8')
        full_size = len(self.text)
        self.totalData.emit(full_size)
        pieces = full_size/1024
        remain = full_size%1024
        size = 1024
        t2s = ''
        if self.parent.acp127:
            t2s = "VZCZC "
        sending_data = {}
        sending_data['type'] = self.type 
        sending_data['filename'] = self.filename 
        sending_data['nickname'] = self.nickname
        sending_data['size'] = full_size
        sending_data['pieces'] = pieces
        sending_data['remain'] = remain
        try:
            t2s += json.dumps(sending_data)
        except Exception as e:
            print(e)
        t2s += "_E_s_F_"
        if self.parent.acp127:
            t2s += " NNNN"
        self.ser.write(t2s)
        self.ser.flush()
        time.sleep(3) 
        texttmp = '' 
        sending_data = {}
        self.counter = 0

        for i in range(0,pieces+1):
            if i== pieces and remain !=0:

                t2s = ''
                if self.parent.acp127:
                    t2s = "VZCZC "
                sending_data = {}
                texttmp = self.text[-(remain):]
                self.counter += len(texttmp)
                sending_data['data_remain'] = base64.b64encode(texttmp)
                try:
                    t2s += json.dumps(sending_data)
                except Exception as e:
                    print(e) 
                t2s += "_E_0_F_"
                if self.parent.acp127:
                    t2s += " NNNN"
                self.ser.write(t2s)
                self.ser.flush()
                self.sendData.emit(self.counter)
                self.endData.emit()
                self.ser.flushInput()
                self.ser.flushOutput()
            elif i == pieces and remain == 0:
                t2s = ''
                if self.parent.acp127:
                    t2s = "VZCZC "
                sending_data['data_remain'] = base64.b64encode("_")
                try:
                    t2s += json.dumps(sending_data)
                except Exception as e:
                    print(e)
                t2s += "_E_0_F_"
                if self.parent.acp127:
                    t2s += " NNNN"
                self.ser.write(t2s)
                self.ser.flush()
                self.endData.emit()
                self.ser.flushInput()
                self.ser.flushOutput()
            else:
                t2s = ''
                if self.parent.acp127:
                    t2s = "VZCZC "
                sending_data = {}
                texttmp = self.text[size*i:size*(i+1)]
                self.counter += len(texttmp)
                sending_data['data_'+str(i)] =  base64.b64encode(texttmp)
                try:
                    t2s += json.dumps(sending_data)
                except Exception as e:
                    print(e)
                t2s += "_E_0_P_"
                if self.parent.acp127:
                    t2s += " NNNN"
                self.ser.write(t2s)
                self.ser.flush()
                self.sendData.emit(self.counter)
                time.sleep(self.interval_time)




class Receive(QThread):

    startRCV = Signal(int)
    endRCV = Signal()
    catchESF = Signal(str)
    catchEOP = Signal(int)

    def __init__(self,parent):
        QThread.__init__(self)
        self.iswaitingData = False
        self.data = {} 
        self.size = 0
        self.pieces = 0
        self.remain = 0
        self.filename = None 
        self.nickname = None
        self.type = None
        self.ser = parent.serial_port 
        self.parent = parent
        self.loopRun = True
        self.tdata = ''


    def clear_vars(self):
        self.data = {}
        self.tdata = ''


    def run(self):
        self.tdata = ''
        self.counter = 0
        while self.loopRun:
        
            
            iswait = self.ser.inWaiting()
            
            if iswait > 0:
                #self.emit(SIGNAL('startRCV(int)'),self.ser.inWaiting())
                self.startRCV.emit(self.ser.inWaiting())
                if iswait >1024:
                    iswait = 1024
                if self.tdata == '':
                    self.tdata = self.ser.read(iswait) 
                else:
                    self.tdata += self.ser.read(iswait) 
                if "_E_s_F_" in self.tdata:
                    #self.emit(SIGNAL('catchESF(str)'),self.tdata)
                    if self.parent.acp127 :
                        self.tdata = self.tdata.replace("VZCZC ","")
                        self.tdata = self.tdata.replace(" NNNN","")

                    self.tdata = self.tdata.replace("_E_s_F_","")
                    self.catchESF.emit(self.tdata)
                    try:
                        self.tdata = json.loads(self.tdata)
                        self.size = self.tdata['size']
                        self.filename = self.tdata['filename']
                        self.nickname = self.tdata['nickname']
                        self.pieces = self.tdata['pieces']
                        self.remain = self.tdata['remain']
                        self.type = self.tdata['type']
                        self.tdata=''
                    except Exception:
                        print(Exception)
                        self.tdata=''

                if "_E_0_P_" in self.tdata:
                    if self.parent.acp127 :
                        self.tdata = self.tdata.replace("VZCZC ","")
                        self.tdata = self.tdata.replace(" NNNN","")
                    self.tdata  = self.tdata.replace("_E_0_P_","")
                    #lenofdata = len(self.tdata)
                    try:
                        self.tdata = json.loads(self.tdata) 
                        key,value = self.tdata.popitem() 
                        value = base64.b64decode(value)
                    except Exception:
                        print("Problem... b64")
                        print(value)
                    self.data[key]=str(value)
                    lenofdata = len(value)
                    #self.emit(SIGNAL('catchEOP(int)'),lenofdata)
                    self.catchEOP.emit(lenofdata)
                    self.tdata = ''

                if "_E_0_F_" in self.tdata:
                    if self.parent.acp127 :
                        self.tdata = self.tdata.replace("VZCZC ","")
                        self.tdata = self.tdata.replace(" NNNN","")
                    self.tdata  = self.tdata.replace("_E_0_F_","")
                    try:
                        self.tdata = json.loads(self.tdata) 
                        key,value = self.tdata.popitem() 
                        value = base64.b64decode(value)
                    except Exception:
                        print("Problem...b64")
                        print(value)
                    self.data[key]=str(value)
                    lenofdata = len(value)
                    #self.emit(SIGNAL('catchEOP(int)'),lenofdata)
                    self.catchEOP.emit(lenofdata)
                    #self.emit(SIGNAL('endRCV()'))
                    self.endRCV.emit()
                    self.tdata = ''
                    self.counter = 0
                    self.ser.flushInput()
                    self.ser.flushOutput()
            time.sleep(0.5)
