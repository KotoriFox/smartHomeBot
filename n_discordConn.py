import n_restClient
import discord
import asyncio
import threading

def getReserveText():
    replies = {0: "Working on grid\n",
                     1: "No grid on heatpump\n",
                     2: "Bad grid on main, running on battery\n",
                     3: "No grid, running on battery\n"}
    i = n_restClient.restGetVar("inner_reserve")
    o = n_restClient.restGetVar("outer_reserve")
    key = o << 1 + i #key in range 0..3
    return replies[key]

class temps():
    def __init__(self,  cli):
        self.client = cli
        self.cmd = "temp"
    async def execute(self, msg):
        te = n_restClient.getTemp()
        res = ""
        for i in te:
            res += str(i) + " : " + str(te[i][0]) + " C"
            if te[i][1]:
                res += " / "+str(te[i][1]) + "%"
            res += "\n"
        await msg.channel.send(f'```\n{res}```')

class tempGraph():
    def plot(self, li):
        name = "displot.png"
        n_restClient.restPlot(name, li)
        return name
    def __init__(self, cli):
        self.client = cli
        self.cmd = "graph"
    async def execute(self, msg):
        from os.path import exists
        x = msg.content
        x = x.split()
        if len(x) == 0:
            await msg.channel.send("Specify names to be included into graph, max 10")
            return
        s = self.plot(x)
        if exists(s):
            with open(s,'rb') as f:
                ff = discord.File(f)
                await msg.channel.send(s, file=ff)

class getHeat():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "get"
    def printVar(self,  name):
        x = n_restClient.restGetVar(name)
        return f"{name} = {x}\n"
    async def execute(self, msg):
        onoff = n_restClient.restGetVar("onoff")
        realonoff  = n_restClient.restGetVar("realonoff")
        s   = f"On  temp = {onoff[0]} ({realonoff[0]})\n"
        s += f"Off  temp = {onoff[1]} ({realonoff[1]})\n"
        x = n_restClient.restGetTemps()
        key = "_ТеплаПідлога"
        if key in x:
            s += f"Current temp   = {x[key][0]}\n"
        s+= self.printVar("sw1_giver")
        s+= self.printVar("sw2_radiant")
        s+= self.printVar("sw3_syncer")
        s+= self.printVar("sw4_cooler")
        key = "_Бак"
        if key in x:
            s += f"Tank temp  = {x[key][0]}"
        key = "NewTank"
        if key in x:
            s += f"/{x[key][0]}"
        s+="\n"
        tmax = n_restClient.restGetVar("tmax")
        s += f"Tank max   = {tmax}\n"
        s += getReserveText()+ "\n"
        await msg.channel.send(s)


class setHeat():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "set"
    async def execute(self, msg):
        x = msg.content
        try:
          x = x.split()
          on = int(x[0])
          off = int(x[1])
          tmax = int(x[2])
        except:
          await msg.channel.send("Specify on temp and off temp like 'set 20 24'")
          return
        onoff = str([on, off])
        n_restClient.restSetVar("onoff", onoff)
        n_restClient.restSetVar("tmax", tmax)
        await msg.channel.send("On set to %d and off set to %d, Tank max temp set to %d" % (on, off, tmax))

class poolHeat():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "pool"
    async def execute(self, msg):
        x = msg.content
        try:
            opt = int(x!='0')
            n_restClient.restSetVar("fsw1_pool", opt)
            await msg.channel.send("Changed forced sw1 state to %d" % opt)
        except:
            await msg.channel.send("'pool 1' to ON, 'cool 0' to OFF")

class cooler():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "cool"
    async def execute(self, msg):
        x = msg.content
        try:
            opt = int(x!='0')
            n_restClient.restSetVar("sw4_cooler", opt)
            await msg.channel.send("Changed state to %d" % opt)
        except:
            await msg.channel.send("'cool 1' to ON, 'cool 0' to OFF")

class solarGet():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "sol"
    async def execute(self, msg):
        x = n_restClient.restGetInv()
        x = n_restClient.solarConvert(x)
        res = "```\n"
        for i in x:
              res += i + " = " + str(x[i]) + "\n"
        await msg.channel.send(res+"```")

class NotifyMe():
    def __init__(self,cli):
        self.client = cli
        self.cmd = "noti"
    async def execute(self, msg):
        cha = msg.channel.id
        noti = n_restClient.restGetVar("discord")
        if cha in noti:
            noti.remove(cha)
            n_restClient.restSetVar("discord", str(noti))
            await msg.channel.send("Removed notifications here")
        else:
            noti.append(cha)
            n_restClient.restSetVar("discord", str(noti))
            await msg.channel.send("Added notifications here")
            nv = getReserveText()
            await msg.channel.send(nv)


class smarty:
    def  __init__(self):
        self.curStatus = ""
        self.ready = 0
        self.client = discord.Client()
        self.client.event(self.on_ready)
        self.client.event(self.on_message)
        self.parts = []
        self.ready = 1
    async def notify(self):
        noti = n_restClient.restGetVar("discord")
        nv = getReserveText()
        if nv != self.curStatus:
            self.curStatus = nv
            for i in noti:
                cha = self.client.get_channel(i)
                await cha.send(nv)
    def run(self):
         with open('token.data', 'r') as f:
            x = f.read()
            self.client.run(x)
    def isAdmin(self, msg):
        #if msg.author.id == 215548836419076106 return True
        return isinstance(msg.channel, discord.abc.GuildChannel) and msg.channel.permissions_for(msg.author).manage_guild
    async def on_ready(self):
        print('Logged in as')
        print(self.client.user.name)
        print(self.client.user.id)
        print("Servers: ", [i.name for i in self.client.guilds])
        print('------')
        g = discord.Game("!!help")
        await self.client.change_presence(activity=g)
        self.parts.append(temps(self.client, self.h))
        self.parts.append(tempGraph(self.client, self.h))
        self.parts.append(getHeat(self.client, self.h))
        self.parts.append(setHeat(self.client, self.h))
        self.parts.append(cooler(self.client, self.h))
        self.parts.append(poolHeat(self.client, self.h))
        self.parts.append(solarGet(self.client, self.h))
        self.parts.append(NotifyMe(self.client, self.h))
        #more parts add here
    async def on_message(self, message):
        if message.type != discord.MessageType.default:
            return
        if not message.content.startswith("!!"):
            return
        message.content = message.content[2:].strip()
        if message.content == "help":
            lst = []
            for i in self.parts:
                lst.append(i.cmd)
            await message.channel.send("Available commands:\n"+'\n'.join(lst))
            return
        for i in self.parts:
            if message.content.startswith(i.cmd):
                message.content = message.content[len(i.cmd):].strip()
                await i.execute(message)
                return
        await message.channel.send("Command not found")


from discord.ext import tasks

bot = smarty()

@tasks.loop(seconds=30.0)
async def notifyAll():
    #print("   Loop noti")
    await bot.notify()
@notifyAll.before_loop
async def before():
    print("   Loop noti wait")
    await bot.client.wait_until_ready()

notifyAll.start()
bot.run()
