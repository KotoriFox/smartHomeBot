
def insideDelta(h):
    t = 0
    t += h.temp['011933991f9a']*4
    t += h.temp['3c01b556fe32']*2
    t += h.temp['3c01a8162fb0']
    t += h.temp['3c01a816bf53']*3
    t += h.temp['011933a43229']*7
    t /= (4+2+1+3+7) # avg inside
    req = h._conf["onoff"][0]-4
    return req-t
def outsideDelta(h):
    north = h.temp['01193ce058f1']
    south = h.temp['01193ce99459']
    under = h.temp['01193cd5001d']
    temp = (north*1.5+south*1.2+under*0.3)/3
    #default on 10C outside +1 every -10 outside
    delta = 11.27-temp/6-(1300*((temp+717)**(2/3))+(temp*2/3+20)**3)/12100
    #delta = (10-temp)*2/10
    on = h._conf["onoff"][0]+delta
    off= h._conf["onoff"][1]+delta
    h.log.info("outside delta %f" % delta)
    return on,off
def heatLogic(h):
   on,off = outsideDelta(h)
   x = insideDelta(h)
   h.log.info("delta inside %f" % x)
   temp = h.temp[h.heaterKey]
   x = x*2
   on += x
   off += x
   h.ronoff = [on,off]
   h.log.info("on %f off %f" %(on,off))
   if (h.r.isReserve()):
       h.log.info("on reserve off heating")
       print("on reserve off heating")
       h.r.off('sw1')
       h.r.off('sw2')
       return
   if h.temp['01193ce99459'] < 15: #TODO: tune this
       h.r.on('sw2')
   else:
       h.r.off('sw2')
   if (temp > off):
       h.log.info("off heating")
       print("off heating")
       h.r.off('sw1')
       return
   if temp < on:
       h.log.info("on heating")
       print("on heating")
       h.r.on('sw1')
