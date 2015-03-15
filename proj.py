from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
import calendar, datetime
import sys
import urllib2
import re
from twisted.python import log

HOST = "YOUR HOST HERE"

API_KEY = "YOUR KEY HERE"

PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?&location=%s&radius=%s&key=%s"

SERVER_CONNECTIONS = {'Alford':['Parker','Powell'], 'Bolden':['Parker', 'Powell'], 'Hamilton':['Parker'], 'Parker':['Alford', 'Bolden', 'Hamilton'], 'Powell':['Alford', 'Bolden']}

SERVER_PORTS = {'Alford':12010, 'Bolden':12011, 'Hamilton':12012, 'Parker':12013, 'Powell':12014}

size_IAMAT = 4
size_WHATSAT = 4
size_AT = 6


class Chat(LineReceiver):

    def __init__(self, users, server):
        self.users = users
        self.server = server

    def connectionMade(self):
        log.msg("Connected to %s" % self.server)

    def connectionLost(self, reason):
        pass

    def lineReceived(self, line):
        log.msg("Received: " + line)
        args = line.split()
        if (len(args) == size_IAMAT and args[0] == "IAMAT"):
            self.handle_IAMAT(args, line)
        elif (len(args)==size_WHATSAT and args[0] == "WHATSAT"):
            self.handle_WHATSAT(args, line)
        elif  (len(args)==size_AT and args[0] == "AT"):
            self.handle_AT(args, line)
        else:
            self.handle_unknown(line)
    

    def handle_IAMAT(self, args, line):
        d = datetime.datetime.utcnow()
        #compute the time elapsed between when the message says it was sent
        #and when it was recieved. Does not account for clock skew
        timediff = calendar.timegm(d.timetuple())-float(args[3])
        resp = "AT %s " % (self.server)
        if timediff > 0:
            resp += "+" 
        resp += "%f" % (timediff)
        for i in range(1, len(args)):
            resp += " " + args[i] #append the IAMAT command's arguments
        self.sendLine(resp)
        self.handle_AT(resp.split(),resp)

    def handle_WHATSAT(self, args, line):

        def format(data, num):
            startstr = '"results" : [\n      '
            endstr = '   ],\n   "status" :'
            resultsstr = '{\n         "geometry" :'
            start = data.split(startstr)
            pref = start[0] + startstr
            self.sendLine(start[1] + "\n\n")
            end = start[1].split(endstr)
            suf = endstr + end[1]
            results = end[0].split(resultsstr)
            ret = pref
            maxlen = num+1
            if maxlen > len(results):
                maxlen = len(results)
            for i in range(1, maxlen):
                ret += resultsstr
                ret += results[i]
            ret += suf
            return ret

        if args[1] in self.users and int(args[2]) <= 50 and int(args[3]) <= 20:
            unformattedloc = self.users[args[1]].split()[4]
            #adds a ',' between the latitude and longitude
            absvals = re.split("[+-]", unformattedloc)
            location = unformattedloc[0] + absvals[1] + "," + unformattedloc[len(absvals[1])+1] + absvals[2]
            json = urllib2.urlopen(PLACES_URL % (location,args[2],API_KEY)).read()
            self.sendLine(self.users[args[1]] + "\n" + format(json, int(args[3])))
        else:
            self.handle_unknown(line)

    def handle_AT(self, args, line):
        name = args[3]
        #if user not recoreded or newer timestamp than last IAMAT
        if ((not (name in self.users)) or (float(args[5]) > float(self.users[name].split()[5]))):
            #for each server it connects to
            connections = SERVER_CONNECTIONS[self.server]
            for i in range (0, len(connections)):
                log.msg("Forwarding AT to " + connections[i])
                reactor.connectTCP(HOST,SERVER_PORTS[connections[i]], TCPFactory(line))
            self.users[name] = line

    def handle_unknown(self, line):
        self.sendLine("? " + line)
        log.msg("unknown command")

    def places(self, result, limit):
        self.sendLine(self.users[args[1]] + result)

class ChatFactory(Factory):

    def __init__(self, server):
        self.users = {} # maps user names to Chat instances
        self.server = server #server id

    def buildProtocol(self, addr):
        return Chat(self.users, self.server)

    def startedConnecting(self, transport):
        pass

    def clientConnectionLost(self, transport, reason):
        pass

    def clientConnectionFailed(self, transport, reason):
        pass

    def doStart(self):
        log.startLogging(open('%s.log' % (self.server), 'a'), setStdout=False)

    def doStop(self):
        pass

#used for inter-server communication
class TCPFactory(Factory):

    def __init__(self, message):
        self.message = message

    def buildProtocol(self, addr):
        return TCPCon(self.message)

    def startedConnecting(self, transport):
        pass

    def clientConnectionLost(self, transport, reason):
        pass

    def clientConnectionFailed(self, transport, reason):
        pass

    def doStart(self):
        pass

    def doStop(self):
        pass

class TCPCon(LineReceiver):

    def __init__(self, message):
        self.message = message

    def connectionMade(self):
        self.sendLine(self.message)
        log.msg("Connection made")
        log.msg("Connection dropped")
        self.transport.loseConnection()

    def lineReceived(self, line):
         pass

#start all the servers
for i in SERVER_PORTS:
    reactor.listenTCP(SERVER_PORTS[i], ChatFactory(i))
reactor.run()
