TEHs=[6,4,5,3,2] #1kw, 1kw, 1.5kw, 1.5kw, 1.5kw
TEH_pw=[1000,1000,1500,1500,1500]
cur2pw = [0,1000,1500,2000,2500,3000,3500,4000,4500,5000,5500]
pw2cur = {0:0,1000:1,1500:2,2000:3,2500:4,3000:5,3500:6,4000:7,4500:8,5000:9,5500:10}
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
         5000 : [0,0,0,0,1],
         5500 : [1,0,0,0,0]}
minBuy=40
pwMaxCharge = 5000
maxLoad = 6500
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
   func = lambda x: (40.0/(x+20)-4.0/3)*1.5
   delta = bVmax - bV
   if delta > 1:
     return pwMaxCharge
   key = 10-delta*10
   r = func(key)
   r = (pwMaxCharge+1000)*r
   if r > pwMaxCharge:
     return pwMaxCharge
   return r

# decrease pwCur by ndiff
def minusCalc(pwCur, ndiff):
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

# pwCur is what we have, -diff is what we need to add
def plusCalc(pwCur, pLoad, pBuy, pwMax, diff, full):
   global maxLoad
   if pBuy > 200:
      return minusCalc(pwCur,pBuy)
   if pLoad >= maxLoad:
      ndiff = pLoad-maxLoad
      return minusCalc(pwCur,ndiff)
   nonOurLoad = pLoad - pwCur
   normalize = lambda x : int(x/500)*500
   ofRoom = normalize(pwMax-800-pLoad)
   toAdd = min(normalize(-diff),ofRoom)
   cur = pw2cur[pwCur]
   sss = f"diff {diff} pw {pwCur}, room {ofRoom}, toAdd {toAdd}"
   if (full) and (pwCur < 5500):
     cur+=1
     pwCur = cur2pw[cur]
     toAdd = 0
   while toAdd>0:
     cur+=1
     pnew = cur2pw[cur]
     d = pnew-pwCur
     toAdd-=d
     if toAdd < 0:
       #cannot add
       print(f"{sss}, new {pwCur}")
       break
       return pwCur
     pwCur = pnew
     if pwCur >= 5500:
       print(f"{sss}, new 5500")
       pwCur=5500
       break
   print(f"{sss}, new {pwCur}")
   delta = nonOurLoad + pwCur - maxLoad
   if delta > 0:
      print("Overflow, recalc")
      return minusCalc(pwCur, delta)
   return pwCur

# return - heating power in W
def calcHeat(pwCur, pwMax, bV, bVmax, pBuy, pBatt, pLoad, tCur, tMax, grid):
   import datetime
   global pwMaxCharge
   hnow = datetime.datetime.now().hour
   if tCur>= tMax:
      print("return 1")
      return 0
   bres = reservCalc(bV, bVmax)
   #calc minus
   ndiff = bres+pBatt
   if (ndiff >=0)and(abs(pBatt)>500):
      print(f"{bres}+{pBatt} >= 0")
      return minusCalc(pwCur,ndiff)
   #plus calc
   if (pBatt > 400) and (hnow >= 17):
      print("return 3")
      return 0
   plu = plusCalc(pwCur, pLoad, pBuy, pwMax, ndiff, abs(ndiff) < 1000)
   return plu
   battPercent = 500*bV/bVmax-400
   print(f"battPercent = {battPercent}")
   if battPercent > 90:
      print("return 4")
      return plu
   #if not 90% - check not to disturb charging
   print(f"{pBatt} + {plu} - {pwCur} > {-bres}")
   if (pBatt+plu-pwCur) > (-bres):
      print("return 5")
      return pwCur
   return plu

#===============================================
def stopHeat(h):
   applypw(h.r.i2c, 0, h)
def heatLogic(h):
   import datetime
   try:
     lhp = h._lastHeat
   except:
     h._lastHeat = 0
     lhp = 0
   historyPow = h.historyPow
   tb = h.temp['01193cb260aa']
   oldPw = getPwNow(h.r.i2c)
   currr = oldPw
   cur = pw2cur[oldPw]
   d = h.coll.getData()
   grid = d["Grid-connected Status"] == "On-Grid"
   soc = d["Battery SOC"]
   batV = d["Battery Voltage"]
   buy = d["Total Grid Power"]
   solar = d["PV1 Power"]+d["PV2 Power"]+d["PV3 Power"]+d["PV4 Power"]
   batt = d["Battery Current"] * d["Battery Voltage"]
   batV2 = batV
   batV = batV + batt/10000 #offset to get +- real voltage
   print(f"{batV2} => {batV}")
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
   p = calcHeat(oldPw, 9000, batV, 57.2, buy, batt, load, tb, h._conf["tmax"], grid)
   h.log.info(f"{historyPow}, {xxxx}")
   if (hnow>=17)and(p == 1000)and(lastSol<400)and(wasOn):
     p = 0
   t2t = h.temp[h.tank2Key]
   buy -= lhp
   if (p == 0) and (t2t < 32) and grid:
       if buy < 5000:
         p+=1000
         buy+=1000
       if buy < 5000:
         p+=1000
         buy+=1000
       if buy < 5000:
         p+=1500
   applypw(h.r.i2c, p, h)
   h.historyPow = historyPow[1:]
   h.historyPow.append(p)
   h.log.info("Set pw %d" % p)
   h._lastHeat = p

def convert(x):
   keys = {"Update Time" : lambda x: x["ts"],
           "Area 1 V" : lambda x: round(x["PV1 Voltage"],2),
           "Area 2 V" : lambda x: round(x["PV2 Voltage"],2),
           "Area 3 V" : lambda x: round(x["PV3 Voltage"],2),
           "Area 4 V" : lambda x: round(x["PV4 Voltage"],2),
           "Solar Power W" : lambda x: round(x["PV1 Power"]+x["PV2 Power"]+x["PV3 Power"]+x["PV4 Power"],2),
           "Buying W" : lambda x: round(x["Total Grid Power"],2),
           "Battery V" : lambda x: round(x["Battery Voltage"],2),
           "BatteryReal V" : lambda x: round(x["Battery Voltage"]+x["Battery Voltage"]*x["Battery Current"]/10000,2),
           "Battery Charge W" : lambda x: round((-1)*x["Battery Voltage"]*x["Battery Current"],2),
           "Battery SOC" : lambda x : x["Battery SOC"],
           "Home Usage W" : lambda x: round(x["Total Load Power"],2),
           "CT W" : lambda x: str(x["Internal CT L1 Power"])+"/"+str(x["External CT L1 Power"]),
           "Temp Battery" : lambda x: x["Battery Temperature"],
           "Temp DC" : lambda x: x["DC Temperature"],
           "Temp AC" : lambda x: x["AC Temperature"],
           "Daily Energy Bought" : lambda x: round(x["Daily Energy Bought"],2),
           "Daily Load Consumption" : lambda x: round(x["Daily Load Consumption"],2),
           "Daily Production" : lambda x: round(x["Daily Production"],2),
           "Total Battery Discharge" : lambda x: round(x["Total Battery Discharge"],2),
          }
   res = {}
   for i in keys:
     res[i] = keys[i](x)
   return res
