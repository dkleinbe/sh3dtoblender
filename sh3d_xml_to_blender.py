#  ########################################################################
#
#   SweetHome3D XML to Blender inporter
#
#  ########################################################################
#
#   Copyright (c) : 2018  Luis Claudio Gambôa Lopes
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2, or (at your option)
#   any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#   For e-mail suggestions :  lcgamboa@yahoo.com
#  ######################################################################## */

# How to use:
#   1-Open Sweethome 3D  http://www.sweethome3d.com
#   2-Create or open a existent house
#   3-Use the plugin EXPORT to XML http://www.sweethome3d.com/support/forum/viewthread_thread,6708
#   4-Open blender 
#   5-Choose Text Editor window and open sh3d_xml_to_blender.py script
#   6-Run the script, in the File dialog choose the zip file generate by SweetHome 3D EXPORT to HTML5 plugin
   
# It's possible use the imported model with blender render and blender engine (the script add Logic blocks for FPS game like behavior)
# To render with blender cycles it's necessary inport the materials. Try use https://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Material/Blender_Cycles_Materials_Converter

from zipfile import ZipFile
from xml.etree import cElementTree as ElementTree
from collections import namedtuple
from urllib.parse import unquote
    
import os
import math
import bpy
import mathutils
import struct
import shutil
import logging

scale=0.01
speed=0.5


logger = logging.getLogger('my_logger')
logger.debug('effective level' + str(logger.getEffectiveLevel()))

class OpenFile(bpy.types.Operator):
  bl_idname = "object.openfile"
  bl_label = "Open"
  filename_ext = ".zip"
  filter_glob = bpy.props.StringProperty(default='*.zip', options={'HIDDEN'}, maxlen=255)

 
  filepath = bpy.props.StringProperty(subtype="FILE_PATH")

  #Recursivly transverse layer_collection for a particular name
  def recurLayerCollection(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found

  def setActiveCollection(collName) :
    #Change the Active LayerCollection to 'Another Collection'
    layer_collection = bpy.context.view_layer.layer_collection
    layerColl = recurLayerCollection(layer_collection, 'Another Collection')
    bpy.context.view_layer.active_layer_collection = layerColl

  def calcBounds(self, verts):
    """Calculates the bounding box for selected vertices. Requires applied scale to work correctly. """

    # [+x, -x, +y, -y, +z, -z]
    v = verts[0]
    bounds = [v[0], v[0], v[1], v[1], v[2], v[2]]

    for v in verts:
      if bounds[0] < v[0]:
          bounds[0] = v[0]
      if bounds[1] > v[0]:
          bounds[1] = v[0]
      if bounds[2] < v[1]:
          bounds[2] = v[1]
      if bounds[3] > v[1]:
          bounds[3] = v[1]
      if bounds[4] < v[2]:
          bounds[4] = v[2]
      if bounds[5] > v[2]:
          bounds[5] = v[2]
    return bounds

  def execute(self, context):
      
    zip_name=self.filepath

    #file paths ans zip extraction dirs

    zip_path = os.path.abspath(zip_name)
    zip_dir = os.path.dirname(zip_path)
    self.xml_path = os.path.join(zip_dir, 'xml')

    #remove old files
    shutil.rmtree(self.xml_path,True)
    
    #unzip files
    with ZipFile(zip_path, 'r') as zip_file:
       zip_file.extractall(self.xml_path)


    #clear scene
    bpy.data.scenes["Scene"].unit_settings.scale_length=1.0
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    #clear collections
    colls = bpy.data.collections
    for coll in colls:
      bpy.data.collections.remove(coll)

    #clear images
    imgs = bpy.data.images
    for image in imgs:
        image.user_clear()

    #clear materials
    for material in bpy.data.materials:
        material.user_clear()
        bpy.data.materials.remove(material)    
        
    #clear textures
    textures = bpy.data.textures
    for tex in textures:
        tex.user_clear()
        bpy.data.textures.remove(tex)


    #read xml and files
    xmlPath = os.path.join(self.xml_path,'Home.xml')
    xmlRoot = ElementTree.parse(xmlPath).getroot()
    #
    # Create collections
    #
    self.collections = {
      'home' : bpy.data.collections.new(name="Home"),
      'structure' : bpy.data.collections.new(name="Structure"),
      'doorOrWindow' : bpy.data.collections.new(name="DoorsOrWindows"),
      'pieceOfFurniture' : bpy.data.collections.new(name="Furnitures"),
      'light' : bpy.data.collections.new(name="Lights"),
      'library' : bpy.data.collections.new(name="Library"),
      } # create home collections
    
    # link collections to scene
    # Home
    #  | Structure
    #  | DoorsOrWindows
    #  | Furnitures
    #  | Lights
    #  | ... groups
    #
    for collec in self.collections.values() :
      if 'Home' in collec.name :
        context.scene.collection.children.link(collec)
      elif 'Library' in collec.name :
        context.scene.collection.children.link(collec)
      else :
        self.collections['home'].children.link(collec)

    #
    # read house structure
    #
    filename=os.path.join(self.xml_path,xmlRoot.get('structure'))
    bpy.ops.import_scene.obj(filepath=filename, use_split_objects=True)
    obs = bpy.context.selected_editable_objects[:] 
    # apply rotation
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
    
    bpy.context.view_layer.objects.active=obs[0]
    #bpy.ops.object.join()
    for o in obs:
      bpy.context.view_layer.objects.active=o
      #o.name=xmlRoot.get('name')
      o.dimensions=o.dimensions*scale
      o.location=(0.0, 0.0, 0.0)
      bpy.ops.object.shade_flat()
      
      # Remove structure from all collection
      for coll in o.users_collection:
        coll.objects.unlink(o)
      # add structure to collections
      self.collections['structure'].objects.link(o) # Home structure
      #self.collections['home'].objects.link(o) # Home structure

    Level = namedtuple("Level", "id elev ft")
    levels=[]

    self.LoadObjectTree(xmlRoot, self.collections['home'])

    obj = bpy.data.objects['Porte ouverte']
    logger.debug("+ Porte ouverte location")   
    logger.debug(obj.location)

    logger.info('END SH3D_2_BLENDER')

    return {'FINISHED'}

  def LoadObjectTree(self, xmlRoot, collection):

    obs = []

    for element in xmlRoot:
      objectType = element.tag

      if objectType == 'level':
         levels.append(Level(id=element.get('id'),elev=float(element.get('elevation')),ft=float(element.get('floorThickness'))))
      #
      # furniture group     
      #
      if objectType == 'furnitureGroup':

        groupColl = bpy.data.collections.new(name=element.get('name'))
        collection.children.link(groupColl)
        # TODO: manage visibility
        if 'visible' in element.keys() and False :
          if element.get('visible') == 'false': 
            groupColl.hide_viewport = True

        # recursive call to load children    
        self.LoadObjectTree(element, groupColl)
         
      
      elif 'model' in element.keys():  
       
        filename=os.path.join(self.xml_path,unquote(element.get('model')))
        filename = filename.replace('/', '\\')
        dimX = float(element.get('width'))
        dimZ = float(element.get('height'))
        dimY = float(element.get('depth')) 
        
        locX = float(element.get('x'))*scale
        locY = -float(element.get('y'))*scale
        
        lve=0.0
        if 'level' in element.keys():
          for lv in levels:
            if lv.id == element.get('level'):
              lve=(lv.elev)*scale

        del obs[:]
        # deselect all
        bpy.ops.object.select_all(action='DESELECT')
        #
        # search for element in the collection
        # if exist create a linked copy
        # else load the object
        name = element.get('name')
        logger.info("+==============================================")
        
        logger.info('+ Importing <%s>', name)
        isTemplate = False

        if self.collections['library'].objects.find(name) != -1 :
            obj = bpy.data.objects[name].copy()
            obs.append(obj)
            obs[0].location = (0, 0, 0)
            
            logger.info('+ instancing object <%s>', name)      

        else:

            logger.info('+ loading object <%s>', filename)
            isTemplate = True
            bpy.ops.import_scene.obj(filepath=filename)
            obs = bpy.context.selected_editable_objects[:] 
            obs[0].name=name
        
            bpy.context.view_layer.objects.active=obs[0]

            bpy.ops.object.join()
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='BOUNDS')  
            
            logger.debug("+ location")   
            logger.debug(obs[0].location)
            
            obs[0].location = (0, 0, 0)
            
            logger.debug("+ applying rotation") 
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
            logger.debug(obs[0].rotation_euler)

        bpy.context.view_layer.objects.active=obs[0]

        # Remove object from all collection
        for coll in obs[0].users_collection:
          coll.objects.unlink(obs[0])
        #
        # Link object to collection
        #
        if 'Home' in collection.name :
          self.collections[objectType].objects.link(obs[0]) 
        else :
          collection.objects.link(obs[0])
        # if object is not an instance add it to library
        if isTemplate is True :
          self.collections['library'].objects.link(obs[0])

        # Set active object
        obs[0].select_set(True)

        bpy.context.view_layer.objects.active=obs[0]  
        logger.debug("+ Active type")
        logger.debug(type(bpy.context.view_layer.objects.active))

        # 
        # TODO: manage visibility
        #
        if 'visible' in element.keys() and False :
          if element.get('visible') == 'false': 
            obs[0].hide_viewport = True
        #
        # mirrored model
        #
        if 'modelMirrored' in element.keys() :
          if element.get('modelMirrored') == 'true':

            bpy.ops.transform.mirror(constraint_axis=(True, False, False),orient_type='GLOBAL', use_proportional_edit=False)
        #
        # rotated model
        #
        if 'modelRotation' in element.keys():
          value=element.get('modelRotation')
          va=value.split()
          
          mat_rot = mathutils.Matrix()

          mat_rot[0][0]=float(va[0])
          mat_rot[0][1]=float(va[1])
          mat_rot[0][2]=float(va[2])
          mat_rot[1][0]=float(va[3])
          mat_rot[1][1]=float(va[4])
          mat_rot[1][2]=float(va[5])
          mat_rot[2][0]=float(va[6])
          mat_rot[2][1]=float(va[7])
          mat_rot[2][2]=float(va[8])

          ob = bpy.context.object   
          ob.matrix_world = mat_rot
         
          bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
          
          ob.rotation_euler=(math.pi/2,0.0,0.0)   
        #  
        # TODO: if 'backFaceShown' in element.keys():
        #TODO    

        #
        # set dimmensions
        #
        obs[0].dimensions=(dimX*scale,dimY*scale,dimZ*scale)        

        # reset delta center
        delta_center = [0.0, 0.0, 0.0]
        fixCenter = False
        #
        # angle
        #
        if 'angle' in element.keys():
          angle = element.get('angle') 
          obs[0].rotation_euler[2] = -float(angle)
          fixCenter = True
        else:   
          obs[0].rotation_euler[2] = 0.0
        #
        # pitch
        #
        if 'pitch' in element.keys() :
          pitch = element.get('pitch') 
          obs[0].rotation_euler[0] = -float(pitch)
          fixCenter = True
        else:
          obs[0].rotation_euler[0] = 0.0
          height = dimZ * scale
        #
        # Compute correct height and new center with after angle and pitch rotation
        #
        if fixCenter :
          logger.debug(obs[0].rotation_euler)
          # update to get correct transform
          bpy.context.view_layer.update()
          logger.debug(obs[0].rotation_euler)
          
          # transform vertices to world space to compute correct height
          #   a faire seulement si pitch != 0 sinon height = dimY/2*scale
          wvertices = [obs[0].matrix_world @ mathutils.Vector(v.co) for v in obs[0].data.vertices]

          # get bounds in world space
          bounds = self.calcBounds(wvertices)
          logger.debug("+ bounds:")
          logger.debug(bounds)

          # get height
          zmin = bounds[5]
          zmax = bounds[4]
          height = zmax - zmin

          logger.debug("+ dimX: " + str(dimX) + " dimY: " + str(dimY) + " dimZ: " + str(dimZ))
          logger.debug("+ scale: " + str(scale))
          logger.debug("+ height: " + str(height))

          # compute delta center
          delta_center = [
            -bounds[0] - (bounds[1] - bounds[0]) / 2.0,
            -bounds[2] - (bounds[3] - bounds[2]) / 2.0,
            -bounds[4] - (bounds[5] - bounds[4]) / 2.0]
          logger.debug(delta_center)

        #
        # adjust Z value
        #
        if 'elevation' in element.keys():
          locZ= (height/2.0)+(float(element.get('elevation'))*scale)+lve 
          logger.debug("+ elevation: " + element.get('elevation'))
          logger.debug("+ lve: " + str(lve))
          logger.debug("+ locZ: " + str(locZ))
        else:    
          locZ= (height/2.0)+lve
 
        #
        # set location
        #
        logger.debug("+ location: " + str(locX) + " | " + str(locY) + " | " + str(locZ))

        obs[0].location=(locX + delta_center[0], locY + delta_center[1], locZ + delta_center[2])

        logger.debug(obs[0].location)
        #
        # color
        #
        if 'color' in element.keys():
          color = element.get('color') 
          r=int(color[2:4],16)/255.0
          g=int(color[4:6],16)/255.0
          b=int(color[6:8],16)/255.0
          bcolor=[r,g,b,1.0]
          for material in bpy.context.active_object.data.materials:
            material.diffuse_color=bcolor
        #
        # search for texture or materials
        #
        for prop in element:
          if prop.tag == 'texture' and False:
              image=prop.get('image')
              for material in bpy.context.active_object.data.materials:
                  img = bpy.data.images.load(os.path.join(self.xml_path,image))
                  tex = bpy.data.textures.new(image, type = 'IMAGE')
                  tex.image = img        
                  mtex = material.texture_slots.add()
                  mtex.texture = tex
              
          if prop.tag == 'material':
              mname=prop.get('name')
              if 'color' in prop.keys():
                color = prop.get('color') 
                r=int(color[2:4],16)/255.0
                g=int(color[4:6],16)/255.0
                b=int(color[6:8],16)/255.0
                bcolor=[r,g,b,0]

                logger.debug("+ material:color: ")
            
                for material in obs[0].data.materials:
                  if mname in material.name: 
                    material.diffuse_color=bcolor
        
              #face texture of material
              for texture in prop:
                if texture.tag == 'texture' :  
                  image=texture.get('image')
                  for material in bpy.context.active_object.data.materials:
                    if mname in material.name: 
                      
                      # if image not already loaded
                      if image not in bpy.data.images :
                        logger.debug("+ Image loading: " + image)
                        img = bpy.data.images.load(os.path.join(self.xml_path,image))
                      else :
                        logger.debug("+ Image already loaded: " + image)
                        img = bpy.data.images[image]

                      material.use_nodes = True
                      bsdf = material.node_tree.nodes["Principled BSDF"]
                      #tex = bpy.data.textures.new(image, type = 'IMAGE')
                      tex = material.node_tree.nodes.new('ShaderNodeTexImage')
                      tex.image = img

                      material.node_tree.links.new(bsdf.inputs['Base Color'], tex.outputs['Color'])
                
      
      if objectType in ('light'):   
        owner=bpy.context.active_object    
       
        power= float(element.get('power'))       
  
        # FIXME: Disabled for now
        for light in element:
          if light.tag == 'lightSource' and False:       
            color=light.get('color')
            r=int(color[2:4],16)/255.0
            g=int(color[4:6],16)/255.0
            b=int(color[6:8],16)/255.0
            bcolor=[r,g,b]
            lposx=(float(light.get('x'))-0.5)*dimX*scale*2.1
            lposy=(float(light.get('y'))-0.5)*dimY*scale*2.1
            lposz=(float(light.get('z'))-0.5)*dimZ*scale*2.1
                
            bpy.ops.object.lamp_add(type='POINT',location=(lposx, lposy, lposz))
            bpy.context.active_object.data.energy=4000.0*power*scale
            bpy.context.active_object.data.shadow_method='RAY_SHADOW'
            bpy.context.active_object.data.color=bcolor
            bpy.context.active_object.data.distance=10*scale
            bpy.context.active_object.parent=owner
            bpy.context.active_object.layers[3]= True
            bpy.context.active_object.layers[0]= False
            bpy.context.active_object.layers[1]= False
            bpy.context.active_object.layers[2]= False

        
    #insert camera  
     # FIXME: Disabled for now
      if objectType in ('observerCamera') and False: 
       if element.get('attribute') == 'observerCamera':
        locX = float(element.get('x'))*scale
        locY = -float(element.get('y'))*scale
        locZ = float(element.get('z'))*scale
        yaw = float(element.get('yaw'))
        pitch = float(element.get('pitch'))
        
        
        bpy.ops.object.camera_add(location=(locX, locY, locZ),rotation=((-pitch/8.0)+(-math.pi/2.0),math.pi,0))
        bpy.ops.mesh.primitive_cube_add(location=(locX, locY, locZ-(170.0*scale/2.0)),rotation=(0.0,0.0,-yaw))
        
        obs = bpy.context.selected_editable_objects[:] 
        #bpy.context.scene.objects.active=obs[0]
        bpy.context.view_layer.objects.active=obs[0]
        obs[0].name='player'
        obs[0].dimensions=(40*scale,20*scale,170.0*scale)
        
        bpy.data.objects["Camera"].parent=bpy.data.objects["player"]
        bpy.data.objects["Camera"].location=(0.0,-30.0*scale,22*scale)
        
        #bpy.data.objects["player"].game.physics_type='CHARACTER'
        #bpy.data.objects["player"].game.use_collision_bounds=True
        #bpy.data.objects["player"].game.step_height=0.8
        
        
        #add logic blocks
        obj=bpy.data.objects["player"]
        cam=bpy.data.objects["Camera"]
        
        #foward
        bpy.ops.logic.sensor_add(type="KEYBOARD", object="player")
        bpy.ops.logic.controller_add(type="LOGIC_AND", object="player")
        bpy.ops.logic.actuator_add(type="MOTION", object="player")
        
        obj.game.sensors[-1].link(obj.game.controllers[-1])
        obj.game.actuators[-1].link(obj.game.controllers[-1])
        
        obj.game.sensors[-1].name="w"
        obj.game.sensors[-1].key="W"
        obj.game.actuators[-1].offset_location[1]=-speed
        
        #backward
        bpy.ops.logic.sensor_add(type="KEYBOARD", object="player")
        bpy.ops.logic.controller_add(type="LOGIC_AND", object="player")
        bpy.ops.logic.actuator_add(type="MOTION", object="player")
        
        obj.game.sensors[-1].link(obj.game.controllers[-1])
        obj.game.actuators[-1].link(obj.game.controllers[-1])
        
        obj.game.sensors[-1].name="s"
        obj.game.sensors[-1].key="S"
        obj.game.actuators[-1].offset_location[1]=speed
        
        #left
        bpy.ops.logic.sensor_add(type="KEYBOARD", object="player")
        bpy.ops.logic.controller_add(type="LOGIC_AND", object="player")
        bpy.ops.logic.actuator_add(type="MOTION", object="player")
        
        obj.game.sensors[-1].link(obj.game.controllers[-1])
        obj.game.actuators[-1].link(obj.game.controllers[-1])
        
        obj.game.sensors[-1].name="a"
        obj.game.sensors[-1].key="A"
        obj.game.actuators[-1].offset_location[0]=speed  
        
        #right
        bpy.ops.logic.sensor_add(type="KEYBOARD", object="player")
        bpy.ops.logic.controller_add(type="LOGIC_AND", object="player")
        bpy.ops.logic.actuator_add(type="MOTION", object="player")
        
        obj.game.sensors[-1].link(obj.game.controllers[-1])
        obj.game.actuators[-1].link(obj.game.controllers[-1])
        
        obj.game.sensors[-1].name="d"
        obj.game.sensors[-1].key="D"
        obj.game.actuators[-1].offset_location[0]=-speed        
        
        #jump
        bpy.ops.logic.sensor_add(type="KEYBOARD", object="player")
        bpy.ops.logic.controller_add(type="LOGIC_AND", object="player")
        bpy.ops.logic.actuator_add(type="MOTION", object="player")
        
        obj.game.sensors[-1].link(obj.game.controllers[-1])
        obj.game.actuators[-1].link(obj.game.controllers[-1])
        
        obj.game.sensors[-1].name="space"
        obj.game.sensors[-1].key="SPACE"
        obj.game.actuators[-1].mode='OBJECT_CHARACTER'
        obj.game.actuators[-1].use_character_jump=True
        
        #mouse view
        bpy.ops.logic.sensor_add(type="MOUSE", object="player")
        bpy.ops.logic.controller_add(type="LOGIC_AND", object="player")
        bpy.ops.logic.actuator_add(type="MOUSE", object="player")
      
        
        obj.game.sensors[-1].link(obj.game.controllers[-1])
        obj.game.actuators[-1].link(obj.game.controllers[-1])
        
        obj.game.sensors[-1].mouse_event='MOVEMENT'
        
        obj.game.actuators[-1].mode='LOOK'
        obj.game.actuators[-1].sensitivity_y=0.0
        
        
        
        bpy.ops.logic.actuator_add(type="MOUSE", object="Camera")
        cam.game.actuators[-1].link(obj.game.controllers[-1]) 
        
        cam.game.actuators[-1].mode='LOOK'
        cam.game.actuators[-1].sensitivity_x=0.0
        
    
    #world settings
    if False:
        bpy.data.worlds["World"].light_settings.use_ambient_occlusion=True
        bpy.data.worlds["World"].light_settings.ao_factor=0.01
        bpy.data.worlds["World"].light_settings.use_environment_light=True
        bpy.data.worlds["World"].light_settings.environment_energy=0.01
        
        bpy.data.scenes["Scene"].unit_settings.system='METRIC'
        bpy.data.scenes["Scene"].unit_settings.scale_length=0.01/scale
        bpy.data.scenes["Scene"].layers[0]=True
        bpy.data.scenes["Scene"].layers[1]=True
        bpy.data.scenes["Scene"].layers[2]=True
        bpy.data.scenes["Scene"].layers[3]=True
        
    return {'FINISHED'}


 
  def invoke(self, context, event):
      context.window_manager.fileselect_add(self)
      return {'RUNNING_MODAL'}
 
 
bpy.utils.register_class(OpenFile)
 
bpy.ops.object.openfile('INVOKE_DEFAULT')
