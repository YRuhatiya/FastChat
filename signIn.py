# from server import addNewUser,isValidPassword, checkUserName
from termcolor import colored
from client import goOnline
# from interface import IP, PORT


def handleSignIn(proxy, IP, PORT):
    """Handles sign-in requests

    :param [proxy]: proxy server for calls to checkUserName and isValidPassword
    :type [proxy]: ServerProxy
    :param [IP]: server IP
    :type [IP]: str
    :param [PORT]: server PORT
    :type [PORT]: int
    :return: username and the created socket
    :rtype: str, socket
    """
    userName = input("USER NAME: ")
    if (not proxy.checkUserName(userName)):
        print(colored("USER DOES NOT EXIST!!", 'yellow'))
        handleSignIn(proxy, IP, PORT)
    else:
        password = input("PASSWORD: ")
        with open('hello.txt', 'w') as f:
            f.write(userName)
            f.write(password)
        if (proxy.isValidPassword(userName, password)):
            print(colored("LOGIN SUCCESSFUL!!", 'yellow'))
            client_sockets, client_pending_sockets = goOnline(
                userName, IP, PORT)
        return userName, client_sockets, client_pending_sockets
