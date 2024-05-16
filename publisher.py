import broker
import datetime
from DISTRIBUTED.Monitoring.utils.utils import type_trame

ep1 = broker.Endpoint()
subscriber = ep1.make_subscriber("/robot1/mb_rdire")
ep1.peer("127.0.0.1", 9999)

ep2 = broker.Endpoint()
ep2.peer("10.10.101.18", 5890)

def main():	
    try:
        while True:
            if (subscriber.available()):
                (t,d) = subscriber.get()
                trace=type_trame(d)

                if (trace.stadd==18):
                    #print(trace.data)
                    print("%M44", trace.data[-1])
                    if (trace.data[-1] == True):
                        a1 = broker.zeek.Event("Pick_and_Place_Busy", trace.ts)
                        ep2.publish("/maxitest", a1)

    except KeyboardInterrupt:
        pass



if __name__ == "__main__":
    main()
