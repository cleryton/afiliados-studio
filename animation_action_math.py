"""Small motion primitives with measurable contact and reach constraints."""
import math


def ease(value):
    value=max(0.,min(1.,value))
    return value*value*(3-2*value)


def leg_angles(y,z,upper=.51,lower=.53):
    distance=math.hypot(y,z)
    if not abs(upper-lower)<distance<=upper+lower+1e-7:
        raise ValueError('Foot target is outside the leg reach.')
    cosine=max(-1.,min(1.,(distance*distance-upper*upper-lower*lower)/(2*upper*lower)))
    knee=math.acos(cosine)
    hip=math.atan2(y,-z)-math.atan2(lower*math.sin(knee),upper+lower*math.cos(knee))
    return hip,knee


def walk_y(time,speed=.34,stop=3.6):
    return .25+speed*min(stop,max(0.,time))


def step_target(time,phase,period=1.2):
    # Finish the trailing foot's final swing, then settle both feet at arrival.
    if time>=3.6+period*.5:return walk_y(3.6),0.,True
    cycle=math.floor((time+phase)/period)
    progress=((time+phase)/period)-cycle
    start=cycle*period-phase
    planted=walk_y(start+period*.25)
    if progress<.5:
        return planted,0.,True
    swing=(progress-.5)*2
    target=walk_y(start+period*1.25)
    return planted+(target-planted)*ease(swing),.115*math.sin(math.pi*swing),False
