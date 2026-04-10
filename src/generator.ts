import { Anthropic } from '@anthropic-ai/sdk';
import { config } from './config';

const SYSTEM_PROMPT = `You are a crypto-native with deep knowledge of Web3 and AI agents.
You write SHORT, PUNCHY, FUNKY replies with NEW perspectives - no boring validation.

CRITICAL Rules:
- NEVER just agree - that's mid
- New angle, contrarian take, missing context, or hot data drop
- NO PERIODS. Use line breaks between thoughts. Think X/Twitter energy
- Keep each line SHORT (10-20 chars max). Be fragmented and punchy
- Casual AF. Use crypto slang. Emoji OK but minimal
- Never include links, product names, promo language
- If it's obvious agreement, return "SKIP"
- Under 280 chars total
- FUNKY > polished. Weird > safe
- MATCH THE TWEET'S LANGUAGE: If tweet is in English, reply in English. If in Korean, reply in Korean. If in other language, reply in that language.

Your expertise:
- On-chain AI agents (ERC-8004)
- Agent trading & performance analytics
- Intersection of DeFi and AI
- Multi-chain agent ecosystems (Ethereum, Base, Celo, Monad, BNB, etc.)`;

const USER_PROMPT_TEMPLATE = `Write a reply to this tweet. Short lines, no periods, NEW value only.
IMPORTANT: Reply in the SAME LANGUAGE as the tweet.

Author: @{username}
Bio: {bio}
Tweet: {content}
Thread context: {thread_context}

Think weird. What's the contrarian angle? Missing data? Unpopular take? Risk they missed?

Format: Short punchy lines, line breaks between thoughts, NO PERIODS.`;

export class ReplyGenerator {
  private client: Anthropic;

  constructor() {
    this.client = new Anthropic({
      apiKey: config.anthropic_api_key,
    });
  }

  async generate(
    tweetContent: string,
    authorUsername: string,
    authorBio: string,
    threadContext: string | null
  ): Promise<string | null> {
    const userPrompt = USER_PROMPT_TEMPLATE.replace('{username}', authorUsername)
      .replace('{bio}', authorBio)
      .replace('{content}', tweetContent)
      .replace('{thread_context}', threadContext || 'None');

    try {
      const message = await this.client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 1024,
        system: SYSTEM_PROMPT,
        messages: [
          {
            role: 'user',
            content: userPrompt,
          },
        ],
      });

      const text = message.content[0]?.type === 'text' ? message.content[0].text.trim() : null;

      if (!text) {
        return null;
      }

      if (text.toUpperCase() === 'SKIP') {
        return null;
      }

      // Remove preamble
      const lines = text.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].toLowerCase();
        if (
          lines[i].trim() &&
          !line.includes("here's") &&
          !line.includes('draft') &&
          !line.includes('reply:') &&
          !line.includes('response:') &&
          !line.includes('here:')
        ) {
          const result = lines.slice(i).join('\n').trim();
          if (result.length > 280) {
            return result.substring(0, 277) + '...';
          }
          return result;
        }
      }

      if (text.length > 280) {
        return text.substring(0, 277) + '...';
      }

      return text;
    } catch (err) {
      console.error('[ERROR] Reply generation failed:', err);
      return null;
    }
  }
}

export const generator = new ReplyGenerator();
