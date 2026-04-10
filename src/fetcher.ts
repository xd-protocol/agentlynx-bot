import { spawnSync } from 'child_process';
import { config } from './config';
import { FetchedTweet } from './types';

interface TwitterResponse {
  ok: boolean;
  data: Array<{
    id: string;
    text: string;
    author: { screenName: string };
    metrics: Record<string, unknown>;
  }>;
}

interface UserResponse {
  ok: boolean;
  data: {
    screenName: string;
    name: string;
    bio: string;
    followers: number;
    verified: boolean;
  };
}

export class Fetcher {
  private env: NodeJS.ProcessEnv;

  constructor() {
    this.env = {
      ...process.env,
      TWITTER_AUTH_TOKEN: config.twitter_auth_token,
      TWITTER_CT0: config.twitter_ct0,
    };
  }

  private runTwitter(args: string[]): TwitterResponse | null {
    try {
      const result = spawnSync('twitter', [...args, '--json'], {
        env: this.env,
        encoding: 'utf-8',
        timeout: 30000,
      });

      if (result.status !== 0) {
        console.error('[ERROR] twitter CLI failed:', result.stderr);
        return null;
      }

      if (!result.stdout) {
        return null;
      }

      return JSON.parse(result.stdout);
    } catch (err) {
      console.error('[ERROR] runTwitter exception:', err);
      return null;
    }
  }

  private parseTweet(raw: any, sourceType: 'keyword' | 'account', sourceValue: string): FetchedTweet {
    return {
      tweet_id: raw.id,
      content: raw.text || '',
      author_username: raw.author?.screenName || '',
      author_bio: '',
      thread_context: null,
      source_type: sourceType,
      source_value: sourceValue,
      created_at: raw.createdAt || raw.created_at || new Date().toISOString(),
      fetched_at: new Date().toISOString(),
      metrics: raw.metrics || {},
    };
  }

  async searchKeyword(keyword: string, maxResults: number = 20): Promise<FetchedTweet[]> {
    console.log(`[INFO] Searching keyword: ${keyword}`);

    const data = this.runTwitter(['search', keyword, '--lang', 'en', '-n', String(maxResults)]);

    if (!data || !data.ok) {
      console.error(`[ERROR] Search failed for keyword: ${keyword}`);
      return [];
    }

    const tweets = (data.data || []).map((t: any) =>
      this.parseTweet(t, 'keyword', keyword)
    );

    console.log(`[INFO] Found ${tweets.length} tweets for keyword ${keyword}`);
    return tweets;
  }

  async fetchAccountTweets(username: string, maxResults: number = 10): Promise<FetchedTweet[]> {
    const data = this.runTwitter(['user-posts', username, '-n', String(maxResults)]);

    if (!data || !data.ok) {
      return [];
    }

    return (data.data || []).map((t: any) => this.parseTweet(t, 'account', username));
  }

  async fetchUserProfile(
    username: string
  ): Promise<{ username: string; name: string; bio: string; followers: number; verified: boolean } | null> {
    const result = spawnSync('twitter', ['user', username, '--json'], {
      env: this.env,
      encoding: 'utf-8',
      timeout: 30000,
    });

    if (result.status !== 0) {
      return null;
    }

    try {
      const data = JSON.parse(result.stdout) as UserResponse;
      if (!data.ok || !data.data) {
        return null;
      }

      return {
        username: data.data.screenName,
        name: data.data.name,
        bio: data.data.bio,
        followers: data.data.followers,
        verified: data.data.verified,
      };
    } catch {
      return null;
    }
  }

  async checkAuth(): Promise<boolean> {
    const data = this.runTwitter(['status']);
    return !!(data?.ok && data?.data);
  }
}

export const fetcher = new Fetcher();
