"""Original action clips, executed only by Blender's Python interpreter."""
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector, Euler
import animation3d_scene as studio
from animation_action_math import ease,leg_angles,walk_y,step_target


def descendants(root):
    return [root,*root.children_recursive]


def reach(char,index,target,hand_rotation=(0,0,0),pole_direction=None):
    """Two-link arm IK; preserve the original articulated mesh proportions."""
    upper=char['arms'][index];lower=char['forearms'][index];wrist=char['hands'][index]
    bpy.context.view_layer.update()
    shoulder=upper.matrix_world.translation.copy();desired=Vector(target)
    direction=desired-shoulder;distance=direction.length
    first=lower.location.length;second=wrist.location.length
    if not abs(first-second)+.001<distance<first+second-.001:
        raise ValueError('Hand target is outside arm reach: '+char['root'].name+' '+str(distance))
    direction.normalize();pole=Vector(pole_direction or (.2 if index else -.2,-1.,.15))
    pole-=direction*pole.dot(direction);pole.normalize()
    along=(first*first-second*second+distance*distance)/(2*distance)
    elbow=shoulder+direction*along+pole*math.sqrt(max(0,first*first-along*along))
    parent_rotation=upper.parent.matrix_world.to_quaternion()
    local_direction=parent_rotation.inverted()@(elbow-shoulder)
    upper.rotation_euler=lower.location.normalized().rotation_difference(local_direction.normalized()).to_euler()
    bpy.context.view_layer.update()
    fore_direction=upper.matrix_world.to_quaternion().inverted()@(desired-lower.matrix_world.translation)
    lower.rotation_euler=Vector((0,0,-1)).rotation_difference(fore_direction.normalized()).to_euler()
    bpy.context.view_layer.update()
    wrist.rotation_euler=(lower.matrix_world.to_quaternion().inverted()@Euler(hand_rotation).to_quaternion()).to_euler()
    bpy.context.view_layer.update()
    return (wrist.matrix_world.translation-desired).length


def palm(char,index):
    return next(o for o in char['hands'][index].children if ' palm' in o.name).matrix_world.translation.copy()


def build(config):
    action=config['action']
    if action not in ('arrival','handoff','reveal'):raise ValueError('Unknown action')
    stage=studio.build({**config,'kind':'room','episode':2,'prepare_only':True})
    scene=stage['scene'];lia=stage['lia'];eva=stage['eva'];actors=[lia,eva]
    key=stage['key'];drawing=stage['drawing'];door=stage['door'];camera=stage['camera']
    for obj in scene.objects:obj.animation_data_clear()
    camera.data.animation_data_clear()
    bpy.data.objects['Floor'].location.z=-.10
    for char in actors:
        char['root'].rotation_euler=(0,0,0)
        for obj in (char['body'],char['head'],*char['arms'],*char['forearms'],*char['hands'],*char['legs'],*char['knees']):obj.rotation_euler=(0,0,0)
        for shoe in char['shoes']:shoe.rotation_euler=(0,0,0)
    controlled=[camera,key,drawing,door]
    for char in actors:
        controlled += [char['root'],char['body'],char['head'],char['mouth'],*char['eyes'],*char['brows'],
                       *char['arms'],*char['forearms'],*char['hands'],*char['legs'],*char['knees'],*char['shoes']]
    fps=scene.render.fps;frames=scene.frame_end;records=[];max_error=0.;max_contact_error=0.;last_contacts={};max_slide=0.
    for frame in range(1,frames+1):
        t=(frame-1)/fps
        for index,char in enumerate(actors):
            char['root'].location=(-.65 if index==0 else .65,.25,-.06)
            char['root'].rotation_euler=(0,0,.20 if index==0 else -.20)
            char['body'].rotation_euler=(0,.01*math.sin(t*1.6+index),0)
            char['head'].rotation_euler=(.02*math.sin(t),0,.08*math.sin(t*.8+index))
            char['mouth'].scale.z=.014
            blink=.07 if abs((t+index*.4)%3.7-1.8)<.065 else 1.
            for eye in char['eyes']:eye.scale.z=blink
            for arm in char['arms']:arm.rotation_euler=(0,0,0)
            for fore in char['forearms']:fore.rotation_euler=(0,0,0)
        door.rotation_euler.z=-.08;contact_flags=[True,True]
        if action=='arrival':
            lia['root'].location=(1.30,walk_y(t),-.12+.06*ease((t-4.3)/.8))
            lia['root'].rotation_euler.z=math.pi
            eva['root'].location=(1.65,3.6,-.06);eva['root'].rotation_euler.z=0
            for index,phase in enumerate((0,.6)):
                foot_y,lift,planted=step_target(t,phase)
                height=lia['root'].location.z+1.22
                shoe=lia['shoes'][index]
                hip,knee=leg_angles(-(foot_y-walk_y(t)),.12+lift-height,.51,math.hypot(shoe.location.y,shoe.location.z))
                knee-=math.atan2(shoe.location.y,-shoe.location.z)
                lia['legs'][index].rotation_euler.x=hip;lia['knees'][index].rotation_euler.x=knee
                lia['shoes'][index].rotation_euler.x=-(hip+knee)
                contact_flags[index]=planted
            for index in range(2):
                lia['arms'][index].rotation_euler.x=.18*math.sin(t*math.tau/1.2+index*math.pi)*(1-ease((t-3.5)/.8))
            door.rotation_euler.z=-1.05*ease((t-1.9)/2.0)
            eva['arms'][1].rotation_euler.x=-.85*ease((t-2.8)/.7)
            eva['forearms'][1].rotation_euler.x=-.7*ease((t-2.8)/.7)
            eva['forearms'][1].rotation_euler.z=.15*math.sin(t*5)*ease((t-3)/.7)
            camera.location=(3.0-.12*ease(t/6),-4.4,2.65);focus=Vector((1.43,1.7,1.42));camera.data.lens=46
        elif action=='handoff':
            lia['root'].rotation_euler.z=.28;eva['root'].rotation_euler.z=-.28
            offer=ease((t-.3)/2.0);receive=ease((t-1.3)/1.1);back=ease((t-3.8)/1.4)
            left=Vector((-.32,.24,1.02)).lerp(Vector((-.10,-.16,1.40)),offer)
            left=left.lerp(Vector((-.30,.18,1.05)),back)
            right=Vector((.32,.24,1.02)).lerp(Vector((.10,-.16,1.40)),receive)
            right=right.lerp(Vector((.33,.12,1.20)),back)
            max_error=max(max_error,reach(lia,1,left,(-math.pi/2,0,math.pi/2)),reach(eva,0,right,(-math.pi/2,0,-math.pi/2)))
            bpy.context.view_layer.update();transfer=ease((t-2.7)/.6)
            key.location=palm(lia,1).lerp(palm(eva,0),transfer)+Vector((0,0,.045))
            key.rotation_euler=(math.pi/2,0,-math.pi/2);key.scale=(.6,.6,.6)
            lia['head'].rotation_euler.z=.25-.1*back;eva['head'].rotation_euler.z=-.25+.1*back
            camera.location=(.50+.12*ease(t/6),-4.6+.20*ease(t/6),2.50);focus=Vector((0,.1,1.48));camera.data.lens=46
        else:
            lift=ease((t-.4)/2.0)
            drawing.location=(.40,.20-.30*lift,1.27+.38*lift)
            drawing.rotation_euler=(.05*(1-lift),0,-.06*math.sin(t*.7));drawing.scale=(1.15,1.15,1.15)
            bpy.context.view_layer.update()
            for index,side in enumerate((-1,1)):
                position=drawing.matrix_world@Vector((side*.255,0,-.18));position.z+=.065
                max_error=max(max_error,reach(eva,index,position,(0,0,0),(-.3 if index==0 else .3,-.5,-1)))
            gesture=ease((t-2.6)/.8)*(1-.6*ease((t-4.7)/.8))
            target=Vector((-.30,.20,1.05)).lerp(Vector((-.03,-.24,1.65)),gesture)
            max_error=max(max_error,reach(lia,1,target,(-.8,0,.3)))
            lia['head'].rotation_euler=(.08*(1-lift),0,.24);eva['head'].rotation_euler=(.04,0,-.20)
            camera.location=(.70,-4.5+.35*ease(t/6),2.5);focus=Vector((.15,.05,1.50));camera.data.lens=46
        camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update()
        actor_states=[]
        for char in actors:
            feet=[]
            for index,shoe in enumerate(char['shoes']):
                minimum=min((shoe.matrix_world@Vector(corner)).z for corner in shoe.bound_box)
                position=shoe.matrix_world.translation.copy();planted=contact_flags[index] if action=='arrival' and char is lia else True
                if planted:max_contact_error=max(max_contact_error,abs(minimum))
                name=char['root'].name+str(index)
                if planted and name in last_contacts:
                    previous=last_contacts[name]
                    # Only consecutive planted frames of this foot belong to the same contact.
                    if previous['frame']==frame-1:max_slide=max(max_slide,(position-Vector(previous['position'])).xy.length)
                if planted:last_contacts[name]={'frame':frame,'position':list(position)}
                feet.append({'side':index,'minimum_z':minimum,'planted':planted,'position':list(position)})
            actor_states.append({'name':char['root'].name,'root':list(char['root'].location),'heading':char['root'].rotation_euler.z,
                                 'head':list(char['head'].rotation_euler),'wrists':[list(h.matrix_world.translation) for h in char['hands']],'feet':feet})
        if frame==1 or frame==frames or frame%max(1,fps//2)==0:
            records.append({'frame':frame,'camera':list(camera.location),'door_angle':door.rotation_euler.z,'actors':actor_states,
                            'key':list(key.location),'drawing':list(drawing.location)})
        for obj in controlled:studio.keyframe(obj,frame)
        camera.data.keyframe_insert(data_path='lens',frame=frame)
    if max_error>.005 or max_contact_error>.015 or max_slide>.015:
        raise ValueError('Motion contact or reach check failed: '+str((max_error,max_contact_error,max_slide)))
    for obj in controlled:
        if obj.animation_data and obj.animation_data.action:
            for curve in obj.animation_data.action.fcurves:
                for point in curve.keyframe_points:point.interpolation='LINEAR'
    output=Path(config['output']);output.mkdir(parents=True,exist_ok=True)
    report={'action':action,'world_up':'Z','character_front':'-Y','fps':fps,'frames':frames,'width':scene.render.resolution_x,
            'height':scene.render.resolution_y,'objects':len(scene.objects),'meshes':sum(o.type=='MESH' for o in scene.objects),
            'rig':'Original hierarchical objects; no imported armature or retargeting.',
            'maximum_hand_target_error':max_error,'maximum_planted_foot_height_error':max_contact_error,
            'maximum_planted_foot_slide_per_frame':max_slide,'samples':records,'mouth':'Closed/rest expression; no dialogue or lip sync.'}
    (output/'motion-state.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(output/'scene.blend'))
    if config.get('preview_frame'):
        scene.frame_set(config['preview_frame']);scene.render.filepath=str(output/'preview.png');bpy.ops.render.render(write_still=True)
    else:
        scene.render.filepath=str(output/'frame-');bpy.ops.render.render(animation=True)


if __name__=='__main__':
    configuration=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text(encoding='utf-8-sig'))
    for item in configuration.get('jobs',[configuration]):
        build(item)
        bpy.ops.outliner.orphans_purge(do_recursive=True)
