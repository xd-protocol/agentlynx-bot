import TelegramBot from 'node-telegram-bot-api';
import { config } from './config';
import { FetchedTweet } from './types';

export class TelegramReviewBot {
  private bot: TelegramBot;
  private chatId: string;

  constructor(token: string, chatId: string) {
    this.bot = new TelegramBot(token);
    this.chatId = chatId;
  }

  async sendResult(tweet: FetchedTweet, replyText: string, status: string): Promise<void> {
    try {
      const truncated =
        tweet.content.length > 200 ? tweet.content.substring(0, 200) + '...' : tweet.content;

      let tweetLink = '';
      if (tweet.tweet_id) {
        const tweetIdStr = String(tweet.tweet_id);
        if (/^\d+$/.test(tweetIdStr)) {
          tweetLink = `\nhttps://x.com/${tweet.author_username}/status/${tweetIdStr}`;
        }
      }

      const text =
        `${status}\n\n` +
        `@${tweet.author_username}:\n` +
        `${truncated}${tweetLink}\n\n` +
        `Reply:\n${replyText}`;

      await this.bot.sendMessage(this.chatId, text);
    } catch (err) {
      console.error('[ERROR] sendResult:', err);
    }
  }
}

export const telegram = new TelegramReviewBot(config.telegram_bot_token, config.telegram_chat_id);
