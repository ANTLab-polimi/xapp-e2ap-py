import src.e2ap_xapp as e2ap_xapp
from ran_messages_pb2 import *
from time import sleep,time
from ricxappframe.e2ap.asn1 import IndicationMsg
from math import ceil

import cvxpy as cp
import numpy as np
import signal
import csv
import sys

NO_UE_SLEEP_INTERVAL_S = 1
LOOP_SLEEP_INTERVAL_S = 2
MAX_PRB_DL = 106
USE_BS_THR = True

UE1_WEIGHT = 0.1
UE2_WEIGHT = 1
UE3_WEIGHT = 2
UE4_WEIGHT = 0.1
UE5_WEIGHT = 0.1
UE6_WEIGHT = 0.1
UE7_WEIGHT = 0.1
UE8_WEIGHT = 0.1


UE1_GBR_MBPS = 15
UE2_GBR_MBPS = 15
UE3_GBR_MBPS = 20
UE4_GBR_MBPS = 10
UE5_GBR_MBPS = 10
UE6_GBR_MBPS = 10
UE7_GBR_MBPS = 10
UE8_GBR_MBPS = 10

UE1_IS_GBR = True
UE2_IS_GBR = True
UE3_IS_GBR = True
UE4_IS_GBR = True
UE5_IS_GBR = True
UE6_IS_GBR = True
UE7_IS_GBR = True
UE8_IS_GBR = True

ue_gbr_weights = [UE1_WEIGHT, UE2_WEIGHT, UE3_WEIGHT, UE4_WEIGHT, UE5_WEIGHT, UE6_WEIGHT, UE7_WEIGHT, UE8_WEIGHT]
ue_gbr_mbps_info = [UE1_GBR_MBPS, UE2_GBR_MBPS, UE3_GBR_MBPS, UE4_GBR_MBPS, UE5_GBR_MBPS, UE6_GBR_MBPS, UE7_GBR_MBPS, UE8_GBR_MBPS]
ue_needs_gbr_mask = [UE1_IS_GBR, UE2_IS_GBR, UE3_IS_GBR, UE4_IS_GBR, UE5_IS_GBR, UE6_IS_GBR, UE7_IS_GBR, UE8_IS_GBR]

ue1_data = []
ue2_data = []
ue3_data = []
ue4_data = []

ue_data = [ue1_data, ue2_data, ue3_data, ue4_data]
CORR_F = 1.3

def write_to_csv():
    """Write data to a CSV file"""
    if not ue_data:
        return
    for idx, ued in enumerate(ue_data):
        filename = "data{}.csv".format(idx)
        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "THR", "ISGBR"])  # Add header if needed
            for timestamp, thr, isgbr in ued:
                writer.writerow([timestamp, thr, isgbr])

def signal_handler(sig, frame):
    """Signal handler for capturing Ctrl-C (SIGINT)"""
    print("\nSaving data to CSV and exiting gracefully...")
    write_to_csv()
    print("done")
    sys.exit(0)

ue_weights = {}

def xappLogic():

    # instanciate xapp 
    connector = e2ap_xapp.e2apXapp()
    try:
        signal.signal(signal.SIGINT, signal_handler)
        # get gnbs connected to RIC
        gnb_id_list = connector.get_gnb_id_list()
        print("{} gNB connected to RIC, listing:".format(len(gnb_id_list)))
        for gnb_id in gnb_id_list:
            print(gnb_id)
        print("---------")

        print("Setting max PRB DL to {}".format(MAX_PRB_DL))
        set_gnb_max_dl_prb(connector, MAX_PRB_DL, gnb_id)

        iteration = 0

        while True:

            # tic
            tic = time()

            iteration += 1
            print("xApp Iteration {}".format(iteration))

            # het ue info list from gnb
            ue_info_list = request_ue_info_list(connector,gnb_id_list)

            # check if there's any ue connected
            if len(ue_info_list) == 0:
                print("\t---------")
                print("\tNo ues connected, sleeping {}s".format(NO_UE_SLEEP_INTERVAL_S))
                print("")
                sleep(NO_UE_SLEEP_INTERVAL_S)
                continue
        
            ues_to_change = list()
            ue_required_prb_gbr = {}
            ue_required_tbs_gbr = {}
            ue_tbs_per_prb_dl = {}

            # loop ues and check if any must be set to GBR or not set to GBR, but don't set TBS yet
            for idx, ue in enumerate(ue_info_list):
                #if USE_BS_THR:
                #    ue.tbs_avg_dl = ue.tbs_avg_dl * 1e3
                print("\tUE {} - isGBR {} - THR {} - SLA {} - Bsize {}"
                      .format(ue.rnti,ue.is_GBR,round((ue.tbs_avg_dl*8)/1e3,2),ue_gbr_mbps_info[idx],ue.dl_mac_buffer_occupation))
                ue_data[idx].append((time(), round((ue.tbs_avg_dl*8)/1e3,2),ue.is_GBR))
                
                ue_weights[ue.rnti] = ue_gbr_weights[idx]

                ue_tbs_per_prb_dl[ue.rnti] = ue.avg_tbs_per_prb_dl
                if not ue_needs_gbr_mask[idx]:
                    print("\tskipping because no SLA set for this ue")
                    continue

                if ue.is_GBR:
                    # if ue is gbr then we check if it is making traffic by checking the buffer occupation
                    if ue.dl_mac_buffer_occupation < 1:
                        # this ue does not need gbr anymore
                        print("\t\tdoes not requires GBR anymore")
                        this_ue = ue_info_m()
                        this_ue.rnti = ue.rnti
                        this_ue.is_GBR = False
                        ues_to_change.append(this_ue)
                    else:
                        # this ue still requires gbr, so we need to compute the new tbs
                        print("\t\tstill requires GBR")
                        this_ue = ue_info_m()
                        this_ue.rnti = ue.rnti
                        this_ue.is_GBR = True
                        ues_to_change.append(this_ue)
                        gbr_tbs = (ue_gbr_mbps_info[idx]/8)*1e3
                        ue_required_tbs_gbr[ue.rnti] = gbr_tbs*CORR_F
                        ue_required_prb_gbr[ue.rnti] = (gbr_tbs*CORR_F)/ue.avg_tbs_per_prb_dl
                        print("\t\t{} PRBs are required for this ue".format(ceil(gbr_tbs/ue.avg_tbs_per_prb_dl)))
                    continue

                # now check if the the bu is high, if the ue is not gbr and if the thr is lowe than its gbr
                # because in that case the ue has to be made gbr
                if ue.dl_mac_buffer_occupation > 100:
                    # compute tp from tbs
                    thr = (ue.tbs_avg_dl*8)/1e3
                    if thr < UE1_GBR_MBPS:
                        # this ue requires gbr
                        print("\t\tnow requires GBR because throughput is below SLA")
                        print("\t\t Thrp. {} Mbps - SLA {} Mbps".format(round(thr), round(ue_gbr_mbps_info[idx])))
                        this_ue = ue_info_m()
                        this_ue.rnti = ue.rnti
                        this_ue.is_GBR = True
                        ues_to_change.append(this_ue)

                        # we also compute how many prbs are required to guarantee the gbr
                        gbr_tbs = (ue_gbr_mbps_info[idx]/8)*1e3
                        ue_required_tbs_gbr[ue.rnti] = gbr_tbs*CORR_F
                        ue_required_prb_gbr[ue.rnti] = (gbr_tbs*CORR_F)/ue.avg_tbs_per_prb_dl
                        print("\t\t{} PRBs are required for this ue".format(ceil(gbr_tbs/ue.avg_tbs_per_prb_dl)))
                        print("")
                        continue
                else:
                    print("\t\tdoes not require any action")
            # trailing print
            print("\t-----------\n")

            # now check if there is a new allocation to be enforced in the gnb and allocate
            if ue_required_prb_gbr:
                print("\tAllocating resources")
                print("")
                tot_req_prbs = ceil(sum(ue_required_prb_gbr.values()))
                print("\t\t{} PRBs are required to satisfy all the GBR users".format(tot_req_prbs))
                if tot_req_prbs <= MAX_PRB_DL:
                    print("\t\t {} PRBs are available in the gNB, reserving SPS without contention".format(MAX_PRB_DL))
                    for ue_m in ues_to_change:
                        if ue_m.is_GBR:
                            ue_m.tbs_dl_toapply = ue_required_tbs_gbr[ue_m.rnti]
                            ue_m.tbs_ul_toapply = (5/8)*1e3 # hardcoding gbr 5mbps in ul
                else: 
                    print("\t\t {} PRBs are available in the gNB, resource contention required".format(MAX_PRB_DL))
                    if len(ue_required_tbs_gbr) == 1 and ues_to_change[0].is_GBR:
                        print("\t\tUE {} is alone, assigning all the available resources".format(ues_to_change[0].rnti))
                        ues_to_change[0].tbs_dl_toapply = ue_required_tbs_gbr[ues_to_change[0].rnti]
                        ues_to_change[0].tbs_ul_toapply = (5/8)*1e3 # hardcoding gbr 5mbps in ul
                    else:
                        # build ues optimization objects
                        opti_ues = {}
                        for ue_i in range(0,len(ues_to_change)):
                            ue_m = ues_to_change[ue_i]
                            if ue_m.is_GBR:
                                opti_ues[ue_m.rnti] = Ue(id=ue_m.rnti, weight=ue_required_prb_gbr[ue_m.rnti], control_mess=ue_m, value=ue_weights[ue_m.rnti])
                                #ue_m.tbs_dl_toapply = ue_required_tbs_gbr[ue_m.rnti] * ue_gbr_weights[ue_i]
                                #ue_m.tbs_ul_toapply = (5/8)*1e3 # hardcoding gbr 5mbps in ul
                                #print("\t\t Assigning TBS {} to UE {}".format(round(ue_m.tbs_dl_toapply),ue_m.rnti))
                        # build cvx problem
                        
                        constraint = [sum(ue.scheduled * ue.weight for ue in opti_ues.values()) <= MAX_PRB_DL]
                        objective = cp.Maximize(sum(ue.value * ue.scheduled for ue in opti_ues.values()))
                        prob = cp.Problem(objective, constraint)
                        prob.solve()
                        print("\t\t building and solving problem")
                        print("\t\t {}".format(prob))
                        for ue in opti_ues.values():
                            print(ue.scheduled.value)
                        rem_prbs = MAX_PRB_DL
                        for ue_i in range(0,len(ues_to_change)):
                            ue_m = ues_to_change[ue_i]
                            if ue_m.is_GBR:
                                if opti_ues[ue_m.rnti].scheduled.value:
                                    ue_m.tbs_dl_toapply = ue_required_tbs_gbr[ue_m.rnti]
                                    ue_m.tbs_ul_toapply = (5/8)*1e3 # hardcoding gbr 5mbps in ul
                                    print("\t\t Assigning TBS {} to UE {}".format(round(ue_m.tbs_dl_toapply),ue_m.rnti))
                                    rem_prbs = rem_prbs - opti_ues[ue_m.rnti].weight
                                else:
                                    print("\t\tUE {} cannot be scheduled as GBR".format(ue_m.rnti))
                                    ue_m.is_GBR = False

            # now finally build control message and send, but only if there is any ue to change
            if ues_to_change:
                print("\t........")
                print("\tSending control request to change {} UEs".format(len(ues_to_change)))
                master_mess = RAN_message()
                master_mess.msg_type = RAN_message_type.CONTROL
                inner_mess = RAN_control_request()

                # ue list map entry
                ue_list_control_element = RAN_param_map_entry()
                ue_list_control_element.key = RAN_parameter.UE_LIST

                # ue list message 
                ue_list_message = ue_list_m()
                ue_list_message.connected_ues = len(ues_to_change)

                ue_list_message.ue_info.extend(ues_to_change)
                ue_list_control_element.ue_list.CopyFrom(ue_list_message)

                inner_mess.target_param_map.extend([ue_list_control_element])
                master_mess.ran_control_request.CopyFrom(inner_mess)
                # print(master_mess)
                buf = master_mess.SerializeToString()
                connector.send_e2ap_control_request(buf,gnb_id)
            toc = time()
            elapsed = toc-tic
            print("This iteration took {} ms".format(elapsed * 1000))
            print("\n\n")
            if elapsed <= LOOP_SLEEP_INTERVAL_S:
                print("Sleeping for {}".format(LOOP_SLEEP_INTERVAL_S - elapsed))
                sleep(LOOP_SLEEP_INTERVAL_S - elapsed)
    except KeyboardInterrupt:  # In case Ctrl-C is pressed
        signal_handler(signal.SIGINT, None) 

def e2sm_report_request_buffer():
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.UE_LIST])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    return buf

def request_ue_info_list(connector,gnb_id_list):
    buf = e2sm_report_request_buffer()

    for gnb in gnb_id_list:
        connector.send_e2ap_control_request(buf,gnb)

    # receive and parse
    ue_info_list = list()
    messgs = connector.get_queued_rx_message()
    if len(messgs) == 0:
        return ue_info_list
    
    for msg in messgs:
        if msg["message type"] == connector.RIC_IND_RMR_ID:
            print_debug("RIC Indication received from gNB {}, decoding E2SM payload".format(msg["meid"]))
            indm = IndicationMsg()
            indm.decode(msg["payload"])
            ran_ind_resp = RAN_indication_response()
            ran_ind_resp.ParseFromString(indm.indication_message)
            for entry in ran_ind_resp.param_map:
                if entry.key == RAN_parameter.UE_LIST:
                # print("connected ues {}".format( entry.ue_list.connected_ues))
                    if entry.ue_list.connected_ues > 0:
                        for ue_i in range(0,entry.ue_list.connected_ues):
                            # print(ue_i)
                            ue_info_list.append(entry.ue_list.ue_info[ue_i])
        else:
            print("Unrecognized E2AP message received from gNB {}".format(msg["meid"]))
    return ue_info_list

def set_gnb_max_dl_prb(connector, max_prb: int,gnb_id):
    if max_prb > 0:
        master_mess = RAN_message()
        master_mess.msg_type = RAN_message_type.CONTROL
        inner_mess = RAN_control_request()

        
        control_element = RAN_param_map_entry()
        control_element.key = RAN_parameter.MAX_PRB
        control_element.int64_value = max_prb

        inner_mess.target_param_map.extend([control_element])
        master_mess.ran_control_request.CopyFrom(inner_mess)
        buf = master_mess.SerializeToString()
        connector.send_e2ap_control_request(buf,gnb_id)

def print_debug(s: str):
    DEBUG_LOGS = False
    if DEBUG_LOGS:
        print(str)

class Ue(object): 
    def __init__(self,id,weight, control_mess,value) -> None:
        self.scheduled=cp.Variable(name="{}.scheduled".format(id), boolean=True)
        self.id = id
        self.weight = weight
        self.control_mess = control_mess
        self.value = value


if __name__ == "__main__":
    xappLogic()
