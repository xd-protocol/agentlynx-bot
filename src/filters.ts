import { Anthropic } from '@anthropic-ai/sdk';
import { db } from './db';
import { fetcher } from './fetcher';
import { config } from './config';
import { FetchedTweet } from './types';

const CLASSIFY_PROMPT = `Classify this X account as "individual" or "organization".

Username: @{username}
Display name: {name}
Bio: {bio}
Verified: {verified}
Followers: {followers}

"individual" = real person (influencer, developer, researcher, trader, etc.)
"organization" = company, protocol, DAO, VC fund, exchange, lab, foundation, media outlet, bot

Reply with ONLY "individual" or "organization".`;

const RELEVANCE_PROMPT = `Is this tweet relevant to on-chain AI agents, agent trading, DeFi automation, or the agent economy?

Tweet: {content}

Reply with ONLY "relevant" or "irrelevant".`;

export class Filters {
  private client: Anthropic;

  constructor() {
    this.client = new Anthropic({
      apiKey: config.anthropic_api_key,
    });
  }

  dedup(tweets: FetchedTweet[]): FetchedTweet[] {
    const seen = new Set<string>();
    return tweets.filter((tweet) => {
      if (seen.has(tweet.tweet_id)) {
        return false;
      }
      seen.add(tweet.tweet_id);
      return true;
    });
  }

  isWithinFollowerRange(followers: number): boolean {
    return followers >= config.MIN_FOLLOWERS && followers <= config.MAX_FOLLOWERS;
  }

  async classifyAccount(username: string): Promise<string> {
    const cached = await db.getCachedAccount(username);
    if (cached) {
      return cached.account_type;
    }

    const profile = await fetcher.fetchUserProfile(username);
    if (!profile) {
      return 'organization';
    }

    const prompt = CLASSIFY_PROMPT.replace('{username}', profile.username)
      .replace('{name}', profile.name)
      .replace('{bio}', profile.bio)
      .replace('{verified}', String(profile.verified))
      .replace('{followers}', String(profile.followers));

    try {
      const message = await this.client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 50,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
      });

      const accountType = (
        message.content[0]?.type === 'text' ? message.content[0].text : ''
      )
        .toLowerCase()
        .trim();

      const result = accountType === 'individual' ? 'individual' : 'organization';
      await db.cacheAccount(username, result, profile.bio, profile.followers);
      return result;
    } catch (err) {
      console.error('[ERROR] classifyAccount:', err);
      return 'organization';
    }
  }

  async checkRelevance(content: string): Promise<boolean> {
    const prompt = RELEVANCE_PROMPT.replace('{content}', content);

    try {
      const message = await this.client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 50,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
      });

      const response = (
        message.content[0]?.type === 'text' ? message.content[0].text : ''
      )
        .toLowerCase()
        .trim();

      return response === 'relevant';
    } catch (err) {
      console.error('[ERROR] checkRelevance:', err);
      return false;
    }
  }

  async filterTweet(tweet: FetchedTweet): Promise<boolean> {
    const username = tweet.author_username;

    console.log(`[INFO] Classifying account: ${username}`);
    const accountType = await this.classifyAccount(username);
    console.log(`[INFO] Account type: ${accountType}`);

    if (accountType !== 'individual') {
      console.log('[INFO] Filtered: not individual');
      return false;
    }

    const cached = await db.getCachedAccount(username);
    if (cached && !this.isWithinFollowerRange(cached.followers)) {
      console.log(`[INFO] Filtered: followers out of range (${cached.followers})`);
      return false;
    }

    console.log('[INFO] Checking relevance for tweet');
    if (!(await this.checkRelevance(tweet.content))) {
      console.log('[INFO] Filtered: not relevant');
      return false;
    }

    console.log('[INFO] Tweet passed all filters');
    return true;
  }
}

export const filters = new Filters();
