import src.e2ap_xapp as e2ap_xapp
from ran_messages_pb2 import *
from time import sleep
from ricxappframe.e2ap.asn1 import IndicationMsg

def xappLogic():

    # instanciate xapp 
    connector = e2ap_xapp.e2apXapp()

    # get gnbs connected to RIC
    gnb_id_list = connector.get_gnb_id_list()
    print("{} gNB connected to RIC, listing:".format(len(gnb_id_list)))
    for gnb_id in gnb_id_list:
        print(gnb_id)
    print("---------")

    # subscription requests
    for gnb in gnb_id_list:
        e2sm_buffer = e2sm_report_request_buffer()
        connector.send_e2ap_sub_request(e2sm_buffer,gnb)
    
    # read loop
    sleep_time = 4
    while True:
        print("Sleeping {}s...".format(sleep_time))
        sleep(sleep_time)
        messgs = connector.get_queued_rx_message()
        if len(messgs) == 0:
            print("{} messages received while waiting".format(len(messgs)))
            print("____")
        else:
            print("{} messages received while waiting, printing:".format(len(messgs)))
            for msg in messgs:
                if msg["message type"] == connector.RIC_IND_RMR_ID:
                    print("RIC Indication received from gNB {}, decoding E2SM payload".format(msg["meid"]))
                    indm = IndicationMsg()
                    indm.decode(msg["payload"])
                    resp = RAN_indication_response()
                    resp.ParseFromString(indm.indication_message)
                    print(resp)
                    print("___")
                else:
                    print("Unrecognized E2AP message received from gNB {}".format(msg["meid"]))

def e2sm_report_request_buffer():
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    return buf

if __name__ == "__main__":
    xappLogic()