import { spawnSync } from 'child_process';
import { config } from './config';

export class Poster {
  private env: NodeJS.ProcessEnv;

  constructor() {
    this.env = {
      ...process.env,
      TWITTER_AUTH_TOKEN: config.twitter_auth_token,
      TWITTER_CT0: config.twitter_ct0,
    };
  }

  postReply(tweetId: string, text: string): boolean {
    try {
      const result = spawnSync('twitter', ['reply', tweetId, text], {
        env: this.env,
        encoding: 'utf-8',
        timeout: 30000,
      });

      if (result.status !== 0) {
        console.error('[ERROR] Failed to post reply:', result.stderr);
        return false;
      }

      return true;
    } catch (err) {
      console.error('[ERROR] Error posting reply:', err);
      return false;
    }
  }

  checkAuth(): boolean {
    try {
      const result = spawnSync('twitter', ['status', '--json'], {
        env: this.env,
        encoding: 'utf-8',
        timeout: 30000,
      });

      if (result.status !== 0) {
        return false;
      }

      const data = JSON.parse(result.stdout);
      return !!(data?.ok && data?.data?.authenticated);
    } catch {
      return false;
    }
  }
}

export const poster = new Poster();
