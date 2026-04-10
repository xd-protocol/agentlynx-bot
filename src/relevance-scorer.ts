import { Anthropic } from '@anthropic-ai/sdk';
import { config } from './config';
import { FetchedTweet } from './types';

const SCORING_PROMPT = `You are an expert in on-chain AI agents and DeFi. Score this tweet's relevance to the agent economy, agent trading, and on-chain automation.

Tweet: {content}
Author: @{username}

Score from 1-10 based on:
- Direct mention of AI agents, agent economy, or agent trading: +3
- Discussion of on-chain automation or DeFi agents: +2
- Mentions specific chains or protocols: +1
- Contrarian/analytical angle (not just promotion): +2
- Engagement/discussion opportunity (not just news): +1

Reply with ONLY a number 1-10, no explanation.`;

export class RelevanceScorer {
  private client: Anthropic;

  constructor() {
    this.client = new Anthropic({
      apiKey: config.anthropic_api_key,
    });
  }

  async scoreRelevance(tweet: FetchedTweet): Promise<number> {
    const prompt = SCORING_PROMPT.replace('{content}', tweet.content)
      .replace('{username}', tweet.author_username);

    try {
      const message = await this.client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 10,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
      });

      const response = message.content[0]?.type === 'text' ? message.content[0].text : '';
      const score = parseInt(response.trim(), 10);

      if (isNaN(score) || score < 1 || score > 10) {
        return 0;
      }

      return score;
    } catch (err) {
      console.error('[ERROR] scoreRelevance:', err);
      return 0;
    }
  }

  async findBestTweet(tweets: FetchedTweet[]): Promise<FetchedTweet | null> {
    if (tweets.length === 0) {
      return null;
    }

    if (tweets.length === 1) {
      return tweets[0];
    }

    console.log(`[INFO] Scoring ${tweets.length} tweets for relevance...`);

    const scores: Array<{ tweet: FetchedTweet; score: number }> = [];

    for (const tweet of tweets) {
      const score = await this.scoreRelevance(tweet);
      scores.push({ tweet, score });
      console.log(`[INFO] Tweet ${tweet.tweet_id}: score ${score}`);
    }

    // Sort by score descending
    scores.sort((a, b) => b.score - a.score);

    const best = scores[0];
    console.log(
      `[INFO] Best tweet selected: ${best.tweet.tweet_id} (score: ${best.score})`
    );

    return best.tweet;
  }
}

export const relevanceScorer = new RelevanceScorer();
