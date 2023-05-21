# "" are used to make table names case insensitive
#################################
# IMPLEMENT TRY-EXCEPT BLOCKS !!!
# for deletions of socket
# keyboard interruptions
# FOR IMAGES the dictinary received will have imageData as encrypted and not message
# Exception being raised on second time login , i.e if first incorrect and second correct then
#################################

import socket
import select
import json
import sys

from json.decoder import JSONDecodeError

import threading
import psycopg2
from termcolor import colored

HEADER_LENGTH = 10

def connectToDb():
    serverDbName = "fastchat"
    """Connect to the appropriate PostgreSQL account and set autocommit to true.

    :return: cursor to the server database
    :rtype: _Cursor
    """
    conn = psycopg2.connect(database=f"{serverDbName}", user="postgres",
                            password="fastchat", host=IP, port="5432")
    conn.autocommit = True
    cur = conn.cursor()
    return cur


def getPublicKey(username):
    """
    :param [username]: username whose public key needs to be extracted from database
    :type [username]: str
    :return: parameters n and e of the public key
    :rtype: tuple
    """
    cur = connectToDb()
    query = f'''SELECT publicn, publice FROM userinfo WHERE username='{username}';'''
    cur.execute(query)
    record = cur.fetchall()[0]
    return record
    # return (password == recordPassword)


def isValidPassword(userName, password):
    """Validate password

    :param [userName]: username entered by user. This has already been validated by checkUserName
    :type [userName]: str
    :param [password]: password entered by user
    :type [password]: str
    :return: True if success, False if failure
    :rtype: bool
    """
    cur = connectToDb()
    query = f'''SELECT password = crypt('{password}', password) FROM userinfo WHERE username='{userName}';'''
    cur.execute(query)
    recordPassword = cur.fetchall()
    return recordPassword[0][0]

#######################################
# Make a column isGroup
# OR append GRP: to each name
#######################################


def checkUserName(userName):
    """
    :param [userName]: username entered by user
    :type [userName]: str
    :return: Whether the username is a registered user (True) or not (False)
    :rtype: bool
    """
    cur = connectToDb()
    query = f'''SELECT username FROM userinfo;'''
    cur.execute(query)
    record = cur.fetchall()
    return (f"{userName}",) in record


def addNewUser(userName, password, n, e):
    """Add a new user to the database

    :param [userName]: username entered by user. This has already been validated by checkUserName
    :type [userName]: str
    :param [password]: password entered by user
    :type [password]: str
    :param [n]: parameter n of the public key of new user
    :type [n]: int
    :param [e]: parameter e of the public key of new user
    :type [e]: int
    """
    cur = connectToDb()
    # --------------------------
    # CREATE EXTENSION pgcrypto;
    # --------------------------
    query = f'''INSERT INTO userinfo
                VALUES ('{userName}', crypt('{password}', gen_salt('bf', 8)), {n}, {e}, True);'''
    cur.execute(query)
    cur.execute("SELECT * FROM userinfo")


def unpack_message(client_socket):
    """Receive as many bytes as specified by the header in units of 16 bytes

    :param [client_socket]: the socket that is receiving data
    :type [client_socket]: socket
    :return: Dictionary of the received json data. False if any exception occured
    :rtype: dict/bool
    """
    try:
        userData = ''
        new_message = True
        while True:
            temp = client_socket.recv(16).decode('utf-8')
            if temp == '':
                return False
            if (new_message):
                message_len = int(temp[:HEADER_LENGTH].strip())
                userData += temp[HEADER_LENGTH:]
                new_message = False
                continue

            userData += temp
            # print("USER: ",userData)
            if (message_len == len(userData)):
                userData = json.loads(userData)
                return userData

        # return {'Len':userData['userHeader'], 'Message':message}
    except JSONDecodeError as e:
        # Something went wrong like empty message or client exited abruptly.
        return False

# extracts the scket corresponding to a particular username


def getSocket(username, clients):
    """Extracts the socket corresponding to a particular username

    :param [username]: username in question
    :type [username]: str
    :param [clients]: dictionary mapping sockets to usernames
    :type [clients]: dict
    :return: the socket corresponding to that username
    :rtype: socket
    """
    return list(clients.keys())[list(clients.values()).index(username)]


def createGroupAtServer(grpName, ADMIN):
    """Create a new group by updating the database

    :param [grpName]: name of the new group
    :type [grpName]: str
    :param [ADMIN]: username of the creator
    :type [ADMIN]: str
    :return: the socket corresponding to that username
    :rtype: socket
    """
    cur = connectToDb()
    query = f'''CREATE TABLE "{grpName}"(
                name TEXT);'''
    cur.execute(query)

    # public key = -1 TO identify a group into userinfo table #
    query = f'''INSERT INTO userinfo
                VALUES('{grpName}', '', -1, -1)'''
    cur.execute(query)

    query = f'''INSERT INTO "{grpName}"
                VALUES('{ADMIN}')'''
    cur.execute(query)


def addUserToGroup(grpName, newuser):
    """Add newuser to grpName by an administrator's request

    :param [grpName]: name of the group to which new participant is to be added
    :type [grpName]: str
    :param [newuser]: new member
    :type [newuser]: str
    :return: True if successful, False if failure
    :rtype: bool
    """
    cur = connectToDb()
    query = f'''SELECT name FROM "{grpName}";'''
    cur.execute(query)
    record = cur.fetchall()
    if (not (f"{newuser}",) in record):
        query = f'''INSERT INTO "{grpName}"
                    VALUES('{newuser}');'''
        cur.execute(query)
        return False
    else:
        return True


def removeUserFromGroup(grpName, removeuser):
    """Remove removeuser from grpName by an administrator's request

    :param [grpName]: name of the group from which participant is to be removed
    :type [grpName]: str
    :param [removeuser]: participant to be removed
    :type [removeuser]: str
    :return: True if successful, False if failure
    :rtype: bool
    """
    cur = connectToDb()
    query = f'''SELECT name FROM "{grpName}";'''
    cur.execute(query)
    record = cur.fetchall()
    if (f"{removeuser}",) in record:
        query = f'''DELETE FROM "{grpName}" WHERE name = '{removeuser}';'''
        cur.execute(query)
        return True
    else:
        return False


def getUsersList(grpName):
    """Get a list of all participants

    :param [grpName]: name of the group
    :type [grpName]: str
    :return: list of all participants (each participant is a string)
    :rtype: list
    """
    cur = connectToDb()
    query = f'''SELECT name FROM "{grpName}"'''
    cur.execute(query)
    record = cur.fetchall()
    usersList = [i[0] for i in record]
    return usersList


def initialize():
    """Initialize the postgreSQL database with the database schema

    """
    cur = connectToDb()
    lis = ['pending', 'userinfo']
    for table in lis:
        query = f'''SELECT EXISTS (
                SELECT FROM
                    pg_tables
                WHERE
                    schemaname = 'public' AND
                    tablename  = '{table}'
                )'''
        cur.execute(query)
        response = cur.fetchall()[0][0]
        if (not response):
            if (table == 'userinfo'):
                query = f'''CREATE TABLE userinfo(
                            username TEXT,
                            password TEXT,
                            publicn TEXT,
                            publice TEXT,
                            isOnline BOOLEAN);'''
                cur.execute(query)
            elif (table == 'pending'):
                query = f'''CREATE TABLE pending(
                            SNo INT,
                            sender TEXT,
                            receiver TEXT,
                            grpName TEXT,
                            message TEXT,
                            symmetricKey TEXT,
                            timestamp timestamp NOT NULL DEFAULT NOW());'''
                cur.execute(query)

            query = '''DROP FUNCTION IF EXISTS pending_delete_old_rows() CASCADE;'''
            cur.execute(query)

            query = '''CREATE FUNCTION pending_delete_old_rows() RETURNS trigger
                            LANGUAGE plpgsql
                            AS $$
                        BEGIN
                        DELETE FROM pending WHERE timestamp < NOW() - INTERVAL '7 DAYS';
                        RETURN NEW;
                        END;
                        $$;'''
            cur.execute(query)

            query = '''CREATE TRIGGER pending_delete_old_rows_trigger
                        AFTER INSERT ON pending
                        EXECUTE PROCEDURE pending_delete_old_rows();'''
            cur.execute(query)


def receiveAck(client_socket):
    """Receive an acknowledgement from the client on receipt of a message over socket

    :param [client_socket]: the socket that is sending the ack
    :type [client_socket]: socket
    :return: whether the acknowledgement received is meaningful (True) or not (False)
    :rtype: bool
    """
    data = unpack_message(client_socket)

    # handling exception of keyboard interrupt as in that case unpack message would return
    # false on getting an empty string
    if (not data):
        return False
    elif (data['userMessage'] == "__ACK__"):
        return True

    return False


def sendPendingMessages(client_socket, receiverName):
    """Send pending messages to reveiverName whenever he/she logs in, over client_socket

    :param [client_socket]: the socket that is sending the pending messages
    :type [client_socket]: socket
    :param [receiverName]: username of the reeceiver
    :type [receiverName]: str
    """
    # print("hlhls")
    # receiverName = clients[client_socket]
    cur = connectToDb()
    query = f'''SELECT EXISTS(SELECT * FROM pending WHERE receiver = '{receiverName}');'''
    cur.execute(query)
    record = []

    if (cur.fetchall()[0][0]):
        query = f'''SELECT * FROM pending WHERE receiver = '{receiverName}';'''
        cur.execute(query)
        record = cur.fetchall()

    isImg = False
    isAdd = False
    prevImg = ""
    prevAdd = ""

    for rec in record:
        imgSent = False
        addSent = False

        rec = list(rec)

        if (isImg):

            temp1 = rec[4]
            temp1 = temp1.replace("\'\'", "\'")
            temp1 = temp1.replace("\"\"", "\"")
            rec[4] = temp1

            temp2 = rec[5]
            temp2 = temp2.replace("\'\'", "\'")
            temp2 = temp2.replace("\"\"", "\"")
            rec[5] = temp2

            prevImg['imageFormat'] = rec[1]
            prevImg['imageData'] = rec[4]
            prevImg['fernetKey'] = rec[5]

            jsonData = json.dumps(prevImg)
            print("SENT")
            client_socket.send(
                bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))
            imgSent = True

        elif (isAdd):
            prevAdd['privateKey'] = rec[4]
            jsonData = json.dumps(prevAdd)
            print("SENT")
            client_socket.send(
                bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))
            addSent = True

        isGroup = True
        #######
        print(rec[3], rec[4], '-------------')
        # DON'T ENCRYPT SEND IMAGE , ADD_PARTICIPANT
        if (rec[3] == "" or rec[4] == "ADD_PARTICIPANT"):
            isGroup = False

        if (rec[4] == "ADD_PARTICIPANT"):
            prevAdd = {'messageId': f"{rec[0]}", 'sender': f"{rec[1]}", 'receiver': f"{rec[2]}", 'fernetKey': f"{rec[5]}",
                       'grpName': f"{rec[3]}", 'userMessage': f"{rec[4]}", 'isGroup': isGroup, 'isComplete': False}
            isAdd = True
            continue

        elif (rec[4] == "SEND IMAGE"):
            print(rec[3])
            prevImg = {'messageId': f"{rec[0]}", 'sender': f"{rec[1]}", 'receiver': f"{rec[2]}", 'fernetKey': f"{rec[5]}",
                       'grpName': f"{rec[3]}", 'userMessage': f"{rec[4]}", 'isGroup': isGroup, 'isComplete': False}
            isImg = True
            continue

        elif (not imgSent and not addSent):
            temp1 = rec[4]
            temp1 = temp1.replace("\'\'", "\'")
            temp1 = temp1.replace("\"\"", "\"")
            rec[4] = temp1

            temp2 = rec[5]
            temp2 = temp2.replace("\'\'", "\'")
            temp2 = temp2.replace("\"\"", "\"")
            rec[5] = temp2

            message = {'messageId': f"{rec[0]}", 'sender': f"{rec[1]}", 'receiver': f"{rec[2]}", 'fernetKey': f"{rec[5]}",
                       'grpName': f"{rec[3]}", 'userMessage': f"{rec[4]}", 'isGroup': isGroup, 'isComplete': False}
            jsonData = json.dumps(message)
            print("SENT")
            client_socket.send(
                bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))

        if (receiveAck(client_socket)):
            if (isImg or isAdd):
                query = f'''DELETE FROM pending WHERE SNo = {rec[0]};'''
                cur.execute(query)
                query = f'''DELETE FROM pending WHERE SNo = {rec[0]-1};'''
                isImg = False
                isAdd = False
            else:
                query = f'''DELETE FROM pending WHERE SNo = {rec[0]};'''

            cur.execute(query)

        else:
            return

    message = {'isComplete': True}
    jsonData = json.dumps(message)
    print("SENT")
    client_socket.send(
        bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))
    print(f"All pending messages sent succesfully to {receiverName}")

    ####################################################
    # Send second message/delete first when ack for recieval
    # of first is received on server as client is unable to handle
    # so many messages one after other
    ####################################################


def updatestatus(isOnline, username):
    """Update the status of username on database when they log on/off

    :param [username]: username whose status changed
    :type [username]: str
    :param [username]: the current status of username
    :type [username]: bool
    """
    cur = connectToDb()
    query = f'''UPDATE userinfo SET isOnline = {isOnline} WHERE username = '{username}';'''
    cur.execute(query)


def replace_quote(msg, fernet):
    """Duplicate all occurences of both double and single quotes

    :param [msg]: message string
    :type [msg]: str
    :param [fernet]: fernet string
    :type [fernet]: str
    :return: return the string with duplicated quotes
    :rtype: str,str
    """
    msg = msg.replace("\'", "\'\'")
    msg = msg.replace("\"", "\"\"")
    fernet = fernet.replace("\'", "\'\'")
    fernet = fernet.replace("\"", "\"\"")
    return msg, fernet

IP = sys.argv[1]
PORT = int(sys.argv[2])

if __name__ == '__main__':


    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((IP, PORT))
    print('Server socket initialized')
    server_socket.listen()

    sockets_list = [server_socket]

    clients = {}
    # clients_pending = {}
    print(f'Listening for connections on {IP}:{PORT}...')

    # NEW XMLRPC SERVER
    # rpcServer = SimpleXMLRPCServer.SimpleXMLRPCServer((IP, 3000), logRequests=False,allow_none=True)
    # # rpcServer.register_instance(ServerTrial())
    # rpcServer.register_function(isValidPassword)
    # rpcServer.register_function(addNewUser)
    # rpcServer.register_function(checkUserName)
    # rpcServer.register_function(getPublicKey)
    # print("hello")
    # server_thread = threading.Thread(target = rpcServer.serve_forever())
    # server_thread.start()
    # print("skdhks")

    initialize()
    print('Initialized the server database')
    while True:
        # Of these three lists, returned by the selet method, 1st is the one which has all sockets whcih are ready to proceed.
        # 3rd is the one which throws some exception
        read_sockets, _, exception_sockets = select.select(
            sockets_list, [], sockets_list)
        # print(sockets_list)

        for iter_socket in read_sockets:
            if iter_socket == server_socket:
                client_socket, client_address = server_socket.accept()
                user = unpack_message(client_socket)
                if not user:
                    continue
                if (not user['isPending']):
                    sockets_list.append(client_socket)
                    clients[client_socket] = user['userMessage']
                    updatestatus(True, user['userMessage'])

                # handlePendingMessages(client_socket)
                else:
                    # clients_pending[client_socket] = user['userMessage']
                    # print("hello")
                    pendingThread = threading.Thread(
                        target=sendPendingMessages, args=(client_socket, user['userMessage']))
                    pendingThread.start()

                print('Accepted new connection from {}:{}, username: {}'.format(
                    *client_address, user['userMessage']))

            else:
                message = unpack_message(iter_socket)
                if not message:
                    print('Closed connection from: {}'.format(
                        clients[iter_socket]))
                    updatestatus(False, clients[iter_socket])
                    sockets_list.remove(iter_socket)
                    # removes that particular socket from the clients dictionary
                    del clients[iter_socket]

                    continue

                # if message typed is exactly LEAVE GROUP the remove that client.(for which message should be true)
                if message:
                    print(message)
                    if message['isAck']:
                        cur = connectToDb()
                        if (message['isImage']):
                            query = f'''DELETE FROM pending WHERE SNo={int(message['messageId'])+1};'''
                            cur.execute(query)
                        query = f'''DELETE FROM pending WHERE SNo={int(message['messageId'])};'''
                        cur.execute(query)
                        continue

                    if message['userMessage'] == "LEAVE GROUP":
                        print('Closed connection from: {}'.format(
                            clients[iter_socket]))
                        sockets_list.remove(iter_socket)
                        if message['userMessage'] == "LEAVE GROUP":
                            iter_socket.send("LEAVE".encode())
                        del clients[iter_socket]

                        continue

                user = clients[iter_socket]
                print(f"Received message from {user}")
                if (not message['isGroup']):

                    if not message['receiver'] in list(clients.values()):
                        print(f"HANDLING OFFLINE USER:{message['receiver']}")

                        cur = connectToDb()
                        query = f'''SELECT COALESCE(MAX(SNo), 0) FROM pending;'''
                        cur.execute(query)
                        record = cur.fetchall()
                        nextRowNum = record[0][0] + 1
                        # print(nextRowNum)
                        if (message['userMessage'] == "SEND IMAGE"):
                            print('Sending image')
                            fernet = message['fernetKey']
                            encrypted = message['imageData']
                            encrypted, fernet = replace_quote(
                                encrypted, fernet)

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '', '{message['userMessage']}', '{fernet}');'''
                            cur.execute(query)

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum + 1}, '{message['imageFormat']}', '{message['receiver']}', '', '{encrypted}', '{fernet}');'''
                            cur.execute(query)

                        elif (message['userMessage'] == "ADD_PARTICIPANT"):
                            print('Adding participant')
                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{message['userMessage']}');'''
                            cur.execute(query)

                            message['privateKey'] = [
                                int(i) for i in message['privateKey']]

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum+1}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{message['privateKey']}');'''
                            cur.execute(query)

                            # message['privateKey'] = [str(i) for i in message['privateKey']]
                        elif (message['userMessage'] == "REMOVE_PARTICIPANT"):
                            print('Removing participant')
                            fernet = message['fernetKey']
                            encrypted = message['userMessage']

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{encrypted}', '{fernet}');'''
                            cur.execute(query)

                        else:
                            fernet = message['fernetKey']
                            encrypted = message['userMessage']
                            encrypted, fernet = replace_quote(
                                encrypted, fernet)

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '', '{encrypted}', '{fernet}');'''
                            cur.execute(query)

                    else:
                        # message['userName'] = user['userMessage'] # sender name
                        cur = connectToDb()
                        query = f'''SELECT COALESCE(MAX(SNo), 0) FROM pending;'''
                        cur.execute(query)
                        record = cur.fetchall()
                        nextRowNum = record[0][0] + 1

                        message['messageId'] = nextRowNum

                        if (message['userMessage'] == "SEND IMAGE"):
                            print('Sending image')
                            fernet = message['fernetKey']
                            encrypted = message['imageData']
                            encrypted, fernet = replace_quote(
                                encrypted, fernet)

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '', '{message['userMessage']}', '{fernet}');'''
                            cur.execute(query)
                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum + 1}, '{message['imageFormat']}', '{message['receiver']}', '', '{encrypted}', '{fernet}');'''
                            cur.execute(query)

                        elif (message['userMessage'] == "ADD_PARTICIPANT"):
                            print('Adding participant')
                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{message['userMessage']}');'''
                            cur.execute(query)

                            message['privateKey'] = [
                                int(i) for i in message['privateKey']]
                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum+1}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{message['privateKey']}');'''
                            cur.execute(query)
                        # print(nextRowNum)
                        elif (message['userMessage'] == "REMOVE_PARTICIPANT"):
                            print('Removing participant')
                            fernet = message['fernetKey']
                            encrypted = message['userMessage']

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{encrypted}', '{fernet}');'''
                            cur.execute(query)

                        else:
                            fernet = message['fernetKey']
                            encrypted = message['userMessage']
                            encrypted, fernet = replace_quote(
                                encrypted, fernet)

                            query = f'''INSERT INTO pending
                                            VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '', '{encrypted}', '{fernet}');'''
                            cur.execute(query)

                        jsonData = json.dumps(message)
                        sock = getSocket(message['receiver'], clients)
                        sock.send(
                            bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))

                elif (message['isGroup']):
                    usersList = getUsersList(message['receiver'])
                    message['grpName'] = message['receiver']
                    for client_socket in clients:
                        # But don't sent it to sender
                        if client_socket != iter_socket and (clients[client_socket] in usersList):
                            message['receiver'] = clients[client_socket]

                            # Send user and message (both with their headers)
                            # We are reusing here message header sent by sender, and saved username header send by user when he connected
                            cur = connectToDb()
                            query = f'''SELECT COALESCE(MAX(SNo), 0) FROM pending;'''
                            cur.execute(query)
                            record = cur.fetchall()
                            nextRowNum = record[0][0] + 1

                            message['messageId'] = nextRowNum

                            if (message['userMessage'] == "SEND IMAGE"):
                                print('Sending image to group')
                                fernet = message['fernetKey']
                                encrypted = message['imageData']
                                encrypted, fernet = replace_quote(
                                    encrypted, fernet)

                                query = f'''INSERT INTO pending
                                                VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{message['userMessage']}', '{fernet}');'''
                                cur.execute(query)
                                query = f'''INSERT INTO pending
                                                VALUES({nextRowNum + 1}, '{message['imageFormat']}', '{message['receiver']}', '{message['grpName']}', '{encrypted}', '{fernet}');'''
                                cur.execute(query)

                            # print(nextRowNum)
                            else:
                                fernet = message['fernetKey']
                                encrypted = message['userMessage']
                                encrypted, fernet = replace_quote(
                                    encrypted, fernet)

                                query = f'''INSERT INTO pending
                                                VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{encrypted}', '{fernet}');'''
                                cur.execute(query)

                            jsonData = json.dumps(message)
                            client_socket.send(
                                bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))

                            # if(not receiveAck(sock)):
                            # print("MESSAGE NOT RECEIVED COMPLETELY!!")

                    for groupMem in usersList:
                        message['receiver'] = groupMem
                        if (not groupMem in list(clients.values())):
                            cur = connectToDb()
                            query = f'''SELECT COALESCE(MAX(SNo), 0) FROM pending;'''
                            cur.execute(query)
                            nextRowNum = cur.fetchall()[0][0] + 1
                            # print(nextRowNum)

                            if (message['userMessage'] == "SEND IMAGE"):
                                print('Sending group image to offline client')
                                fernet = message['fernetKey']
                                encrypted = message['imageData']
                                encrypted, fernet = replace_quote(
                                    encrypted, fernet)

                                query = f'''INSERT INTO pending
                                                VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{message['userMessage']}', '{fernet}');'''
                                cur.execute(query)
                                query = f'''INSERT INTO pending
                                                VALUES({nextRowNum + 1}, '{message['imageFormat']}', '{message['receiver']}', '{message['grpName']}', '{encrypted}', '{fernet}');'''
                                cur.execute(query)

                            else:
                                print('Sending group msg to offline client')
                                fernet = message['fernetKey']
                                encrypted = message['userMessage']
                                encrypted, fernet = replace_quote(
                                    encrypted, fernet)

                                query = f'''INSERT INTO pending
                                                VALUES({nextRowNum}, '{message['sender']}', '{message['receiver']}', '{message['grpName']}', '{encrypted}', '{fernet}');'''
                                cur.execute(query)

        # It's not really necessary to have this, but will handle some socket exceptions just in case
        for notified_socket in exception_sockets:
            # Remove from list for socket.socket()
            sockets_list.remove(notified_socket)
            updatestatus(False, clients[notified_socket])

            # Remove from our list of users
            del clients[notified_socket]
