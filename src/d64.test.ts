/** Testing */
import { INTERNALS, FORMAT_METADATA } from './d64'
import * as D64_LIB from './d64'
import { describe, test } from 'mocha'
import { expect } from 'chai'

type D64 = D64_LIB.D64
const { D64, add, from, Undefined, div } = D64_LIB
const { BN, POWERS, pack } = INTERNALS
const { DIGITS } = FORMAT_METADATA
const MIN = FORMAT_METADATA.MANTISSA_MIN
const MAX = FORMAT_METADATA.MANTISSA_MAX
const E_MIN = FORMAT_METADATA.EXPONENT_MIN
const E_MAX = FORMAT_METADATA.EXPONENT_MAX
const D = FORMAT_METADATA.DIGITS

describe('internals', () => {
    describe('BN.log10', () => {
        test('computes border values correctly', () => {
            for (let i = 0; i < POWERS.length; i++) {
                expect(BN.log10(POWERS[i])).equals(i + 1)
                expect(BN.log10(POWERS[i] - 1n)).equals(i)
            }
        })

        test('computes negative border values correctly', () => {
            for (let i = 0; i < POWERS.length; i++) {
                expect(BN.log10(-POWERS[i])).equals(i + 1)
                expect(BN.log10(-POWERS[i] + 1n)).equals(i)
            }
        })
    })
})

describe('D64', () => {
    describe('add', () => {
        describe('rounding: positive', () => {
            check($(MIN     ), () => add($(MIN     ), $(4999, -D))) // DOWN
            check($(MIN     ), () => add($(MIN     ), $(5000, -D))) // EVEN->DOWN
            check($(MIN + 1n), () => add($(MIN     ), $(5001, -D))) // UP
            check($(MIN + 1n), () => add($(MIN + 1n), $(4999, -D))) // DOWN
            check($(MIN + 2n), () => add($(MIN + 1n), $(5000, -D))) // EVEN->UP
            check($(MIN + 2n), () => add($(MIN + 1n), $(5001, -D))) // UP
        })

        describe('rounding: negative', () => {
            check($(-MIN     ), () => add($(-MIN     ), $(-4999, -D))) // DOWN
            check($(-MIN     ), () => add($(-MIN     ), $(-5000, -D))) // EVEN->DOWN
            check($(-MIN - 1n), () => add($(-MIN     ), $(-5001, -D))) // UP
            check($(-MIN - 1n), () => add($(-MIN - 1n), $(-4999, -D))) // DOWN
            check($(-MIN - 2n), () => add($(-MIN - 1n), $(-5000, -D))) // EVEN->UP
            check($(-MIN - 2n), () => add($(-MIN - 1n), $(-5001, -D))) // UP
        })

        describe('carry', () => {
            check($(1, 1), () => add(from(9), from(1)))
            check($(1, 0), () => add(from(0.9), from(0.1)))
            check($(9, -1), () => add(from(1), from(-0.1)))
        })

        describe('overflow', () => {
            check(Undefined, () => add($(MAX, E_MAX), $(5001, E_MAX - D)))
            check($(MAX, E_MAX), () => add($(MAX, E_MAX), $(0)))
        })
    })

    describe('div', () => {
        describe('rounding', () => {
            check($(1111111111111111n), () => div($(2222222222222222n), $(2)))
            check($(9999999999999910n, -1), () => div($(1000000000000000n), $(1000000000000009n)))
        })
    })
})

function check(expected: D64, f: () => D64) {
    const code = f.toString().slice(6)
    const num = expected === Undefined ? 'Undefined' : `${expected.mantissa}e${expected.exponent}`

    test(`${code} = ${num}`, () => {
        const number = f()
        expect([number.mantissa, number.exponent]).deep.equals([expected.mantissa, expected.exponent])
    })
}

function $(m: number | bigint, e: number = 0) {
    return pack(BigInt(m), e, BN.log10(BigInt(m)))
}