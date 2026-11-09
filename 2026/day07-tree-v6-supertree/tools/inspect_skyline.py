"""Read-only evaluation of the actual city instances and their footing."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE = Path(__file__).resolve().parents[1]  # the piece folder
ob=bpy.data.objects['PA_GardenAndSkyline']
t=ob.modifiers[0].node_group
out=next(n for n in t.nodes if n.bl_idname=='NodeGroupOutput')
city=None
for n in t.nodes:
 if n.bl_idname!='GeometryNodeInstanceOnPoints' or not n.inputs['Instance'].is_linked:continue
 src=n.inputs['Instance'].links[0].from_node
 if src.bl_idname=='GeometryNodeSetMaterial':
  mat=src.inputs['Material'].default_value
  if mat and 'DistantCityGlass' in mat.name:city=n;break
if city is None:raise RuntimeError('City instance node not found')
real=t.nodes.new('GeometryNodeRealizeInstances');t.links.new(city.outputs['Instances'],real.inputs['Geometry']);t.links.new(real.outputs['Geometry'],out.inputs['Geometry'])
ob.update_tag();bpy.context.view_layer.update()
ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
adj=[[] for _ in mesh.vertices]
for e in mesh.edges:
 a,b=e.vertices;adj[a].append(b);adj[b].append(a)
unseen=set(range(len(adj)));towers=[]
while unseen:
 todo=[unseen.pop()];verts=[]
 while todo:
  a=todo.pop();verts.append(a)
  for b in adj[a]:
   if b in unseen:unseen.remove(b);todo.append(b)
 co=[mesh.vertices[i].co for i in verts]
 towers.append({'x':sum(v.x for v in co)/len(co),'y':sum(v.y for v in co)/len(co),
  'bottom':min(v.z for v in co),'top':max(v.z for v in co),
  'bounds_x':[min(v.x for v in co),max(v.x for v in co)],
  'bounds_y':[min(v.y for v in co),max(v.y for v in co)]})
r={'tower_count':len(towers),'base_z_range':[min(v['bottom'] for v in towers),max(v['bottom'] for v in towers)],
   'city_y_range':[min(v['y'] for v in towers),max(v['y'] for v in towers)],'towers':towers}
ev.to_mesh_clear()
land=next((n for n in t.nodes if n.label=='Continuous distant ground'),None)
if land:
 t.links.new(land.outputs['Geometry'],out.inputs['Geometry'])
 ob.update_tag();bpy.context.view_layer.update()
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 bvh=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],[tuple(f.vertices) for f in mesh.polygons])
 gaps=[];misses=0
 for tower in towers:
  samples=[(tower['x'],tower['y'])]+[(x,y) for x in tower['bounds_x'] for y in tower['bounds_y']]
  for x,y in samples:
   hit=bvh.ray_cast(Vector((x,y,20)),Vector((0,0,-1)),100)[0]
   if hit is None:misses+=1
   else:gaps.append(tower['bottom']-hit.z)
 r['footing_check']={'surface_samples':len(gaps),'missed_ground_samples':misses,
   'base_minus_ground_range_m':[min(gaps),max(gaps)],
   'all_bases_intersect_ground':misses==0 and max(gaps)<=.001}
 r['terrain_bounds']={'x':[min(v.co.x for v in mesh.vertices),max(v.co.x for v in mesh.vertices)],
  'y':[min(v.co.y for v in mesh.vertices),max(v.co.y for v in mesh.vertices)]}
 r['passed']=len(towers)==36 and r['footing_check']['all_bases_intersect_ground']
 ev.to_mesh_clear()
(HERE/'checks'/'skyline-inspection.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if land and not r['passed']:raise RuntimeError('A tower foundation misses the ground')
