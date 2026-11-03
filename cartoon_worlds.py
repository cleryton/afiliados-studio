"""Reusable original 2D characters with story-specific props and blocking."""
import math

from PIL import ImageDraw


def prop(d, kind, x, y, t, scale=1, accent='#e9be75'):
    from cartoon2d import INK, boat, font, oval, star
    s=scale
    p=lambda a,b:(x+a*s,y+b*s)
    if kind=='star':star(d,x,y,26*s,rotation=math.sin(t)*.2)
    elif kind in ('letter','card','map','recipe','ticket'):
        d.rounded_rectangle((*p(-31,-21),*p(31,21)),radius=max(1,int(4*s)),fill='#f5e5bd',outline=INK,width=2)
        if kind=='letter':d.line([p(-29,-19),p(0,3),p(29,-19)],fill='#b68872',width=2)
        else:
            for k in (-10,0,10):d.line([p(-20,k),p(18,k-2)],fill='#ad9780',width=2)
    elif kind in ('ball','pearl','marble'):
        oval(d,x,y,22*s,22*s,accent,INK)
        d.arc((*p(-16,-16),*p(16,16)),20,135,fill='#fff1c8',width=max(1,int(3*s)))
    elif kind in ('fish','feather','leaf'):
        oval(d,x,y,27*s,10*s,'#8eb7ac' if kind!='feather' else '#f2d6a3',INK)
        if kind=='fish':
            d.polygon([p(21,0),p(42,-15),p(42,15)],fill='#87b1ad',outline=INK)
            oval(d,*p(-16,-2),2*s,2*s,INK)
        else:d.line([p(-32,5),p(26,-3)],fill=INK,width=2)
    elif kind in ('bell','cup','bucket','pot'):
        d.polygon([p(-20,-20),p(20,-20),p(16,19),p(-16,19)],fill=accent,outline=INK)
        d.arc((*p(-28,-35),*p(28,9)),180,360,fill=INK,width=2)
        if kind=='bell':oval(d,x,y+22*s,5*s,5*s,INK)
    elif kind=='oar':
        d.line([p(-38,-15),p(21,8)],fill='#b99065',width=max(2,int(7*s)))
        d.polygon([p(17,-1),p(45,5),p(39,23),p(14,12)],fill='#d7b589',outline=INK)
    elif kind in ('key','spoon','brush'):
        oval(d,*p(-18,-5),12*s,12*s,accent,INK)
        d.line([p(-6,-5),p(33,-5)],fill=accent,width=max(2,int(8*s)))
        for dx in (17,29):d.line([p(dx,-5),p(dx,7)],fill=accent,width=max(2,int(6*s)))
    elif kind in ('bread','bun','cake','biscuit'):
        oval(d,x,y+12*s,40*s,9*s,'#ead6b5',INK)
        d.rounded_rectangle((*p(-32,-22),*p(32,12)),radius=max(1,int(16*s)),fill=accent,outline=INK,width=2)
        for dx in (-16,0,16):d.line([p(dx-3,-14),p(dx+2,-4)],fill='#ffe1a3',width=3)
    elif kind in ('book','box','radio','frame','mirror'):
        d.rounded_rectangle((*p(-29,-27),*p(29,27)),radius=max(1,int(5*s)),fill=accent,outline=INK,width=3)
        if kind in ('frame','mirror'):d.rectangle((*p(-20,-18),*p(20,18)),fill='#9ebfc4' if kind=='mirror' else '#ead2a9',outline=INK)
        elif kind=='radio':
            for dx in (-15,-6,3):d.line([p(dx,-13),p(dx,13)],fill=INK,width=2)
            oval(d,*p(18,8),4*s,4*s,INK)
        elif kind=='book':d.line([p(0,-25),p(0,24)],fill=INK,width=2)
        else:d.line([p(-27,-24),p(0,-6),p(27,-24)],fill=INK,width=2)
    elif kind in ('clock','compass'):
        oval(d,x,y,27*s,27*s,'#f1dbab',INK,3)
        d.line([p(0,-18),p(0,0),p(15,7)],fill=INK,width=3)
        for a in range(4):oval(d,x+math.cos(a*math.pi/2)*22*s,y+math.sin(a*math.pi/2)*22*s,2*s,2*s,INK)
    elif kind in ('flower','seed'):
        d.line([p(0,24),p(0,-17)],fill='#63886a',width=4)
        for a in range(5):
            angle=a*math.tau/5
            oval(d,x+math.cos(angle)*13*s,y-17*s+math.sin(angle)*13*s,10*s,10*s,accent)
        oval(d,x,y-17*s,7*s,7*s,'#e6c17e')
    elif kind in ('lantern','lighthouse'):
        d.rounded_rectangle((*p(-19,-23),*p(19,25)),radius=max(1,int(5*s)),fill='#edd795',outline=INK,width=3)
        d.line([p(-13,-27),p(0,-40),p(13,-27)],fill=INK,width=3)
        d.line([p(0,-20),p(0,22)],fill='#b99462',width=2)
        oval(d,x,y,4*s,7*s,'#fff4c6')
    elif kind=='boat':boat(d,x,y+6*s,.8*s)
    elif kind in ('umbrella','ribbon','scarf','kite','blanket'):
        d.polygon([p(-28,-20),p(0,-32),p(29,2),p(0,25)],fill=accent,outline=INK)
        d.line([p(0,-30),p(0,35)],fill=INK,width=2)
        if kind=='kite':d.line([p(0,25),p(12,44),p(-2,59)],fill=INK,width=2)
    else:
        d.rounded_rectangle((*p(-25,-21),*p(25,21)),radius=max(1,int(7*s)),fill=accent,outline=INK,width=2)


def draw(im,story,scene,u,t):
    from cartoon2d import INK, boat, cat, cloud, ease, lerp, oval, person, rain, robot
    d=ImageDraw.Draw(im);world=story['key'];action=story['actions'][scene]
    thing=story.get('props',[story['prop']]*6)[scene]
    accent=story['accent'];day=story.get('daytime',False)
    if world in ('cat','lighthouse'):
        for i in range(8):
            x=(i*83+t*17)%600-20;y=535+(i%3)*15+math.sin(t*2+i)*3
            d.arc((x,y,x+43,y+8),0,170,fill='#54778a',width=2)
        if not day:
            oval(d,437,226,28,28,'#d7e0dc');oval(d,449,218,26,26,'#192946' if world=='cat' else '#1a3048')
        boat(d,425+math.sin(t*.4)*25,565+math.sin(t*2)*3,.5)
    else:
        cloud(d,275+math.sin(t*.2)*20,225,.7,'#edf0dd')
    movement=ease(u)
    x=lerp(180,300,movement) if action in ('carry','walk','give') else 238+math.sin(t*1.1)*4
    y=675
    if action=='jump':y-=math.sin(u*math.pi)*85
    if world=='cat':cat(d,x,y,t,False,1.2)
    elif world=='robot':
        robot(d,x-62,691,t,.6 if action in ('find','show','give') else .15)
        person(d,411,735,t,'#cb867b',1,.5 if scene>=4 else .1)
    elif world=='umbrella':
        person(d,x-50,730,t,'#e38a75',1.1,.5,walking=action=='walk')
        if scene in (2,4,5):person(d,403,715,t+.8,'#7b9a9b',.92,.35)
        if thing=='umbrella':
            from cartoon2d import umbrella
            umbrella(d,x-40,480,t,1 if scene!=5 else .25)
    else:
        person(d,x,713,t,'#d3ac64',1,.7 if action in ('give','show') else .15,walking=action=='walk')
        if scene>=3:person(d,369,720,t+1,'#7ba4a8',.9,.5)
        if story.get('weather')=='rain' and scene<5:rain(d,t,amount=35)
    px,py=x+25,y-55
    if world=='robot':px,py=179,673
    if world=='umbrella':px,py=x+25,640
    if world=='lighthouse':px,py=x+37,632
    if action in ('show','find'):px,py=310,455+math.sin(t*2)*5
    elif action=='fall':px,py=lerp(315,365,movement),lerp(420,658,movement)
    elif action=='lift':px,py=lerp(x+20,300,movement),lerp(645,370,movement)
    elif action=='give':px=lerp(x+25,390,movement)
    elif action=='rest':px,py=365,695
    elif action=='hide':px,py=110,690
    elif action=='float':px,py=320+math.sin(t*1.2)*30,430+math.cos(t)*25
    elif action=='fix':px,py=300,595+math.sin(t*7)*3
    if thing!='umbrella' or world!='umbrella':prop(d,thing,px,py,t,1.3 if action in ('show','find') else 1,accent)
    if action in ('show','lift','fix'):
        for i in range(5):
            a=t+i*math.tau/5
            oval(d,px+math.cos(a)*54,py+math.sin(a)*50,2,2,accent)
    if story.get('secondary') and scene>=3:prop(d,story['secondary'],444,686,t,.7,accent)
    if scene==5:
        for i in range(4):
            yy=290+(i*37)%100+math.sin(t+i)*6
            oval(d,290+i*37,yy,2,2,accent)
