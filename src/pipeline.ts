import { v4 as uuidv4 } from 'uuid';
import { db } from './db';
import { fetcher } from './fetcher';
import { filters } from './filters';
import { generator } from './generator';
import { poster } from './poster';
import { telegram } from './telegram';
import { relevanceScorer } from './relevance-scorer';
import { Tweeter, StatsCollector } from './tweeter';
import { config } from './config';

interface PipelineStats {
  fetched: number;
  drafts_created: number;
  skipped: number;
  skipped_reason?: string;
  tweeter?: any;
}

export class Pipeline {
  private tweeter: Tweeter;

  constructor() {
    const statsCollector = new StatsCollector(config.agentlynx_api_url);
    this.tweeter = new Tweeter(statsCollector);
  }

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

    if (dedupTweets.length === 0) {
      console.log('[INFO] Pipeline complete: no new tweets');
      return stats;
    }

    // Filter tweets: only last 24 hours
    const now = new Date();
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const recentTweets = dedupTweets.filter((tweet) => {
      const tweetTime = new Date(tweet.created_at);
      return tweetTime >= twentyFourHoursAgo;
    });

    console.log(`[INFO] Filtered to ${recentTweets.length} tweets from last 24 hours`);

    if (recentTweets.length === 0) {
      console.log('[INFO] No tweets from last 24 hours');
      stats.skipped = dedupTweets.length;
      return stats;
    }

    // Apply additional filters
    const filteredTweets = [];
    for (const tweet of recentTweets) {
      if (await filters.filterTweet(tweet)) {
        filteredTweets.push(tweet);
      } else {
        stats.skipped++;
      }
    }

    console.log(`[INFO] Filtered down to ${filteredTweets.length} tweets`);

    if (filteredTweets.length === 0) {
      console.log('[INFO] No tweets passed filtering');
      return stats;
    }

    // Find the single best tweet by relevance score
    const bestTweet = await relevanceScorer.findBestTweet(filteredTweets);
    if (!bestTweet) {
      console.log('[INFO] Could not determine best tweet');
      return stats;
    }

    // Generate and post reply for the best tweet only
    console.log(`[INFO] Generating reply for best tweet ${bestTweet.tweet_id}`);
    const replyText = await generator.generate(
      bestTweet.content,
      bestTweet.author_username,
      bestTweet.author_bio,
      bestTweet.thread_context
    );
    console.log(`[INFO] Reply generated: ${replyText ? replyText.substring(0, 50) : 'None'}`);

    if (!replyText) {
      stats.skipped++;
      return stats;
    }

    // Save tweet
    await db.saveTweet(bestTweet);

    // Post reply immediately
    const replyId = uuidv4();
    const success = poster.postReply(bestTweet.tweet_id, replyText);

    // Save reply with status
    const status: 'posted' | 'failed' = success ? 'posted' : 'failed';
    await db.saveReply({
      id: replyId,
      tweet_id: bestTweet.tweet_id,
      draft_text: replyText,
      final_text: null,
      status,
      reviewed_at: null,
      posted_at: success ? new Date().toISOString() : null,
      created_at: new Date().toISOString(),
    });

    // Send result to Telegram
    const label = success ? '✓ Posted' : '✗ Failed';
    await telegram.sendResult(bestTweet, replyText, label);
    stats.drafts_created++;
    console.log(`[INFO] Reply ${label} for tweet ${bestTweet.tweet_id}`);

    // Always try to tweet one original tweet (A, B, or C)
    console.log('[INFO] Running tweeter for original tweet...');
    try {
      const tweeterResult = await this.tweeter.run();
      stats.tweeter = tweeterResult;
    } catch (err) {
      console.error('[ERROR] Tweeter failed:', err);
    }

    console.log(`[INFO] Pipeline complete: ${JSON.stringify(stats)}`);
    return stats;
  }
}

export const pipeline = new Pipeline();
