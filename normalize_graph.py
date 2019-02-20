from decimal import Decimal
from math import floor,ceil,isclose,remainder,pow

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
        ticks = 1.0*tickpower
        suggested_minor_tick = 4
    elif basictick >= 1.5 and basictick < 2.5:
        ticks = 2.0*tickpower
        suggested_minor_tick = 4
    elif basictick >= 2.5 and basictick < 7.5:
        ticks = 5.0*tickpower
        suggested_minor_tick = 5
    elif basictick >= 7.5:
        ticks = 10.0*tickpower
        suggested_minor_tick = 4
    # calculate good (rounded) min and max
    goodmin = floor(fman(minval - remainder(minval,ticks)))*pow(10,fexp(minval))
    if isclose(goodmin,0.0,abs_tol = 0.1) and goodmin > 0.0:
        goodmin = 0.0
    goodmax =fman(maxval + ticks)*pow(10,fexp(maxval))
    return goodmin, goodmax, ticks, suggested_minor_tick
    
       
if __name__ == '__main__':
    from random import uniform
    data = [uniform(452,533) for i in range(500)]
    maxdata = max(data)
    mindata = min(data)
    nticks = 20
    print(f"min: {mindata}; max: {maxdata}; num ticks: {nticks}")
    calcmin, calcmax, tick, minor = get_bounds_and_ticks(mindata,maxdata,nticks)
    print(f"calculated min: {calcmin}; calculated max: {calcmax}")
    print(f"tick: {tick} ; minor ticks: {minor}")