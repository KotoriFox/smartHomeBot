from w1thermsensor import W1ThermSensor
import time
import datetime
import n_restClient

def setLanes(li):
  val = str(li)
  n_restClient.restSetVar("lanes", val)

class local1wire:
    def __init__(self):
        with open('adj.data', 'r') as f:
          x = f.read()
          self.tuning = eval(x)
        self.namesMap = {'Base' : 'Малина',
                         '011933991f9a' : 'Ванна',
                         '3c01b556fe32' : 'Кабінет',
                         '011933a43229' : 'Вітальня',

                         #'3c01a8162fb0' : 'Тамбур',
                         #'3c01a816bf53' : 'Коридор',
                         '01193ce99459' : 'в_Південь',

                         '3c01b55634fd' : 'Паливна',
                         '01193cb260aa' : '_Бак',
                         '01193cc5f4a9' : '_ТеплаПідлога',
                         '01193cb40a10' : 'ТрубаВерх',
                         '01193cb58b09' : 'NewTank',

                         #'01193cbde6d6' : 'в_Земля',
                         #'01193ce058f1' : 'в_Північ',
                         #'01193cd5001d' : 'в_ПідБудинком'
                         }
        self.lanesMap = {'011933991f9a' : 0,
                         '3c01b556fe32' : 0,
                         '011933a43229' : 0,

                         #'3c01a8162fb0' : 3,
                         #'3c01a816bf53' : 3,
                         '01193ce99459'  : 3,

                         '3c01b55634fd' : 2,
                         '01193cb260aa' : 2,
                         '01193cc5f4a9' : 2,
                         '01193cb40a10' : 2,
                         '01193cb58b09' : 2,

                         #'01193cbde6d6' : 1,
                         #'01193ce058f1' : 1,
                         #'01193cd5001d' : 1
                         }
        self.lanesCnt = {0:0,1:0,2:0,3:0}
        self.laneToKeys = [[i for i,j in self.lanesMap.items() if j == lane] for lane in range(4)]
        for i in self.lanesMap:
            self.lanesCnt[self.lanesMap[i]] += 1
        self.init1Wire()
    def init1Wire(self):
        # enable all lanes
        setLanes([1,1,1,1])
        total = sum(self.lanesCnt.values())
        cc = 0
        tries = 0
        while cc < total:
          time.sleep(1)
          tries +=1
          try:
            cc = len(W1ThermSensor.get_available_sensors())
            print("%d vs %d" % (cc,total))
          except:
            cc = 0
          if tries > 20:
            setLanes([0,0,0,0])
            time.sleep(1)
            setLanes([1,1,1,1])
            time.sleep(5)
            tries = 0
        self.onewire = {}
        for i in W1ThermSensor.get_available_sensors():
           lane = self.lanesMap[i.id]
           if not (lane in self.onewire):
               self.onewire[lane] = []
           self.onewire[lane].append(i)
        print(self.onewire)
    def readTemp(self):
      self.valid = 0
      tmpT = self.temp
      self.newTemp = {}
      for i in range(4):
          print("Read Lane ", i)
          self.readLane(i,tmpT)
      self.temp = self.newTemp
    def normalize(self, name, temp):
        #return temp
        temp = temp + self.tuning[name]
        temp = temp *1000
        temp = round(temp)
        temp = temp / 1000.0
        return temp
    def readLane(self, idx, tmpT):
        readcc = 0
        tries = 0
        while readcc < self.lanesCnt[idx]:
            tries += 1
            readcc = 0
            print ("reading lane ", idx, " expected ", self.lanesCnt[idx])
            try:
                for i in self.onewire[idx]:
                  t = i.get_temperature()
                  t = self.normalize(i.id, t)
                  n = self.nameConv(i.id)
                  condi = 1
                  if i.id in tmpT:
                    condi = (abs(t-tmpT[i.id]) < 20)
                  if condi:
                    self.newTemp[i.id] = t
                    readcc += 1
                    print (n, " Temp = ", t)
                  else:
                    print (n, " Temp invalid = ", t)
            except:
                pass
            if tries > 20:
                l = [1,1,1,1]
                l[idx] = 0
                setLanes(l)
                time.sleep(1)
                setLanes([1,1,1,1])
                tries = 0
                time.sleep(1)


if __name__ == '__main__':
    onewire = local1wire()
    rdt = datetime.timedelta(seconds=30)
    tnow = datetime.datetime.now()
    while 1:
        onewire.readTemp()
        res = {}
        for i in onewire.temp:
            name = onewire.namesMap[i]
            res[name] = onewire.temp[i]
        n_restClient.restDropTemp(res)
        nt = datetime.datetime.now()
        tdiff = nt-tnow
        if tdiff.seconds < 30:
          stime = (rdt-tdiff).seconds
          print("read took %d sec, now wait %d sec" % (tdiff.seconds, stime))
          time.sleep(stime)
        else:
          print("read took %d sec, no waiting" % (tdiff.seconds))
        tnow = datetime.datetime.now()
