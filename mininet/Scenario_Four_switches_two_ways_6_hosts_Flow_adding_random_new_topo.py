from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from thread import start_new_thread
import random
import os, stat
import json
import time
import copy
import csv
import requests
import sys
sys.path.append("...")
sys.path.append("..")
sys.path.append("../controller")
sys.path.append(".")
print(os.getcwd())
print(sys.path.__str__())
from config import Config


#             s2
#  h11   14ms/     \14ms    h41
#     -- s1          s4 --
#  h13    10ms\     /10ms   h43
#             s3

###################################################################
####### Scenario - 6 Hosts (adding flows, new topo)    ############
###################################################################

def reset_load_level(loadLevel):
    requests.put('http://0.0.0.0:8080/simpleswitch/params/load_level', data=json.dumps({"load_level": loadLevel}))
    requests.put('http://0.0.0.0:8080/simpleswitch/params/reset_flag', data=json.dumps({"reset_flag": True}))

def reset_iteration(iteration):
    requests.put('http://0.0.0.0:8080/simpleswitch/params/iteration', data=json.dumps({"iteration": iteration}))
    requests.put('http://0.0.0.0:8080/simpleswitch/params/iteration_flag', data=json.dumps({"iteration_flag": True}))

def stop_controller():
    requests.put('http://0.0.0.0:8080/simpleswitch/params/stop_flag', data=json.dumps({"stop_flag": True}))

def startIperf(host1, host2, amount, port, timeTotal, loadLevel):
    #host2.cmd("iperf -s -u -p {} &".format(port))
    bw = float(amount) * (float(loadLevel) / float(10))
    print("Host {} to Host {} Bw: {}".format(host1.name, host2.name, bw))
    command = "iperf -c {} -u -p {} -t {} -b {}M &".format(host2.IP(), port, timeTotal, bw)
    host1.cmd(command)

def write_in_File(fileName, logs, loadlevel, iteration_split_up_flag, iteration):
    dir = logs + '/'
    if iteration_split_up_flag:
        dir = dir + str(iteration) + '/'
    with open('{}{}.csv'.format(dir, fileName), 'a') as csvfile:
        fileWriter = csv.writer(csvfile, delimiter=',')
        fileWriter.writerow([loadlevel, time.time()])

def clearingSaveFile(fileName, logs):
    dir = logs + '/'
    with open('{}{}.csv'.format(dir, fileName), 'w') as file:
        file.write("# loadlevel, timestamp \n")

def clearingSaveFileIterations(fileName, logs, iterations):
    # cleans it all up
    for iteration in range(iterations):
        dir = logs + '/' + str(iteration) + '/'
        if not os.path.exists(dir):
            os.makedirs(dir)
            # give folder rights
            os.chmod(dir, stat.S_IRWXO)
        with open('{}{}.csv'.format(dir, fileName), 'w') as file:
            file.write("# loadlevel, timestamp \n")

def minToSec(min):
    return min * 60

def four_switches_network():
    net = Mininet(topo=None,
                  build=False,
                  ipBase='10.0.0.0/8', link=TCLink)

    queue_lenght = Config.queue_lenght

    bw_max_dict = Config.bw_max_dict

    # linkarray
    linkArray = []
    splitUpLoadLevelsFlag = Config.split_up_load_levels_flag
    logs = Config.log_path
    # importante! the load levels for measurements
    loadLevels = Config.load_levels
    print("LoadLevel: {}".format(loadLevels))
    timeTotal = minToSec(Config.duration_iperf_per_load_level_minutes)
    controllerIP = '127.0.0.1'
    fileName = 'timestamp_changing_load_levels_mininet'
    info('*** Adding controller\n')
    c0 = net.addController(name='c0',
                           controller=RemoteController,
                           ip=controllerIP,
                           protocol='tcp',
                           port=6633)

    info('*** Add switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)
    s4 = net.addSwitch('s4', cls=OVSKernelSwitch)

    info( '*** Add hosts\n')
    h11 = net.addHost('h11', cls=Host, ip='10.0.0.11', defaultRoute=None)
    h12 = net.addHost('h12', cls=Host, ip='10.0.0.12', defaultRoute=None)
    h13 = net.addHost('h13', cls=Host, ip='10.0.0.13', defaultRoute=None)

    h41 = net.addHost('h41', cls=Host, ip='10.0.0.41', defaultRoute=None)
    h42 = net.addHost('h42', cls=Host, ip='10.0.0.42', defaultRoute=None)
    h43 = net.addHost('h43', cls=Host, ip='10.0.0.43', defaultRoute=None)

    info('*** Add links\n')
    linkArray.append(net.addLink(s1, s2, delay='10ms', bw=4, max_queue_size=queue_lenght))
    linkArray.append(net.addLink(s2, s4, delay='10ms', bw=4, max_queue_size=queue_lenght))
    linkArray.append(net.addLink(s1, s3, delay='14ms', bw=3, max_queue_size=queue_lenght))
    linkArray.append(net.addLink(s3, s4, delay='14ms', bw=3, max_queue_size=queue_lenght))

    net.addLink(h11, s1)
    net.addLink(h12, s1)
    net.addLink(h13, s1)

    net.addLink(h41, s4)
    net.addLink(h42, s4)
    net.addLink(h43, s4)

    info('*** Starting network\n')
    net.build()
    info('*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info('*** Starting switches\n')
    net.get('s1').start([c0])
    net.get('s2').start([c0])
    net.get('s3').start([c0])
    net.get('s4').start([c0])


    iterations = Config.iterations
    if iterations > 1:
        iteration_split_up_flag = True
    else:
        iteration_split_up_flag = False

    # erasing previous file
    if not splitUpLoadLevelsFlag:
        if iteration_split_up_flag:
            clearingSaveFileIterations(fileName, logs, iterations)
        else:
            clearingSaveFile(fileName, logs)

    # possible connections
    time.sleep(15)
    # incrementing the load
    clearingSaveFileIterations(fileName, logs, iterations)
    for iteration in range(iterations):
        i = 0
        flowArray = [[h11, h41, 2.75], [h12, h42, 1.75], [h13, h43, 1.75]]
        laterJoin = random.choice(flowArray)
        flowArray.remove(laterJoin)
        print(flowArray)

        for loadLevel in loadLevels:
            # iperf threads
            # if the load levels are not split up -> write the load level change
            if splitUpLoadLevelsFlag:
                reset_load_level(loadLevel)
            if not splitUpLoadLevelsFlag:
                write_in_File(fileName, logs, loadLevel, iteration_split_up_flag, iteration)
            # send load level
            print("(Re)starting iperf -- loadLevel:  {}".format(loadLevel))

            for flow in flowArray:
                start_new_thread(startIperf, (flow[0], flow[1], flow[2], 5001, timeTotal, loadLevel))
            if i > 0:
                start_new_thread(startIperf, (laterJoin[0], laterJoin[1], laterJoin[2], 5001, timeTotal, loadLevel))
            i = i + 1
            time.sleep(timeTotal)
            # waiting additional 2 sec to reset states

        # last load level past
        if not splitUpLoadLevelsFlag:
            write_in_File(fileName, logs, -1, iteration_split_up_flag, iteration)
        if iteration_split_up_flag and iteration < iterations - 1:
            reset_iteration(iteration + 1)
            time.sleep(1)
    stop_controller()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')

four_switches_network()