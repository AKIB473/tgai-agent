from RestrictedPython.PrintCollector import PrintCollector
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import safe_builtins

code = 'print("hello world")\nprint(1+2)'
byte_code = compile_restricted(code, '<sandbox>', 'exec')

_print = PrintCollector()
globs = {
    **safe_globals,
    '__builtins__': safe_builtins,
    '__name__': '__sandbox__',
    '_print_': _print,
    '_getattr_': getattr,
}
exec(byte_code, globs)
print('dir:', [a for a in dir(_print) if not a.startswith('__')])
print('str repr:', repr(str(_print)))
print('call result:', repr(_print()))
