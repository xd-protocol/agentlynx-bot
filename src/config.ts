import 'dotenv/config';

export const config = {
  // Twitter
  twitter_auth_token: process.env.TWITTER_AUTH_TOKEN || '',
  twitter_ct0: process.env.TWITTER_CT0 || '',

  // Supabase
  supabase_url: process.env.SUPABASE_URL || '',
  supabase_key: process.env.SUPABASE_KEY || '',

  // Telegram
  telegram_bot_token: process.env.TELEGRAM_BOT_TOKEN || '',
  telegram_chat_id: process.env.TELEGRAM_CHAT_ID || '',

  // Anthropic
  anthropic_api_key: process.env.ANTHROPIC_API_KEY || '',

  // API URLs
  agentlynx_api_url: 'https://agentlynx.org',

  // Constants
  DAILY_REPLY_CAP: 10,
  DAILY_TWEET_CAP: 3,
  MIN_FOLLOWERS: 1000,
  MAX_FOLLOWERS: 100000,
  CRON_INTERVAL_HOURS: 2,
};

export function validateConfig(): void {
  const required = [
    'twitter_auth_token',
    'twitter_ct0',
    'supabase_url',
    'supabase_key',
    'telegram_bot_token',
    'telegram_chat_id',
    'anthropic_api_key',
  ];

  for (const key of required) {
    if (!config[key as keyof typeof config]) {
      throw new Error(`Missing environment variable: ${key.toUpperCase()}`);
    }
  }
}
