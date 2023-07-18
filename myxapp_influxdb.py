import src.e2ap_xapp as e2ap_xapp
from ran_messages_pb2 import *
from time import sleep,time
from ricxappframe.e2ap.asn1 import IndicationMsg
from math import ceil

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


NO_UE_SLEEP_INTERVAL_S = 1
LOOP_SLEEP_INTERVAL_S = 1

def xappLogic():
	# configure influxdb
    bucket = "wineslab-xapp-demo"
    client = InfluxDBClient.from_config_file("influx-db-config.ini")
    print(client)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    # query_api = client.query_api()


	# instanciate xapp 
    connector = e2ap_xapp.e2apXapp()

    # get gnbs connected to RIC
    gnb_id_list = connector.get_gnb_id_list()
    print("{} gNB connected to RIC, listing:".format(len(gnb_id_list)))
    for gnb_id in gnb_id_list:
        print(gnb_id)
    print("---------")

    iteration = 0

    while True:
        iteration += 1
        print("xApp Iteration {}".format(iteration))

        # get ue info list from gnb
        ue_info_list = request_ue_info_list(connector, gnb_id_list)

        # check if there's any ue connected
        if len(ue_info_list) == 0:
            print("\t---------")
            print("\tNo ues connected, sleeping {}s".format(NO_UE_SLEEP_INTERVAL_S))
            print("")
            sleep(NO_UE_SLEEP_INTERVAL_S)
            continue

        for idx, ue in enumerate(ue_info_list):
        	print(ue)
        	try: 
	            rnti = ue.rnti
	            mcs = ue.mcs  # not sure if this is ok

	            p = Point("xapp-stats").tag("rnti", rnti).field("mcs", mcs)

	            print(p)
	            logging.info('Write to influxdb: ' + repr(p))
	            write_api.write(bucket=bucket, record=p)
	        
	        except:
	            print("Skip log, influxdb error")

        time.sleep(LOOP_SLEEP_INTERVAL_S)




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


def print_debug(s: str):
    DEBUG_LOGS = False
    if DEBUG_LOGS:
        print(str)

if __name__ == "__main__":
    xappLogic()