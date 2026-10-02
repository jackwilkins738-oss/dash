import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { choiceAlert, clampEngagement, cleanPhone, isBotUserAgent } from './engagement.ts'

describe('isBotUserAgent', () => {
  it('flags scanners and crawlers, not phones', () => {
    for (const ua of [
      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/120.0 Safari/537.36',
      'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
      'python-requests/2.31',
      '',
      null,
    ]) {
      assert.equal(isBotUserAgent(ua), true, String(ua))
    }
    assert.equal(isBotUserAgent('Mozilla/5.0 (Linux; Android 13; CUBOT X30) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36'), false)
    assert.equal(isBotUserAgent('Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)'), true)
    assert.equal(
      isBotUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'),
      false,
    )
  })
})

describe('cleanPhone', () => {
  it('keeps UK numbers in national form, drops anything else', () => {
    assert.equal(cleanPhone('+44 7700 900123'), '07700900123')
    assert.equal(cleanPhone('01483 000000'), '01483000000')
    assert.equal(cleanPhone('447700900123'), '07700900123')
    assert.equal(cleanPhone('call me <script>'), '')
    assert.equal(cleanPhone('12345'), '')
    assert.equal(cleanPhone(undefined), '')
  })
})

describe('clampEngagement', () => {
  it('caps time and scroll, keeps known sections once', () => {
    assert.deepEqual(clampEngagement({ seconds: 99999, scroll: -5, reached: ['pricing', 'pricing', 'x', 'rebuilt'] }), {
      seconds: 1800,
      scroll: 0,
      reached: ['pricing', 'rebuilt'],
    })
    assert.deepEqual(clampEngagement({}), { seconds: 0, scroll: 0, reached: [] })
  })
})

describe('choiceAlert', () => {
  const firm = { business_name: 'Kerr Roofing', trade: 'roofer', area: 'Leeds', view_count: 3 }
  it('says what they tapped and what to do', () => {
    const call = choiceAlert('call', firm, '07700900123')
    assert.match(call, /Kerr Roofing tapped "Yes, give me a ring".*visit 3/)
    assert.match(call, /Number they gave: 07700900123/)
    assert.match(choiceAlert('call', firm, ''), /ring the one on your list/)
    assert.match(choiceAlert('whatsapp', firm, ''), /WhatsApp me/)
    assert.match(choiceAlert('not_now', firm, ''), /Follow-up emails stop/)
  })
})
