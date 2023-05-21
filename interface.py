# from colorama import init
from signIn import handleSignIn
from signUp import handleSignUp
from termcolor import colored
from client import addNewDM, getAllUsers, isInConnections
from DM import handleDM
# from handleGroup import handleGroup
from client import receive_message, unpack_message, createGroup, isAdminOfGroup, getPrivateKey, handlePendingMessages, sendAck
import xmlrpc.client as cl
import select
import sys
import json

RPC_PORT = int(sys.argv[3])
"""
The port of the RPC server.
"""  # pylint: disable=W0105

HEADER_LENGTH = 10
"""
In order to communicate large messages over a socket, they are broken into multiple smaller messages.
The first HEADER_LENGTH characters of the initial message inform the listener how many bytes of data to receive, so that they may stop listening once these many bytes have been received.
"""  # pylint: disable=W0105

if __name__ == '__main__':
    # IP Address of the server, taken as a command line argument
    IP = sys.argv[1]
    # The port of the server, taken as a command line argument
    PORT = int(sys.argv[2])

    # Initialize proxy server for remote calls
    proxy = cl.ServerProxy(f"http://{IP}:{RPC_PORT}/", allow_none=True)

    MY_USERNAME = ""

    IP = sys.argv[1]
    PORT = int(sys.argv[2])

    # Welcome to NawaabChat
    print(colored("        NAWAB CHAT", 'green'))
    print("===========================\n")

    # Options screen
    print(colored("OPTIONS", 'red'))
    print('1.', colored("SIGN IN", 'blue'))
    print('2.', colored("SIGN UP", 'blue'))
    print('3.', colored("EXIT", 'blue'))

    choice = input("\nType your choice: ")

    #############
    # IF USER MISTYPE HIS NAME THEN ON RETRYING THE SYSTEM EXITS ?? ---> ERROR
    #############
    while True:
        if (choice == '1'):
            MY_USERNAME, client_sockets, client_pending_sockets = handleSignIn(
                proxy, IP, PORT)
            # print(client_socket)
            break
        elif (choice == '2'):
            MY_USERNAME, client_sockets, client_pending_sockets = handleSignUp(
                proxy, IP, PORT)
            # print(client_socket)
            break
        elif (choice == '3'):
            sys.exit()
        else:
            continue

    # As happens in the whatsapp webapp
    print(colored("FETCHING PENDING MESSAGES... ", 'yellow'))
    serverId, port = proxy.getFreeServerId()
    print(colored("CONNECTED TO PROXY SERVER", 'yellow'))
    handlePendingMessages(client_pending_sockets[serverId], proxy)
    print(colored("UP TO DATE!", 'green'))

    # List of sockets from which input needs to be handled
    socket_list = client_sockets[0:]
    socket_list.append(sys.stdin)

    while True:
        print(colored("\nUSER OPTIONS", 'red'))
        print("------------")
        print('1.', colored("ADD USER", 'blue'))
        print('2.', colored("ADD USER TO A GROUP", 'blue'))
        print('3.', colored("CHAT", 'blue'))
        print('4.', colored("CREATE GROUP", 'blue'))
        print('5.', colored("REMOVE USER FROM GROUP", 'blue'))
        print('6.', colored("EXIT", 'blue'))

        print("\nType your choice: ")

        # selector module will handle all the sockets
        read_sockets, _, error_sockets = select.select(
            socket_list, [], socket_list)

        # read_sockets is the set of sockets that are pending to be read
        for iter_socket in read_sockets:
            if (iter_socket != sys.stdin):
                # server sent us a message
                # print("IN")
                # if(checkSocketReady(client_socket)):
                data = unpack_message(iter_socket)

                # this function receives the message and updates the database accordingly
                rec = receive_message(data, proxy)
                sendAck(iter_socket, data['messageId'], rec[4])
                # print("OUT")

            else:
                # stdin has input that needs to be read
                choice = sys.stdin.readline()[0:-1]
                # print(choice)
                if (choice == '1'):
                    username = input("Enter username to be added: ")
                    if (not isInConnections(MY_USERNAME, username)):
                        if (not addNewDM(MY_USERNAME, username, proxy)):
                            print(colored("INVALID USERNAME!!\n", 'yellow'))
                            continue
                        print(colored("SUCCESSFULLY ADDED!!", 'yellow'))
                        continue

                    print(colored("USER ALREADY CONNECTED!!", 'yellow'))
                    continue

                elif (choice == '2'):
                    grpName = input("ENTER GROUP NAME: ")
                    if (not proxy.checkUserName(grpName)):
                        print(colored("INVALID GROUP NAME!!", 'yellow'))
                    else:
                        if (isAdminOfGroup(grpName, MY_USERNAME)):
                            newuser = input("NEW PARTICIPANT: ")
                            if (proxy.checkUserName(newuser)):
                                if (not proxy.addUserToGroup(grpName, newuser)):
                                    # SENDING KEYWORD TO ADD THE GROUP TO THE NEW USER SIDE
                                    message = "ADD_PARTICIPANT"
                                    jsonData = json.dumps({'userMessage': f"{message}", 'sender': f"{MY_USERNAME}", 'receiver': f"{newuser}", 'fernetKey': 'NA',
                                                           'grpName': f"{grpName}", 'privateKey': getPrivateKey(grpName, MY_USERNAME), 'isGroup': False, 'isAck': False})

                                    serverId, port = proxy.getFreeServerId()
                                    client_sockets[serverId].send(
                                        bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))
                                else:
                                    print(
                                        colored("USER ALREADY IN THE GROUP!", 'yellow'))
                            else:
                                print(colored("USER DOESN'T EXIST!!", 'yellow'))
                        else:
                            print(
                                colored(f"ADMIN PRIVILEGES NOT AVAILABLE FOR GROUP:{grpName}", 'yellow'))
                    ## QUERY ABOUT THE ADMIN USER ##

                elif (choice == '3'):
                    print('1.', colored("LIST CONNECTIONS", 'green'))
                    print('2.', colored("SEARCH", 'green'))
                    print('3.', colored("BACK", 'green'))

                    DM, group = getAllUsers(MY_USERNAME)

                    chatWith = ""
                    choose = input("Choice: ")
                    if (choose == '3'):
                        break
                    if (choose == '1'):
                        print(colored("USERS", 'red'))
                        print("-----")
                        for i in DM:
                            print(colored(i, 'blue'))

                        print(colored("\nGROUP", 'red'))
                        print("-----")
                        for i in group:
                            print(colored(i, 'blue'))

                        chatWith = input(
                            "Enter name of the user to chat with: ")

                    elif (choose == '2'):
                        chatWith = input(
                            "Enter name of the user to chat with: ")

                    if (chatWith in DM):
                        print("----->")
                        handleDM(MY_USERNAME, chatWith,
                                 client_sockets, proxy, False)
                    elif (chatWith in group):
                        print("----->")
                        handleDM(MY_USERNAME, chatWith,
                                 client_sockets, proxy, True)
                        # handleGroup(MY_USERNAME, chatWith, client_socket, proxy)
                    else:
                        print(colored("INVALID USERNAME!", 'yellow'))
                        continue

                elif (choice == '4'):
                    grpName = input("ENTER GROUP NAME: ")
                    if (not proxy.checkUserName(grpName)):
                        createGroup(grpName, MY_USERNAME, proxy)
                        print(colored('GROUP SUCCESSFULLY CREATED!!', 'yellow'))
                    else:
                        print(colored("GROUP-NAME TAKEN!", 'yellow'))

                elif (choice == '5'):
                    grpName = input("ENTER GROUP NAME: ")
                    if (not proxy.checkUserName(grpName)):
                        print(colored("INVALID GROUP NAME!!", 'yellow'))
                    else:
                        if (isAdminOfGroup(grpName, MY_USERNAME)):
                            removeuser = input("PARTICIPANT TO BE REMOVED: ")
                            if (proxy.removeUserFromGroup(grpName, removeuser)):
                                message = "REMOVE_PARTICIPANT"
                                jsonData = json.dumps({'userMessage': f"{message}", 'sender': f"{MY_USERNAME}", 'fernetKey': 'NA',
                                                       'receiver': f"{removeuser}", 'grpName': f"{grpName}", 'isGroup': False, 'isAck': False})

                                serverId, port = proxy.getFreeServerId()
                                client_sockets[serverId].send(
                                    bytes(f'{len(jsonData):<10}{jsonData}', encoding='utf-8'))
                            else:
                                print(colored("USER NOT IN GROUP", 'yellow'))
                        else:
                            print(
                                colored(f"ADMIN PRIVILEGES NOT AVAILABLE FOR GROUP: {grpName}", 'yellow'))

                elif (choice == '6'):
                    sys.exit()

                else:
                    print(colored("INVALID OPTION!!", 'yellow'))
                    continue
