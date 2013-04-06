import ctypes
import math
import os
import pygame
import random
import sys
from OpenGL.GL import *
from OpenGL.GLU import *


MAX_CUBES = 1000
F = ctypes.sizeof(ctypes.c_float)
FP = lambda x: ctypes.cast(x * F, ctypes.POINTER(ctypes.c_float))


class Pos(object):
  def __init__(self, x, y, z):
    self.x = x
    self.y = y
    self.z = z
  def Copy(self):
    return Pos(self.x, self.y, self.z)
  def __hash__(self):
    return hash(tuple(self))
  def __eq__(self, o):
    return tuple(self) == tuple(o)
  def __nonzero__(self):
    return self.x != 0 or self.y != 0 or self.z != 0
  def __len__(self):
    return 3
  def __getitem__(self, i):
    if i == 0: return self.x
    elif i == 1: return self.y
    elif i == 2: return self.z
    else: raise IndexError()
  def __mul__(self, o):
    return Pos(self.x * o, self.y * o, self.z * o)
  def __add__(self, o):
    return Pos(self.x + o.x, self.y + o.y, self.z + o.z)
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
  def __imul__(self, o):
    self.x *= o
    self.y *= o
    self.z *= o
    return self
  def __gt__(self, o):
    return any(abs(s) > o for s in self)
  def Rotate(self, rot):
    rx = rot.x * math.pi / 180
    ry = rot.y * math.pi / 180
    rz = rot.z * math.pi / 180
    self.y, self.z = self.y * math.cos(rx) + self.z * math.sin(rx), self.z * math.cos(rx) - self.y * math.sin(rx)
    self.x, self.z = self.x * math.cos(ry) + self.z * math.sin(ry), self.z * math.cos(ry) - self.x * math.sin(ry)
    self.x, self.y = self.x * math.cos(rz) + self.y * math.sin(rz), self.y * math.cos(rz) - self.x * math.sin(rz)
  def Round(self):
    return Pos(round(self.x), round(self.y), round(self.z))
  def __abs__(self):
    return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

DOWN = Pos(0, -1, 0)
UP = Pos(0, 1, 0)
LEFT = Pos(-1, 0, 0)
RIGHT = Pos(1, 0, 0)
FRONT = Pos(0, 0, 1)
BACK = Pos(0, 0, -1)

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
  def Copy(self):
    c = Cube(self.x, self.y, self.z)
    c.rot = self.rot.Copy()
    return c


class Qube(Pos):
  def __init__(self, x, y, z):
    super(Qube, self).__init__(x, y, z)
    self.quat = Quat(0, 0, 0, 1)
  def Copy(self):
    c = Qube(self.x, self.y, self.z)
    c.quat = self.quat.Copy()
    return c
  def Apply(self, p):
    p = p.Copy()
    p = self.quat.Rotate(p)
    p += self
    return p
  def Matrix(self):
    m = self.quat.Matrix()
    m[12] += self.x
    m[13] += self.y
    m[14] += self.z
    return m
  def InverseMatrix(self):
    m = self.quat.Conj().Matrix()
    r = self.quat.Conj().Rotate(self)
    m[12] -= r.x
    m[13] -= r.y
    m[14] -= r.z
    return m


class Quat(object):
  @staticmethod
  def FromAngle(degrees, x, y, z):
    r = degrees * math.pi / 180 / 2
    return Quat(x * math.sin(r), y * math.sin(r), z * math.sin(r), math.cos(r))
  def __init__(self, x, y, z, w):
    self.x = x
    self.y = y
    self.z = z
    self.w = w
  def Copy(self):
    return Quat(self.x, self.y, self.z, self.w)
  def Normalized(self):
    l = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w)
    return Quat(self.x / l, self.y / l, self.z / l, self.w / l)
  def __mul__(a, b):
    return Quat(a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
                a.w * b.y + a.y * b.w + a.z * b.x - a.x * b.z,
                a.w * b.z + a.z * b.w + a.x * b.y - a.y * b.x,
                a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z)
  def Conj(self):
    return Quat(-self.x, -self.y, -self.z, self.w)
  def Rotate(self, v):
    result = self.Conj() * Quat(v.x, v.y, v.z, 0) * self
    return Pos(result.x, result.y, result.z)
  def Matrix(self):
    x2 = self.x * self.x
    y2 = self.y * self.y
    z2 = self.z * self.z
    xy = self.x * self.y
    xz = self.x * self.z
    xw = self.x * self.w
    yz = self.y * self.z
    yw = self.y * self.w
    zw = self.z * self.w
    return (ctypes.c_float * 16)(1 - 2 * (y2 + z2), 2 * (xy - zw), 2 * (xz + yw), 0,
                                 2 * (xy + zw), 1 - 2 * (x2 + z2), 2 * (yz - xw), 0,
                                 2 * (xz - yw), 2 * (yz + xw), 1 - 2 * (x2 + y2), 0,
                                 0, 0, 0, 1)


class Block(object):

  def __init__(self):
    self.p = Cube(0, 0, 0)
    self.t = Cube(0, 0, 0)
    self.shape = random.choice([
        [Cube(0, 0, 0), Cube(-1, 0, 0), Cube(1, 0, 0), Cube(0, 1, 0)],
        [Cube(0, 0, 0), Cube(-1, 0, 0), Cube(1, 0, 0), Cube(2, 0, 0)],
        [Cube(0, 0, 0), Cube(-1, 0, 0), Cube(0, 1, 0), Cube(1, 1, 0)],
        [Cube(0, 0, 0), Cube(-1, 0, 0), Cube(-2, 0, 0), Cube(0, 1, 0)],
        ])
    self.rendered = 0

  def Cubes(self):
    return self.At(self.p)

  def Logical(self):
    return [c.Round() for c in self.At(self.t)]

  def At(self, p):
    cubes = [c.Copy() for c in self.shape]
    for cube in cubes:
      cube.rot = p.rot
      cube.Rotate(cube.rot)
      cube += p
    return cubes

  def Update(self):
    dt = self.t - self.p
    dr = self.t.rot - self.p.rot
    if dt > 0.01 or dr > 1:
      self.p += dt * 0.1
      self.p.rot += dr * 0.1
      self.rendered = 0


class Object(list):
  def __init__(self):
    super(Object, self).__init__()
    self.p = Qube(0, 0, 0)
    self.v = Qube(0, 0, 0)
    self.cube_vbo = None

  def Update(self):
    self.p.quat *= self.v.quat
    self.p += self.v

  def Render(self):
    if self.cube_vbo is None:
      self.cube_vbo = (ctypes.c_float * (2 * 3 * 4 * 6 * MAX_CUBES))()
      self.cube_vbo_id = glGenBuffers(1)
      glBindBuffer(GL_ARRAY_BUFFER, self.cube_vbo_id)
      glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.cube_vbo), self.cube_vbo, GL_DYNAMIC_DRAW)
    i = 0
    changed = False
    for block in self:
      if block.rendered:
        i += block.rendered * 6 * 4 * 6
        continue
      changed = True
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
        block.rendered += 1
    glBindBuffer(GL_ARRAY_BUFFER, self.cube_vbo_id)
    glPushMatrix()
    glMultMatrixf(self.p.Matrix())
    if changed:
      glBufferSubData(GL_ARRAY_BUFFER, 0, ctypes.sizeof(self.cube_vbo), self.cube_vbo)
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glVertexPointer(3, GL_FLOAT, 6 * F, FP(0))
    glNormalPointer(GL_FLOAT, 6 * F, FP(3))
    glDrawArrays(GL_QUADS, 0, i / 6)
    glPopMatrix()


def RandomObject():

  def AddBlock(p):
    b = Block()
    b.shape = [Cube(0, 0, 0)]
    b.p = p.Copy()
    b.t = p.Copy()
    o.append(b)
    logical.add(p.Copy())

  o = Object()
  logical = set()
  p = Cube(0, 0, 0)
  AddBlock(p)
  while random.random() < 0.95:
    p += random.choice([UP, DOWN, LEFT, RIGHT, FRONT, BACK])
    if p not in logical:
      AddBlock(p)
  return o


def Music(filename):
  if os.path.exists(filename):
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

class Game(object):

  def __init__(self):
    self.cam = Qube(1, 10, 10)
    self.cam.quat = Quat.FromAngle(30, 1, 0, 0)
    self.camt = self.cam.Copy()
    self.update_func = self.Build
    self.blocks = Object()
    self.objects = [self.blocks]
    self.logical = set()
    self.falling = Block()
    self.falling.p.y += 10
    self.falling.t.y += 10
    self.blocks.append(self.falling)

  def Start(self):
    pygame.init()
    width, height = 800, 600
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 16)
    screen = pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF | pygame.HWSURFACE)
    pygame.display.set_caption('Space Bear Cathedrals')
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glFrustum(-0.8, 0.8, -0.6, 0.6, 1, 500)
    glMatrixMode(GL_MODELVIEW)

    glUseProgram(CubeProgram())
    glEnable(GL_DEPTH_TEST)
    glLightfv(GL_LIGHT0, GL_POSITION, (ctypes.c_float * 3)(0, 3, 0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (ctypes.c_float * 3)(2, 1, 0))
    glClearColor(0.2, 0.3, 0.4, 0)

    clock = pygame.time.Clock()
    while True:
      clock.tick(60)
      self.update_func()
      glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)
      glLoadIdentity()
      glMultMatrixf(self.cam.InverseMatrix())
      for obj in self.objects:
        obj.Render()
      pygame.display.flip()

  def Build(self):
    for block in self.blocks:
      block.Update()
    self.cam += (self.camt - self.cam) * 0.1
    for e in pygame.event.get():
      if e.type == pygame.QUIT or e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
        pygame.quit()
        sys.exit(0)
      elif e.type == pygame.KEYDOWN and e.key == pygame.K_LEFT and not any(p + LEFT in self.logical for p in self.falling.Logical()):
        self.falling.t += LEFT
      elif e.type == pygame.KEYDOWN and e.key == pygame.K_RIGHT and not any(p + RIGHT in self.logical for p in self.falling.Logical()):
        self.falling.t += RIGHT
      elif e.type == pygame.KEYDOWN and e.key == pygame.K_UP:
        self.falling.t.rot.z += 90
        if any(p in self.logical or p.y < 0 for p in self.falling.Logical()):  # Oops, undo.
          self.falling.t.rot.z -= 90
      elif e.type == pygame.KEYDOWN and e.key == pygame.K_DOWN:
        if any(p + DOWN in self.logical or p.y == 0 for p in self.falling.Logical()):
          for p in self.falling.Logical():
            self.logical.add(p)
          self.falling = Block()
          self.falling.t.y += 10
          self.falling.t.z = self.blocks[-1].t.z
          self.falling.p = self.falling.t.Copy()
          self.blocks.append(self.falling)
        else:
          self.falling.t += DOWN
      elif e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
        self.falling.t += FRONT
        self.camt += FRONT
        if self.falling.t.z > max(self.logical | set([Pos(0, 0, 0)]), key=lambda c: c.z).z + 1:
          self.blocks.pop()
          self.cam = Qube(0, 0, 20)
          self.camt = self.cam.Copy()
          for i in range(100):
            o = RandomObject()
            o.p.x = random.gauss(0, 100)
            o.p.y = random.gauss(0, 100)
            o.p.z = random.gauss(0, 100)
            r = lambda: random.gauss(0, 0.01)
            o.v.quat = Quat(r(), r(), r(), 1).Normalized()
            self.objects.append(o)
          Music('sbc1.ogg')
          self.update_func = self.Fly

  def Fly(self):
    keys = pygame.key.get_pressed()
    r = lambda x, y, z: self.blocks.p.quat.Rotate(Pos(x, y, z))
    if keys[pygame.K_RIGHT]: self.blocks.p.quat *= Quat.FromAngle(2, *r(0, 1, 0))
    if keys[pygame.K_LEFT]: self.blocks.p.quat *= Quat.FromAngle(-2, *r(0, 1, 0))
    if keys[pygame.K_DOWN]: self.blocks.p.quat *= Quat.FromAngle(-2, *r(1, 0, 0))
    if keys[pygame.K_UP]: self.blocks.p.quat *= Quat.FromAngle(2, *r(1, 0, 0))
    if keys[pygame.K_SPACE]: self.blocks.v += r(0, 0, -0.01)
    self.blocks.v *= 0.99  # Space friction.
    self.camt = self.blocks.p + r(0, 2, 10)
    cam_speed = 0.1
    self.camt.quat = self.blocks.p.quat
    self.cam += (self.camt - self.cam) * cam_speed
    self.cam.quat.x += (self.camt.quat.x - self.cam.quat.x) * cam_speed
    self.cam.quat.y += (self.camt.quat.y - self.cam.quat.y) * cam_speed
    self.cam.quat.z += (self.camt.quat.z - self.cam.quat.z) * cam_speed
    self.cam.quat.w += (self.camt.quat.w - self.cam.quat.w) * cam_speed
    self.cam.quat = self.cam.quat.Normalized()
    for obj in self.objects:
      obj.Update()
    if len(self.objects) > 1:  # See if we can eat anything.
      p = self.blocks.p
      closest = min(self.objects, key=lambda o: abs(p - o.p) if o is not self.blocks else float('inf'))
      eaten = set()
      for block in closest:
        if eaten:
          block.rendered = 0
        if abs(p - closest.p.Apply(block.p)) < 1:
          eaten.add(block)
      for block in eaten:
        closest.remove(block)
      if len(closest) == 0:
        self.objects.remove(closest)
    for e in pygame.event.get():
      if e.type == pygame.QUIT or e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
        pygame.quit()
        sys.exit(0)


if __name__ == '__main__':
  Game().Start()
