"""
The MIT License (MIT)

Copyright (c) 2015 Guillermo Romero Franco (AKA Gato)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import math
import pygame
import resources as R
from glcompat import *
import numpy as N
import gltools as glt
from OpenGL.arrays import vbo

mat_params = {'Ka','Kd','Ks','Ns'}

class Material:
    def __init__(self, args={}):
        self._props = args


    def getDiffuseColor(self):
        try:
            return self._props["Kd"]
        except:
            return (0.7,0.7,0.7)


    def getSpecularColor(self):
        try:
            return self._props["Ks"]
        except:
            return (0.8,0.8,0.8)


    def getAmbientColor(self):
        try:
            return self._props["Ka"]
        except:
            return (0.1,0.1,0.1)


    def getSpecularExp(self):
        try:
            return self._props["Ns"][0]
        except:
            return 10.0

    def getTextureBinders(self, loc):
        try:
            return (self._props["texture"].getBinder(0,loc),)
        except:
            return (glt.Texture.getNullTexture().getBinder(0,loc),)



class Materials:

    _default_material = Material()

    def __init__(self, filename = None):
        if filename:
            self.load(filename)

        self._materials_by_name = {}
        self._materials = []


    def load(self, filename):
        contents = {}
        mtl = None
        for line in R.openResource(filename, "rt"):
            if line.startswith('#'): continue
            values = line.split()
            if not values: continue
            if values[0] == 'newmtl':
                mtl = contents[values[1]] = {}
            elif mtl is None:
                raise ValueError, "mtl file doesn't start with newmtl stmt"
            elif values[0] == 'map_Kd':
                # load the texture referred to by this declaration
                mtl["texture"] = glt.Texture(values[1])
            elif values[0] in mat_params:
                mtl[values[0]] = map(float, values[1:])

        for k,v in contents.iteritems():
            if len(v)==0: continue
            # don't overwrite materials
            if k not in self._materials_by_name or self._materials_by_name[k] is None:
                self.setNamedMaterial(k, Material(v))


    # sets a material. Overwrites already there
    def setNamedMaterial(self, mat_name, material):
        try:
            n = self._materials_by_name[mat_name]
            self._materials[n] = material
        except:
            n = len(self._materials)
            self._materials.append(material)
            self._materials_by_name[mat_name] = n

        return n


    def getMaterialIdByName(self, mat_name):
        try:
            return self._materials_by_name[mat_name]
        except:
            return self.setNamedMaterial(mat_name, None) # no material defined for that name


    def getMaterial(self, mat_id):
        try:
            return self._materials[mat_id] or self._default_material
        except:
            return self._default_material


class ObjFile:
    def __init__(self, filename, swapyz=False):
        self._filename = filename
        self.clear()
        self._data_vbo = None
        self._indices_vbo = None
        self._long_index = False
        self._bounds = None

        if filename:
            self.readObj(filename, swapyz)


    def clear(self):
        self._batches = []
        self._has_normals = False
        self._has_tc = False
        self._materials = Materials()

    def hasNormals(self):
        return self._has_normals

    def hasTextureCoords(self):
        return self._has_tc

    def readObj(self, filename, swapyz = False):
        positions = []
        normals = []
        faces = []
        vert_tuple2number = {}
        texcoords = []
        vertices = []

        material = -1
        for line in R.openResource(filename, "rt"):
            if line.startswith('#'): continue
            values = line.split()
            if not values: continue
            if values[0] == 'v':
                v = map(float, values[1:4])
                if swapyz:
                    v = v[0], v[2], v[1]
                positions.append(v)
            elif values[0] == 'vn':
                v = map(float, values[1:4])
                if swapyz:
                    v = v[0], v[2], v[1]
                n = math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])
                if n>0:
                    v[0] /= n
                    v[1] /= n
                    v[2] /= n
                normals.append(v)
            elif values[0] == 'vt':
                texcoords.append(map(float, values[1:3]))
            elif values[0] in ('usemtl', 'usemat'):
                material = self._materials.getMaterialIdByName(values[1])
            elif values[0] == 'mtllib':
                self._materials.load(values[1])
            elif values[0] == 'f':
                tri_v = [0,0,0]
                for i,v in enumerate(values[1:]):
                    w = map(lambda a:int(a) if a else 0,v.split('/'))
                    pos = w[0]
                    tc = w[1] if len(w)>1 else 0
                    n  = w[2] if len(w)>2 else 0

                    if v not in vert_tuple2number:
                        vert_tuple2number[v] = len(vertices)
                        vertices.append((pos-1, n-1, tc-1))

                    vnum = vert_tuple2number[v]

                    # if a face has more than 3 vertices, split it into triangles
                    if i == 0:
                        tri_v[0] = vnum
                    else:
                        tri_v[1],tri_v[2] = tri_v[2],vnum


                    if i >= 2:
                        faces.append((material, tri_v[:]))


        texcoords = N.array(texcoords, dtype="f")
        positions = N.array(positions, dtype="f")
        normals = N.array(normals, dtype="f")


        x_arr = positions[:,0]
        y_arr = positions[:,1]
        z_arr = positions[:,2]

        self._bounds = N.array(((N.min(x_arr),N.min(y_arr),N.min(z_arr)),(N.max(x_arr),N.max(y_arr),N.max(z_arr))),dtype="f")

        self._has_normals = len(normals) > 0
        self._has_tc = len(texcoords) > 0


        self.createBuffers(texcoords, positions, normals, faces, vertices)
        self.resolveMaterials()

    def getBounds(self):
        return self._bounds

    def resolveMaterials(self):
        for i in xrange(len(self._batches)):
            from_face, to_face, mat_id = self._batches[i]
            self._batches[i] = (from_face, to_face, self._materials.getMaterial(mat_id))


    def createBuffers(self, texcoords, positions, normals, faces, vertices):

        faces.sort() #sort by materials

        vertex_items = 3

        if self._has_normals:
            vertex_items += 3

        if self._has_tc:
            vertex_items += 2

        data = N.empty((len(vertices), vertex_items),dtype="f")


        for i,v in enumerate(vertices):
            data[i,0:3] = positions[v[0]]

        p = 3

        if len(normals) > 0:
            for i,v in enumerate(vertices):
                data[i,p:p+3] =normals[v[1]]
            p+=3

        if len(texcoords) > 0:
            for i,v in enumerate(vertices):
                data[i,p:p+2] =texcoords[v[2]]
            p+=2

        total_indices = len(faces)*3

        self._long_index = total_indices > 65535

        indices = N.empty((total_indices,), dtype=N.int32 if self._long_index else N.int16)

        material_id = faces[0][0] # equal to the material of the first face
        material_begin = 0
        i = 0
        n = 0
        for f in faces:
            if material_id != f[0]:
                self._batches.append((material_begin*3, n*3,f[0]))
                material_id = f[0]
                material_begin = n


            indices[i] = f[1][0]
            indices[i+1] = f[1][1]
            indices[i+2] = f[1][2]
            i+=3
            n+=1

        if material_begin != n:
            self._batches.append((material_begin*3, n*3, material_id))


        # create the VBOs
        if self._data_vbo:
            self._data_vbo.bind()
            self._data_vbo.set_array(data)
        else:
            self._data_vbo = vbo.VBO(data, GL_STATIC_DRAW)
            self._data_vbo.bind()

        if self._indices_vbo:
            self._indices_vbo.bind()
            self._indices_vbo.set_array(indices.flatten())
        else:
            self._indices_vbo = vbo.VBO(indices.flatten(), GL_STATIC_DRAW, target=GL_ELEMENT_ARRAY_BUFFER)
            self._indices_vbo.bind()


    def getRenderer(self, shader):
        return ObjRenderer(self, shader)


class ObjRenderer:
    def __init__(self, obj_file, default_shader):
        self._shader = default_shader
        self._obj_file = obj_file

        self._has_normals = False
        self._has_tc = False
        self._normals_loc = -1
        self._tc_loc = -1
        self._pos_loc = -1
        self._stride = 0

        self._diffuse_texture_loc = self._shader.getUniformPos("texture0")
        self._diffuse_color_loc = self._shader.getUniformPos( "mat_diffuse_color")
        self._specular_color_loc = self._shader.getUniformPos("mat_specular_color")
        self._ambient_color_loc = self._shader.getUniformPos( "mat_ambient_color")
        self._specular_exp_loc = self._shader.getUniformPos(  "mat_specular_exp")

        self.checkAttribs()

        self.setupVao()
        self.setupBatches()

        self._elem_index_type = GL_UNSIGNED_INT if self._obj_file._long_index else GL_UNSIGNED_SHORT



    def getObj(self):
        return self._obj_file

    def checkAttribs(self):
        self._normals_ofs = 0
        self._tc_ofs = 0
        self._normals_loc = -1
        self._tc_loc = -1

        self._pos_loc = self._shader.getAttribPos("position")
        p = 3

        if self._obj_file.hasNormals():
            self._normals_loc = self._shader.getAttribPos("normal")
            self._normals_ofs = p # offset increases even if loc == -1
            p += 3
        self._has_normals = self._normals_loc != -1

        if self._obj_file.hasTextureCoords():
            self._tc_loc = self._shader.getAttribPos("tc")
            self._tc_ofs = p # offset increases even if loc == -1
            p += 2
        self._has_tc = self._tc_loc != -1

        self._normals_ofs *= ctypes.sizeof(ctypes.c_float)
        self._tc_ofs *= ctypes.sizeof(ctypes.c_float)
        self._stride = p * ctypes.sizeof(ctypes.c_float)


    def setupVao(self):
        self._vao = glGenVertexArray()

        glBindVertexArray(self._vao)

        self._obj_file._data_vbo.bind()

        # set up the pointers to each component of the vertices
        glEnableVertexAttribArray(self._pos_loc)
        glVertexAttribPointer(self._pos_loc, 3, GL_FLOAT, False, self._stride, None)

        if self._has_normals:
            glEnableVertexAttribArray(self._normals_loc)
            glVertexAttribPointer(self._normals_loc, 3, GL_FLOAT, False, self._stride, ctypes.c_void_p(self._normals_ofs))

        if self._has_tc:
            glEnableVertexAttribArray(self._tc_loc)
            glVertexAttribPointer(self._tc_loc, 2, GL_FLOAT, False, self._stride, ctypes.c_void_p(self._tc_ofs))

        self._obj_file._indices_vbo.bind()

        glBindVertexArray(0)


    def setupBatches(self):
        self._batches = [] # this _batches has more info than the obj_file batches

        idx_size = ctypes.sizeof(ctypes.c_uint32 if self._obj_file._long_index else ctypes.c_uint16)

        for from_vertex,to_vertex, mtl in self._obj_file._batches:
            self._batches.append((
                mtl.getTextureBinders(self._diffuse_texture_loc), # textures
                mtl.getDiffuseColor(),
                mtl.getSpecularColor(),
                mtl.getAmbientColor(),
                mtl.getSpecularExp(),
                to_vertex-from_vertex,  # total vertices
                ctypes.c_void_p(from_vertex * idx_size )  # offset the way OpenGL likes it
            ))


    def draw(self, scene,  transform = None, shader= None):
        if shader is None:
            shader = self._shader

        glBindVertexArray(self._vao)
        shader.begin()

        if transform is not None: scene.pushTransform(transform)

        scene.uploadMatrices(self._shader)
        self._obj_file._indices_vbo.bind() #TODO: check if necessary

        elem_index_type = self._elem_index_type

        for batch in self._batches:
            # bind all the textures in the material
            for tex in batch[0]: tex()

            glUniform3f(self._diffuse_color_loc, *batch[1])
            glUniform3f(self._specular_color_loc, *batch[2])
            glUniform3f(self._ambient_color_loc, *batch[3])
            glUniform1f(self._specular_exp_loc, float(batch[4]))

            glDrawElements(GL_TRIANGLES, batch[5], elem_index_type,batch[6])

        shader.end()

        if transform is not None: scene.popTransform()

        glBindVertexArray(0)

