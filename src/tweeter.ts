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

const PROMPTS: Record<string, string> = {
  agent_highlight: `You are a crypto-native analyst sharing a standout AI agent's on-chain performance.
Write ONE tweet highlighting this agent's activity.

Rules:
- Under 280 characters (URL counts as 23 chars on X)
- English only, crypto-native casual tone
- Start with "Agent [name] on [chain]" format
- Focus on concrete numbers: volume, transactions, P&L
- End the tweet with the agent's URL on its own line
- No hashtags, no emojis
- Never mention any product or service name

Agent data:
{data_json}

Write the tweet.`,

  anomaly: `You are a crypto-native analyst who spotted something unusual in on-chain AI agent data.
Write ONE tweet about an interesting pattern or anomaly you found.

Rules:
- Under 280 characters (URL counts as 23 chars on X)
- English only, crypto-native casual tone
- Refer to agents as "Agent [name] on [chain]" format
- Highlight what's unusual: sudden spikes, outliers, unexpected behavior
- Be specific with numbers and comparisons
- Include the URL of the most notable agent on its own line at the end
- No hashtags, no emojis
- Never mention any product or service name

Data:
{data_json}

Write the tweet.`,

  comparison: `You are a crypto-native analyst comparing AI agent activity across chains.
Write ONE tweet with a specific cross-chain or category comparison.

Rules:
- Under 280 characters
- English only, crypto-native casual tone
- Refer to agents as "Agent [name] on [chain]" when mentioning specific agents
- Compare specific metrics between chains or agent categories
- Include concrete numbers, ratios, or percentages
- No links, no hashtags, no emojis
- Never mention any product or service name

Data:
{data_json}

Write the tweet.`,
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

      const response = await fetch(url.toString(), { timeout: 15000 });
      if (!response.ok) {
        console.error(`[ERROR] API request failed ${path}: ${response.status}`);
        return null;
      }

      return response.json();
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
    const chainId = agent.chain_id || agent.chainId;
    const agentId = agent.agent_id || agent.agentId;

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

  private getNextTweetType(): string {
    return TWEET_TYPES[Math.floor(Math.random() * TWEET_TYPES.length)];
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

    try {
      const message = await this.client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 1024,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
      });

      let text = message.content[0]?.type === 'text' ? message.content[0].text : null;

      if (!text) {
        return null;
      }

      if (text.length > 280) {
        text = text.substring(0, 277) + '...';
      }

      return text;
    } catch (err) {
      console.error('[ERROR] Tweet generation failed:', err);
      return null;
    }
  }

  async run(): Promise<any> {
    const result = { tweets_generated: 0 };

    const todayCount = await this.getTodayTweetCount();
    if (todayCount >= this.DAILY_TWEET_CAP) {
      result.skipped_reason = 'daily_tweet_cap_reached';
      return result;
    }

    const tweetType = this.getNextTweetType();
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
        source_type: 'original',
        source_value: 'system',
        fetched_at: new Date().toISOString(),
        metrics: {},
      },
      tweetText,
      '📌 Original Tweet'
    );

    result.tweets_generated = 1;
    (result as any).tweet_type = tweetType;
    return result;
  }
}
