"""Original local 2D animation, narration and subtitles. No publishing actions."""
import argparse
from array import array
import bisect
from functools import lru_cache
import hashlib
import json
import math
import random
import re
import subprocess
from uuid import uuid4
import wave

from PIL import Image, ImageDraw

import core
import creative
from cartoon_catalog import STORIES, caption
from renderer import font as load_font, wrap

W, H, FPS = 540, 960, 24
INK = '#263644'
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


font = lru_cache(maxsize=32)(load_font)


def ease(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def lerp(a, b, value):
    return a + (b - a) * value


def oval(d, x, y, rx, ry, color, outline=None, width=2):
    d.ellipse((x-rx, y-ry, x+rx, y+ry), fill=color, outline=outline, width=width)


def star(d, x, y, radius, color='#ffe09a', rotation=0):
    points=[]
    for i in range(10):
        a=rotation + i*math.pi/5 - math.pi/2
        r=radius if i%2 == 0 else radius*.43
        points.append((x+math.cos(a)*r, y+math.sin(a)*r))
    d.polygon(points, fill=color)


def cloud(d, x, y, scale, color):
    for dx, dy, r in ((-34,0,26),(-8,-15,34),(29,-3,28),(3,8,34)):
        oval(d,x+dx*scale,y+dy*scale,r*scale,22*scale,color)


def boat(d, x, y, scale, color='#e5a267'):
    p=lambda a,b:(x+a*scale,y+b*scale)
    d.polygon([p(-40,0),p(45,0),p(28,20),p(-22,20)],fill=color)
    d.line([p(2,-66),p(2,1)],fill='#f1dec1',width=max(1,int(4*scale)))
    d.polygon([p(-3,-62),p(-3,-7),p(-35,-7)],fill='#f9eed8')
    d.polygon([p(8,-53),p(34,-12),p(8,-12)],fill='#e29f86')


def person(d, x, y, t, color='#e89063', scale=1, gesture=0, walking=False, smile=True):
    """Animated jointed silhouette; y is the ground contact, not head center."""
    s=scale
    p=lambda a,b:(x+a*s,y+b*s)
    width=max(2,int(9*s))
    stride=math.sin(t*6)*14 if walking else math.sin(t*1.3)*1.2
    d.line([p(-11,-48),p(-12-stride*.5,-24),p(-13-stride,0)],fill=INK,width=width)
    d.line([p(11,-48),p(12+stride*.5,-24),p(13+stride,0)],fill=INK,width=width)
    oval(d,x+(-16-stride)*s,y,10*s,4*s,INK)
    oval(d,x+(16+stride)*s,y,10*s,4*s,INK)
    bob=math.sin(t*3)*2
    d.rounded_rectangle((*p(-25,-116+bob),*p(25,-44+bob)),radius=int(14*s),fill=color,outline=INK,width=2)
    for side in (-1,1):
        wave=math.sin(t*3+side)*5
        hand_y=-64-gesture*35+wave
        d.line([p(side*23,-101+bob),p(side*(33+gesture*6),-82),p(side*(40+gesture*11),hand_y)],fill=color,width=width)
        oval(d,*p(side*(40+gesture*11),hand_y),6*s,6*s,'#f4c9a4')
    oval(d,*p(0,-144+bob),27*s,31*s,'#f4c9a4',INK)
    d.pieslice((*p(-28,-178+bob),*p(28,-127+bob)),180,355,fill=INK)
    blink=(t%4.1)<.11
    for dx in (-9,9):
        if blink:d.line([p(dx-3,-145+bob),p(dx+3,-145+bob)],fill=INK,width=2)
        else:oval(d,*p(dx,-145+bob),2.7*s,3.6*s,INK)
    mouth=(*p(-8,-139+bob),*p(8,-129+bob))
    d.arc(mouth,0 if smile else 180,180 if smile else 360,fill=INK,width=2)
    oval(d,*p(-18,-136+bob),5*s,2*s,'#e99887')


@lru_cache(maxsize=12)
def background(key, daytime=False):
    """Draw the scenery once; characters, props, light and weather move per frame."""
    sky={'cat':'#192946','robot':'#f2e3ce','umbrella':'#cde6e0','lighthouse':'#1a3048'}[key]
    if daytime and key=='cat':sky='#a8d3d7'
    im=Image.new('RGB',(W,H),sky);d=ImageDraw.Draw(im)
    if key in ('cat','lighthouse'):
        d.rectangle((0,480,W,H),fill='#274b63' if daytime else '#183c55')
        for i in range(9):
            x=i*66-20;top=365+(i*37)%95
            d.rectangle((x,top,x+58,525),fill=('#37566a' if daytime else '#253a51'))
            d.polygon(((x-4,top),(x+29,top-32),(x+62,top)),fill='#b36f62')
            for wx in (x+12,x+36):
                d.rounded_rectangle((wx,top+15,wx+10,top+34),radius=2,fill='#f3c780')
        if key=='cat':
            d.polygon(((0,660),(250,550),(540,655),(540,960),(0,960)),fill='#a86462')
            for y in range(650,960,32):d.line((0,y,540,y),fill='#87545b',width=2)
            for y in range(680,960,64):
                for x in range(10,540,70):d.line((x,y-28,x+25,y+2),fill='#87545b',width=2)
            d.rectangle((355,475,433,642),fill='#d7a580',outline=INK,width=3)
            d.rounded_rectangle((345,464,445,485),radius=5,fill='#f3c69a',outline=INK,width=3)
            d.rounded_rectangle((75,624,179,749),radius=45,fill='#332e42',outline='#e8ac87',width=5)
        else:
            d.polygon(((0,723),(210,631),(540,704),(540,960),(0,960)),fill='#46596a')
            d.polygon(((18,653),(34,348),(95,348),(115,653)),fill='#dfd5bd',outline=INK)
            d.rectangle((29,423,100,467),fill='#b66b65')
            d.rounded_rectangle((28,318,103,357),radius=5,fill='#7c9eaa',outline=INK,width=3)
            d.polygon(((17,320),(65,287),(113,320)),fill='#bc7166',outline=INK)
            d.rectangle((61,599,83,653),fill='#34414f')
            d.rectangle((360,647,540,666),fill='#bb9776')
            for x in (385,468,523):d.rectangle((x,660,x+10,737),fill='#7c6758')
    elif key=='robot':
        d.rounded_rectangle((28,240,253,508),radius=95,fill='#94c2ca',outline=INK,width=4)
        d.line((140,265,140,505),fill='#fff1d8',width=8)
        d.line((35,381,245,381),fill='#fff1d8',width=8)
        d.rectangle((0,640,W,H),fill='#c99374')
        for y in range(660,960,45):d.line((0,y,W,y),fill='#b58269',width=2)
        d.rounded_rectangle((309,250,511,530),radius=22,fill='#64868d',outline=INK,width=4)
        d.rounded_rectangle((332,302,488,456),radius=15,fill='#253d4a',outline='#b8c9be',width=6)
        for x in (352,393,434,475):oval(d,x,280,8,8,'#ecd3a0',INK)
        d.rounded_rectangle((16,708,298,792),radius=15,fill='#b27d63',outline=INK,width=3)
        d.rounded_rectangle((10,695,305,720),radius=10,fill='#f2c897',outline=INK,width=3)
    else:
        d.rectangle((0,552,540,960),fill='#d9c9af')
        d.rectangle((0,548,540,565),fill='#aab9a2')
        d.rounded_rectangle((20,265,184,529),radius=12,fill='#e6ae82',outline=INK,width=3)
        d.rounded_rectangle((39,286,165,431),radius=8,fill='#638c98')
        d.rectangle((27,252,180,272),fill='#7d655e')
        d.line((308,300,510,323),fill='#737d78',width=3)
        for x in (340,405,465):
            d.polygon(((x,303),(x+27,307),(x+30,360),(x-3,355)),fill='#f3d7ae' if x!=405 else '#e6a69c')
        d.line((0,780,540,780),fill='#c7b89f',width=3)
        d.line((0,870,540,870),fill='#c7b89f',width=3)
    return im


def cat(d, x, y, t, carrying=False, scale=1):
    s=scale;bob=math.sin(t*5)*2
    p=lambda a,b:(x+a*s,y+b*s)
    # Tail and feet have independent motion, rather than moving a single cutout.
    tail=[p(32,-27),p(54,-39),p(61+math.sin(t*3)*8,-65),p(52,-77)]
    d.line(tail,fill='#eda76a',width=max(3,int(15*s)),joint='curve')
    oval(d,*p(0,-35+bob),42*s,32*s,'#eda76a',INK)
    for side in (-1,1):
        foot=math.sin(t*7+side)*5
        oval(d,*p(side*24+foot,-4),13*s,7*s,'#f1bb84',INK)
    oval(d,*p(-16,-72+bob),31*s,28*s,'#efa96b',INK)
    d.polygon([p(-45,-85+bob),p(-43,-119+bob),p(-22,-94+bob)],fill='#efa96b',outline=INK)
    d.polygon([p(-16,-97+bob),p(4,-119+bob),p(11,-83+bob)],fill='#efa96b',outline=INK)
    for dx in (-28,-7):
        if t%3.7<.12:d.line([p(dx-5,-76+bob),p(dx+4,-76+bob)],fill=INK,width=2)
        else:oval(d,*p(dx,-77+bob),4*s,6*s,INK)
    d.polygon([p(-21,-65+bob),p(-13,-65+bob),p(-17,-60+bob)],fill='#92515c')
    for side in (-1,1):
        for i in (-1,1):d.line([p(-17+side*13,-61+bob),p(-17+side*39,-62+i*7+bob)],fill=INK,width=1)
    if carrying:star(d,x+22*s,y-48*s,17*s,rotation=math.sin(t)*.2)


def rain(d,t,left=0,right=W,top=180,bottom=750,color='#8aafc7',amount=55):
    for i in range(amount):
        x=left+((i*37+t*22)%(max(1,right-left)))
        y=top+((i*67+t*320)%(max(1,bottom-top)))
        d.line((x,y,x-4,y+15),fill=color,width=2)


def animate_cat(im, scene, u, t):
    d=ImageDraw.Draw(im)
    day=scene==5
    if not day:
        for i in range(14):
            x=30+(i*67)%490;y=175+(i*41)%140
            oval(d,x,y,1+(.7*math.sin(t*2+i)),1.5,'#9fb8cc')
        oval(d,437,226,31,31,'#d7e0dc')
        oval(d,449,218,29,29,'#192946')
    else:cloud(d,370+t*2%40,230,1.2,'#e8ede0')
    for i in range(8):
        x=(i*83+t*21)%600-20;y=533+(i%3)*16+math.sin(t*2+i)*3
        d.arc((x,y,x+43,y+8),0,170,fill='#54778a',width=2)
    bx=290+math.sin(t*.5)*22
    if scene in (2,3):bx=250+math.sin(t*1.4)*55
    if scene==4:bx=lerp(280,470,ease(u))
    boat(d,bx,568+math.sin(t*2)*4,.55)
    if scene==2:
        cat(d,130,727,t,False,.85)
        star(d,124,667,19)
    elif scene==4:
        jump=math.sin(min(1,u*2)*math.pi)*135
        x=lerp(290,390,ease(u*1.8));y=635-jump
        cat(d,x,y,t,u<.35,.95)
        sy=lerp(y-55,210,ease((u-.32)*1.7))
        sx=lerp(x+15,280,ease((u-.32)*1.7))
        for r in range(4):oval(d,sx,sy,28+r*7,28+r*7, '#b39969' if r==3 else '#d8ba75')
        star(d,sx,sy,26,rotation=t*.2)
        for i in range(6):star(d,sx+math.sin(t+i)*35,sy+35+i*15,3,'#ffe6ab')
    elif scene==5:
        cat(d,215,733,t,False,1.05)
        oval(d,120,738,24,9,'#83abb3',INK)
        d.polygon(((138,738),(156,726),(156,748)),fill='#83abb3',outline=INK)
        oval(d,106,736,2,2,INK)
    else:
        x=lerp(185,290,ease(u)) if scene in (0,3) else lerp(260,145,ease(u))
        cat(d,x,655+math.sin(u*math.pi)*-8,t,True,1.15)
        if scene==3:
            for i in range(4):d.line((x+47+i*9,560-i*3,x+53+i*9,547-i*3),fill='#ffe09a',width=2)


def bread(d,x,y,t,crooked=False):
    oval(d,x,y,46,10,'#e7d5b8',INK)
    points=[(x-35,y-7),(x-31,y-24),(x-18,y-34),(x+9,y-37),(x+31,y-25),(x+39,y-5)]
    if crooked:points=[(x-35,y-7),(x-29,y-30),(x-4,y-24),(x+14,y-41),(x+33,y-26),(x+39,y-5)]
    d.polygon(points,fill='#d6a167',outline=INK)
    if crooked:oval(d,x+26,y-21,12,12,'#835745')
    for i in (-15,0,15):d.line((x+i-4,y-24,x+i+2,y-13),fill='#f2c78b',width=3)
    for i in range(3):
        xx=x-20+i*20+math.sin(t*2+i)*4;yy=y-50-((t*12+i*16)%35)
        d.arc((xx-5,yy,xx+6,yy+16),90,270,fill='#dbcbb3',width=2)


def robot(d,x,y,t,gesture=0):
    bob=math.sin(t*3)*3
    for side in (-1,1):
        d.line((x+side*19,y-39,x+side*23,y),fill='#527883',width=15)
        oval(d,x+side*23,y,16,7,INK)
    d.rounded_rectangle((x-39,y-133+bob,x+39,y-32+bob),radius=18,fill='#80afb3',outline=INK,width=3)
    d.rectangle((x-26,y-112+bob,x+26,y-46+bob),fill='#f6e8cf')
    for side in (-1,1):
        yy=y-72+math.sin(t*3+side)*8-gesture*35
        d.line((x+side*37,y-112+bob,x+side*58,yy),fill='#688f99',width=13)
        oval(d,x+side*58,yy,10,10,'#c6d8cf',INK)
    d.rounded_rectangle((x-46,y-215+bob,x+46,y-137+bob),radius=20,fill='#86b8be',outline=INK,width=3)
    d.rounded_rectangle((x-33,y-199+bob,x+33,y-162+bob),radius=9,fill='#294956')
    for side in (-1,1):
        if t%4.3<.12:d.line((x+side*16-5,y-182+bob,x+side*16+5,y-182+bob),fill='#b9ecd4',width=3)
        else:oval(d,x+side*16,y-182+bob,4,7,'#b9ecd4')
    d.arc((x-9,y-157+bob,x+9,y-146+bob),0,180,fill=INK,width=2)
    d.rounded_rectangle((x-46,y-237+bob,x+46,y-214+bob),radius=7,fill='#fff2db',outline=INK,width=2)
    for xx,yy in ((-25,-250),(0,-262),(25,-250)):oval(d,x+xx,y+yy+bob,22,18,'#fff2db',INK)


def animate_robot(im,scene,u,t):
    d=ImageDraw.Draw(im)
    if scene in (1,4):
        for i in range(3):
            a=t*2+i*2;oval(d,409+math.sin(a)*41,405+math.cos(a)*15,10,8,'#e9ad63')
        d.rounded_rectangle((341,315,479,449),radius=12,outline='#d49d65',width=4)
    person(d,404,735,t,'#ce867a',1,gesture=.15 if scene<3 else .45)
    d.rounded_rectangle((309,660,517,681),radius=12,fill='#9b705c',outline=INK,width=3)
    d.line((343,682,336,764),fill=INK,width=8)
    d.line((484,682,493,764),fill=INK,width=8)
    for x in (352,467):
        d.rounded_rectangle((x-12,630,x+12,654),radius=4,fill='#f6ead3',outline=INK,width=2)
        d.arc((x+5,630,x+23,650),270,90,fill=INK,width=3)
    rx=155 if scene not in (3,5) else 275
    if scene==4:rx=lerp(150,280,ease(u))
    robot(d,rx,692,t,.6 if scene in (0,1) else .1)
    bx=159 if scene<3 else 407
    by=695 if scene<3 else 657
    if scene==4:bx=lerp(159,407,ease(u));by=lerp(695,657,ease(u))
    bread(d,bx,by,t,scene>=4)
    if scene==0:
        d.rounded_rectangle((287,465,510,537),radius=20,fill='#fff2da',outline=INK,width=2)
        d.text((309,486),'Gosto de domingo?',font=font(17,True),fill=INK)
    if scene==1:
        d.line((76,620,226,620),fill='#e9d1a7',width=9)
        for x in range(80,226,12):d.line((x,615,x,624),fill=INK,width=1)
    if scene==3:
        for i in range(3):
            x=330+i*35;oval(d,x,447-math.sin(t+i)*4,4+i,4+i,'#b99c86')


def umbrella(d,x,y,t,opened=1):
    radius=max(18,92*opened)
    d.line((x,y,x,y+159),fill=INK,width=4)
    d.arc((x-21,y+142,x+2,y+172),0,180,fill=INK,width=4)
    d.pieslice((x-radius,y-radius*.76,x+radius,y+radius*.76),180,360,fill='#e78071',outline=INK,width=3)
    d.line((x-radius,y,x+radius,y),fill=INK,width=3)
    for dx in (-.5,0,.5):d.line((x,y-radius*.76,x+radius*dx,y),fill='#ad5d62',width=2)
    if opened>.5:rain(d,t,x-radius+8,x+radius-8,y+10,y+156,'#619fae',22)


def pots(d,t,bloom=False):
    for i,x in enumerate((327,406,479)):
        yy=715+(i%2)*22
        d.polygon(((x-26,yy),(x+26,yy),(x+18,yy+50),(x-18,yy+50)),fill='#c37f67',outline=INK)
        d.rounded_rectangle((x-29,yy-7,x+29,yy+7),radius=4,fill='#df9d79',outline=INK,width=2)
        bend=math.sin(t*2+i)*4
        d.line((x,yy-6,x+bend,yy-(80 if bloom else 26)),fill='#5f8b70',width=4)
        if bloom:
            for side in (-1,1):oval(d,x+side*13,yy-40,15,6,'#7b9e72')
            for a in range(5):
                angle=a*math.tau/5
                oval(d,x+bend+math.cos(angle)*13,yy-82+math.sin(angle)*13,10,10,'#ee9b9f' if i!=1 else '#f1d18d')
            oval(d,x+bend,yy-82,8,8,'#bd815c')
        else:d.line((x,yy-25,x+17,yy-20),fill='#9d9471',width=3)


def animate_umbrella(im,scene,u,t):
    d=ImageDraw.Draw(im)
    cloud(d,265+math.sin(t*.2)*20,226,.8,'#edf1de')
    oval(d,459,218,28,28,'#efce8e')
    pots(d,t,scene==5)
    x=204 if scene<3 else 198
    if scene==3:x=lerp(215,255,ease(u))
    person(d,x,739,t,'#e38a75',1.12,gesture=.9 if scene<3 else .55,walking=scene==3)
    if scene==2:
        person(d,85,589,t,'#7b969a',.72,gesture=.5)
        d.rounded_rectangle((91,448,161,480),radius=5,fill='#f6e6bf',outline=INK,width=2)
        d.text((98,455),'INVERSO',font=font(11,True),fill=INK)
    if scene<3:
        op=.35+.65*abs(math.sin(u*math.tau)) if scene==1 else 1
        umbrella(d,x+10,485+math.sin(t*1.5)*2,t,op)
        oval(d,x+10,748,43+math.sin(t*2)*4,5,'#7eafae')
    elif scene==4:
        ux=lerp(328,474,ease(u))
        d.line((x+42,641,ux,569),fill='#e38a75',width=9)
        umbrella(d,ux,506,t,1)
    elif scene==5:
        person(d,288,610,t,'#d2ac66',.8,gesture=.4)
        umbrella(d,139,597,t,.2)
        d.rounded_rectangle((58,710,106,745),radius=8,fill='#78a9a2',outline=INK,width=2)
        d.line((103,720,122,700),fill='#78a9a2',width=8)
        d.arc((48,701,85,737),90,270,fill='#78a9a2',width=5)
    else:umbrella(d,159,614,t,.2)


def animate_lighthouse(im,scene,u,t):
    d=ImageDraw.Draw(im)
    for i in range(13):
        x=(i*61+t*31)%620-40;y=518+(i%5)*27+math.sin(t*2+i)*4
        d.arc((x,y,x+57,y+12),0,180,fill='#5f8295',width=3)
    if scene<5:rain(d,t,0,W,180,760,amount=65)
    if scene==0 and u<.32:
        d.polygon(((68,337),(W,210),(W,435)),fill='#9b9b79')
        oval(d,65,338,13,14,'#ffe5a1')
    x=260;y=698
    person(d,x,y,t,'#d6ae61',1,gesture=.5 if scene>1 else .1,smile=scene>=4)
    if scene in (1,2):
        oval(d,x+45,y-80,7,7,'#ffe4a2')
        d.rounded_rectangle((x+36,y-78,x+54,y-59),radius=3,fill='#72949a',outline=INK,width=2)
    if scene in (3,4,5):
        for i,xx in enumerate((150,340,423)):
            person(d,xx,712+(i%2)*13,t+i,('#b37d78','#7da3a0','#aa8eaf')[i],.78,.7,walking=scene==3)
        if scene>=4:
            for i,xx in enumerate((150,260,340,423)):
                end=490+math.sin(t*.8+i)*12
                d.polygon(((xx+30,639),(end,440-i*7),(end,460+i*4)),fill=('#7c8e87','#a4a185','#b4ac86','#81978e')[i])
                oval(d,xx+30,639,6,6,'#ffe8a9')
    bx=450+math.sin(t*.6)*22;by=540+math.sin(t*2)*6
    if scene==4:bx=lerp(480,460,ease(u));by=lerp(546,632,ease(u))
    if scene==5:bx=490;by=642
    boat(d,bx,by,.72)
    if scene==5:
        # The son walks from the landing to the waiting parent.
        sx=lerp(475,282,ease(u*1.7))
        person(d,sx,695,t,'#75a4aa',.95,.8,walking=u<.6)
        if u>.55:
            d.line((260,602,282,608),fill='#d6ae61',width=11)
            d.line((283,605,259,610),fill='#75a4aa',width=9)


ANIMATORS={'cat':animate_cat,'robot':animate_robot,'umbrella':animate_umbrella,'lighthouse':animate_lighthouse}


@lru_cache(maxsize=128)
def subtitle_layer(text):
    im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
    for size in (28,26,24,22):
        face=font(size,True);lines=wrap(d,text.replace('\n',' '),face,432)
        if len(lines)<=3:break
    if len(lines)>3:raise ValueError('Legenda precisa de menos palavras.')
    top=798
    d.rounded_rectangle((27,top,486,top+len(lines)*33+26),radius=16,fill=(15,27,37,232))
    for i,line in enumerate(lines):
        width=d.textlength(line,font=face)
        d.text((256-width/2,top+12+i*33),line,font=face,fill='#fff4dc')
    return im


def frame(story,scene,u,t,text,progress):
    im=background(story['key'],story['key']=='cat' and (scene==5 or story.get('daytime',False))).copy()
    if story.get('monthly'):
        import cartoon_worlds
        cartoon_worlds.draw(im,story,scene,u,t)
    else:
        ANIMATORS[story['key']](im,scene,u,t)
    # Scene-specific camera moves sit above actual joint and prop animation.
    zoom=1+(.035+.05*(scene%3))*ease(u)
    cw,ch=W/zoom,H/zoom
    cx=(.5+(.045 if scene%2 else -.035))*W;cy=H*.52
    left=max(0,min(W-cw,cx-cw/2));top=max(0,min(H-ch,cy-ch/2))
    im=im.crop((round(left),round(top),round(left+cw),round(top+ch))).resize((W,H),Image.Resampling.BICUBIC)
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((25,81,486,155),radius=17,fill=INK)
    d.text((42,91),'NOVELITAS  /  HISTÓRIA COMPLETA',font=font(13,True),fill=story['accent'])
    face=font(22,True)
    title=story['title']
    if d.textlength(title,font=face)>426:face=font(20,True)
    d.text((42,116),title,font=face,fill='#fff0d8')
    d.rounded_rectangle((28,173,231,198),radius=8,fill=INK)
    d.text((38,176),'FICÇÃO · ANIMAÇÃO 2D · IA',font=font(12,True),fill='#fff0d8')
    # Small film strip progression, kept within the TikTok safe text region.
    for i in range(6):
        x=29+i*77
        d.rounded_rectangle((x,769,x+68,773),radius=2,fill='#738089')
        if progress*6>i:d.rounded_rectangle((x,769,x+max(1,68*min(1,progress*6-i)),773),radius=2,fill=story['accent'])
    im.paste(subtitle_layer(text),(0,0),subtitle_layer(text))
    return im


def state():
    """Expose complete cartoons only. Do not add them to old episode queues."""
    from story_library import read_json
    catalog=read_json(core.DATA/'cartoon-2d'/'catalog.json',65536)
    if not catalog or not isinstance(catalog.get('clips'),list):return []
    result=[];seen=set();root=(core.DATA/'stories').resolve()
    for row in catalog['clips'][:40]:
        if not isinstance(row,dict):continue
        identifier=row.get('id')
        if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier) or identifier in seen:continue
        folder=root/identifier
        if folder.is_symlink() or folder.resolve().parent!=root:continue
        meta=read_json(folder/'roteiro.json',65536)
        if not meta or meta.get('animation_type')!='original_procedural_2d' or 'episode' in meta:continue
        if any(not (folder/name).is_file() or (folder/name).is_symlink() or (folder/name).resolve().parent!=folder
               for name in ('video.mp4','poster.png','legenda.txt','legendas.srt')):continue
        if meta.get('voice') is not True or meta.get('validation',{}).get('decoded') is not True:continue
        duration=meta.get('duration');digest=meta.get('sha256');title=meta.get('title')
        if type(duration) not in (int,float) or not 20<=duration<=120 or not isinstance(title,str) or len(title)>100:continue
        if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):continue
        seen.add(identifier)
        result.append({'id':identifier,'title':title,'duration':duration,'fps':FPS,'status':'ready_local',
                       'video_url':f'/stories/{identifier}/video.mp4?v={digest}',
                       'poster_url':f'/stories/{identifier}/poster.png'})
    return result


def narration(story,folder):
    durations=[];timings=[];raw=[]
    for i,text in enumerate(story['scenes']):
        config=folder/f'speech-{i}.json';audio=folder/f'speech-{i}.wav';timing=folder/f'timing-{i}.json'
        config.write_text(json.dumps({'text':text,'rate':0,'timing_path':str(timing.resolve())},ensure_ascii=False),encoding='utf-8')
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(core.ROOT/'speech.ps1'),str(config),str(audio)],
                       check=True,capture_output=True,timeout=70,creationflags=FLAGS)
        with wave.open(str(audio)) as r:
            if (r.getnchannels(),r.getsampwidth(),r.getframerate())!=(1,2,16000):raise ValueError('Formato de narração inesperado.')
            content=r.readframes(r.getnframes());duration=r.getnframes()/16000
        if duration<.5:raise ValueError('A narração desta cena está vazia.')
        duration=math.ceil((duration+.35)*FPS)/FPS
        raw.append(content+b'\0'*max(0,(round(duration*16000)*2-len(content))))
        durations.append(duration);timings.append(json.loads(timing.read_text(encoding='utf-8-sig')))
    total=sum(durations)
    if not 20<=total<=120:raise ValueError('A história não cabe no formato curto.')
    output=folder/'narration.wav'
    with wave.open(str(output),'wb') as writer:
        writer.setparams((1,2,16000,0,'NONE','not compressed'));writer.writeframes(b''.join(raw))
    import story_director
    cards,methods=story_director.timed_cards(story['scenes'],durations,timings)
    return durations,cards,methods,output


def source_hash():
    digest=hashlib.sha256()
    for name in ('cartoon2d.py','cartoon_catalog.py','cartoon_worlds.py'):
        digest.update((core.ROOT/name).read_bytes())
    return digest.hexdigest()


def soundtrack(story,durations,folder):
    """Quiet, original synthesized music; no external recordings or licenses."""
    rate=16000;total=sum(durations);rng=random.Random(story['key'])
    notes={'cat':(261.63,329.63,392,523.25,440,392),
           'robot':(293.66,369.99,440,587.33,440,369.99),
           'umbrella':(349.23,440,523.25,659.25,523.25,440),
           'lighthouse':(220,261.63,329.63,392,329.63,261.63)}[story['key']]
    samples=array('h')
    for i in range(round(total*rate)):
        t=i/rate;phase=t%1.2;note=notes[int(t/1.2)%len(notes)]
        envelope=math.exp(-phase*4)*min(1,phase*35)
        pluck=(math.sin(math.tau*note*t)+.25*math.sin(math.tau*note*2*t))*.035*envelope
        pad=.009*math.sin(math.tau*(notes[0]/2)*t)*math.sin(math.pi*min(1,t/2))
        weather=(rng.random()-.5)*.009 if story['key'] in ('umbrella','lighthouse') else 0
        fade=min(1,t/1.5,(total-t)/2)
        samples.append(round(max(-1,min(1,(pluck+pad+weather)*max(0,fade)))*32767))
    path=folder/'soundtrack.wav'
    with wave.open(str(path),'wb') as out:
        out.setparams((1,2,rate,0,'NONE','not compressed'));out.writeframes(samples.tobytes())
    return path


def output_folder(identifier,*,resume_incomplete=False):
    """Reuse only a partial private render; never overwrite a finished master."""
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):
        raise ValueError('Identificador de vídeo inválido.')
    root=(core.DATA/'stories').resolve();folder=root/identifier
    if folder.is_symlink() or folder.resolve().parent!=root:
        raise ValueError('Pasta fora do destino original.')
    if folder.exists():
        if not resume_incomplete or not folder.is_dir():raise ValueError('O destino já existe.')
        for path in folder.iterdir():
            if path.is_symlink() or not path.is_file() or path.resolve().parent!=folder:
                raise ValueError('A pasta incompleta precisa de revisão.')
            if path.name in ('video.mp4','roteiro.json','agendamento-tiktok.json'):
                raise ValueError('Há um arquivo concluído ou recibo; não remontar automaticamente.')
            if path.name not in ('video.building.mp4','encode.log','narration.wav','soundtrack.wav') and not re.fullmatch(r'(speech-\d+\.(wav|json)|timing-\d+\.json)',path.name):
                raise ValueError('Arquivo inesperado no destino incompleto.')
    else:folder.mkdir(parents=True)
    return folder


def render_story(story,identifier,project,*,resume_incomplete=False):
    import imageio_ffmpeg
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    folder=output_folder(identifier,resume_incomplete=resume_incomplete)
    durations,cards,methods,audio=narration(story,folder)
    music=soundtrack(story,durations,folder)
    total_frames=round(sum(durations)*FPS);ends=[];current=0
    for duration in durations:current+=round(duration*FPS);ends.append(current)
    card_ends=[c['end'] for c in cards]
    video=folder/'video.building.mp4';log=folder/'encode.log'
    command=[ffmpeg,'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0',
             '-i',str(audio),'-i',str(music),'-vf','scale=720:1280:flags=lanczos','-c:v','libx264','-preset','fast','-crf','19',
             '-pix_fmt','yuv420p','-filter_complex',
             '[1:a]loudnorm=I=-18:TP=-2:LRA=11[v];[v][2:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0[a]',
             '-map','0:v','-map','[a]','-c:a','aac','-ar','44100','-b:a','128k',
             '-movflags','+faststart','-t',str(sum(durations)),str(video)]
    sample_hashes={};poster=None
    print(f"Rendering {story['title']}: {total_frames} frames",flush=True)
    with log.open('wb') as errors:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors,creationflags=FLAGS)
        try:
            for index in range(total_frames):
                scene=min(5,bisect.bisect_right(ends,index))
                start=ends[scene-1] if scene else 0
                u=(index-start)/max(1,ends[scene]-start-1);t=index/FPS
                card=cards[min(len(cards)-1,bisect.bisect_right(card_ends,t+1e-8))]
                image=frame(story,scene,u,t,card['text'],index/max(1,total_frames-1))
                if index==FPS:poster=image.copy()
                if index%max(1,FPS//2)==0:sample_hashes[index]=hashlib.sha256(image.crop((0,200,W,760)).tobytes()).hexdigest()
                process.stdin.write(image.tobytes())
            process.stdin.close()
            if process.wait(timeout=180):raise ValueError('Falha na montagem. Consulte encode.log no novo vídeo.')
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=10)
    # Decode every frame and audio packet; metadata must come from the actual output.
    check=subprocess.run([ffmpeg,'-hide_banner','-v','info','-xerror','-i',str(video),'-f','null','-'],capture_output=True,
                         text=True,encoding='utf-8',errors='replace',timeout=180,creationflags=FLAGS)
    if check.returncode or '720x1280' not in check.stderr or 'Audio: aac' not in check.stderr:
        raise ValueError('O vídeo não passou na conferência de imagem e áudio.')
    if len(set(sample_hashes.values()))<len(sample_hashes)*.9:raise ValueError('Movimento insuficiente na região dos personagens.')
    video.replace(folder/'video.mp4')
    poster.save(folder/'poster.png')
    (folder/'legenda.txt').write_text(caption(story),encoding='utf-8')
    (folder/'legendas.srt').write_text(creative.srt(cards),encoding='utf-8')
    meta={'animation_type':'original_procedural_2d','title':story['title'],'key':story['key'],
          'genre':story['genre'],'voice':True,'fps':FPS,'size':[720,1280],'duration':sum(durations),
          'scenes':story['scenes'],'scene_durations':durations,'subtitle_timing_scenes':methods,
          'script_sha256':hashlib.sha256(json.dumps(story,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
          'character_animation':True,'mouth_alignment':'expressions_not_speech_aligned',
          'sound_design':'original_local_synthesized_music_and_weather',
          'visual_source':'Original Pillow vector shapes, articulated characters and props; no third-party images.',
          'project':str(project),'source_sha256':source_hash(),'sha256':hashlib.sha256((folder/'video.mp4').read_bytes()).hexdigest(),
          'target_handle':'novelitas0213','offer':None,'publication_status':'ready_local',
          'validation':{'decoded':True,'motion_samples':len(sample_hashes),'unique_motion_samples':len(set(sample_hashes.values())),
                        'captions':len(cards),'full_story':True}}
    (folder/'roteiro.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ready':identifier,'title':story['title'],'duration':round(sum(durations),2)},ensure_ascii=False),flush=True)
    return {'id':identifier,'key':story['key']}


def render():
    from instance_lock import InstanceLock
    root=core.DATA/'cartoon-2d';root.mkdir(parents=True,exist_ok=True)
    with InstanceLock(root/'render'):
        existing=state();catalog=root/'catalog.json'
        from story_library import read_json
        from story_local_archive import archived
        if any(archived(r.get('id')) for r in (read_json(catalog) or {}).get('clips',[]) if isinstance(r,dict)):
            raise ValueError('Os pilotos já agendados foram retirados a seu pedido. Recupere os MP4s na Lixeira para assistir; não gerar cópias automaticamente.')
        if catalog.is_file() and len(existing)==4 and json.loads(catalog.read_text(encoding='utf-8')).get('source_sha256')==source_hash():
            print(json.dumps({'existing':True,'clips':existing},ensure_ascii=False),flush=True);return
        project=root/uuid4().hex;project.mkdir()
        for name in ('cartoon2d.py','cartoon_catalog.py'):
            (project/name).write_bytes((core.ROOT/name).read_bytes())
        spec={'source_sha256':source_hash(),'stories':STORIES,'clips':[{'id':uuid4().hex,'key':s['key']} for s in STORIES]}
        (project/'project.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
        clips=[]
        for story,row in zip(STORIES,spec['clips']):clips.append(render_story(story,row['id'],project))
        temporary=root/'catalog.tmp'
        temporary.write_text(json.dumps({'source_sha256':source_hash(),'project':project.name,'clips':clips},indent=2),encoding='utf-8')
        temporary.replace(catalog)
        print(json.dumps({'complete':True,'clips':state()},ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Prepare four original 2D stories locally. No uploads.')
    parser.add_argument('command',choices=['render','state','contact-sheet']);args=parser.parse_args()
    if args.command=='render':render()
    elif args.command=='state':print(json.dumps(state(),ensure_ascii=False))
    else:
        sheet=Image.new('RGB',(W*4,H*3),'#172936')
        for col,story in enumerate(STORIES):
            for row,scene in enumerate((0,3,5)):
                sheet.paste(frame(story,scene,.6,scene*5+.6,story['scenes'][scene].split('.')[0]+'.',.5),(col*W,row*H))
        path=core.DATA/'cartoon-2d'/'contact-sheet.png';path.parent.mkdir(exist_ok=True,parents=True);sheet.save(path)
        print(path)
