import { v4 as uuidv4 } from 'uuid';
import { db } from './db';
import { fetcher } from './fetcher';
import { filters } from './filters';
import { generator } from './generator';
import { poster } from './poster';
import { telegram } from './telegram';
import { config } from './config';

interface PipelineStats {
  fetched: number;
  drafts_created: number;
  skipped: number;
  skipped_reason?: string;
  tweeter?: any;
}

export class Pipeline {
  async run(): Promise<PipelineStats> {
    const stats: PipelineStats = {
      fetched: 0,
      drafts_created: 0,
      skipped: 0,
    };

    const replyCount = await db.getTodayReplyCount();
    if (replyCount >= config.DAILY_REPLY_CAP) {
      console.log(`[INFO] Daily cap reached (${config.DAILY_REPLY_CAP}). Skipping.`);
      stats.skipped_reason = 'daily_cap_reached';
      return stats;
    }

    // Collect tweets
    const tweets = [];
    const keywords = await db.getActiveKeywords();
    for (const keyword of keywords) {
      tweets.push(...(await fetcher.searchKeyword(keyword)));
    }

    const accounts = await db.getActiveAccounts();
    for (const account of accounts) {
      tweets.push(...(await fetcher.fetchAccountTweets(account)));
    }

    // Dedup
    const dedupTweets = filters.dedup(tweets);
    stats.fetched = dedupTweets.length;
    console.log(`[INFO] Fetched ${dedupTweets.length} new tweets`);

    // Filter and generate drafts
    for (let i = 0; i < dedupTweets.length; i++) {
      const tweet = dedupTweets[i];

      if (replyCount + stats.drafts_created >= config.DAILY_REPLY_CAP) {
        break;
      }

      console.log(
        `[INFO] Processing tweet ${i + 1}/${dedupTweets.length}: ${tweet.tweet_id}`
      );

      if (!(await filters.filterTweet(tweet))) {
        stats.skipped++;
        console.log('[INFO] Tweet filtered out (relevance/account type)');
        continue;
      }

      console.log(`[INFO] Generating reply for tweet ${tweet.tweet_id}`);
      const replyText = await generator.generate(
        tweet.content,
        tweet.author_username,
        tweet.author_bio,
        tweet.thread_context
      );
      console.log(`[INFO] Reply generated: ${replyText ? replyText.substring(0, 50) : 'None'}`);

      if (!replyText) {
        stats.skipped++;
        continue;
      }

      // Save tweet
      await db.saveTweet(tweet);

      // Post reply immediately
      const replyId = uuidv4();
      const success = poster.postReply(tweet.tweet_id, replyText);

      // Save reply with status
      const status: 'posted' | 'failed' = success ? 'posted' : 'failed';
      await db.saveReply({
        id: replyId,
        tweet_id: tweet.tweet_id,
        draft_text: replyText,
        final_text: null,
        status,
        reviewed_at: null,
        posted_at: success ? new Date().toISOString() : null,
        created_at: new Date().toISOString(),
      });

      // Send result to Telegram
      const label = success ? '✓ Posted' : '✗ Failed';
      await telegram.sendResult(tweet, replyText, label);
      stats.drafts_created++;
      console.log(`[INFO] Reply ${label} for tweet ${tweet.tweet_id}`);
    }

    console.log(`[INFO] Pipeline complete: ${JSON.stringify(stats)}`);
    return stats;
  }
}

export const pipeline = new Pipeline();
