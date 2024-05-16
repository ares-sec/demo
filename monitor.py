from transitions import Machine
from typing import Callable
import time
from datetime import timedelta
import broker


class monitor(object):
    """
    """
    
    def __init__(self, name, description, active = False):
        self.name = name
        self.desc = description     
        self.active = active
        self.alert = False
        
    def activate(self, n=None):
        self.considered_node = n
        self.active = True

    def deactivate(self):
        self.active = False
    
    def print_alert(self, frame = None):
        self.alert = True
        if frame!=None:
            self.considered_node=frame.nodeID
        print(time.time())
        # try:
        #     print('[monitor {} - node {}] ALERTE "{}"'.format(self.name, self.considered_node, self.desc))
        # except:
        #     print('[monitor {}] ALERTE "{}"'.format(self.name, self.desc))
        
        
    def cond_true(self, var, frame):
        try:
            l=[]
            for cond in var:
                try:
                    res = frame.selector(*cond)
                except:
                    res=False
                l.append(res)
            return(all(l)) 
        except:
            return(frame.selector(*var))




###################################################

class never(monitor):

    def __init__(self, name, description, condition, active = False):
        super().__init__(name, description, active = active)
        self.e = condition

        
    def monitoring(self, frame):
        if self.active==True:
            if (frame.fcode==broker.Count(5)):
                self.print_alert(frame)
            #if frame.selector(*self.e):
            if self.cond_true(self.e, frame):
                self.print_alert(frame)



class whitelist(monitor):

    def __init__(self, name, description, condition, active = False):
        super().__init__(name, description, active = active)
        self.e = condition
        self.considered_node = None
     
    def monitoring(self, frame):
        if self.active==True:
            if frame.nodeID == self.considered_node:
                if self.cond_true(self.e, frame) == False:
                    self.print_alert(frame)
    


class periodicity(monitor):

    interval = range(95000, 105000)
    
    def __init__(self, name, description, condition, active = False):
        super().__init__(name, description, active = active)
        self.e = condition
        self.now = None
        self.timer = None
  
    def monitoring(self, frame):
        if (self.active==True and (time.time()-self.timer)>0.3):
            #print(time.time()-self.timer)
            if self.cond_true(self.e, frame):
                if (self.now == None):
                    self.now=frame.ts
                else:
                    delta = frame.ts-self.now
                    #print(delta.microseconds)
                    if (delta.microseconds not in self.interval): 
                        print(delta.microseconds)
                        self.print_alert(frame)
                    self.now = frame.ts
    
    def activate(self):
        #Need a tempo of 0.3sec before activating monitor
        self.timer=time.time()
        self.active = True
                
                


class position(monitor):

    borne_inf = {1 : [0x00, 0x04, 0x90, 0x00], 2 : [0x00, 0x03, 0xf0, 0x00]}
    borne_sup = {1 : [0xff, 0xff, 0xf0, 0x00], 2 : [0xff, 0xff, 0xf0, 0x00]}

    def __init__(self, name, description, condition, active = False):
        super().__init__(name, description, active = active)
        self.e = condition

    def monitoring(self, frame):
        if self.active==True:
            if self.cond_true(self.e, frame):
                res=frame.data[4:]
                res.reverse()
                if ((res>self.borne_inf[frame.nodeID]) and (res<self.borne_sup[frame.nodeID])):
                    self.print_alert(frame)                
           


class speed(monitor):

    neg_inf = [0xff, 0xff, 0xfb, 0xc8]
    neg_sup = [0xff, 0xff, 0xff, 0xa1]
    pos_inf = [0x00, 0x00, 0x00, 0x5f]
    pos_sup = [0x00, 0x00, 0x04, 0x19]
    imm_inf = [0xff, 0xff, 0xff, 0x97]
    imm_sup = [0x00, 0x00, 0x00, 0x69]

    def __init__(self, name, description, condition, active = False):
        super().__init__(name, description, active = active)
        self.e = condition

    def monitoring(self, frame):
        if (self.active==True and (time.time()-self.timer)>0.05):
            if self.cond_true(self.e, frame):
                res=frame.data[4:]
                res.reverse()
                #print(res)
                if not (self.neg_inf<res<self.neg_sup or self.pos_inf<res<self.pos_sup or self.imm_inf<res or res<self.imm_sup):
                    print(res)
                    self.print_alert(frame) 

    def activate(self):
        #Need a tempo of 0.05sec before activating monitor
        self.timer=time.time()
        self.active = True


###################################################


class BA_existence(monitor):

    # Define states.
    states = [
        { 'name': '0'},
        { 'name': '1', 'on_exit': ['prop_unsatisfied'], 'on_enter': ['prop_satisfied']},
        { 'name': 'forbidden', 'on_enter': ['print_alert']}
        ]

    # Define transitions.
    transitions = [
        {'trigger':'a', 'source':'0', 'dest':'1'},
        {'trigger':'a', 'source':'1', 'dest':'forbidden'},
        {'trigger':'a', 'source':'forbidden', 'dest': None},
        ]

    def __init__(self, name, description, cond_a, active = False):

        super().__init__(name, description, active = active)
        # Initialize the state machine
        self.machine = Machine(model=self, states=BA_existence.states, transitions=BA_existence.transitions, queued=True, initial='0')
        # Mapping
        self.cond_transition_a = cond_a
        # State of security pattern to monitor
        self.is_prop_satisfied = False


    def monitoring(self, frame):
        if self.active==True:
            if self.cond_true(self.cond_transition_a, frame):
                #print('transition a')
                self.trigger('a')
    

    def deactivate(self):
        self.active = False
        if self.verdict() == False:
            self.print_alert()
        #print('verdict', self.verdict())
        self.to_0()
 
    def prop_unsatisfied(self):
        self.is_prop_satisfied = False
    
    def prop_satisfied(self):
        self.is_prop_satisfied = True
    
    def verdict(self):
        return self.is_prop_satisfied





class BA_prec_and_resp(monitor):

    # Define states.
    states = [
        { 'name': '0', 'on_exit': ['prop_unsatisfied'], 'on_enter': ['prop_satisfied']},
        { 'name': '1', 'on_exit': ['stop_clock'], 'on_enter': ['start_clock']},
        { 'name': 'forbidden', 'on_enter': ['print_alert']}
        ]

    # Define transitions.
    # 'prepare' callback is executed as soon as a transition starts, before any 'conditions' are checked or other callbacks are executed.
    transitions = [
        {'trigger':'x', 'source':'0', 'dest':'1'},
        {'trigger':'y', 'source':'0', 'dest':'forbidden'},
        {'trigger':'x', 'source':'1', 'dest':'forbidden'},
        {'trigger':'y', 'source':'1', 'dest':'0'},
        {'trigger':'x', 'source':'forbidden', 'dest': None},
        {'trigger':'y', 'source':'forbidden', 'dest': '='}, #in order to print alerts every time state f is entered, put '=' instead of None
        ]

    def __init__(self, name, description, cond_x, cond_y, timeinterval=None, active=False):
    #def __init__(self, *args, cond_x, cond_y, timeinterval = None):
        
        super().__init__(name, description, active = active)
        
        # Initialize the state machine
        self.machine = Machine(model=self, states=BA_prec_and_resp.states, transitions=BA_prec_and_resp.transitions, queued=True, initial='0')
        # Mapping
        self.cond_transition_x = cond_x
        self.cond_transition_y = cond_y
        # Interval in ms
        self.inter = timeinterval
        # State of security pattern to monitor
        self.is_prop_satisfied = True
        # For timed transitions
        self.ts = None
        self.start_time = None


    def monitoring(self, frame):
        # if (self.ts is not None):
        #     print('delta ts', (getattr(frame, 'ts')-self.ts)/timedelta(milliseconds=1))
        #     print('delta temps', (time.time()-self.tempo)*1000)
        # self.tempo = time.time()
        self.ts = getattr(frame, 'ts')
        #print ('ts :', self.ts, 'time', time.time())
        if self.cond_true(self.cond_transition_x, frame):
            print('transition x', self.ts)
            self.trigger('x')
        if self.cond_true(self.cond_transition_y, frame):
            print('transition y', self.ts)
            self.trigger('y')

        if (self.start_time is not None and self.inter is not None):
            if (((self.ts - self.start_time)/timedelta(milliseconds=1))>self.inter[1]):
                print((self.ts - self.start_time)/timedelta(milliseconds=1))
                print('no response - go to forbidden state')
                self.to_forbidden()        
    

    def deactivate(self):
        self.active = False
        if self.verdict() == False:
            self.print_alert()
        #print('verdict', self.verdict())
        self.to_0()

    def prop_unsatisfied(self):
        self.is_prop_satisfied = False
    
    def prop_satisfied(self):
        self.is_prop_satisfied = True
    
    def verdict(self):
        return self.is_prop_satisfied

    @property
    def start_clock(self):
        self.start_time = self.ts
        #print('start clock . ts = ', self.start_time)

    def stop_clock(self):
        if self.inter is not None:
            if ((self.ts-self.start_time)/timedelta(milliseconds=1))<self.inter[0]:
                print('stop clock', (self.ts-self.start_time)/timedelta(milliseconds=1), 'ms')
                print('response not in interval - go to forbidden state')
                self.to_forbidden()
            else:
                #print('stop clock', (self.ts-self.start_time)/timedelta(milliseconds=1), 'ms')
                self.start_time = None





