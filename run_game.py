import ctypes
import math
import pygame
import random
import sys
from OpenGL.GL import *
from OpenGL.GLU import *


MAX_CUBES = 100
F = ctypes.sizeof(ctypes.c_float)
FP = lambda x: ctypes.cast(x * F, ctypes.POINTER(ctypes.c_float))


class Pos(object):
  def __init__(self, x, y, z):
    self.x = x
    self.y = y
    self.z = z
  def __nonzero__(self):
    return self.x != 0 or self.y != 0 or self.z != 0
  def __len__(self):
    return 3
  def __getitem__(self, i):
    return [self.x, self.y, self.z][i]
  def __mul__(self, o):
    return Pos(self.x * o, self.y * o, self.z * o)
  def __sub__(self, o):
    return Pos(self.x - o.x, self.y - o.y, self.z - o.z)
  def __isub__(self, o):
    self.x -= o.x
    self.y -= o.y
    self.z -= o.z
    return self
  def __iadd__(self, o):
    self.x += o.x
    self.y += o.y
    self.z += o.z
    return self
  def Rotate(self, r):
    if r:
      self.y, self.z = self.y * math.cos(r.x) + self.z * math.sin(r.x), self.z * math.cos(r.x) - self.y * math.sin(r.x)
      self.x, self.z = self.x * math.cos(r.y) + self.z * math.sin(r.y), self.z * math.cos(r.y) - self.x * math.sin(r.y)
      self.x, self.y = self.x * math.cos(r.z) + self.y * math.sin(r.z), self.y * math.cos(r.z) - self.x * math.sin(r.z)


def CubeProgram():
  program = glCreateProgram()
  vertex_shader = glCreateShader(GL_VERTEX_SHADER)
  glShaderSource(vertex_shader, ['''
#version 120

varying vec3 position;
varying vec3 normal;

void main() {
  gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
  position = vec3(gl_ModelViewMatrix * gl_Vertex);
  normal = normalize(gl_NormalMatrix * gl_Normal);
}
  '''])
  fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
  glShaderSource(fragment_shader, ['''
#version 120

varying vec3 position;
varying vec3 normal;

void main() {
  vec3 light = normalize(gl_LightSource[0].position.xyz - position);
  vec4 color = gl_FrontLightProduct[0].diffuse * max(dot(normal, light), 0.0);
  color = clamp(color, 0.0, 1.0);
  gl_FragColor = color;
}
  '''])
  for shader in vertex_shader, fragment_shader:
    glCompileShader(shader)
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
      print 'fail shader', glGetShaderInfoLog(shader)
      sys.exit(1)
    glAttachShader(program, shader)
    glDeleteShader(shader)
  glLinkProgram(program)
  glValidateProgram(program)
  #print glGetProgramInfoLog(program)
  return program


class Cube(Pos):

  def __init__(self, x, y, z):
    super(Cube, self).__init__(x, y, z)
    self.rot = Pos(0, 0, 0)


class Block(object):

  def __init__(self):
    self.p = Cube(0, 0, 0)
    self.t = Cube(0, 0, 0)
    self.cubes = None

  def Cubes(self):
    if self.cubes:
      return self.cubes
    self.cubes = [Pos(0, 0, 0), Pos(-1, 0, 0), Pos(1, 0, 0), Pos(0, 1, 0)]
    for cube in self.cubes:
      cube.rot = self.p.rot
      cube.Rotate(cube.rot)
      cube += self.p
    return self.cubes

  def Drop(self):
    self.t.y -= 1
    self.p = self.t
    self.cubes = None

  def Update(self):
    dt = self.t - self.p
    self.p += dt * 0.1
    dr = self.t.rot - self.p.rot
    self.p.rot += dr * 0.01
    self.cubes = None


class Game(object):

  def __init__(self):
    self.cam = Pos(-1, -10, -10)
    self.blocks = [Block()]

  def Start(self):
    pygame.init()
    width, height = 800, 600
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 16)
    screen = pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.display.set_caption('Space Bear Cathedrals')
    glViewport(0, 0, width, height)

    self.cube_vbo = (ctypes.c_float * (2 * 3 * 4 * 6 * MAX_CUBES))()
    self.cube_vbo_id = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, self.cube_vbo_id)
    glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.cube_vbo), self.cube_vbo, GL_DYNAMIC_DRAW)
    self.cube_program = CubeProgram()
    glEnable(GL_DEPTH_TEST)
    glLightfv(GL_LIGHT0, GL_POSITION, (ctypes.c_float * 3)(0, 3, 0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (ctypes.c_float * 3)(2, 1, 0))

    clock = pygame.time.Clock()
    while True:
      clock.tick(60)
      # Update.
      for e in pygame.event.get():
        if e.type == pygame.QUIT or e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
          return pygame.quit()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_LEFT:
          self.blocks[-1].t.x -= 1
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_RIGHT:
          self.blocks[-1].t.x += 1
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_UP:
          self.blocks[-1].t.rot.z += math.pi / 2
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_DOWN:
          self.blocks[-1].Drop()
      self.keys = pygame.key.get_pressed()
      self.blocks[-1].Update()

      # Render.
      glClearColor(1, 1, 1, 0)
      glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)
      glMatrixMode(GL_PROJECTION)
      glLoadIdentity()
      #gluPerspective(45.0, 1.2, 0.1, 100.0)
      glFrustum(-0.8, 0.8, -0.6, 0.6, 1, 100)
      glMatrixMode(GL_MODELVIEW)
      glLoadIdentity()
      glRotate(30, 1, 0, 0)
      glTranslate(self.cam.x, self.cam.y, self.cam.z)
      self.DrawCubes()
      pygame.display.flip()

  def DrawCubes(self):
    i = 0
    for block in self.blocks:
      for cube in block.Cubes():
        for dim in range(3):
          for c in -1, 1:
            for a, b in (-1, -1), (-1, 1), (1, 1), (1, -1):
              d = Pos(*[a, b, c, a, b][dim:dim + 3])
              n = Pos(*[0, 0, c, 0, 0][dim:dim + 3])
              d.Rotate(cube.rot)
              n.Rotate(cube.rot)
              for j in range(3):
                self.cube_vbo[i + j] = cube[j] + 0.49 * d[j]
                self.cube_vbo[i + j + 3] = n[j]
              i += 6
    glBufferSubData(GL_ARRAY_BUFFER, 0, ctypes.sizeof(self.cube_vbo), self.cube_vbo)
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glVertexPointer(3, GL_FLOAT, 6 * F, FP(0))
    glNormalPointer(GL_FLOAT, 6 * F, FP(3))
    glUseProgram(self.cube_program)
    glDrawArrays(GL_QUADS, 0, i)

Game().Start()
