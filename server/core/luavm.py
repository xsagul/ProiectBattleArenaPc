"""Riot's own Lua scripts, run as Riot's server runs them: a Lua 5.1.5 virtual machine (server/lua51/lua51.dll, the
stock lua.org 5.1.5 sources - the version the 13.3 client links, client-src/src/gen/Lua.txt) loading the scripts'
original bytecode (data/lua133/scripts/*.luabin64), with the engine's functions supplied from Python.

Riot's server is an engine that exposes some 300 functions to Lua (FindTargetWithFilter, SetTimerDelay, AttackTarget,
DistanceBetweenObjectCenterAndPoint ...: every GETGLOBAL of the 169 scripts of the 13.3 client) and the game's rules
written in Lua on top of it (the AI of minions, monsters and turrets, the map's level script, the plants, the
BuildingBlocks of the spells). Here the scripts are Riot's; only the engine is ours (core/luaapi.py).

Values crossing the border: numbers, booleans, strings, nil, tables (to / from Python dicts and lists) and engine
objects (units, points), which Lua holds as light userdata - a handle number into VM.objects.
"""
import ctypes
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DLL = os.path.join(os.path.dirname(HERE), 'lua51', 'lua51.dll')

LUA_GLOBALSINDEX = -10002
LUA_REGISTRYINDEX = -10000
T_NIL, T_BOOLEAN, T_LIGHTUSERDATA, T_NUMBER, T_STRING, T_TABLE, T_FUNCTION, T_USERDATA = 0, 1, 2, 3, 4, 5, 6, 7

CFUNC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
_lib = None


def lib():
    global _lib
    if _lib is None:
        L = ctypes.CDLL(DLL)
        sig = {
            'luaL_newstate': (ctypes.c_void_p, []),
            'luaL_openlibs': (None, [ctypes.c_void_p]),
            'lua_close': (None, [ctypes.c_void_p]),
            'luaL_loadbuffer': (ctypes.c_int, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p]),
            'lua_pcall': (ctypes.c_int, [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
            'lua_gettop': (ctypes.c_int, [ctypes.c_void_p]),
            'lua_settop': (None, [ctypes.c_void_p, ctypes.c_int]),
            'lua_pushvalue': (None, [ctypes.c_void_p, ctypes.c_int]),
            'lua_type': (ctypes.c_int, [ctypes.c_void_p, ctypes.c_int]),
            'lua_tonumber': (ctypes.c_double, [ctypes.c_void_p, ctypes.c_int]),
            'lua_toboolean': (ctypes.c_int, [ctypes.c_void_p, ctypes.c_int]),
            'lua_tolstring': (ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]),
            'lua_touserdata': (ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_int]),
            'lua_pushnil': (None, [ctypes.c_void_p]),
            'lua_pushnumber': (None, [ctypes.c_void_p, ctypes.c_double]),
            'lua_pushboolean': (None, [ctypes.c_void_p, ctypes.c_int]),
            'lua_pushlstring': (None, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]),
            'lua_pushlightuserdata': (None, [ctypes.c_void_p, ctypes.c_void_p]),
            'lua_pushcclosure': (None, [ctypes.c_void_p, CFUNC, ctypes.c_int]),
            'lua_createtable': (None, [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]),
            'lua_settable': (None, [ctypes.c_void_p, ctypes.c_int]),
            'lua_gettable': (None, [ctypes.c_void_p, ctypes.c_int]),
            'lua_setfield': (None, [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]),
            'lua_getfield': (None, [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]),
            'lua_rawseti': (None, [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]),
            'lua_next': (ctypes.c_int, [ctypes.c_void_p, ctypes.c_int]),
            'lua_error': (ctypes.c_int, [ctypes.c_void_p]),
        }
        for name, (res, args) in sig.items():
            f = getattr(L, name)
            f.restype, f.argtypes = res, args
        _lib = L
    return _lib


class LuaError(Exception):
    pass


class Handle:
    """an engine object as Lua sees it (a unit, a point): Lua keeps its handle number"""
    __slots__ = ('obj',)


class VM:
    def __init__(self, missing=None):
        """missing(name, args) is called for an engine function no one supplied (the census of what is left)"""
        self.L = lib()
        self.state = self.L.luaL_newstate()
        self.L.luaL_openlibs(self.state)
        self.objects = {}            # handle -> object
        self.handles = {}            # id(object) -> handle
        self.next_handle = 1
        self.funcs = {}              # name -> python function (kept alive with its C callback)
        self._cb = {}
        self.missing = missing
        self.error = None            # a Python exception raised inside a call from Lua

    def close(self):
        if self.state:
            self.L.lua_close(self.state)
            self.state = None

    # ------------------------------------------------------------------ values
    def handle(self, obj):
        h = self.handles.get(id(obj))
        if h is None:
            h = self.next_handle
            self.next_handle += 1
            self.handles[id(obj)] = h
            self.objects[h] = obj
        return h

    def push(self, v):
        L, s = self.L, self.state
        if v is None:
            L.lua_pushnil(s)
        elif v is True or v is False:
            L.lua_pushboolean(s, 1 if v else 0)
        elif isinstance(v, (int, float)):
            L.lua_pushnumber(s, float(v))
        elif isinstance(v, str):
            b = v.encode()
            L.lua_pushlstring(s, b, len(b))
        elif isinstance(v, bytes):
            L.lua_pushlstring(s, v, len(v))
        elif isinstance(v, dict):
            L.lua_createtable(s, 0, len(v))
            for k, x in v.items():
                self.push(k)
                self.push(x)
                L.lua_settable(s, -3)
        elif isinstance(v, (list, tuple)):
            L.lua_createtable(s, len(v), 0)
            for i, x in enumerate(v):
                self.push(x)
                L.lua_rawseti(s, -2, i + 1)
        elif callable(v) and not hasattr(v, 'net'):
            L.lua_pushcclosure(s, self._wrap(getattr(v, '__name__', 'fn'), v), 0)
        else:
            L.lua_pushlightuserdata(s, ctypes.c_void_p(self.handle(v)))

    def get(self, idx, depth=0):
        L, s = self.L, self.state
        t = L.lua_type(s, idx)
        if t == T_NIL or t == -1:
            return None
        if t == T_BOOLEAN:
            return bool(L.lua_toboolean(s, idx))
        if t == T_NUMBER:
            x = L.lua_tonumber(s, idx)
            return int(x) if x == int(x) and abs(x) < 2 ** 53 else x
        if t == T_STRING:
            n = ctypes.c_size_t()
            p = L.lua_tolstring(s, idx, ctypes.byref(n))
            return ctypes.string_at(p, n.value).decode(errors='replace')
        if t == T_LIGHTUSERDATA:
            return self.objects.get(L.lua_touserdata(s, idx) or 0)
        if t == T_TABLE and depth < 6:
            if idx < 0 and idx > LUA_REGISTRYINDEX:
                idx = L.lua_gettop(s) + idx + 1
            out = {}
            L.lua_pushnil(s)
            while L.lua_next(s, idx):
                v = self.get(-1, depth + 1)
                L.lua_settop(s, -2)
                k = self.get(-1, depth + 1)
                out[k] = v
            return out
        return ('<lua %d>' % t)

    # ------------------------------------------------------------------ the engine's functions
    def _wrap(self, name, fn):
        def cb(state):
            try:
                n = self.L.lua_gettop(state)
                args = [self.get(i) for i in range(1, n + 1)]
                res = fn(*args)
            except Exception as e:                       # noqa: BLE001 - reported to the caller of the Lua code
                self.error = self.error or (name, e)
                return 0
            if isinstance(res, MultiReturn):
                for x in res:
                    self.push(x)
                return len(res)
            if res is None:
                return 0
            self.push(res)
            return 1
        c = CFUNC(cb)
        self._cb[name + '#%d' % len(self._cb)] = c
        return c

    def register(self, name, fn):
        self.funcs[name] = fn
        self.L.lua_pushcclosure(self.state, self._wrap(name, fn), 0)
        self.L.lua_setfield(self.state, LUA_GLOBALSINDEX, name.encode())

    def set_global(self, name, v):
        self.push(v)
        self.L.lua_setfield(self.state, LUA_GLOBALSINDEX, name.encode())

    def global_(self, name):
        self.L.lua_getfield(self.state, LUA_GLOBALSINDEX, name.encode())
        v = self.get(-1)
        self.L.lua_settop(self.state, -2)
        return v

    def has_function(self, name):
        self.L.lua_getfield(self.state, LUA_GLOBALSINDEX, name.encode())
        t = self.L.lua_type(self.state, -1)
        self.L.lua_settop(self.state, -2)
        return t == T_FUNCTION

    # ------------------------------------------------------------------ running
    def _pcall(self, nargs, nres):
        L, s = self.L, self.state
        self.error = None
        r = L.lua_pcall(s, nargs, nres, 0)
        if r != 0:
            msg = self.get(-1)
            L.lua_settop(s, -2)
            if self.error is not None:
                raise LuaError(f'{self.error[0]}: {self.error[1]!r}') from self.error[1]
            raise LuaError(str(msg))
        if self.error is not None:
            name, e = self.error
            self.error = None
            raise LuaError(f'{name}: {e!r}') from e

    def load(self, code, name='chunk'):
        """run a chunk (bytecode or source)"""
        if isinstance(code, str):
            code = code.encode()
        r = self.L.luaL_loadbuffer(self.state, code, len(code), name.encode())
        if r != 0:
            msg = self.get(-1)
            self.L.lua_settop(self.state, -2)
            raise LuaError(f'load {name}: {msg}')
        self._pcall(0, 0)

    def load_file(self, path):
        self.load(open(path, 'rb').read(), os.path.basename(path))

    def call(self, name, *args, nres=1):
        """call a global Lua function -> its first result (None if it is not defined)"""
        L, s = self.L, self.state
        top = L.lua_gettop(s)
        L.lua_getfield(s, LUA_GLOBALSINDEX, name.encode())
        if L.lua_type(s, -1) != T_FUNCTION:
            L.lua_settop(s, top)
            return None
        for a in args:
            self.push(a)
        self._pcall(len(args), nres)
        out = self.get(-1) if nres else None
        L.lua_settop(s, top)
        return out


class MultiReturn(tuple):
    """an engine function returning several values to Lua"""
