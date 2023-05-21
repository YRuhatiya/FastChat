# README

### Features implemented so far

1. Single server multiple client communication
2. Server-side and client-side PostgreSQL databases
3. Login and Signup at the start of a session. Storing passwords as a hash
4. Online/Offline status of clients
5. Group and Direct Messaging options for communicating images and text
6. Create group, add user to a group, remove user from a group
7. Storing unacknowledged messages on the server-side database, and delivering them when the client comes online again
8. Deleting pending messages after a predetermined duration
9. Server load balancing strategies: random, round-robin, memory-based, and CPU-based
10. E2E encryption in both personal and group chats

### Technology used

- Python
- socket library
- open source libraries for authentication and communication
- PostgreSQL
- XMLRPC, BCrypt, Select, Threading, pwntools libraries for Python
- bash for scripting and collecting results

### Running Instructions

On server system: python3 server.py IP PORT, python3 loadBalancer.py IP PORT NUM_SERVERS RPC_PORT
On client side: python3 interface.py IP PORT RPC_PORT

### Resources

[Client](https://pythonprogramming.net/client-chatroom-sockets-tutorial-python-3/)
[Server](https://pythonprogramming.net/server-chatroom-sockets-tutorial-python-3/)

### Member Contributions

**Aryan Mathe**: Ideation of interface and program logic, database design, actively writing the python code, code review <br>
**Yashwanth Reddy Challa**: Code documentation, database design, preparing presentation and flowcharts, ideation of interface and program logic, code review <br>
**Yash Ruhatiya**: Database design, ideation of interface and program logic, actively writing python code, code review <br>
