// A Telegram message to the owner - the same bot the contact form and preview alerts use.
// "📞 Number + research": answered by the panel's bot on the owner's PC, which alone has prospects'
// phone numbers. Telegram allows 64 bytes of button data, so a very long slug simply gets no button.
export function callNowButtons(slug: string): { inline_keyboard: { text: string; callback_data: string }[][] } | undefined {
  const data = `callnow:${slug}`
  return new TextEncoder().encode(data).length <= 64
    ? { inline_keyboard: [[{ text: '📞 Number + research', callback_data: data }]] }
    : undefined
}

export async function ownerAlert(text: string, tag: string, replyMarkup?: object): Promise<void> {
  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID
  if (!token || !chatId) {
    console.log(`[${tag}] (Telegram not configured)\n${text}`)
    return
  }
  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true, ...(replyMarkup ? { reply_markup: replyMarkup } : {}) }),
    })
  } catch (error) {
    console.error(`[${tag}] Telegram request error:`, error)
  }
}
