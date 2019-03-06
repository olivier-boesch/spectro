from decimal import Decimal
from math import pow

def step_data(rawval, step):
    val = step * (rawval // float(step))
    if (rawval > 0.) and (abs(rawval) % float(step) > (step/2.0)):
        val += step
    elif (rawval < 0.) and (abs(rawval) % float(step) < (step/2.0)):
        val += step
    return val

def fexp(number):
    (sign, digits, exponent) = Decimal(number).as_tuple()
    return len(digits) + exponent - 1

def fman(number):
    return float(Decimal(number).scaleb(-fexp(number)).normalize())
    
def get_bounds_and_ticks(minval, maxval, nticks):
    # amplitude of data
    amp = maxval - minval
    # basic tick
    basictick = fman(amp/float(nticks))
    # correct basic tick to 1,2,5 as mantissa
    tickpower = pow(10.0,fexp(amp/float(nticks)))
    if basictick < 1.5:
        tick = 1.0*tickpower
        suggested_minor_tick = 4
    elif basictick >= 1.5 and basictick < 2.5:
        tick = 2.0*tickpower
        suggested_minor_tick = 4
    elif basictick >= 2.5 and basictick < 7.5:
        tick = 5.0*tickpower
        suggested_minor_tick = 5
    elif basictick >= 7.5:
        tick = 10.0*tickpower
        suggested_minor_tick = 4
    # calculate good (rounded) min and max
    goodmin = tick * (minval // tick)
    goodmax = tick * (maxval // tick +1)
    return goodmin, goodmax, tick, suggested_minor_tick
    
if __name__ == "__main__":
    import random
    minval = -37
    maxval = -11
    N = 20
    data = [random.uniform(minval,maxval) for i in range(N)]
    min_data = min(data)
    max_data = max(data)
    m,M,t,mt = get_bounds_and_ticks(min_data, max_data, 10)
    
    print(min_data, max_data)
    print(m, M, t, mt)

    step = 5
    print(N,"values from",minval,"to",maxval,"step:",step)
    for it in [random.uniform(minval,maxval) for i in range(N)]:
        print(it,"->",step_data(it,step))