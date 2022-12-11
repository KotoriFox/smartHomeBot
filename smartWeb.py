def multiline2Table(s):
  s = s.split('\n')
  res = "<table><tr><td>"
  x = '</td></tr><tr><td>'.join(s)
  res += x + "</tr></td></table>"
  return res

def img(nameli):
  res = ""
  for i in nameli:
    res += f'<img src="{i}" alt="{i}"><br>'
  return res

def show(h):
     x = h.coll.getData()
     try:
          import smartSolar
          import importlib
          importlib.reload(smartSolar)
          pw = smartSolar.getPwNow(h.r.i2c)
          s  = "On  temp = " + str(h._conf["onoff"][0]) + "(" + str(h.ronoff[0]) + ")\n"
          s += "Off temp = " + str(h._conf["onoff"][1]) + "(" + str(h.ronoff[1]) + ")\n"
          s += "Current temp   = " + str(h.temp[h.heaterKey]) + "\n"
          s += "Current status = " + str(h.r.status('sw1')) + "\n"
          s += "Tank temp  = " + str(h.temp[h.tankKey]) + "\n"
          s += "Tank max   = " + str(h._conf["tmax"]) + '\n'
          s += "On battery = " + str(h.r.isReserve()) + "\n"
          s += "Tank Heating = " + str(pw) + " W\n"
          x = smartSolar.convert(x)
          res = ""
          for i in x:
              res += i + " = " + str(x[i]) + "\n"          
     except:
          s = full_stack()
          print(s)
          for i in s.split('\n'):
            self.log.error(i)
          res = s
     solarData = multiline2Table(res)
     getData = multiline2Table(s)
     h1,s = h.getTemp()
     tempData = multiline2Table('\n'.join(s))
     h.plotName(["в_Південь", "в_Земля", "в_Північ", "в_ПідБудинком"], "static/lane4")
     h.plotName(["Ванна", "Кабінет", "Вітальня"], "static/lane1")
     h.plotName(["Тамбур", "Коридор"], "static/lane2")
     h.plotName(["Паливна", "_Бак", "ТрубаВерх"], "static/lane3")
     tempGraph = img(["static/lane1.png","static/lane2.png","static/lane3.png","static/lane4.png"])
     h.plotName(["Сонце"], "static/solar")
     h.plotName(["Споживання"], "static/usage")
     solGraph = img(["static/solar.png", "static/usage.png"])     
     return f"<!DOCTYPE html> <html> <body> {getData} {solarData} {solGraph} {tempData} {tempGraph} </body></html>"


