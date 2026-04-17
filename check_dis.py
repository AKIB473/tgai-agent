import dis
from RestrictedPython import compile_restricted
from RestrictedPython.PrintCollector import PrintCollector

# See what bytecode is generated for print("hello")
code = compile_restricted('print("hello")', '<s>', 'exec')
print("=== BYTECODE ===")
dis.dis(code)

# Now test the correct pattern from RestrictedPython docs
print("\n=== CORRECT PATTERN TEST ===")
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import safe_builtins

_print = PrintCollector()
globs = {
    **safe_globals,
    '__builtins__': safe_builtins,
    '__name__': '__sandbox__',
    '_print_': _print._call_print,  # bound method as _print_
    '_getattr_': getattr,
}
exec(code, globs)
output = _print()
print(f"Captured output: {repr(output)}")
assert 'hello' in output, f"FAIL: expected 'hello' in {output!r}"
print("PASS!")
