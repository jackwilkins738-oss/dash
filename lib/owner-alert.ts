// A Telegram message to the owner - the same bot the contact form and preview alerts use.
export async function ownerAlert(text: string, tag: string): Promise<void> {
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
      body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
    })
  } catch (error) {
    console.error(`[${tag}] Telegram request error:`, error)
  }
}
