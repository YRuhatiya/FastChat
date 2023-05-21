import socket
import select
import json
from json.decoder import JSONDecodeError
import psycopg2
import rsa
from datetime import datetime

HEADER_LENGTH = 10
"""
In order to communicate large messages over a socket, they are broken into multiple smaller messages.
The first HEADER_LENGTH characters of the initial message inform the listener how many bytes of data to receive, so that they may stop listening once these many bytes have been received.
"""  # pylint: disable=W0105


def handlePendingMessages(client_pending_socket, proxy):
    """Handles the sending of pending messages. Called every time the client logs in.

    :param [client_pending_socket]: socket belonging to the client having pending messages
    :type [client_pending_socket]: socket
    :param [proxy]: proxy server for rpc
    :type [proxy]: ServerProxy
    """
    while True:
        bo = False
        read_sockets, _, error_sockets = select.select(
            [client_pending_socket], [], [client_pending_socket])
        for socket in read_sockets:
            if socket == client_pending_socket:
                data = unpack_message(socket)
                if (data['isComplete']):
                    bo = True
                    break

                # QUERIES
                sender = data['sender']
                MY_USERNAME = data['receiver']
                message = data['userMessage']
                # When message in a group is received the sender would be the person swending it ,
                # while according to the implementation we need to enter in table of sender/grpName
                grpName = sender
                if (data['isGroup']):
                    grpName = data['grpName']
                if (not data['isGroup']):
                    if (message == "REMOVE_PARTICIPANT" or message == "ADD_PARTICIPANT"):
                        grpName = data['grpName']

                cur = connectMydb(MY_USERNAME)
                # decryptedMessage = decryptMessage(message, cur, MY_USERNAME)
                decryptedMessage = message

                query = f'''SELECT EXISTS (
                        SELECT FROM
                            pg_tables
                        WHERE
                            schemaname = 'public' AND
                            tablename  = '{grpName}'
                        )'''
                cur.execute(query)
                response = cur.fetchall()[0][0]

                if message == "SEND IMAGE":
                    if (not response):
                        addNewDM(MY_USERNAME, sender, proxy)

                    query = f'''SELECT COALESCE(MAX(messageId), 0) FROM "{grpName}";'''
                    cur.execute(query)
                    record = cur.fetchall()
                    nextRowNum = record[0][0] + 1

                    encrypted = data["imageData"]
                    key = data["fernetKey"]
                    encrypted, key = replace_quote(encrypted, key)

                    query = f'''INSERT INTO "{grpName}"
                                VALUES ('{sender}','{message}', {nextRowNum}, '{key}');'''
                    cur.execute(query)

                    query = f'''INSERT INTO "{grpName}"
                                VALUES ('{data["imageFormat"]}', '{encrypted}', {nextRowNum + 1}, '{key}');'''
                    cur.execute(query)

                    # return (sender, grpName, decryptedMessage, data['messageId'], data['imageFormat'], data['imageData'])

                elif message == "ADD_PARTICIPANT":
                    cur = connectMydb(MY_USERNAME)
                    query = f'''CREATE TABLE "{grpName}"(
                            name TEXT,
                            message TEXT,
                            messageId INT DEFAULT 0,
                            symmetricKey TEXT DEFAULT 'NA');'''
                    cur.execute(query)

                    # #############################TODO################################ #
                    # YOU MUST HAVE TO DECRYPT PRIVATE KEY USING THE PUBLIC KEY OF THIS USER
                    # #############################TODO################################ #

                    # privaet key list is being passed as a string here so handle that issue
                    data['privateKey'] = eval(data['privateKey'])

                    query = f'''INSERT INTO connections
                                VALUES('{data['grpName']}', {data['privateKey'][0]}, {data['privateKey'][1]}, {data['privateKey'][2]}, {data['privateKey'][3]}, {data['privateKey'][4]}, False)'''
                    cur.execute(query)
                    # return (sender, grpName, decryptedMessage, data['messageId'])

                # if message == "REMOVE_PARTICIPANT":
                # NOT HERE , as we have to let user know that he is removed so drop table only when
                # only when he opens the group

                # storing the data into the table corresponding to the sender
                # print(type(response))
                else:
                    encrypted = message
                    key = data["fernetKey"]
                    encrypted, key = replace_quote(encrypted, key)
                    # If table already exists
                    if (response):
                        query = f'''SELECT COALESCE(MAX(messageId), 0) FROM "{grpName}";'''
                        cur.execute(query)
                        record = cur.fetchall()
                        nextRowNum = record[0][0] + 1
                        query = f'''INSERT INTO "{grpName}"
                            VALUES('{sender}', '{encrypted}', {nextRowNum}, '{key}');'''
                        cur.execute(query)
                        # print(colored(f'{decryptedMessage}', 'white', 'on_red'))
                    if (not response):
                        addNewDM(MY_USERNAME, sender, proxy)
                        query = f'''SELECT COALESCE(MAX(messageId), 0) FROM "{grpName}";'''
                        cur.execute(query)
                        record = cur.fetchall()
                        nextRowNum = record[0][0] + 1
                        query = f'''INSERT INTO "{sender}"
                                    VALUES('{sender}', '{encrypted}', {nextRowNum}, '{key}');'''
                        cur.execute(query)

                # #################
                ack = "__ACK__"
                jsonData = json.dumps({'userMessage': f"{ack}"})
                client_pending_socket.send(
                    bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))
        if (bo):
            break
    client_pending_socket.close()


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


def isAdminOfGroup(grpName, MY_USERNAME):
    """
    :param [grpName]: name of the group
    :type [grpName]: str
    :param [MY_USERNAME]: admin username
    :type [MY_USERNAME]: str
    :return: whether MY_USERNAME is an admin of grpName
    :rtype: bool
    """
    cur = connectMydb(MY_USERNAME)
    query = f'''SELECT isAdmin FROM connections WHERE username = '{grpName}';'''
    cur.execute(query)
    record = cur.fetchall()
    if (record == []):
        return False

    return record[0][0]


def decryptMessage(message, cur, MY_USERNAME):
    """
    :param [message]: encrypted message
    :type [message]: str
    :param [cur]: cursor pointing to the user's local database
    :type [cur]: _Cursor
    :param [MY_USERNAME]: username of the client in question
    :type [MY_USERNAME]: str
    :return: the decrypted message
    :rtype: str
    """
    query = f'''SELECT publicn,publice,privated,privatep,privateq FROM
                userinfo WHERE username = {MY_USERNAME};'''
    cur.execute(query)
    components = cur.fetchall()[0]
    PrivateKey = rsa.key.PrivateKey(
        int(components[0]), int(components[1]), int(components[2]), int(components[3]), int(components[4]))
    # check if has been already decoded or not
    decryptedMessage = rsa.decrypt(message, PrivateKey).decode()
    return decryptedMessage


def receive_message(data, proxy):
    """Handle the reception of normal messages as well as the SEND_IMAGE and ADD_PARTICIPANT keywords along with updating the user-side database

    :param [data]: dictionary containing all details of the message received
    :type [data]: dict
    :param [proxy]: proxy server for remote calls
    :type [proxy]: ServerProxy
    """
    if not data:
        # graceful termination has already been achieved
        print('Connection closed by the server')
        return None
    # print(data)
    sender = data['sender']
    MY_USERNAME = data['receiver']
    message = data['userMessage']

    logfile = open(f"received_logs.txt", "a")
    logfile.write(datetime.now().strftime("%H:%M:%S")+"\n")
    # When message in a group is received the sender would be the person swending it ,
    # while according to the implementation we need to enter in table of sender/grpName
    grpName = sender
    if (data['isGroup']):
        grpName = data['grpName']
    if (not data['isGroup']):
        # Message sent only to this person so isGroup false but grpName diff. from sender
        if (message == "REMOVE_PARTICIPANT" or message == "ADD_PARTICIPANT"):
            grpName = data['grpName']

    cur = connectMydb(MY_USERNAME)
    # decryptedMessage = decryptMessage(message, cur, MY_USERNAME)
    decryptedMessage = message

    query = f'''SELECT EXISTS (
            SELECT FROM
                pg_tables
            WHERE
                schemaname = 'public' AND
                tablename  = '{grpName}'
            )'''
    cur.execute(query)
    response = cur.fetchall()[0][0]

    if message == "SEND IMAGE":
        if (not response):
            addNewDM(MY_USERNAME, sender, proxy)

        query = f'''SELECT COALESCE(MAX(messageId), 0) FROM "{grpName}";'''
        cur.execute(query)
        record = cur.fetchall()
        nextRowNum = record[0][0] + 1

        encrypted = data["imageData"]
        key = data["fernetKey"]
        encrypted, key = replace_quote(encrypted, key)

        query = f'''INSERT INTO "{grpName}" 
                    VALUES ('{sender}','{message}', {nextRowNum}, '{key}');'''
        cur.execute(query)
        query = f'''INSERT INTO "{grpName}"
                    VALUES ('{data["imageFormat"]}', '{encrypted}', {nextRowNum + 1}, '{key}');'''
        cur.execute(query)
        return (sender, grpName, decryptedMessage, data['messageId'], True, data["fernetKey"], data['isGroup'], data['imageFormat'], data['imageData'])

    if message == "ADD_PARTICIPANT":
        cur = connectMydb(MY_USERNAME)
        query = f'''CREATE TABLE "{grpName}"(
                name TEXT,
                message TEXT,
                messageId INT DEFAULT 0,
                symmetricKey TEXT DEFAULT 'NA');'''
        cur.execute(query)

        # #############################TODO################################ #
        # YOU MUST HAVE TO DECRYPT PRIVATE KEY USING THE PUBLIC KEY OF THIS USER
        # #############################TODO################################ #

        # In live messaging the private Key is sent as a list
        query = f'''INSERT INTO connections
                    VALUES('{data['grpName']}', {data['privateKey'][0]}, {data['privateKey'][1]}, {data['privateKey'][2]}, {data['privateKey'][3]}, {data['privateKey'][4]}, False)'''
        cur.execute(query)
        ############
        # return True for add participant too as we need to delete 2 rows here too
        return (sender, grpName, decryptedMessage, data['messageId'], True, data["fernetKey"], data['isGroup'])

    # if message == "REMOVE_PARTICIPANT":
    # NOT HERE , as we have to let user know that he is removed so drop table only when
    # only when he opens the group

    # storing the data into the table corresponding to the sender
    # print(type(response))
    else:
        # If table already exists
        encrypted = message
        key = data["fernetKey"]
        encrypted, key = replace_quote(encrypted, key)

        if (response):
            query = f'''SELECT COALESCE(MAX(messageId), 0) FROM "{grpName}";'''
            cur.execute(query)
            record = cur.fetchall()
            nextRowNum = record[0][0] + 1
            query = f'''INSERT INTO "{grpName}"
                VALUES('{sender}', '{encrypted}', {nextRowNum}, '{key}')'''
            cur.execute(query)
            # print(colored(f'{decryptedMessage}', 'white', 'on_red'))
        if (not response):
            addNewDM(MY_USERNAME, sender, proxy)
            query = f'''SELECT COALESCE(MAX(messageId), 0) FROM "{grpName}";'''
            cur.execute(query)
            record = cur.fetchall()
            nextRowNum = record[0][0] + 1
            query = f'''INSERT INTO "{sender}"
                        VALUES('{sender}', '{encrypted}', {nextRowNum}, '{key}');'''
            cur.execute(query)
        # print(colored(f'{decryptedMessage}', 'white', 'on_red'))

    return (sender, grpName, decryptedMessage, data['messageId'], False, data["fernetKey"], data['isGroup'])


def checkSocketReady(socket):
    """
    :param [socket]: socket in question
    :type [socket]: socket
    :return: return the socket if it is ready to be read, otherwise return false
    :rtype: bool
    """
    read_sockets, _, error_sockets = select.select(
        [socket], [], [socket], 0.01)
    if read_sockets != []:
        return read_sockets[0]
    else:
        return False


def getOwnPublicKey(sender):
    """Get the sender's public key from local database

    :param [sender]: username of the sender
    :type [sender]: str
    :return: sender's public key
    :rtype: rsa.key.PublicKey
    """
    cur = connectMydb(sender)
    query = f'''SELECT publicn ,publice from userinfo
                WHERE username = '{sender}';'''
    cur.execute(query)
    record = cur.fetchall()[0]
    publicKey = rsa.key.PublicKey(int(record[0]), int(record[1]))
    return publicKey


def getOwnPrivateKey(sender):
    """Get the sender's private key from local database

    :param [sender]: username of the sender
    :type [sender]: str
    :return: sender's private key
    :rtype: rsa.key.PrivateKey
    """
    cur = connectMydb(sender)
    query = f'''SELECT publicn ,publice, privated, privatep, privateq from userinfo
                WHERE username = '{sender}';'''
    cur.execute(query)
    record = cur.fetchall()[0]
    privateKey = rsa.key.PrivateKey(int(record[0]), int(
        record[1]), int(record[2]), int(record[3]), int(record[4]))
    return privateKey


def getPublicKey(reciever, sender):
    """
    :param [reciever]: username of the receiver of the message
    :type [reciever]: str
    :param [sender]: username of the sender of the message
    :type [sender]: str
    :return: parameters n and e of the public key of the receiver
    :rtype: list
    """
    cur = connectMydb(sender)
    query = f'''SELECT publicn ,publice from connections
                WHERE username = '{reciever}';'''
    cur.execute(query)
    record = cur.fetchall()[0]
    # print(record)
    publicKey = rsa.key.PublicKey(int(record[0]), int(record[1]))
    return publicKey


def getPrivateKey(group, sender):
    """
    :param [group]: group of which the sender is a participant
    :type [group]: str
    :param [sender]: username of the sender of the message
    :type [sender]: str
    :return: parameters the private key of the group
    :rtype: tuple
    """
    cur = connectMydb(sender)
    query = f'''SELECT publicn ,publice, privated, privatep, privateq from connections
                WHERE username = '{group}';'''
    cur.execute(query)
    record = cur.fetchall()[0]
    # print(record)
    # publicKey = rsa.key.PublicKey(record[0],record[1], record[2], record[3], record[4])
    return record


def goOnline(username, IP, PORT):
    """
    :param [username]: group of which the sender is a participant
    :type [username]: str
    :param [IP]: IP address of the server
    :type [IP]: str
    :param [PORT]: PORT of the server
    :type [PORT]: int
    :return: parameters the private key of the group
    :rtype: tuple
    """

    username_header = f"{len(username):<{HEADER_LENGTH}}"

    client_sockets = []
    client_pending_sockets = []

    for i in range(1, 4):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setblocking(True)
        # print(port, type(port))
        # print("HHHHHHHH")
        client_socket.connect((IP, PORT + 100*i))

        data = {'userHeader': f"{username_header}",
                'userMessage': f"{username}", 'isPending': False}
        jsonData = json.dumps(data)
        client_socket.send(
            bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))

        client_pending_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        client_pending_socket.setblocking(True)
        client_pending_socket.connect((IP, PORT + 100*i))

        dataPen = {'userHeader': f"{username_header}",
                   'userMessage': f"{username}", 'isPending': True}
        jsonDataPen = json.dumps(dataPen)

        client_pending_socket.send(
            bytes(f'{len(jsonDataPen):<10}{jsonDataPen}', encoding='utf-8'))

        client_sockets.append(client_socket)
        client_pending_sockets.append(client_pending_socket)

    return client_sockets, client_pending_sockets


def connectMydb(dbName):
    """
    :param [dbName]: username of the client whose database we need to connect to
    :type [dbName]: str
    :return: cursor pointing to that user's local database
    :rtype: _Cursor
    """
    conn = psycopg2.connect(
        database=f"{dbName}", user="postgres", password="fastchat", host="localhost", port="5432")
    conn.autocommit = True
    cur = conn.cursor()
    return cur

# check the availability in connections table


def isInConnections(MY_USERNAME, username):
    """
    :param [MY_USERNAME]: username of the client whose connections we need to check
    :type [MY_USERNAME]: str
    :param [username]: username of the other client
    :type [username]: str
    :return: whether username is in MY_USERNAME's connections
    :rtype: bool
    """
    cur = connectMydb(MY_USERNAME)
    query = f'''SELECT username FROM connections;'''
    cur.execute(query)
    record = cur.fetchall()

    return ((f"{username}",) in record)


# returns lists of all the users and groups to get listed
def getAllUsers(MY_USERNAME):
    """
    :param [MY_USERNAME]: username of the client whose connections we need to check
    :type [MY_USERNAME]: str
    :return: lists DM, group of all the users and groups in MY_USERNAME's connections
    :rtype: list, list
    """
    DM = []
    group = []

    cur = connectMydb(MY_USERNAME)
    query = f'''SELECT username FROM connections WHERE privated = '-1';'''
    cur.execute(query)
    record = cur.fetchall()
    for i in record:
        DM.append(i[0])

    query = f'''SELECT username FROM connections WHERE privated != '-1';'''
    cur.execute(query)
    record = cur.fetchall()
    for i in record:
        group.append(i[0])

    return DM, group


#  Adding a new DM as requested by the user
def addNewDM(MY_USERNAME, username, proxy):
    """Adding a new DM to username as requested by MY_USERNAME

    :param [MY_USERNAME]: username of the client who requested DM
    :type [MY_USERNAME]: str
    :param [username]: username of the other client
    :type [username]: str
    :return: True for success and False for failure
    :rtype: bool
    """
    # checking that the user is registered with the app or not
    if (not proxy.checkUserName(username)):
        # print("HELLO")
        return False
    else:
        publicKey = proxy.getPublicKey(username)
        # print("HELLO")
        cur = connectMydb(MY_USERNAME)
        query = f'''INSERT INTO connections
                    VALUES('{username}', {publicKey[0]}, {publicKey[1]}, '-1', '-1', '-1', FALSE);'''
        cur.execute(query)

        query = f'''SELECT EXISTS (
            SELECT FROM
                pg_tables
            WHERE
                schemaname = 'public' AND
                tablename  = '{username}'
            )'''
        cur.execute(query)
        response = cur.fetchall()[0][0]

        if (not response):
            query = f'''CREATE TABLE "{username}"(
                        person TEXT,
                        message TEXT,
                        messageId INT DEFAULT 0,
                        symmetricKey TEXT DEFAULT 'NA');'''
            cur.execute(query)

    return True


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
            if (temp == ""):
                return
            if (new_message):
                message_len = int(temp[:HEADER_LENGTH].strip())
                # print(message_len)
                userData += temp[HEADER_LENGTH:]
                new_message = False
                continue

            userData += temp
            # print(len(userData))
            # print(userData)
            # print("USER: ",userData)
            if (message_len == len(userData)):
                userData = json.loads(userData)
                return userData

        # return {'Len':userData['userHeader'], 'Message':message}
    except JSONDecodeError as e:
        print(e)
        # Something went wrong like empty message or client exited abruptly.
        return False


def createGroup(grpName, ADMIN, proxy):
    """Create a new group by updating the database

    :param [grpName]: name of the new group
    :type [grpName]: str
    :param [ADMIN]: username of the creator
    :type [ADMIN]: str
    :param [proxy]: the proxy server, used for a remote call to createGroupAtServer
    :type [proxy]: ServerProxy
    """
    cur = connectMydb(ADMIN)
    ###########################
    publicKey, privateKey = rsa.newkeys(512)

    query = f'''INSERT INTO connections
            VALUES('{grpName}',{publicKey['n']}, {publicKey['e']}, {privateKey['d']}, {privateKey['p']}, {privateKey['q']}, TRUE)'''

    cur.execute(query)
    ###########################
    proxy.createGroupAtServer(grpName, ADMIN)

    query = f'''CREATE TABLE "{grpName}"(
                name TEXT,
                message TEXT,
                messageId INT DEFAULT 0,
                symmetricKey TEXT DEFAULT 'NA');'''
    cur.execute(query)


def sendAck(client_socket, messageId, isImage):
    """Send an acknowledgement to the server on receipt of a message over socket

    :param [client_socket]: the socket that is sending the ack
    :type [client_socket]: socket
    :param [messageId]: unique id used to identify the message
    :type [messageId]: int
    :param [isImage]: whether the message is an image or not
    :type [isImage]: bool
    """
    message = "__ACK__"
    jsonData = json.dumps({'userMessage': f"{message}",
                          'messageId': f"{messageId}", 'isAck': True, 'isImage': isImage})
    client_socket.send(
        bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))

################ TODO ####################
# Recieve ack from client , try doing for messages when receiver is active too!
##########################################
# IDEA - what we can do is that check the ack_text = socket.recv() ,
# now if it is that message has been recieved then send a confiramtion to
# server as a message through client and once that is done only then allow the
# server to move ahead , set a timeout and if ack is not received in that time
# store the message as pending messages and continue with the loop
##########################################
# Pointer to last read messages so the rest are printed when the user opens the interface
# Online-Offline status updation and storing-sending messages accordingly
# ENCRYPTION
# Multi-server load balancing
################ TODO ####################
# Use eval to get the encrypted,message and keys as bytes before decrypting
