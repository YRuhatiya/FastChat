from datetime import datetime, timedelta


def latency():
    """Latency in seconds by average of differences between send time and receive time

    :return: the latency in seconds
    :rtype: float
    """
    sent = open("sent_logs.txt", "r")
    received = open("received_logs.txt", "r")

    delta = 0

    slist = sent.readlines()
    rlist = received.readlines()

    for i in range(len(slist)):
        t1 = datetime.strptime(slist[i].strip('\n'), "%H:%M:%S")
        t2 = datetime.strptime(rlist[i].strip('\n'), "%H:%M:%S")
        delta = delta + (t2-t1).total_seconds()

    return float(delta)/len(slist)


def throughput(t):
    """Throughput by average messages sent/received in total time

    :param [t]: interval-width
    :type [t]: float
    :return: the throughputs in messages/second
    :rtype: float,float
    """
    sent = open("sent_logs.txt", "r")
    received = open("received_logs.txt", "r")

    input_throughput = 0
    output_throughput = 0

    slist2 = sent.readlines()
    rlist2 = received.readlines()

    slist = [datetime.strptime(i.strip('\n'), "%H:%M:%S") for i in slist2]
    rlist = [datetime.strptime(i.strip('\n'), "%H:%M:%S") for i in rlist2]

    start = max(rlist[0], slist[0])
    duration = min(rlist[len(rlist)-1], slist[len(slist)-1]) - start
    num_intervals = -1

    i = duration.total_seconds()

    while i > 0:
        i = i-t
        num_intervals = num_intervals + 1

    for i in range(num_intervals):
        st = start + timedelta(i*t)
        en = start + timedelta((i+1)*t)
        list_in = []
        list_out = []
        for j in slist:
            if (j > st and j < en):
                list_in.append(j)
        for j in rlist:
            if (j > st and j < en):
                list_out.append(j)
        input_throughput = input_throughput + len(list_in)
        output_throughput = output_throughput + len(list_out)

    input_throughput = float(input_throughput)/(num_intervals*t)
    output_throughput = float(output_throughput)/(num_intervals*t)

    return input_throughput, output_throughput
