import sys
import random
# from itertools import cycle
import threading
from server import *
import time
import random
import os
import subprocess
import xmlrpc.server as SimpleThreadedXMLRPCServer

NUM_SERVERS = int(sys.argv[3])
RPC_PORT = int(sys.argv[4])

# dumb netcat server, short tcp connection
# $ ~  while true ; do nc -l 8888 < server1.html; done
# $ ~  while true ; do nc -l 9999 < server2.html; done

# dumb python socket echo server, long tcp connection
# $ ~  while  python server.py
# SERVER_POOL = [('localhost', 6666)]

# ITER = cycle(SERVER_POOL)
# def round_robin(iter):
# round_robin([A, B, C, D]) --> A B C D A B C D A B C D ...
# return next(iter)

# class Server(object):
#     def __init__(self, IP, PORT):
#         self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         self.server_socket.bind((IP, PORT))

#         self.sockets_list = [self.server_socket]


#     def addClient(self, client_socket):
#         self.client_sockets_list.append(client_socket)
roundRobin = 0
algorithm = ""

pid_serverId = dict()
"""
dictionary mapping process id to server id
"""  # pylint: disable=W0105

serverId_pid = dict()
"""
dictionary mapping server id to process id
"""  # pylint: disable=W0105


def assignPid():
    """Initialize the dicts pid_serverId and serverId_pid, so that we can easily find process id from server id and vice versa

    """
    for i in range(1, 4):
        # change localhost in below command to ip address
        cmd = ''' ps aux | grep "server.py localhost ''' + \
            f'''{(PORT + i*100)}''' + '''" | head -1 | awk '{print $2}' '''
        id = subprocess.check_output(
            cmd, shell=True, universal_newlines=True).strip()
        pid_serverId[id] = i-1
        serverId_pid[i-1] = id


def strategy(algorithm):
    """Return a server based on the load balancing algorithm requested

    :param [algorithm]: 'round-robin'/'random'/'memory'/'cpu'
    :type [algorithm]: str
    :return: index of the server and corresponding port
    :rtype: int,int
    """
    global roundRobin
    if (algorithm == 'round-robin'):
        a, b = roundRobin, (PORT + (roundRobin)*100)
        roundRobin = (roundRobin+1) % 3
        print(algorithm + ' Chose server indexed at ' + str(a))
        return a, b
    elif (algorithm == 'random'):
        a = random.randint(0, 2)
        print(algorithm + ' Chose server indexed at ' + str(a))
        return a, PORT + a*100
    elif (algorithm == 'memory'):
        mem = float('inf')
        a = -1
        for id in range(3):
            cmd = ''' ps aux | grep "server.py localhost ''' + \
                f'''{(PORT + (id+1)*100)}''' + \
                '''" | head -1 | awk '{print $4}' '''
            kb = subprocess.check_output(
                cmd, shell=True, universal_newlines=True).strip()
            print(kb)
            currmem = float(kb.replace('K', ''))
            if (mem > currmem):
                mem = currmem
                a = id
            # print (id, currmem)
        print(algorithm + ' Chose server indexed at ' + str(a))
        return a, PORT + a*100
    elif (algorithm == 'cpu'):
        cpu = float('inf')
        a = -1
        for id in range(3):
            # change localhost in below command to ip address
            cmd = ''' ps aux | grep "server.py localhost ''' + \
                f'''{(PORT + (id+1)*100)}''' + \
                '''" | head -1 | awk '{print $3}' '''
            kb = subprocess.check_output(
                cmd, shell=True, universal_newlines=True).strip()
            currcpu = float(kb)
            if (cpu > currcpu):
                cpu = currcpu
                a = id
            # print (id, currcpu)
        print(algorithm + ' Chose server indexed at ' + str(a))
        return a, PORT + a*100


def getFreeServerId():
    """Return the free-est server

    :return: index of the server and corresponding port
    :rtype: int,int
    """
    return strategy(algorithm)


def runServer(IP, PORT):
    """Run a new server process

    :param [IP]: IP address of network
    :type [IP]: str
    :param [PORT]: PORT that the server is to be run on
    :type [PORT]: int
    """
    global r
    os.system(f'python3 server.py {IP} {PORT}')


class LoadBalancer(object):
    """Socket implementation of a load balancer.

    Flow Diagram:
    +---------------+      +-----------------------------------------+      +---------------+
    | client socket | <==> | client-side socket | server-side socket | <==> | server socket |
    |   <client>    |      |          < load balancer >              |      |    <server>   |
    +---------------+      +-----------------------------------------+      +---------------+
    """

    def __init__(self, ip, PORT, algorithm='random'):
        """Constructor

        :param [ip]: message string
        :type [ip]: str
        :param [PORT]: PORT of load balancer. Servers will have ports PORT+index*100
        :type [PORT]: int
        :param [algorithm]: algorithm to decide free-est server
        :type [algorithm]: str
        """
        self.ip = ip
        self.port = PORT
        self.algorithm = algorithm
        self.numservers = NUM_SERVERS

    def startServers(self):
        """Start each server on a separate thread

        """
        for i in range(1, self.numservers + 1):
            serverTh = threading.Thread(
                target=runServer, args=(self.ip, (self.port + 10*i)))
            serverTh.start()
            print("STARTED...")


class ServerThread(threading.Thread):

    def __init__(self, IP):
        """Constructor

        :param [IP]: IP on which to run the server
        :type [IP]: str
        """
        threading.Thread.__init__(self)
        self.server = SimpleThreadedXMLRPCServer.SimpleXMLRPCServer(
            (IP, RPC_PORT), logRequests=False, allow_none=True)
        self.server.register_function(
            isValidPassword)  # just return a string
        self.server.register_function(addNewUser)
        self.server.register_function(checkUserName)
        self.server.register_function(getPublicKey)
        self.server.register_function(createGroupAtServer)
        self.server.register_function(addUserToGroup)
        self.server.register_function(removeUserFromGroup)
        self.server.register_function(getFreeServerId)

    def run(self):
        """Serve Forever
        """
        self.server.serve_forever()


IP = sys.argv[1]
PORT = int(sys.argv[2])

if __name__ == '__main__':
    try:
        server = ServerThread(IP)
        server.start()
        print('CREATED XMLRPC SERVER')
        initialize()
        print('Initialized the postgreSQL database')

        loadBal = LoadBalancer(f'{IP}', PORT, 'memory')
        algorithm = loadBal.algorithm
        print(colored("Starting Load Balancer....", 'yellow'))
        assignPid()
        print('PIDs of server processes:')
        print(serverId_pid)
        # loadBal.startServers()
        time.sleep(1)
    except KeyboardInterrupt:
        print("Ctrl C - Stopping load_balancer")
        sys.exit(1)
