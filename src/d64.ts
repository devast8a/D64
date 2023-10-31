/*
 * D64 is a decimal floating-point format designed to be simple to understand.
 *
 * The format always provides sixteen decimal digits of precision. Any result with more than sixteen digits is rounded
 *  using round-to-nearest ties-to-even.
 * 
 * There is only one special value *Undefined* which represents an undefined value. Undefined is equal to itself. Any
 *  operation on Undefined returns Undefined except for comparison functions (eq, ge, gt, le, lt, ne, min, and max)
 *  which all treat Undefined as less than every other value.
 *
 * Every D64 value has a single unique representation.
 */

import { inspect } from 'util'

export class D64 {
    constructor(
        readonly mantissa: bigint,
        readonly exponent: number,
    ) { }

    [inspect.custom]() { return toString(this) }
    toString() { return toString(this) }

    static toScientificNotation(number: D64) { return toScientificNotation(number) }
    toScientificNotation() { return toScientificNotation(this) }
}

// These constants are used to define the D64 format
const DIGITS        = 16
const MANTISSA_BITS = 55
const MANTISSA_MAX  = (10n ** BigInt(DIGITS)) - 1n
const MANTISSA_MIN  = 10n ** (BigInt(DIGITS) - 1n)
const EXPONENT_BITS = 9
const EXPONENT_MAX  = 2**8 - 1
const EXPONENT_MIN  = -EXPONENT_MAX
const UNDEFINED     = EXPONENT_MIN - 1

const POWERS    = Array.from({ length: DIGITS * 3 }, (_, i) => 10n ** BigInt(i))
const MIDPOINTS = POWERS.map(n => n / 2n)
MIDPOINTS[0] = 1n

export function from(value: number) {
    if (value === 0) {
        return new D64(0n, 0)
    }

    // Deal with fractional parts
    let exponent = 1
    while (Math.floor(value) !== value) {
        value *= 10
        exponent++
    }

    // Deal with integer parts
    let mantissa = BigInt(value)
    let digits = BN.log10(mantissa)

    return pack(mantissa, digits - exponent, digits)
}

// Basic arithmetic
export function add(x: D64, y: D64) {
    if (isInvalid(x) || isInvalid(y)) {
        return Undefined
    }

    const E = Math.max(x.exponent, y.exponent)
    const X = unpack(x, E - DIGITS)
    const Y = unpack(y, E - DIGITS)

    return pack(X + Y, E, DIGITS * 2)
}

export function sub(x: D64, y: D64) {
    if (isInvalid(x) || isInvalid(y)) {
        return Undefined
    }

    const E = Math.max(x.exponent, y.exponent)
    const X = unpack(x, E - DIGITS)
    const Y = unpack(y, E - DIGITS)

    return pack(X + Y, E, DIGITS * 2)
}

export function mul(x: D64, y: D64) {
    if (isInvalid(x) || isInvalid(y)) {
        return Undefined
    }

    return pack(
        x.mantissa * y.mantissa,
        x.exponent + y.exponent,
        DIGITS * 2 - 1
    )
}

export function div(x: D64, y: D64) {
    if (isInvalid(x) || isInvalid(y) || y.mantissa === 0n) {
        return Undefined
    }

    return pack(
        x.mantissa * POWERS[DIGITS] / y.mantissa,
        x.exponent - y.exponent,
        DIGITS + 1,
    )
}

export function mod(x: D64, y: D64) {
    throw new Error('Not implemented')
    return x
}

// Comparison functions
export function eq(x: D64, y: D64) { return x.exponent === y.exponent && x.mantissa === y.mantissa }
export function ge(x: D64, y: D64) { return !(x.exponent < y.exponent || x.mantissa < y.mantissa) }
export function gt(x: D64, y: D64) { return x.exponent > y.exponent || x.mantissa > y.mantissa }
export function le(x: D64, y: D64) { return !(x.exponent > y.exponent || x.mantissa > y.mantissa) }
export function lt(x: D64, y: D64) { return x.exponent < y.exponent || x.mantissa < y.mantissa }
export function ne(x: D64, y: D64) { return x.exponent !== y.exponent || x.mantissa !== y.mantissa }

/** Return the absolute value of `number` */
export function abs(number: D64) {
    return new D64(number.mantissa < 0n ? -number.mantissa : number.mantissa, number.exponent)
}

/** Return the part *after* the decimal point of a number. This function does not lose precision.
 * @example fractionalPart(123.456) = 0.456 */ 
export function fractionalPart(number: D64) {
    throw new Error('Not implemented yet')
    if (isInvalid(number)) { return Undefined }
    if (number.exponent >= DIGITS) { return Zero }
    if (number.exponent < -DIGITS) { return number }

    const point = DIGITS - number.exponent - 1
    const mantissa = number.mantissa % POWERS[point]
    // NOTE: The previous implementation has a bug where there are 0s directly after the decimal point
    return number
}

/** Return the part before the decimal point of a number. This function does not lose precision
 * @example integerPart(123.456) = 123 */ 
export function integerPart(number: D64) {
    if (isInvalid(number)) { return Undefined }
    if (number.exponent >= DIGITS) { return number }
    if (number.exponent < -DIGITS) { return Zero }

    const point = DIGITS - number.exponent - 1
    const mantissa = number.mantissa / POWERS[point]
    return pack(mantissa, 0, 1)
}

/** Return the larger value of `x` and `y` */
export function max(x: D64, y: D64) {
    return lt(x, y) ? y : x
}

/** Return the smaller value of `x` and `y` */
export function min(x: D64, y: D64) {
    return lt(x, y) ? x : y
}

/** Return negative `number` */
export function neg(number: D64) {
    return new D64(-number.mantissa, number.exponent)
}

/**
 * Returns the sign of `number`.
 *  - `0` if `number` is zero
 *  - `1` if `number` is positive
 *  - `-1` if `number` is negative
*/
export function sign(number: D64) {
    if (isInvalid(number)) { return Undefined }
    if (number.mantissa === 0n) { return Zero }
    if (number.mantissa < 0n) { return NegOne }
    return One
}

// Rounding functions
export function round(value: D64) {
    throw new Error()
}

// Trigonometric Functions
export function acos(slope: D64) {
    return sub(TAU_Q, asin(slope))
}

export function asin(slope: D64) {
    throw new Error('Not implemented')
    return slope
}

export function atan(slope: D64) {
    throw new Error('Not implemented')
    return slope
}

export function atan2(y: D64, x: D64) {
    throw new Error('Not implemented')
    return x
}

export function cos(radians: D64) {
    return sin(add(radians, TAU_Q))
}

export function sin(radians: D64) {
    // Same algorithm as https://github.com/vpisarev/DEC64/blob/alt/dec64_math.c
    // TODO: Switch from Taylor Series to CORDIC
    // TODO: Add in argument reduction
    if (isInvalid(radians)) {
        return Undefined
    }

    const r2 = neg(mul(radians, radians))

    let result = radians
    let term = radians

    for (let i = 1; i < 30; i++) {
        term = mul(term, r2)
        term = div(term, from((i * 2) * (i * 2 + 1)))
        const next = add(result, term)
        if (eq(result, next)) { break }
        result = next
    }

    return result
}

export function tan(radians: D64) {
    return div(sin(radians), cos(radians))
}

// Power Functions
export function exp(number: D64) {
    throw new Error('Not implemented')
}

export function log(number: D64) {
    throw new Error('Not implemented')
}

export function pow(base: D64, exponent: D64) {
    throw new Error('Not implemented')
}

export function root(index: D64, radicand: D64) {
    throw new Error('Not implemented')
}

/** Return the square root of `number` */
export function sqrt(number: D64) {
    if (isInvalid(number) || number.mantissa < 0n) { return Undefined }
    if (number.mantissa === 0n) { return Zero }

    // Use Newton/Heron's Method
    //  Split the `sqrt(M * 10**2E)` into `sqrt(M) * 10**E`
    //  This restricts the value of M to between 1 and 100
    const EXTRA_DIGITS = 2
    let input = number.mantissa * POWERS[DIGITS + (number.exponent % 2) + EXTRA_DIGITS*2]
    let result = number.mantissa * POWERS[EXTRA_DIGITS - 1]

    for (let i = 0; i < 7; i++) {
        const next = (result + (input / result)) / 2n
        if (result === next) { break }
        result = next
    }

    // TODO: Redo error analysis
    //  Previous error analysis relied on the following assumptions
    //  - division is infinitely precise
    //  - that small errors are the goal, not correct rounding
    return pack(result, (number.exponent + 1) >> 1, DIGITS + EXTRA_DIGITS)
}

export function isValid(number: D64) {
    const E = number.exponent
    const M = BN.abs(number.mantissa)

    return (M === 0n && E === 0) ||
        (MANTISSA_MIN <= M && M <= MANTISSA_MAX &&
         EXPONENT_MIN <= E && E <= EXPONENT_MAX)
}

export function isInvalid(number: D64) {
    return !isValid(number)
}

export function isUndefined(number: D64) {
    return number.mantissa === 0n && number.exponent === UNDEFINED
}

export function toString(number: D64) {
    if (eq(number, Zero)) { return '0' }
    if (isUndefined(number)) { return 'Undefined' }
    if (isInvalid(number)) { return 'Invalid' }

    // TODO: This is a bit of a scrappy implementation just to get thing working
    const digits = []

    let mantissa = BN.abs(number.mantissa)
    while (mantissa > 0n) {
        digits.push(Number(mantissa % 10n))
        mantissa /= 10n
    }

    let exponent = number.exponent
    let output = ''

    if (exponent < 0) {
        output += '0.'
    }

    while (digits.length > 0) {
        output += digits.pop()

        if (exponent === 0) {
            output += '.'
        }
        exponent--
    }

    return output
}

/** Convert a number to  */
export function toScientificNotation(number: D64) {
    if (eq(number, Zero)) { return '0' }
    if (isUndefined(number)) { return 'Undefined' }
    if (isInvalid(number)) { return 'Invalid' }

    const m = number.mantissa.toString().replace(/0+$/, '')
    const e = number.exponent
    const f = m[0]          // First digit
    const r = m.slice(1)    // Remaining digits
    return m.length === 1 ? `${f}e${e}` : `${f}.${r}e${e}`
}

namespace BN {
    export function abs(value: bigint) {
        return value < 0n ? -value : value
    }

    export function log10(value: bigint) {
        let result = 32

        // TODO: Figure out a way to remove this internal call to abs by merging in with callers
        value = abs(value)
        const absolute = value

        // Calculate approximate log2 of value. This is the same operation as finding the position of the last set bit
        //  counting from the least - significant bit
        while (value > 0xFFFFFFFFn) {
            value >>= 32n
            result += 32
        }
        result = result - Math.clz32(Number(value))

        // Calculate the approximate log10 of value.
        //  2**11 / 617 is an approximation of log2(10) good to three decimal places
        result = (result * 617) >> 11

        // Fix the approximation. The cases where the approximation is wrong is when `value` is greater than the next power
        //  of ten but smaller than the next power of two.
        return absolute >= POWERS[result] ? result + 1 : result
    }
}

/**
 * Construct a D64 from a given `mantissa` and `exponent`.
 * 
 * The `expected` parameter is the number of digits in `mantissa`. This is used to handle cases where an operation
 *  increases or decreases the number of digits. For example, through a carry to a leading zero digit.
 * 
 * This function handles normalization, rounding, overflow, underflow, and zero cases.
 */
function pack(mantissa: bigint, exponent: number, expected: number): D64 {
    const digits = BN.log10(mantissa)
    const index = digits - DIGITS

    if (index > 0) {
        // Rounding occurs here
        const power = POWERS[index]
        const abs = BN.abs(mantissa)
        const remainder = abs % power
        const truncated = abs / power
        const midpoint = MIDPOINTS[index] + (~truncated & 1n)
        let rounded = truncated + (remainder >= midpoint ? 1n : 0n)

        // The rounding caused the number of digits to increase
        // TODO: Clean this up and investigate optimization opportunities
        if (rounded > MANTISSA_MAX) {
            const remainder = rounded % 10n
            const truncated = rounded / 10n
            const midpoint = 4n + (~truncated & 1n)
            rounded = truncated + (remainder >= midpoint ? 1n : 0n)
            exponent++
        }

        mantissa = mantissa < 0n ? -rounded : rounded
    } else {
        mantissa = mantissa * POWERS[-index]
    }
    
    exponent = exponent + (digits - expected)

    if (mantissa === 0n || exponent < EXPONENT_MIN) { return Zero }
    if (exponent > EXPONENT_MAX) { return Undefined }
    return new D64(mantissa, exponent)
}

/**
 * Unpacks a D64 into a `mantissa` aligned to a specified `exponent`.
 * 
 * This function does not handle any of the special cases that `pack` does.
 * It does not round and it does not handle shifting up by large exponents.
 * `exponent` should be at most `number.exponent - (DIGITS + 2)`
 */
function unpack(number: D64, exponent: number) {
    const index = number.exponent - exponent

    return index >= 0n ?
        number.mantissa * POWERS[index] :
        number.mantissa / POWERS[Math.min(-index, DIGITS)]
}

// Just used for testing
export const INTERNALS = {
    pack,
    unpack,
    BN,
    POWERS,
    MIDPOINTS,
}

// Extra information about the format
export const FORMAT_METADATA = {
    DIGITS,
    MANTISSA_BITS,
    MANTISSA_MAX,
    MANTISSA_MIN,
    EXPONENT_BITS,
    EXPONENT_MAX,
    EXPONENT_MIN,
    UNDEFINED,
}

// Common constants
export const Undefined   = new D64(0n, UNDEFINED)
export const Zero        = new D64(0n, 0)
export const One         = new D64( 1000000000000000n, 0)
export const Two         = new D64( 2000000000000000n, 0)
export const NegOne      = new D64(-1000000000000000n, 0)
// TODO: Investigate whether it's a good idea to store lots of digits to make switching precision easy
export const TAU_Q       = new D64( 1570796326794897n, 0)
export const TAU_H       = new D64( 3141592653589793n, 0)
export const TAU         = new D64( 6283185307179586n, 0)
