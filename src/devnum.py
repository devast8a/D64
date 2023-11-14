"""
    DevNum - A library for arbitrary precision floating point number formats
"""

# Operations in this library are defined in the following way:
#   The operation is performed as though it had infinite precision and the result is then rounded to fit the format
#
# This definition has the following consequences:
#   1. The result is accurate
#   2. The result is reproducible (the same expression produces the same result across implementations, versions, etc.)
#
# Every operation is assumed to be both accurate and reproducible. Unfortunately, achieving this is extremely difficult
#   and operations in the library may fall short in two ways (they are documented).
#
# Operations may not correctly round their results.
#   The result is guaranteed to be correct until the final digit - which may be off by at most one.
#   E.g. sqrt(2) may give 1.414213561 or 1.414213563 instead of the correct 1.414213562
#
# Operations may simply be inaccurate.
#   The result may be completely incorrect - every digit in the result may be wrong.
#   E.g. sin(1234567890) may give any result instead of the correct 0.9866539395
#
from __future__ import annotations
from typing import Literal, Any, Final, final
import math
import random

MAX_DIGITS   = 1_000
P            = [10 ** i for i in range(MAX_DIGITS * 3)]
MIDPOINTS    = [(P[i] // 2) - 1 for i in range(MAX_DIGITS * 3)]
MIDPOINTS[0] = 1

########################################################################################################################
class Floating[F]:
    def __init__(self, NAME: F, MANTISSA: Base10, EXPONENT: Base10 | Base2):
        # Format metadata
        self.NAME             = str(NAME)
        self.DIGITS           = int(MANTISSA.DIGITS)
        self.EXPONENT_MAX     = int(EXPONENT.BASE**EXPONENT.DIGITS - 1)
        self.EXPONENT_MIN     = int(-self.EXPONENT_MAX)
        self.SPECIAL          = int(self.EXPONENT_MIN - 1)
        self.MANTISSA_MAX     = int(10**self.DIGITS - 1)
        self.MANTISSA_MIN     = int(10**(self.DIGITS - 1))

        self.MANTISSA_BITS    = int(math.ceil(math.log2(self.MANTISSA_MAX)))
        self.EXPONENT_BITS    = int(math.ceil(math.log2(self.EXPONENT_MAX)))
        self.MASK             = (1 << (self.MANTISSA_BITS + self.EXPONENT_BITS + 2)) - 1

        # Constants
        self.zero           = final(Num[F]( 0, self.SPECIAL, self))
        self.undefined      = final(Num[F](-1, self.SPECIAL, self))
        self.tau            = final(self.pack(TAU     , 0, 1000))
        self.pi             = final(self.pack(TAU // 2, 0, 1000))
        self.e              = final(self.pack(E, 0, 1000))

    def __call__(self, number: Num[Any] | int | float) -> Num[F]:
        """ General purpose constructor of a floating-point number """
        if isinstance(number, int):             return self.make(number)
        if isinstance(number, float):           return self.fromFloat(number)
        if number.format == self:               return number
        return self.pack(number.mantissa, number.exponent, number.format.DIGITS)
    
    def make(self, mantissa: int, exponent: int = 0):
        M_DIGITS = _log10(mantissa)
        return self.pack(mantissa, M_DIGITS - 1 + exponent, M_DIGITS)
    
    def fromFloat(self, value: float):
        exponent = 0
        while math.floor(value) != value:
            value *= 10
            exponent += 1
        return self.make(int(value), -exponent)

    def isNumber(self, n: Num[F]):
        M = abs(n.mantissa)
        E = n.exponent

        return (n.exponent == self.SPECIAL and n.mantissa == 0) or (
            self.MANTISSA_MIN <= M and M <= self.MANTISSA_MAX and
            self.EXPONENT_MIN <= E and E <= self.EXPONENT_MAX)

    def isInvalid(self, n: Num[F]):
        return not self.isNumber(n)

    def isUndefined(self, n: Num[F]):
        return n.exponent == self.SPECIAL and n.mantissa == -1
    
    def validate(self, n: Num[F]):
        return n if self.isNumber(n) else self.undefined
    
    def pack(self, mantissa: int, exponent: int, expected: int):
        """
            Construct a `Num` from a given `mantissa` and `exponent`.
            The `expected` parameter is the number of digits that are expected to be in the `mantissa`.
            This function handles normalization, rounding, overflow, underflow, and zero cases.
        """

        M_DIGITS = _log10(mantissa)
        INDEX  = M_DIGITS - self.DIGITS

        if INDEX > 0:
            # The mantissa contains more significant digits than the format can hold
            truncated, remainder = divmod(abs(mantissa), P[INDEX])
            midpoint = MIDPOINTS[INDEX] + (truncated % 2)
            rounded  = truncated + (1 if remainder >= midpoint else 0)
    
            # Rounding could have caused the number of digits to increase beyond the format's capacity
            if rounded > self.MANTISSA_MAX:
                truncated, remainder = divmod(rounded, 10)
                midpoint = 4 + (truncated % 2)
                rounded  = truncated + (1 if remainder >= midpoint else 0)

                exponent += 1

            mantissa = rounded if mantissa >= 0 else -rounded
        else:
            # The mantissa does not contain enough significant digits to require rounding
            mantissa = mantissa * P[-INDEX]

        exponent = exponent + (M_DIGITS - expected)

        if mantissa == 0: return self.zero
        if exponent > self.EXPONENT_MAX: return self.undefined
        if exponent < self.EXPONENT_MIN: return self.zero
        return Num(mantissa, exponent, self)
    
    def unpack(self, number: Num[F], exponent: int):
        """
            Unpack a `Num` into a `mantissa` aligned to a specified `exponent`.
            This function does not handle any of the special cases that `pack` (including rounding)
            `exponent` should be at most `number.exponent + number.format.DIGITS*2`
        """

        INDEX = number.exponent - exponent
        if INDEX >= 0:
            return number.mantissa * P[INDEX]
        return number.mantissa / P[min(-INDEX, self.DIGITS)]
    
    def add(self, x: Num[F], y: Num[F]):
        if self.isInvalid(x) or self.isInvalid(y): return self.undefined

        E = max(x.exponent, y.exponent)
        X = self.unpack(x, E - self.DIGITS)
        Y = self.unpack(y, E - self.DIGITS)

        return self.pack(X + Y, E, self.DIGITS * 2)

    def sub(self, x: Num[F], y: Num[F]):
        if self.isInvalid(x) or self.isInvalid(y): return self.undefined

        E = max(x.exponent, y.exponent)
        X = self.unpack(x, E - self.DIGITS)
        Y = self.unpack(y, E - self.DIGITS)

        return self.pack(X - Y, E, self.DIGITS * 2)

    def mul(self, x: Num[F], y: Num[F]):
        if self.isInvalid(x) or self.isInvalid(y): return self.undefined

        return self.pack(
            x.mantissa * y.mantissa,
            x.exponent + y.exponent,
            self.DIGITS * 2 - 1
        )

    def div(self, x: Num[F], y: Num[F]):
        if self.isInvalid(x) or self.isInvalid(y) or y.mantissa == 0: return self.undefined

        # Extra digits of precision
        EXTRA_DIGITS = 1

        return self.pack(
            (x.mantissa * P[self.DIGITS + EXTRA_DIGITS]) // (y.mantissa * P[EXTRA_DIGITS]),
            x.exponent - y.exponent,
            self.DIGITS + 1
        )

    def mod(self, x: Num[F], y: Num[F]):
        """
            Calculates the remainder of `x` divided by `y`.

            **inaccurate, incorrect rounding**: Analysis has yet to be done
        """
        if self.isInvalid(x) or self.isInvalid(y) or y.mantissa == 0: return self.undefined
        if x.exponent < y.exponent: return x

        D = min(x.exponent - y.exponent, 15)

        # We scale the second operand such that the division also cuts off any extra digits
        xm = x.mantissa * P[self.DIGITS]
        ym = y.mantissa * P[self.DIGITS - D]

        # Compute: `x - ((x // y) * y)`
        #   We need to scale x to cancel out digits that were introduced in the multiplication of y
        rm = xm // ym
        rm = rm * y.mantissa
        rm = (x.mantissa * P[D]) - rm

        return self.pack(rm, 0, self.DIGITS)
    
    def _compact(self, x: Num[F]):
        # TODO: Look into using a different method for doing comparisons
        if x.mantissa < 0:
            return -((abs(x.mantissa) | ((x.exponent - self.SPECIAL) << self.MANTISSA_BITS)) ^ self.MASK)
        else:
            return x.mantissa | ((x.exponent - self.SPECIAL) << self.MANTISSA_BITS)
    
    def eq(self, x: Num[F], y: Num[F]): return x.exponent == y.exponent and x.mantissa == y.mantissa
    def ge(self, x: Num[F], y: Num[F]): return self._compact(x) >= self._compact(y)
    def gt(self, x: Num[F], y: Num[F]): return self._compact(x)  > self._compact(y)
    def le(self, x: Num[F], y: Num[F]): return self._compact(x) <= self._compact(y)
    def lt(self, x: Num[F], y: Num[F]): return self._compact(x)  < self._compact(y)
    def ne(self, x: Num[F], y: Num[F]): return x.exponent != y.exponent or x.mantissa != y.mantissa
    
    def sin(self, number: Num[F]):
        """
            Calculate sin(number)
            
            **inaccurate**: For large inputs, this function may produce completely incorrect results
        """
        if self.isInvalid(number): return self.undefined

        EXTRA_DIGITS = 2

        # Range reduction
        # TODO: Come up with a different range reduction method
        number = self.mod(number, self.tau)

        term  = number.mantissa * P[EXTRA_DIGITS]
        n2    = term * term // P[max(-2 * number.exponent, 0)]
        SCALE = P[(self.DIGITS + EXTRA_DIGITS - 1) * 2]

        # Use a Taylor series
        result = term
        order = 1
        while term != 0:
            order = order + 2
            term = (term * n2) // ((order - 1) * order * SCALE)
            result -= term

            order = order + 2
            term = (term * n2) // ((order - 1) * order * SCALE)
            result += term

        return self.pack(result, number.exponent, self.DIGITS + EXTRA_DIGITS)
    
    def sqrt(self, number: Num[F]):
        """
            Calculate sin(number)
            
            **incorrect rounding**: For some inputs, the result may be out by at most 1-ULP due to incorrect rounding.
        """

        if self.isInvalid(number) or number.mantissa < 0: return self.undefined
        if number.mantissa == 0: return self.zero
        
        # Extra digits must be at least two for this estimate
        EXTRA_DIGITS = 2

        # Use Heron's method on mantissa - halve the exponent
        #   Take an input of the form `M * 10**(2*E)` and calculate `sqrt(M) * 10**E`
        #   Which means that we only need to compute sqrt on numbers between 1 and 100
        if number.exponent % 2 == 0:
            original = number.mantissa * P[self.DIGITS + EXTRA_DIGITS*2 - 1]
            result   = (number.mantissa * 28 + 89 * P[self.DIGITS - 1]) * P[EXTRA_DIGITS - 2]
        else:
            original = number.mantissa * P[self.DIGITS + EXTRA_DIGITS*2]
            result   = (number.mantissa * 89 + 28 * P[self.DIGITS]) * P[EXTRA_DIGITS - 2]

        # This is guaranteed to converge - For Fn16 format, it will do so in only four iterations
        while True:
            NEXT = (result + (original // result)) // 2
            if NEXT == result:
                break
            result = NEXT

        return self.pack(result, number.exponent // 2, self.DIGITS + EXTRA_DIGITS)
    
    def next(self, number: Num[F]):
        if self.isInvalid(number): return self.undefined

    def toScientificNotation(self, number: Num[F]):
        if self.isUndefined(number): return 'Undefined'
        if self.isInvalid(number):   return 'Invalid'
        if number.mantissa == 0:     return '0'

        N = '-' if number.mantissa < 0 else ''
        M = str(abs(number.mantissa)).rstrip('0')
        E = str(number.exponent)
        return f'{N}{M}e{E}' if len(M) == 1 else f'{N}{M[0]}.{M[1:]}e{E}'
    
    def toString(self, number: Num[F], digits: int | None = None):
        if self.isUndefined(number): return 'Undefined'
        if self.isInvalid(number):   return 'Invalid'
        if number.mantissa == 0:     return '0'

        M = str(abs(number.mantissa)).rstrip('0')
        E = number.exponent + 1

        # Number of digits to print, otherwise switch to scientific notation
        D = self.DIGITS + 1 if digits == None else digits
        N = '-' if number.mantissa < 0 else ''

        if E  > 0 and len(M) > E:          return N + M[:E] + '.' + M[E:]     # There's a decimal point in the string
        if E  > 0 and E <= D:              return N + M + '0'*(E - len(M))    # There's a decimal point after the string
        if E <= 0 and abs(E) + len(M) < D: return N + '0.' + '0'*(abs(E)) + M # There's a decimal point before the string
        
        return self.toScientificNotation(number)
    
    def randomAny(self):
        return Num[F](
            random.randint(self.MANTISSA_MIN, self.MANTISSA_MAX) * random.choice([-1, 1]),
            random.randint(self.EXPONENT_MIN, self.EXPONENT_MAX),
            self
        )
    
    def random0To1(self):
        return self.pack(random.randint(0, self.MANTISSA_MAX), -1, self.DIGITS)
    
    def toInt(self, number: Num[F]):
        return number.mantissa // P[self.DIGITS - 1 - number.exponent]

########################################################################################################################
class Num[F]:
    def __init__(self, mantissa: int, exponent: int, format: Floating[F]):
        self.mantissa = mantissa
        self.exponent = exponent
        self.format = format

    mantissa: Final[int]
    exponent: Final[int]
    format:   Final[Floating[F]]

    def __add__(self, other: Num[F] | int | float): return self.format.add(self, self.format(other))
    def __radd__(self, other: Num[F] | int | float): return self.format.add(self.format(other), self)
    def __sub__(self, other: Num[F] | int | float): return self.format.sub(self, self.format(other))
    def __rsub__(self, other: Num[F] | int | float): return self.format.sub(self.format(other), self)
    def __mul__(self, other: Num[F] | int | float): return self.format.mul(self, self.format(other))
    def __rmul__(self, other: Num[F] | int | float): return self.format.mul(self.format(other), self)
    def __truediv__(self, other: Num[F] | int | float): return self.format.div(self, self.format(other))
    def __rtruediv__(self, other: Num[F] | int | float): return self.format.div(self.format(other), self)
    def __mod__(self, other: Num[F] | int | float): return self.format.mod(self, self.format(other))
    def __rmod__(self, other: Num[F] | int | float): return self.format.mod(self.format(other), self)

    def __eq__(self, other: Any): return self.format.eq(self, self.format(other))
    def __ge__(self, other: Any): return self.format.ge(self, self.format(other))
    def __gt__(self, other: Any): return self.format.gt(self, self.format(other))
    def __lt__(self, other: Any): return self.format.lt(self, self.format(other))
    def __le__(self, other: Any): return self.format.le(self, self.format(other))
    def __ne__(self, other: Any): return self.format.ne(self, self.format(other))

    def __int__(self): return self.format.toInt(self)
    def __str__(self): return self.format.toString(self)
    def __repr__(self): return self.format.toString(self)

    def toString(self, digits: int | None = None): return self.format.toString(self, digits)

def sin[F](number: Num[F]) -> Num[F]:   return number.format.sin(number)
def sqrt[F](number: Num[F]) -> Num[F]:  return number.format.sqrt(number)
def debug(number: Num[Any]) -> str:     return f'{number.format.NAME}({number.mantissa}, {number.exponent})'

########################################################################################################################
# Format Specification Helpers

class Base10:
    def __init__(self, digits: int):
        self.BASE   = 10
        self.DIGITS = digits

class Base2:
    def __init__(self, digits: int):
        self.BASE   = 2
        self.DIGITS = digits

########################################################################################################################
# Constants

TAU = int("6283185307179586476925286766559005768394338798750211641949889184615632812572417997256069650684234135"
          "9642961730265646132941876892191011644634507188162569622349005682054038770422111192892458979098607639"
          "2885762195133186689225695129646757356633054240381829129713384692069722090865329642678721452049828254"
          "7449174013212631176349763041841925658508183430728735785180720022661061097640933042768293903883023218"
          "8661145407315191839061843722347638652235862102370961489247599254991347037715054497824558763660238982"
          "5966734672488131328617204278989279044947438140435972188740554107843435258635350476934963693533881026"
          "4001136254290527121655571542685515579218347274357442936881802449906860293099170742101584559378517847"
          "0840399122242580439217280688363196272595495426199210374144226999999967459560999021194634656321926371"
          "9004891891069381660528504461650668937007052386237634202000627567750577317506641676284123435533829460"
          "7196506980857510937462319125727764707575187503915563715561064342453613226003855753222391818432840398")

E = int("2718281828459045235360287471352662497757247093699959574966967627724076630353547594571382178525166427"
        "4274663919320030599218174135966290435729003342952605956307381323286279434907632338298807531952510190"
        "1157383418793070215408914993488416750924476146066808226480016847741185374234544243710753907774499206"
        "9551702761838606261331384583000752044933826560297606737113200709328709127443747047230696977209310141"
        "6928368190255151086574637721112523897844250569536967707854499699679468644549059879316368892300987931"
        "2773617821542499922957635148220826989519366803318252886939849646510582093923982948879332036250944311"
        "7301238197068416140397019837679320683282376464804295311802328782509819455815301756717361332069811250"
        "9961818815930416903515988885193458072738667385894228792284998920868058257492796104841984443634632449"
        "6848756023362482704197862320900216099023530436994184914631409343173814364054625315209618369088870701"
        "6768396424378140592714563549061303107208510383750510115747704171898610687396965521267154688957035035")

########################################################################################################################
# Internal functions
def _log10(n: int):
    n = abs(n)

    # Calculate an approximation of log10(n) with change of base
    #   n.bit_length() gives a good approximation of log2(n)
    #   315653 / 2**20 is a good approximation of log10(2)
    r = (n.bit_length() * 315653) >> 20

    # The approximation is off when `n` is above a power of ten, but below the next power of two.
    return r + 1 if n >= P[r] else r

########################################################################################################################
# Testing

# Check that _log10 is correct - Only needed if you change the constants in _log10 or the maximum supported digits
for i, power in enumerate(P):
    if i     != _log10(power - 1): raise FloatingPointError(f'_log10(10**{i} - 1) is incorrect')
    if i + 1 != _log10(power    ): raise FloatingPointError(f'_log10(10**{i}) is incorrect')

########################################################################################################################
# Formats
Fd16   = Floating[Literal[ 'Fd16']]( 'Fd16',  Base10(3),  Base2(4))
Fd32   = Floating[Literal[ 'Fd32']]( 'Fd32',  Base10(7),  Base2(6))
Fd64   = Floating[Literal[ 'Fd64']]( 'Fd64', Base10(16),  Base2(8))
Fd128  = Floating[Literal['Fd128']]('Fd128', Base10(34), Base2(13))

Fn16   = Floating[Literal[  'Fn16']]('Fn16',     Base10(16), Base10(2))
Fn1000 = Floating[Literal['Fn1000']]('Fn1000', Base10(1000), Base10(4))