import { Anthropic } from '@anthropic-ai/sdk';
import { config } from './config';

const SYSTEM_PROMPT = `You are a crypto-native with deep knowledge of Web3 and AI agents.
You write SHORT, PUNCHY replies with NEW perspectives - no boring validation.

CRITICAL Rules:
- NEVER just agree - that's mid
- New angle, contrarian take, missing context, or hot data drop
- NO PERIODS. Use line breaks between 2-3 short thoughts for readability
- Each line should be SHORT and punchy (10-30 chars per line)
- Casual AF. Use crypto slang. Emoji OK but minimal
- Never include links, product names, promo language
- If it's obvious agreement, return "SKIP"
- TOTAL CHARACTER COUNT (including line breaks): MUST BE 160 CHARACTERS OR LESS
- FUNKY > polished. Weird > safe
- MATCH THE TWEET'S LANGUAGE: If tweet is in English, reply in English. If in Korean, reply in Korean. If in other language, reply in that language.

Your expertise:
- On-chain AI agents (ERC-8004)
- Agent trading & performance analytics
- Intersection of DeFi and AI
- Multi-chain agent ecosystems (Ethereum, Base, Celo, Monad, BNB, etc.)`;

const USER_PROMPT_TEMPLATE = `Write a reply to this tweet. Make it visually clean with 2-3 short lines.
CRITICAL: Total length INCLUDING line breaks MUST be 160 characters or less. Count every character.
IMPORTANT: Reply in the SAME LANGUAGE as the tweet.

Author: @{username}
Bio: {bio}
Tweet: {content}
Thread context: {thread_context}

Think weird. What's the contrarian angle? Missing data? Unpopular take? Risk they missed?

Format: 2-3 short lines, no periods, punchy. TOTAL MUST BE 160 CHARS OR LESS.`;

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

    let retries = 0;
    const maxRetries = 3;

    while (retries < maxRetries) {
      try {
        const message = await this.client.messages.create({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 300,
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
          retries++;
          continue;
        }

        if (text.toUpperCase() === 'SKIP') {
          return null;
        }

        // Remove preamble
        const lines = text.split('\n');
        let result = text;
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
            result = lines.slice(i).join('\n').trim();
            break;
          }
        }

        // Check 160 character limit
        if (result.length > 160) {
          retries++;
          console.log(
            `[INFO] Generated reply exceeds 160 chars (${result.length}), retrying (${retries}/${maxRetries})...`
          );
          continue;
        }

        return result;
      } catch (err) {
        console.error('[ERROR] Reply generation failed:', err);
        retries++;
      }
    }

    console.error('[ERROR] Failed to generate valid reply after retries');
    return null;
  }
}

export const generator = new ReplyGenerator();
