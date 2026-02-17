import { formatNumeric } from './numberFormat'

describe('formatNumeric', () => {
  it('keeps integers untouched', () => {
    expect(formatNumeric(123)).toBe('123')
  })

  it('rounds long decimals to two digits', () => {
    expect(formatNumeric(2968.3900000000003)).toBe('2968.39')
    expect(formatNumeric('1.9999')).toBe('2')
  })

  it('keeps short decimals as is', () => {
    expect(formatNumeric(12.3)).toBe('12.3')
  })

  it('returns raw string when non-numeric', () => {
    expect(formatNumeric('abc')).toBe('abc')
  })
})
