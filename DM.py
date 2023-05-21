import os
import select
import errno
import sys
import rsa
import json
import base64
from client import receive_message, getPublicKey, getPrivateKey, unpack_message, sendAck, getOwnPublicKey, getOwnPrivateKey
from termcolor import colored
from client import connectMydb
from cryptography.fernet import Fernet
from datetime import datetime


def handleDM(MY_USERNAME, OTHER_USERNAME, client_sockets, proxy, isGroup):
    """To be used when MY_USERNAME sends a message to OTHER_USERNAME.
    Handles the keywords REMOVE_PARTICIPANT, LEAVE GROUP, and SEND IMAGE.

    :param [MY_USERNAME]: username of the client who sent DM
    :type [MY_USERNAME]: str
    :param [OTHER_USERNAME]: username of the receiving client/group
    :type [OTHER_USERNAME]: str
    :param [client_socket]: username of the receiving client/group
    :type [client_socket]: str
    :param [proxy]: proxy server for remote call to receive_message
    :type [proxy]: ServerProxy
    :param [isGroup]: whether the receiver is a group
    :type [isGroup]: bool
    """
    cur = connectMydb(MY_USERNAME)
    query = f'''SELECT readUpto FROM connections WHERE username = '{OTHER_USERNAME}';'''
    cur.execute(query)
    readUpto = cur.fetchall()[0][0]
    query = f'''SELECT * FROM "{OTHER_USERNAME}" WHERE messageId > {readUpto}'''
    cur.execute(query)
    record = cur.fetchall()

    isImage = False
    finalMessageId = 0
    for rec in record:
        if (isImage):

            fernetKey = rec[3]
            encryptedMessage = rec[1]
            fernetKey = fernetKey.replace("\'\'", "\'")
            fernetKey = fernetKey.replace("\"\"", "\"")
            encryptedMessage = encryptedMessage.replace("\'\'", "\'")
            encryptedMessage = encryptedMessage.replace("\"\"", "\"")

            if (not isGroup):
                symmetricKey = rsa.decrypt(
                    eval(fernetKey), getOwnPrivateKey(MY_USERNAME))
            else:
                private = getPrivateKey(OTHER_USERNAME, MY_USERNAME)
                privateKey = rsa.key.PrivateKey(int(private[0]), int(
                    private[1]), int(private[2]), int(private[3]), int(private[4]))
                symmetricKey = rsa.decrypt(eval(fernetKey), privateKey)
            fernetObj = Fernet(symmetricKey)
            decryptedMessage = fernetObj.decrypt(
                eval(encryptedMessage)).decode('utf-8')

            ans = input("DO YOU WANT TO RECIEVE AN IMAGE SENT(YES/NO ?):")
            if (ans.upper() == "YES"):
                name = input("SAVE IMAGE AS: ")
                os.system(f'touch {name}.{rec[0]}')
                with open(f'{name}.{rec[0]}', 'wb') as f:
                    f.write(base64.b64decode(decryptedMessage))
                    print(colored('RECEIVED IMAGE!!', 'green'))
            isImage = False

        elif (rec[1] == "SEND IMAGE"):
            isImage = True

        elif (rec[1] == "REMOVE_PARTICIPANT"):
            query = f'''DROP TABLE "{OTHER_USERNAME}";'''
            cur.execute(query)
            query = f'''DELETE FROM connections WHERE username = '{OTHER_USERNAME}';'''
            cur.execute(query)
            print(colored("YOU WERE KICKED FROM THE GROUP!", 'yellow'))

        else:
            fernetKey = rec[3]
            encryptedMessage = rec[1]
            fernetKey = fernetKey.replace("\'\'", "\'")
            fernetKey = fernetKey.replace("\"\"", "\"")
            encryptedMessage = encryptedMessage.replace("\'\'", "\'")
            encryptedMessage = encryptedMessage.replace("\"\"", "\"")

            if (not isGroup):
                symmetricKey = rsa.decrypt(
                    eval(fernetKey), getOwnPrivateKey(MY_USERNAME))
            else:
                private = getPrivateKey(OTHER_USERNAME, MY_USERNAME)
                privateKey = rsa.key.PrivateKey(int(private[0]), int(
                    private[1]), int(private[2]), int(private[3]), int(private[4]))
                symmetricKey = rsa.decrypt(eval(fernetKey), privateKey)
            fernetObj = Fernet(symmetricKey)
            decryptedMessage = fernetObj.decrypt(
                eval(encryptedMessage)).decode('utf-8')

            print(f"{rec[0]} > ", colored(
                f'{decryptedMessage}', 'white', 'on_red'))

        finalMessageId = rec[2]

    if (finalMessageId != 0):
        query = f'''UPDATE connections SET readUpto = {finalMessageId} WHERE username = '{OTHER_USERNAME}';'''
        cur.execute(query)

    sockets_list = client_sockets[0:]
    sockets_list.append(sys.stdin)

    while True:
        try:
            read_sockets, _, error_sockets = select.select(
                sockets_list, [], sockets_list)
            for sockets in read_sockets:
                # LEAVE GROUP message
                if (sockets != sys.stdin):
                    data = unpack_message(sockets)
                    data = receive_message(data, proxy)
                    
                    sendAck(sockets, data[3], data[4])

                    if (data and data[1] == OTHER_USERNAME and data[2] == "REMOVE_PARTICIPANT"):
                        cur = connectMydb(MY_USERNAME)
                        query = f'''DROP TABLE "{OTHER_USERNAME}";'''
                        cur.execute(query)
                        query = f'''DELETE FROM connections WHERE username = '{OTHER_USERNAME}';'''
                        cur.execute(query)
                        print(colored("YOU WERE KICKED FROM THE GROUP!", 'yellow'))
                    # DON'T PRINT THE MESSAGE OF OTHER USER IN ONE'S TERMINAL

                    # YET TO HANDLE THE CASE WHEN IN A GROUP AS THEN DECRYPT
                    # WITH GROUPS OWN PRIVATE KEY

                    elif (data and data[1] == OTHER_USERNAME and data[2] == "SEND IMAGE"):
                        fernetKey = data[5]
                        encryptedMessage = data[8]
                        fernetKey = fernetKey.replace("\'\'", "\'")
                        fernetKey = fernetKey.replace("\"\"", "\"")
                        encryptedMessage = encryptedMessage.replace(
                            "\'\'", "\'")
                        encryptedMessage = encryptedMessage.replace(
                            "\"\"", "\"")

                        if (not isGroup):
                            symmetricKey = rsa.decrypt(
                                eval(fernetKey), getOwnPrivateKey(MY_USERNAME))
                        else:
                            private = getPrivateKey(
                                OTHER_USERNAME, MY_USERNAME)
                            privateKey = rsa.key.PrivateKey(int(private[0]), int(
                                private[1]), int(private[2]), int(private[3]), int(private[4]))
                            symmetricKey = rsa.decrypt(
                                eval(fernetKey), privateKey)
                            # If group then decrypt by its private key
                        fernetObj = Fernet(symmetricKey)
                        decryptedMessage = fernetObj.decrypt(
                            eval(encryptedMessage)).decode('utf-8')
                        ans = input(
                            "DO YOU WANT TO RECIEVE AN IMAGE SENT(YES/NO ?):")
                        if (ans.upper() == "YES"):
                            name = input("SAVE IMAGE AS: ")
                            os.system(f'touch {name}.{data[7]}')
                            with open(f'{name}.{data[7]}', 'wb') as f:
                                f.write(base64.b64decode(decryptedMessage))
                                print('recieved Image')

                    elif (data and data[1] == OTHER_USERNAME):
                        fernetKey = data[5]
                        encryptedMessage = data[2]
                        fernetKey = fernetKey.replace("\'\'", "\'")
                        fernetKey = fernetKey.replace("\"\"", "\"")
                        encryptedMessage = encryptedMessage.replace(
                            "\'\'", "\'")
                        encryptedMessage = encryptedMessage.replace(
                            "\"\"", "\"")

                        if (not isGroup):
                            symmetricKey = rsa.decrypt(
                                eval(fernetKey), getOwnPrivateKey(MY_USERNAME))
                        else:
                            private = getPrivateKey(
                                OTHER_USERNAME, MY_USERNAME)
                            privateKey = rsa.key.PrivateKey(int(private[0]), int(
                                private[1]), int(private[2]), int(private[3]), int(private[4]))
                            symmetricKey = rsa.decrypt(
                                eval(fernetKey), privateKey)
                        fernetObj = Fernet(symmetricKey)
                        decryptedMessage = fernetObj.decrypt(
                            eval(encryptedMessage)).decode('utf-8')

                        print(f"{data[0]} > ", colored(
                            f'{decryptedMessage}', 'white', 'on_red'))

                    if (data[2] != "REMOVE_PARTICIPANT"):
                        query = f'''SELECT MAX(messageId) FROM "{OTHER_USERNAME}";'''
                        cur.execute(query)
                        maxId = cur.fetchall()[0][0]
                        query = f'''UPDATE connections SET readUpto = {maxId} WHERE username = '{OTHER_USERNAME}';'''
                        cur.execute(query)

                    # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)

                else:
                    print("-------")
                    message = sys.stdin.readline()[0:-1]

                    if (message == "BACK"):
                        return

                    logfile = open(f"sent_logs.txt", "a")
                    logfile.write(datetime.now().strftime("%H:%M:%S")+"\n")

                    if message == "LEAVE GROUP":
                        jsonData = json.dumps(
                            {'userMessage': f"{message}", 'isAck': False})
                        serverId, port = proxy.getFreeServerId()
                        client_sockets[serverId].send(
                            bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))
                        print("You are no longer a participant of this group")
                        sys.exit()

                    elif message == "SEND IMAGE":
                        path = input("PATH OF IMAGE: ")
                        img_json = ""
                        if (path != ""):
                            with open(path, 'rb') as f:

                                ######### ENCRYPT imageData here only ##########
                                symmetricKey = Fernet.generate_key()
                                fernetObj = Fernet(symmetricKey)
                                imgEncrypted = fernetObj.encrypt(base64.encodebytes(
                                    f.read()).decode('utf-8').encode('utf-8'))
                                publicKey = getPublicKey(
                                    OTHER_USERNAME, MY_USERNAME)
                                encrypted_key = rsa.encrypt(
                                    symmetricKey, publicKey)
                                ######### ENCRYPT FERNET KEY USING THE rsa key ########

                                img_json = {'userMessage': f"{message}", 'sender': f"{MY_USERNAME}", 'receiver': f"{OTHER_USERNAME}", 'fernetKey': f"{encrypted_key}",
                                            'imageFormat': f"{path.split('.')[-1]}", 'imageData': f"{imgEncrypted}", 'isGroup': isGroup, 'isAck': False}
                                print("Image sent")
                            jsonData = json.dumps(img_json)

                            serverId, port = proxy.getFreeServerId()
                            client_sockets[serverId].send(
                                bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))

                            query = f'''SELECT COALESCE(MAX(messageId), 0) FROM "{OTHER_USERNAME}";'''
                            cur.execute(query)
                            record = cur.fetchall()
                            nextRowNum = record[0][0] + 1

                            encrypt_for_me = rsa.encrypt(
                                symmetricKey, getOwnPublicKey(MY_USERNAME))

                            encrypted_message = str(imgEncrypted)
                            encrypted_message = encrypted_message.replace(
                                "\'", "\'\'")
                            encrypted_message = encrypted_message.replace(
                                "\"", "\"\"")

                            encrypted_key = str(encrypted_key)
                            encrypted_key = encrypted_key.replace("\'", "\'\'")
                            encrypted_key = encrypted_key.replace("\"", "\"\"")

                            encrypt_for_me = str(encrypt_for_me)
                            encrypt_for_me = encrypt_for_me.replace(
                                "\'", "\'\'")
                            encrypt_for_me = encrypt_for_me.replace(
                                "\"", "\"\"")

                            query = f'''INSERT INTO "{OTHER_USERNAME}" 
                                        VALUES ('{MY_USERNAME}','{message}', {nextRowNum}, '{encrypt_for_me}');'''
                            cur.execute(query)
                            query = f'''INSERT INTO "{OTHER_USERNAME}"
                                        VALUES ('{img_json["imageFormat"]}', '{encrypted_message}', {nextRowNum + 1}, '{encrypt_for_me}');'''
                            cur.execute(query)

                            query = f'''UPDATE connections SET readUpto = {nextRowNum + 1} WHERE username = '{OTHER_USERNAME}';'''
                            cur.execute(query)

                    elif message != "":
                        symmetricKey = Fernet.generate_key()
                        fernetObj = Fernet(symmetricKey)
                        publicKey = getPublicKey(OTHER_USERNAME, MY_USERNAME)
                        encrypted_message = fernetObj.encrypt(
                            message.encode('utf-8'))
                        encrypted_key = rsa.encrypt(symmetricKey, publicKey)
                        
                        encrypt_for_me = rsa.encrypt(
                            symmetricKey, getOwnPublicKey(MY_USERNAME))
                        # INSERT data into the table

                        cur = connectMydb(MY_USERNAME)
                        query = f'''SELECT COALESCE(MAX(messageId),0) FROM "{OTHER_USERNAME}";'''
                        cur.execute(query)
                        maxId = cur.fetchall()[0][0] + 1

                        # encrypted is of form b'' so enclose in double quotes

                        # 3 replacing a quote by 2 makes it escape hence complete ould be identified by postgres as string

                        # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
                        jsonData = json.dumps({'userMessage': f"{encrypted_message}", 'sender': f"{MY_USERNAME}", 'fernetKey': f"{encrypted_key}",
                                              'receiver': f"{OTHER_USERNAME}", 'isGroup': isGroup, 'isAck': False})

                        serverId, port = proxy.getFreeServerId()
                        client_sockets[serverId].send(
                            bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))

                        encrypted_message = str(encrypted_message)
                        encrypted_message = encrypted_message.replace(
                            "\'", "\'\'")
                        encrypted_message = encrypted_message.replace(
                            "\"", "\"\"")

                        encrypted_key = str(encrypted_key)
                        encrypted_key = encrypted_key.replace("\'", "\'\'")
                        encrypted_key = encrypted_key.replace("\"", "\"\"")

                        encrypt_for_me = str(encrypt_for_me)
                        encrypt_for_me = encrypt_for_me.replace("\'", "\'\'")
                        encrypt_for_me = encrypt_for_me.replace("\"", "\"\"")

                        query = f'''INSERT INTO "{OTHER_USERNAME}"
                                    VALUES('{MY_USERNAME}', '{encrypted_message}', {maxId}, '{encrypt_for_me}');'''
                        cur.execute(query)

                        #
                        query = f'''UPDATE connections SET readUpto = {maxId} WHERE username = '{OTHER_USERNAME}';'''
                        cur.execute(query)

        except IOError as e:
            # This is normal on non blocking connections - when there are no incoming data, error is going to be raised
            # Some operating systems will indicate that using AGAIN, and some using WOULDBLOCK error code
            # We are going to check for both - if one of them - that's expected, means no incoming data, continue as normal
            # If we got different error code - something happened
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print('Reading error2: {}'.format(str(e)))
                sys.exit()
            # We just did not receive anything
            continue

        except Exception as e:
            # Any other exception - something happened, exit
            print('Reading error1: {}'.format(str(e)))
            sys.exit()
