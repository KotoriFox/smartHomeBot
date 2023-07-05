TEHs=[6,4,5,3,2] #1kw, 1kw, 1.5kw, 1.5kw, 1.5kw
TEH_pw=[1000,1000,1500,1500,1500]
cur2pw = [0,1000,1500,2000,2500,3000,3500,4000,4500,5500]
pw2cur = {0:0,1000:1,1500:2,2000:3,2500:4,3000:5,3500:6,4000:7,4500:8,5500:9}
pw2bm = {-1000: [1,1,1,1,1],
            0 : [1,1,1,1,1],
         1000 : [0,1,1,1,1],
         1500 : [1,1,0,1,1],
         2000 : [0,0,1,1,1],
         2500 : [0,1,0,1,1],
         3000 : [1,1,0,0,1],
         3500 : [0,0,0,1,1],
         4000 : [0,1,0,0,1],
         4500 : [1,1,0,0,0],
         5500 : [0,0,0,0,1]}
minBuy=40
pwMaxCharge = 6000
def applypw(i2c, pw, h):
   import datetime
   hnow = datetime.datetime.now().hour
   tb = h.temp['01193cb260aa']
   south = h.temp['01193ce99459']
   #under = h.temp['01193cbde6d6']
   buyTemp = minBuy
   #if (south < 2):
   #   h.log.info(f"temp {south} < 10, more buy heating")
   #   buyTemp += 10
   bm = pw2bm[pw]
   #if (tb >= buyTemp) or (h.r.isReserve()) or (pw > 0) or (hnow < 19):
   #   h.log.info("%u >= %u or on reserve or solar, 5kW off" % (tb, buyTemp))
   #else:
   #  h.log.info("%u < %u, 5kW on" % (tb, buyTemp))
   for i in zip(TEHs, bm):
     if i2c.relayGet(i[0]) != i[1]:
       i2c.relaySet(i[0],i[1])
   t2 = h.temp[h.tank2Key]
   t1 = h.temp[h.tankKey]
   h.log.info(f"NewTank {t2}, Tank {t1}")
   if (pw == 0) and (t2-t1 <= 4):
     h.r.off('sw3')
     #h.r.off('sw4')
   else:
     h.r.on('sw3')
     #h.r.on('sw4')
def bm2pw(st):
   st = [not i for i in st]
   return sum([i[0]*i[1] for i in zip(st,TEH_pw)])
def getPwSt(i2c):
   st = []
   for i in TEHs:
     if i2c.relayGet(i):
        st.append(1)
     else:
        st.append(0)
   return st
def getPwStr(i2c):
   st = getPwSt(i2c)
   return str(bm2pw(st))
def getPwNow(i2c):
   st = getPwSt(i2c)
   return bm2pw(st)

def reservCalc(bV, bVmax):
   global pwMaxCharge
   x = 500*bV/bVmax-400
   bRes = pwMaxCharge
   if x > 80:
      d = x-80
      bRes -= pwMaxCharge*(pow(d+3,3)/20)/100
   if bRes<-1000:
      return -700
   return bRes

# decrease pwCur by ndiff
def minusCalc(pwCur, grid, ndiff):
   cur = pw2cur[pwCur]
   if ndiff >= pwCur:
      return 0
   while ndiff>0:
      if cur==0:
         return 0
      m = cur2pw[cur]-cur2pw[cur-1]
      pwCur -= m
      ndiff -= m
      cur -=1
   return pwCur

# add pwCur by one step
def plusCalc(pwCur, grid, pLoad, pBuy, pwMax):
   if pwCur > 4000:
      return pwCur
   if pBuy > 200:
      return minusCalc(pwCur, grid, pBuy)
   cur = pw2cur[pwCur]
   npow = cur2pw[cur+1]
   if pLoad+npow-pwCur > pwMax-800:
      print(f"overflow {pLoad}+{npow}-{pwCur} > {pwMax}-1300")
      return pwCur # overflow if add
   return npow

# return - heating power in W
def calcHeat(pwCur, pwMax, bV, bVmax, pBuy, pBatt, pLoad, tCur, tMax, grid):
   import datetime
   global pwMaxCharge
   hnow = datetime.datetime.now().hour
   if tCur>= tMax:
      return 0
   bres = reservCalc(bV, bVmax)
   #calc minus
   ndiff = bres+pBatt
   if ndiff >=0:
      return minusCalc(pwCur, grid, ndiff)
   #plus calc
   if (pBatt > 400) and (hnow >= 17):
      return 0
   plu = plusCalc(pwCur, grid, pLoad, pBuy, pwMax)
   print(f"{pBatt} + {plu} - {pwCur} > {-bres}")
   if (pBatt+plu-pwCur) > (-bres):
     return pwCur
   return plu

#===============================================
def stopHeat(h):
   applypw(h.r.i2c, 0, h)
def heatLogic(h):
   import datetime
   historyPow = h.historyPow
   tb = h.temp['01193cb260aa']
   oldPw = getPwNow(h.r.i2c)
   currr = oldPw
   cur = pw2cur[oldPw]
   d = h.coll.getData()
   soc = d["Battery SOC"]
   batV = d["Battery Voltage"]
   buy = d["Total Grid Power"]
   solar = d["PV1 Power"]+d["PV2 Power"]+d["PV3 Power"]+d["PV4 Power"]
   batt = d["Battery Current"] * d["Battery Voltage"]
   load = d["Total Load Power"]
   xxxx = h.history["Сонце"][1][-3:]
   lastSol = xxxx
   lastSol = [abs(i-solar) for i in lastSol]
   lastSol = sum(lastSol)/len(lastSol)
   wasOn = sum(h.historyPow) != 0
   hnow = datetime.datetime.now().hour
   h.add2Hist("Акум", d["Battery Voltage"]/14)
   h.add2Hist("Розряд", d["Total Battery Discharge"])
   h.log.info(f'{hnow}:: {lastSol} : cur {cur}({oldPw}) buy {buy} solar {solar} batt {batt} {batV} soc {soc} temp {tb}')
   grid = d["Grid-connected Status"] != "Off-Grid"
   p = calcHeat(oldPw, 5000, batV, 58, buy, batt, load, tb, h._conf["tmax"], grid)
   h.log.info(f"{historyPow}, {xxxx}")
   if (hnow>=17)and(p == 1000)and(lastSol<400)and(wasOn):
     p = 0
   applypw(h.r.i2c, p, h)
   h.historyPow = historyPow[1:]
   h.historyPow.append(p)
   h.log.info("Set pw %d" % p)

def convert(x):
   keys = {"Update Time" : lambda x: x["ts"],
           "Area 1 V" : lambda x: x["PV1 Voltage"],
           "Area 2 V" : lambda x: x["PV2 Voltage"],
           "Area 3 V" : lambda x: x["PV3 Voltage"],
           "Area 4 V" : lambda x: x["PV4 Voltage"],
           "Solar Power W" : lambda x: x["PV1 Power"]+x["PV2 Power"]+x["PV3 Power"]+x["PV4 Power"],
           "Buying W" : lambda x: x["Total Grid Power"],
           "Battery V" : lambda x: x["Battery Voltage"],
           "Battery Charge W" : lambda x: (-1)*x["Battery Voltage"]*x["Battery Current"],
           "Battery SOC" : lambda x : x["Battery SOC"],
           "Home Usage W" : lambda x: x["Total Load Power"],
           "CT W" : lambda x: str(x["Internal CT L1 Power"])+"/"+str(x["External CT L1 Power"]),
           "Temp Battery" : lambda x: x["Battery Temperature"],
           "Temp DC" : lambda x: x["DC Temperature"],
           "Temp AC" : lambda x: x["AC Temperature"],
           "Daily Energy Bought" : lambda x: x["Daily Energy Bought"],
           "Daily Load Consumption" : lambda x: x["Daily Load Consumption"],
           "Daily Production" : lambda x: x["Daily Production"],
           "Total Battery Discharge" : lambda x: x["Total Battery Discharge"],
          }
   res = {}
   for i in keys:
     res[i] = keys[i](x)
   return res
