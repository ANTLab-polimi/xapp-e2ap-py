import src.e2ap_xapp as hwxappp


def launchXapp():
    hwxapp = hwxappp.HWXapp()
    hwxapp.start()


if __name__ == "__main__":

    print(__package__)
    print("pd")
    launchXapp()
