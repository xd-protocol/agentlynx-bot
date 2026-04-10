import { Anthropic } from '@anthropic-ai/sdk';
import { v4 as uuidv4 } from 'uuid';
import { db } from './db';
import { telegram } from './telegram';
import { config } from './config';

const CHAIN_NAMES: Record<number, string> = {
  1: 'Ethereum',
  56: 'BNB Chain',
  143: 'Monad',
  8453: 'Base',
  42220: 'Celo',
};

const CHAIN_SLUGS: Record<number, string> = {
  1: 'ethereum',
  56: 'bsc',
  8453: 'base',
  42220: 'celo',
  143: 'monad',
};

const TWEET_TYPES = ['agent_highlight', 'anomaly', 'comparison'];

const SYSTEM_PROMPT = `You are a crypto-native analyst. You write extremely short, punchy tweets.
HARD LIMIT: Your output must NEVER exceed 160 characters total. No exceptions.
Style: casual, no hashtags, no URLs, no emojis, no product names.`;

const PROMPTS: Record<string, string> = {
  agent_highlight: `Here is agent data: {data_json}

Write ONE tweet about this agent's on-chain performance. Pick ONE interesting number (volume, P&L, or tx count) and make a punchy observation.

HARD LIMIT: 160 characters maximum. Output ONLY the tweet text, nothing else.`,

  anomaly: `Here is agent data: {data_json}

Write ONE tweet about an unusual pattern you see. Highlight ONE weird finding with a number. Contrarian tone.

HARD LIMIT: 160 characters maximum. Output ONLY the tweet text, nothing else.`,

  comparison: `Here is agent data: {data_json}

Write ONE tweet comparing agent activity across chains. Pick ONE cross-chain stat and make it punchy.

HARD LIMIT: 160 characters maximum. Output ONLY the tweet text, nothing else.`,
};

interface Agent {
  chain_id?: number;
  agent_id?: string;
  chainId?: number;
  agentId?: string;
  [key: string]: any;
}

interface EcosystemStats {
  chains: Array<{ id: number; [key: string]: any }>;
  serviceTypes: unknown[];
  capabilities: unknown[];
}

export class StatsCollector {
  private apiUrl: string;

  constructor(apiUrl: string) {
    this.apiUrl = apiUrl.replace(/\/$/, '');
  }

  private async fetch(path: string, params?: Record<string, string>): Promise<any> {
    try {
      const url = new URL(path, this.apiUrl);
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      try {
        const response = await fetch(url.toString(), {
          signal: controller.signal,
        });

        if (!response.ok) {
          console.error(`[ERROR] API request failed ${path}: ${response.status}`);
          return null;
        }

        return response.json();
      } finally {
        clearTimeout(timeoutId);
      }
    } catch (err) {
      console.error(`[ERROR] API request failed ${path}:`, err);
      return null;
    }
  }

  async fetchEcosystemStats(): Promise<EcosystemStats | null> {
    return this.fetch('/api/agents/filter-options');
  }

  async fetchTrendingAgents(): Promise<Agent[] | null> {
    const data = await this.fetch('/api/agents/suggestions');
    if (Array.isArray(data)) {
      return data;
    }
    return data?.data || null;
  }

  async fetchTopAgents(count: number = 5): Promise<Agent[] | null> {
    const data = await this.fetch('/api/agents', {
      sort: 'score',
      pageSize: String(count),
    });
    if (Array.isArray(data)) {
      return data;
    }
    return data?.data || null;
  }

  async fetchAgentDetail(chainId: number, agentId: string): Promise<any> {
    return this.fetch(`/api/agents/${chainId}/${agentId}`);
  }

  async collectForHighlight(): Promise<any> {
    const trending = await this.fetchTrendingAgents();
    if (!trending || trending.length === 0) {
      return null;
    }

    const agent = trending[0];
    const chainId = (agent.chain_id || agent.chainId) as number | undefined;
    const agentId = (agent.agent_id || agent.agentId) as string | undefined;

    if (!chainId || !agentId) {
      return null;
    }

    const detail = await this.fetchAgentDetail(chainId, agentId);
    if (!detail) {
      return null;
    }

    detail.chain_name = CHAIN_NAMES[chainId] || `Chain ${chainId}`;
    const slug = CHAIN_SLUGS[chainId] || String(chainId);
    detail.url = `${this.apiUrl}/agents/${slug}/${agentId}`;

    return detail;
  }

  async collectForAnomaly(): Promise<any> {
    const top = await this.fetchTopAgents(10);
    const trending = await this.fetchTrendingAgents();

    if (!top && !trending) {
      return null;
    }

    const agents = top || trending || [];
    for (const a of agents) {
      const chainId = a.chain_id || a.chainId;
      const agentId = a.agent_id || a.agentId;

      if (chainId && agentId) {
        const slug = CHAIN_SLUGS[chainId] || String(chainId);
        a.chain_name = CHAIN_NAMES[chainId] || `Chain ${chainId}`;
        a.url = `${this.apiUrl}/agents/${slug}/${agentId}`;
      }
    }

    return { top_agents: top || [], trending: trending || [] };
  }

  async collectForComparison(): Promise<any> {
    const ecosystem = await this.fetchEcosystemStats();
    const top = await this.fetchTopAgents(10);

    if (!ecosystem) {
      return null;
    }

    const chains = ecosystem.chains || [];
    for (const c of chains) {
      c.name = CHAIN_NAMES[c.id] || `Chain ${c.id}`;
    }

    return {
      chains,
      serviceTypes: ecosystem.serviceTypes || [],
      capabilities: ecosystem.capabilities || [],
      top_agents: top || [],
    };
  }
}

interface TweeterResult {
  tweets_generated: number;
  skipped_reason?: string;
  tweet_type?: string;
}

export class Tweeter {
  private statsCollector: StatsCollector;
  private client: Anthropic;
  private readonly DAILY_TWEET_CAP = config.DAILY_TWEET_CAP;

  constructor(statsCollector: StatsCollector) {
    this.statsCollector = statsCollector;
    this.client = new Anthropic({
      apiKey: config.anthropic_api_key,
    });
  }

  private async getTodayTweetCount(): Promise<number> {
    const now = new Date();
    const today = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}-${String(now.getUTCDate()).padStart(2, '0')}T00:00:00+00:00`;

    // Simple in-memory count (simplified version)
    return 0;
  }

  private async getNextTweetType(): Promise<string> {
    // Get all original tweets from today, count by type
    // Then return the type with the fewest tweets (or the next in cycle)
    const now = new Date();
    const today = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}-${String(now.getUTCDate()).padStart(2, '0')}T00:00:00+00:00`;

    // For simplicity, just cycle through types in order
    // Get today's tweets and find which type was last
    const count = await this.getTodayTweetCount();
    const tweetTypeIndex = count % TWEET_TYPES.length;
    return TWEET_TYPES[tweetTypeIndex];
  }

  private async collectData(tweetType: string): Promise<any> {
    if (tweetType === 'agent_highlight') {
      return this.statsCollector.collectForHighlight();
    } else if (tweetType === 'anomaly') {
      return this.statsCollector.collectForAnomaly();
    } else if (tweetType === 'comparison') {
      return this.statsCollector.collectForComparison();
    }
    return null;
  }

  private async generateTweet(tweetType: string, data: any): Promise<string | null> {
    const prompt = PROMPTS[tweetType].replace(
      '{data_json}',
      JSON.stringify(data, null, 2)
    );

    let retries = 0;
    const maxRetries = 3;

    while (retries < maxRetries) {
      try {
        const message = await this.client.messages.create({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 200,
          system: SYSTEM_PROMPT,
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        });

        let text = message.content[0]?.type === 'text' ? message.content[0].text : null;

        if (!text) {
          retries++;
          continue;
        }

        // Check 160 character limit
        if (text.length > 160) {
          retries++;
          console.log(
            `[INFO] Generated tweet exceeds 160 chars (${text.length}), retrying (${retries}/${maxRetries})...`
          );
          continue;
        }

        return text;
      } catch (err) {
        console.error('[ERROR] Tweet generation failed:', err);
        retries++;
      }
    }

    console.error('[ERROR] Failed to generate valid tweet after retries');
    return null;
  }

  async run(): Promise<TweeterResult> {
    const result: TweeterResult = { tweets_generated: 0 };

    const todayCount = await this.getTodayTweetCount();
    if (todayCount >= this.DAILY_TWEET_CAP) {
      result.skipped_reason = 'daily_tweet_cap_reached';
      return result;
    }

    const tweetType = await this.getNextTweetType();
    const data = await this.collectData(tweetType);

    if (!data) {
      result.skipped_reason = 'no_data_available';
      return result;
    }

    const tweetText = await this.generateTweet(tweetType, data);

    if (!tweetText) {
      result.skipped_reason = 'generation_failed';
      return result;
    }

    const tweetId = uuidv4();
    await db.saveReply({
      id: tweetId,
      tweet_id: tweetId,
      draft_text: tweetText,
      final_text: null,
      status: 'notified',
      source_type: 'original_tweet',
      reviewed_at: null,
      posted_at: null,
      created_at: new Date().toISOString(),
    });

    await telegram.sendResult(
      {
        tweet_id: tweetId,
        content: `[Original Tweet — ${tweetType}]`,
        author_username: 'agent_lynx',
        author_bio: '',
        thread_context: null,
        source_type: 'keyword',
        source_value: 'system',
        created_at: new Date().toISOString(),
        fetched_at: new Date().toISOString(),
        metrics: {},
      },
      tweetText,
      '📌 Original Tweet'
    );

    result.tweets_generated = 1;
    result.tweet_type = tweetType;
    return result;
  }
}
