"""Original stylized actors and apartment, baked and rendered inside Blender.

Run with Blender --background --factory-startup --python this-file -- config.json.
No downloaded characters, add-ons, cloud calls or automatic script execution.
"""
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def material(name, color, roughness=.65, metallic=0):
    mat = bpy.data.materials.new(name);mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    return mat


def empty(name, location=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None);bpy.context.collection.objects.link(obj)
    obj.parent = parent;obj.location = location
    return obj


def mesh_obj(name, vertices, faces, mat, parent=None):
    mesh = bpy.data.meshes.new(name);mesh.from_pydata(vertices, [], faces);mesh.update()
    obj = bpy.data.objects.new(name, mesh);bpy.context.collection.objects.link(obj)
    obj.parent = parent;obj.data.materials.append(mat)
    return obj


def ball(name, location, scale, mat, parent=None, segments=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=12)
    obj = bpy.context.object;obj.name = name;obj.parent = parent
    obj.location = location;obj.scale = scale;obj.data.materials.append(mat)
    for face in obj.data.polygons:face.use_smooth = True
    return obj


def box(name, location, scale, mat, parent=None, bevel=.06):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object;obj.name = name;obj.parent = parent
    obj.location = location;obj.dimensions = scale;obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new('Soft edges', 'BEVEL');mod.width = bevel;mod.segments = 3
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def rod(name, start, end, radius, mat, parent=None):
    a, b = Vector(start), Vector(end)
    bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=radius, depth=(b-a).length)
    obj = bpy.context.object;obj.name = name;obj.parent = parent
    obj.location = (a+b)/2;obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(mat)
    for face in obj.data.polygons:face.use_smooth = True
    return obj


def text_obj(value, location, size, mat, parent=None):
    curve = bpy.data.curves.new('Text '+value, 'FONT');curve.body = value;curve.size = size
    curve.align_x = 'CENTER';curve.extrude = .001
    obj = bpy.data.objects.new('Text '+value, curve);bpy.context.collection.objects.link(obj)
    obj.parent = parent;obj.location = location;obj.rotation_euler[0] = math.pi/2;curve.materials.append(mat)
    return obj


def actor(name, clothes, hair, skin, location, curly=False, male=False):
    root = empty(name, (location[0],location[1],-.06));body = empty(name+' torso', (0, 0, 1.48), root)
    ball(name+' jacket', (0, 0, .10), (.32, .22, .46), clothes, body)
    box(name+' shirt', (0, -.196, .12), (.20, .065, .60), C['cream'], body, .05)
    for side in (-1, 1):
        lapel = box(name+' lapel', (side*.145, -.216, .23), (.09, .045, .42), clothes, body, .02)
        lapel.rotation_euler[1] = side*.12
    for z in (-.12, .03, .18):ball(name+' button', (.075, -.242, z), (.018, .012, .018), C['gold'], body)
    rod(name+' neck', (0, 0, 1.91), (0, 0, 2.10), .105, skin, root)
    head = empty(name+' head', (0, 0, 2.29), root)
    ball(name+' face', (0, 0, 0), (.345, .30, .425), skin, head, 28)
    for side in (-1, 1):ball(name+' ear', (side*.338, -.012, -.02), (.066, .047, .10), skin, head)
    eyes = []
    for side in (-1, 1):
        eye = empty(name+' eye', (side*.125, -.262, .065), head);eyes.append(eye)
        ball(name+' sclera', (0, 0, 0), (.093, .051, .10), C['white'], eye)
        ball(name+' iris', (.006*side, -.045, -.001), (.046, .019, .061), C['iris'], eye)
        ball(name+' pupil', (.006*side, -.061, -.001), (.023, .008, .039), C['dark'], eye)
        ball(name+' catchlight', (-.009, -.069, .022), (.012, .006, .014), C['white'], eye)
        brow = rod(name+' brow', (side*.065, -.285, .218), (side*.198, -.259, .205), .022, hair, head)
        brow.rotation_euler[1] += side*.08
    ball(name+' nose', (0, -.303, -.032), (.054, .077, .070), skin, head)
    mouth = ball(name+' mouth', (0, -.284, -.158), (.075, .023, .019), C['mouth'], head)
    ball(name+' lower lip', (0, -.278, -.183), (.062, .019, .016), skin, head)
    # Sculpted cap: a higher hairline at the front keeps eyebrows and eyes clear.
    vertices=[];faces=[];segments=32;rings=12
    for ring in range(rings+1):
        for seg in range(segments):
            phi=seg/segments*math.tau;front=max(0,-math.sin(phi))
            theta=(ring/rings)*(1.97-.72*front)
            vertices.append((.36*math.sin(theta)*math.cos(phi),.325*math.sin(theta)*math.sin(phi)+.025,.44*math.cos(theta)+.045))
    for ring in range(rings):
        for seg in range(segments):
            a=ring*segments+seg;b=ring*segments+(seg+1)%segments
            faces.append((a,b,b+segments,a+segments))
    cap=mesh_obj(name+' hair cap',vertices,faces,hair,head)
    for face in cap.data.polygons:face.use_smooth=True
    for side in (-1,1):
        for k in range(5 if curly else 3):
            z=.20-k*(.135 if curly else .11)
            ball(name+' hair lock', (side*(.30+.025*math.sin(k)),.055,z),(.11,.20,.15 if curly else .19),hair,head)
    for k in range(7):
        x=-.27+k*.071
        lock=ball(name+' swept fringe',(x,-.19,.30+.06*math.sin(k*.5)),(.072,.12,.105),hair,head)
        lock.rotation_euler[1]=-.4
    if male:
        for side in (-1,1):ball(name+' silver temple',(side*.32,.005,.13),(.055,.13,.13),C['silver'],head)
    arms=[];forearms=[];hands=[];legs=[];knees=[];shoes=[]
    for side in (-1,1):
        arm=empty(name+' upper arm '+str(side),(side*.31,0,1.85),root)
        ball(name+' sleeve',(side*.025,0,-.18),(.11,.12,.27),clothes,arm)
        elbow=empty(name+' elbow '+str(side),(side*.035,0,-.42),arm)
        ball(name+' forearm',(0,0,-.17),(.080,.085,.22),skin,elbow)
        hand=empty(name+' wrist '+str(side),(0,0,-.38),elbow)
        ball(name+' palm',(0,-.01,-.065),(.082,.062,.115),skin,hand)
        for finger in (-1,0,1):ball(name+' finger',(finger*.035,-.025,-.135),(.022,.030,.065),skin,hand)
        ball(name+' thumb',(-side*.073,-.025,-.055),(.038,.036,.065),skin,hand)
        arms.append(arm);forearms.append(elbow);hands.append(hand)
        leg=empty(name+' hip '+str(side),(side*.14,0,1.22),root)
        ball(name+' trousers',(0,0,-.24),(.123,.128,.32),C['pants'],leg)
        knee=empty(name+' knee '+str(side),(0,0,-.51),leg)
        ball(name+' lower leg',(0,0,-.22),(.09,.10,.29),C['pants'],knee)
        shoe=ball(name+' shoe',(0,-.065,-.53),(.12,.205,.12),C['shoe'],knee)
        legs.append(leg);knees.append(knee);shoes.append(shoe)
    return dict(root=root,body=body,head=head,eyes=eyes,mouth=mouth,arms=arms,forearms=forearms,hands=hands,legs=legs,knees=knees,shoes=shoes)


def key_prop():
    root=empty('Brass key')
    bpy.ops.mesh.primitive_torus_add(major_radius=.085,minor_radius=.018,major_segments=24,minor_segments=8)
    obj=bpy.context.object;obj.parent=root;obj.rotation_euler[0]=math.pi/2;obj.data.materials.append(C['gold'])
    rod('Key shaft',(0,0,-.07),(0,0,-.34),.018,C['gold'],root)
    for z in (-.26,-.32):box('Key tooth',(.035,0,z),(.09,.035,.035),C['gold'],root,.008)
    box('Key label',(.15,0,-.09),(.17,.025,.20),C['gold'],root,.03)
    text_obj('12',(.15,-.016,-.125),.11,C['dark'],root)
    return root


def apartment():
    box('Floor',(0,.5,-.12),(8,9,.20),C['floor'],bevel=.01)
    for x in range(-8,9):box('Floor seam',(x*.48,.5,-.013),(.008,9,.008),C['wood'],bevel=0)
    box('Back wall left',(-1.51,3,1.8),(5.02,.18,3.8),C['wall'])
    box('Back wall right',(3.13,3,1.8),(1.74,.18,3.8),C['wall'])
    box('Wall above doorway',(1.63,3,3.49),(1.25,.18,.82),C['wall'])
    box('Inner apartment wall',(1.65,4.65,1.8),(3,.18,3.8),C['teal'])
    box('Left wall',(-3.2,.9,1.8),(.16,4.4,3.8),C['teal'])
    box('Skirting',(0,2.86,.13),(8,.11,.19),C['cream'],bevel=.015)
    box('Window recess',(-3.10,.7,2.15),(.055,1.55,1.6),C['window'])
    for y in (-.08,.7,1.48):box('Window frame',(-3.05,y,2.15),(.07,.045,1.67),C['cream'],bevel=.01)
    box('Window crossbar',(-3.05,.7,2.15),(.07,1.6,.045),C['cream'],bevel=.01)
    box('Sideboard',(-1.65,2.55,.60),(1.5,.65,1.1),C['wood'])
    for x in (-2,-1.3):ball('Handle',(x,2.19,.7),(.04,.035,.04),C['gold'])
    for k in range(5):
        book=box('Book',(-1.9+k*.15,2.52,1.25),(.12,.27,.27+.025*k),C['burgundy'] if k%2 else C['cream'],bevel=.01)
        book.rotation_euler[1]=.06*math.sin(k)
    box('Table',(0,-.65,.90),(1.9,1.0,.13),C['wood'],bevel=.09)
    for x in (-.75,.75):
        for y in (-1.02,-.3):rod('Table leg',(x,y,.08),(x,y,.86),.06,C['wood'])
    # Plant and lamp create depth without any downloaded environment assets.
    ball('Plant pot',(-2.45,1.55,.36),(.30,.30,.38),C['terracotta'])
    for i in range(9):
        angle=i*2.4;x=-2.45+.30*math.cos(angle);y=1.55+.30*math.sin(angle);z=.9+(i%3)*.16
        rod('Plant stalk',(-2.45,1.55,.62),(x,y,z),.012,C['leaf'])
        leaf=ball('Leaf',(x,y,z),(.08,.24,.055),C['leaf']);leaf.rotation_euler=(.2,angle*.2,angle)
    rod('Lamp stem',(2.45,2.2,.1),(2.45,2.2,2.25),.035,C['gold'])
    ball('Lamp foot',(2.45,2.2,.08),(.30,.30,.08),C['gold'])
    bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.38,radius2=.22,depth=.45,location=(2.45,2.2,2.3))
    bpy.context.object.data.materials.append(C['cream'])
    hinge=empty('Door hinge',(1.02,2.83,0))
    box('Door leaf',(.55,0,1.45),(1.1,.12,2.9),C['wood'],hinge,.025)
    for z in (.70,1.88):box('Door panel',(.55,-.072,z),(.80,.025,.87),C['woodlight'],hinge,.025)
    ball('Door handle',(.91,-.13,1.24),(.055,.06,.055),C['gold'],hinge)
    box('Door number plate',(.55,-.095,2.35),(.25,.025,.30),C['gold'],hinge,.03)
    text_obj('12',(.55,-.115,2.29),.19,C['dark'],hinge)
    for x in (.95,2.2):box('Door casing',(x,2.76,1.48),(.12,.18,3.05),C['cream'],bevel=.015)
    box('Door lintel',(1.58,2.76,3.01),(1.4,.18,.14),C['cream'],bevel=.015)
    return hinge


def light(name, location, energy, color, size, target):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.color=color;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def keyframe(obj, frame):
    obj.keyframe_insert(data_path='location',frame=frame)
    obj.keyframe_insert(data_path='rotation_euler',frame=frame)
    obj.keyframe_insert(data_path='scale',frame=frame)


def build(config):
    global C
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    C={key:material(key,color,metallic=.65 if key=='gold' else 0) for key,color in {
        'skin':(.60,.34,.21),'skinEva':(.52,.27,.17),'skinDavi':(.57,.35,.24),'hair':(.055,.027,.018),
        'hairEva':(.018,.011,.009),'silver':(.32,.32,.29),'green':(.055,.19,.14),'burgundy':(.31,.055,.10),
        'blue':(.065,.16,.27),'cream':(.86,.77,.60),'white':(.95,.94,.89),'iris':(.18,.075,.028),'dark':(.012,.018,.019),
        'mouth':(.17,.025,.026),'pants':(.045,.065,.080),'shoe':(.08,.055,.041),'gold':(.62,.39,.10),
        'floor':(.26,.18,.12),'wood':(.17,.075,.032),'woodlight':(.24,.12,.048),'wall':(.57,.53,.43),
        'teal':(.085,.22,.22),'window':(.28,.51,.60),'leaf':(.09,.25,.10),'terracotta':(.42,.18,.10),
        'paper':(.90,.84,.70)}.items()}
    scene=bpy.context.scene;scene.render.engine=config.get('engine','BLENDER_EEVEE_NEXT')
    scene.render.resolution_x=config.get('width',720);scene.render.resolution_y=config.get('height',1280);scene.render.resolution_percentage=100
    scene.render.fps=config.get('fps',12);scene.frame_start=1;scene.frame_end=round(config['duration']*scene.render.fps)
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.world.color=(.13,.13,.13)
    scene.view_settings.view_transform='AgX'
    if hasattr(scene,'eevee'):scene.eevee.taa_render_samples=config.get('samples',12)
    if scene.render.engine=='BLENDER_WORKBENCH':
        scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
        scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
        scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=True
    scene.render.engine=config.get('engine','BLENDER_EEVEE_NEXT')
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.compression=15
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.render.use_file_extension=True
    hinge=apartment();kind=config['kind'];episode=config.get('episode',1)
    lia=actor('Lia',C['green'],C['hair'],C['skin'],(-.60,.10,0))
    eva=actor('Eva',C['burgundy'],C['hairEva'],C['skinEva'],(.72,.40,0),curly=True)
    davi=actor('Davi',C['blue'],C['hair'],C['skinDavi'],(1.30,1.10,0),male=True)
    visible=[lia]
    if kind in ('portrait','photo','room','door') or (episode>1 and kind=='letter'):visible.append(eva)
    if kind=='building':visible.append(davi)
    for character in (lia,eva,davi):
        if character not in visible:character['root'].location.x=50
    key=key_prop()
    letter=empty('Letter prop');box('Envelope',(0,0,0),(.52,.045,.34),C['paper'],letter,.025)
    text_obj('Vá sozinha.' if episode==1 else 'Uma carta para cada filha.',(0,-.027,-.015),.055 if episode==1 else .033,C['dark'],letter)
    photo=empty('Photograph prop');box('Photo print',(0,0,0),(.55,.028,.39),C['paper'],photo,.008)
    image_path=Path(config['assets'])/'photo-prop.png'
    image=bpy.data.images.load(str(image_path));image.pack()
    mat=bpy.data.materials.new('Original fictional photograph');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
    mat.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.85
    printmesh=mesh_obj('Image on paper',[(-.26,-.017,-.17),(.26,-.017,-.17),(.26,-.017,.17),(-.26,-.017,.17)],[(0,1,2,3)],mat,photo)
    uv=printmesh.data.uv_layers.new()
    for loop,coord in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):loop.uv=coord
    package=box('Keepsake box',(50,0,0),(.70,.44,.32),C['woodlight'],bevel=.04)
    boxlid=box('Box lid',(50,0,0),(.73,.47,.055),C['wood'],bevel=.02)
    for prop in (key,letter,photo):prop.location.x=50
    light('Window key',(-3.0,-1.4,4.8),550,(1.0,.79,.56),4,(0,0,1.3))
    light('Soft fill',(2,-4,3.4),330,(.59,.76,1.0),4,(0,0,1.7))
    light('Warm rim',(1.5,2.3,3.8),480,(1.0,.59,.29),2,(0,0,1.5))
    light('Lamp glow',(2.40,2,2.4),80,(1.0,.70,.40),1,(1,0,1.5))
    camera_data=bpy.data.cameras.new('Story camera');camera=bpy.data.objects.new('Story camera',camera_data)
    bpy.context.collection.objects.link(camera);scene.camera=camera;camera_data.lens=46
    camera_data.clip_end=100;camera_data.dof.use_dof=False
    samples=[];animated=[]
    for char in visible:
        animated += [char['root'],char['body'],char['head'],char['mouth'],*char['arms'],*char['forearms'],*char['eyes']]
    animated += [key,letter,photo,hinge,package,boxlid,camera]
    fps=scene.render.fps;end=scene.frame_end
    sample_frames=sorted(set([1,end,*range(1,end+1,4)]))
    for frame in sample_frames:
        t=(frame-1)/fps;p=t/config['duration'];slow=math.sin(t*1.5)
        for idx,char in enumerate(visible):
            char['body'].rotation_euler[1]=.012*math.sin(t*1.3+idx)
            char['head'].rotation_euler=(.035*math.sin(t*1.6+idx),.025*math.sin(t*.9),.08*math.sin(t*.6+idx))
            blink=.08 if (t+idx*.7)%4.2<.12 else 1
            for eye in char['eyes']:eye.scale.z=blink
            char['mouth'].scale.z=.019
            for side,arm in enumerate(char['arms']):arm.rotation_euler=(.04*slow,(-.12 if side==0 else .12),.015*slow)
            for fore in char['forearms']:fore.rotation_euler=(0,0,0)
        # Hands and faces perform distinct actions, with articulated elbows.
        if kind=='key':
            lia['arms'][1].rotation_euler[0]=-1.10+.12*math.sin(t*.8)
            lia['forearms'][1].rotation_euler[0]=-.60-.20*math.sin(t*.8)
            lia['head'].rotation_euler[0]=.08+.06*math.sin(t)
        if kind=='letter':
            for char in visible:
                char['arms'][0].rotation_euler[0]=-.75;char['forearms'][0].rotation_euler[0]=-.8
                char['arms'][1].rotation_euler[0]=-.85+.12*slow;char['forearms'][1].rotation_euler[0]=-.65
        if kind in ('portrait','photo','room'):
            eva['arms'][1].rotation_euler[0]=-1.0+.10*slow;eva['forearms'][1].rotation_euler[0]=-.7
            eva['head'].rotation_euler[2]=-.25+.10*math.sin(t*.8)
            lia['head'].rotation_euler[2]=.28+.10*math.sin(t*.8)
            if kind=='room':eva['arms'][0].rotation_euler[0]=-.6+.3*math.sin(t*1.8)
            if p>.45:eva['mouth'].scale.z=.019*(1+3*abs(math.sin(t*10)))
        if kind=='building':
            davi['head'].rotation_euler[2]=-.30+.08*slow
            davi['arms'][0].rotation_euler[0]=-.75+.18*slow;davi['forearms'][0].rotation_euler[0]=-.7
            davi['mouth'].scale.z=.019*(1+2.8*abs(math.sin(t*9)))
            lia['head'].rotation_euler[2]=.3
        hinge.rotation_euler[2]=-.85*max(0,min(1,(p-.2)*1.8)) if kind in ('door','portrait') else -.08
        if kind=='door':
            lia['root'].location=(.5,.8,-.06);lia['root'].rotation_euler[2]=2.4
            lia['arms'][1].rotation_euler[0]=-1.15;lia['forearms'][1].rotation_euler[0]=-.25
            eva['root'].location=(1.6,3.5,-.06)
        bpy.context.view_layer.update()
        if kind=='key':
            key.location=lia['hands'][1].matrix_world.translation+Vector((0,-.06,-.05));key.rotation_euler=(0,.08*slow,-.12*slow)
        if kind=='letter':
            letter.location=lia['hands'][1].matrix_world.translation+Vector((-.10,-.10,.10));letter.rotation_euler=(0,.12*slow,.08*slow)
        if kind in ('portrait','photo'):
            photo.location=eva['hands'][1].matrix_world.translation+Vector((-.10,-.10,.10));photo.rotation_euler=(0,.08*slow,-.10+.10*slow)
        if kind=='building' and episode>1:
            package.location=davi['hands'][0].matrix_world.translation+Vector((.15,-.10,.12));boxlid.location=package.location+Vector((0,0,.19))
        # Frame the actors above the subtitle safe area; cut between real 3D views.
        shot=int(t/3.6)%3
        if kind=='key' and shot==1:
            target=Vector(key.location)+Vector((0,0,.04));camera.location=target+Vector((.8,-2.4,.50));camera_data.lens=53
        elif kind=='letter' and shot==1:
            target=Vector(letter.location);camera.location=target+Vector((.65,-2.15,.38));camera_data.lens=50
        elif kind=='photo' and shot==1:
            target=Vector(photo.location);camera.location=target+Vector((.5,-2.2,.25));camera_data.lens=50
        elif kind=='door':
            target=Vector((1.0,1.6,1.65));camera.location=(3.8,-3.7,2.6);camera_data.lens=42
        else:
            target=Vector((.1,.4,1.78))
            camera.location=(3.0+.10*slow,-5.5+.12*math.cos(t*.35),2.7)
            camera_data.lens=49 if shot!=2 else 57
            if kind=='building':target=Vector((.35,.65,1.8));camera.location=(3.4,-5.3,2.8)
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        camera_data.keyframe_insert(data_path='lens',frame=frame)
        for obj in animated:keyframe(obj,frame)
        if frame in (1,sample_frames[len(sample_frames)//2],end):
            bpy.context.view_layer.update()
            samples.append({'frame':frame,'camera':list(camera.location),'door_angle':hinge.rotation_euler.z,
                'actors':[{'name':c['root'].name,'head_rotation':list(c['head'].rotation_euler),
                           'upper_arm':list(c['arms'][1].rotation_euler),'wrist_world':list(c['hands'][1].matrix_world.translation),'mouth_scale':list(c['mouth'].scale),
                           'shoe_min_z':min((shoe.matrix_world@Vector(corner)).z for shoe in c['shoes'] for corner in shoe.bound_box)} for c in visible]})
    # Cut changes must not interpolate through the room or through actor heads.
    for frame in range(1,end+1):
        if frame>1 and int(((frame-1)/fps)/3.6)!=int(((frame-2)/fps)/3.6):
            prev=max(f for f in sample_frames if f<frame);nxt=min(f for f in sample_frames if f>=frame)
            scene.frame_set(prev);loc=camera.location.copy();rot=camera.rotation_euler.copy();lens=camera_data.lens
            scene.frame_set(nxt);newloc=camera.location.copy();newrot=camera.rotation_euler.copy();newlens=camera_data.lens
            camera.location=loc;camera.rotation_euler=rot;camera_data.lens=lens;keyframe(camera,frame-1);camera_data.keyframe_insert(data_path='lens',frame=frame-1)
            camera.location=newloc;camera.rotation_euler=newrot;camera_data.lens=newlens;keyframe(camera,frame);camera_data.keyframe_insert(data_path='lens',frame=frame)
    scene.frame_set(1)
    output=Path(config['output']);output.mkdir(parents=True,exist_ok=True)
    (output/'motion-state.json').write_text(json.dumps({'engine':scene.render.engine,'kind':kind,'world_up':'Z','character_front':'-Y',
        'objects':len(scene.objects),'meshes':sum(o.type=='MESH' for o in scene.objects),'frames':end,'fps':fps,'samples':samples,
        'rig':'Hierarchical articulated shoulder, elbow, hip and knee controls; baked object animation; no imported avatar.',
        'mouth':'Procedural opening, not phoneme-aligned lip synchronization.'},indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'scene.blend'))
    scene.render.filepath=str(output/'frame-')
    if config.get('preview_frame'):
        scene.frame_set(config['preview_frame']);scene.render.filepath=str(output/'preview.png');bpy.ops.render.render(write_still=True)
    else:bpy.ops.render.render(animation=True)


if __name__=='__main__':
    configuration=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text(encoding='utf-8-sig'))
    for job in configuration.get('jobs',[configuration]):
        build(job)
        bpy.ops.outliner.orphans_purge(do_recursive=True)
