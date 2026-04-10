import { config } from './config';

const BEARER_TOKEN =
  'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs' +
  '%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA';

const QUERY_IDS: Record<string, string> = {
  SearchTimeline: 'MJpyQGqgklrVl_0X9gNy3A',
  UserTweets: 'E3opETHurmVJflFsUBVuUQ',
  UserByScreenName: 'qRednkZG-rn1P6b48NINmQ',
  CreateTweet: 'bDE2rBtZb3uyrczSZ_pI9g',
};

const DEFAULT_FEATURES = {
  responsive_web_graphql_exclude_directive_enabled: true,
  creator_subscriptions_tweet_preview_api_enabled: true,
  responsive_web_graphql_timeline_navigation_enabled: true,
  c9s_tweet_anatomy_moderator_badge_enabled: true,
  tweetypie_unmention_optimization_enabled: true,
  responsive_web_edit_tweet_api_enabled: true,
  graphql_is_translatable_rweb_tweet_is_translatable_enabled: true,
  view_counts_everywhere_api_enabled: true,
  longform_notetweets_consumption_enabled: true,
  responsive_web_twitter_article_tweet_consumption_enabled: true,
  longform_notetweets_rich_text_read_enabled: true,
  rweb_video_timestamps_enabled: true,
  responsive_web_media_download_video_enabled: true,
  freedom_of_speech_not_reach_fetch_enabled: true,
  standardized_nudges_misinfo: true,
};

export interface TwitterTweet {
  id: string;
  text: string;
  createdAt: string;
  author: {
    screenName: string;
    name: string;
    followersCount: number;
  };
  metrics: {
    replyCount: number;
    retweetCount: number;
    likeCount: number;
  };
}

export interface TwitterUser {
  id: string;
  screenName: string;
  name: string;
  bio: string;
  followersCount: number;
  verified: boolean;
}

function buildHeaders(ct0: string, authToken: string): Record<string, string> {
  return {
    authorization: `Bearer ${BEARER_TOKEN}`,
    cookie: `auth_token=${authToken}; ct0=${ct0}`,
    'x-csrf-token': ct0,
    'content-type': 'application/json',
    'x-twitter-active-user': 'yes',
    'x-twitter-auth-type': 'OAuth2Session',
    'x-twitter-client-language': 'en',
    'user-agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
  };
}

function buildGqlUrl(
  operation: string,
  variables: Record<string, any>,
  features: Record<string, any>
): string {
  const queryId = QUERY_IDS[operation];
  const compactFeatures = Object.fromEntries(
    Object.entries(features).filter(([, v]) => v !== false)
  );
  return (
    `https://x.com/i/api/graphql/${queryId}/${operation}` +
    `?variables=${encodeURIComponent(JSON.stringify(variables))}` +
    `&features=${encodeURIComponent(JSON.stringify(compactFeatures))}`
  );
}

async function apiGet(url: string, headers: Record<string, string>): Promise<any> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const res = await fetch(url, { headers, signal: controller.signal });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

async function apiPost(
  url: string,
  headers: Record<string, string>,
  body: any
): Promise<any> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

function parseTweetResult(result: any): TwitterTweet | null {
  try {
    const core = result?.core || result?.tweet?.core;
    const legacy = result?.legacy || result?.tweet?.legacy;
    const userLegacy = core?.user_results?.result?.legacy;

    if (!legacy || !userLegacy) return null;

    return {
      id: legacy.id_str || result.rest_id,
      text: legacy.full_text || legacy.text || '',
      createdAt: legacy.created_at || '',
      author: {
        screenName: userLegacy.screen_name || '',
        name: userLegacy.name || '',
        followersCount: userLegacy.followers_count || 0,
      },
      metrics: {
        replyCount: legacy.reply_count || 0,
        retweetCount: legacy.retweet_count || 0,
        likeCount: legacy.favorite_count || 0,
      },
    };
  } catch {
    return null;
  }
}

function extractTweetsFromInstructions(instructions: any[]): TwitterTweet[] {
  const tweets: TwitterTweet[] = [];

  for (const instruction of instructions || []) {
    const entries = instruction?.entries || [];
    for (const entry of entries) {
      const content = entry?.content;
      if (!content) continue;

      // Single tweet
      const itemContent = content?.itemContent;
      if (itemContent?.tweet_results?.result) {
        const tweet = parseTweetResult(itemContent.tweet_results.result);
        if (tweet) tweets.push(tweet);
      }

      // Module (multiple tweets in one entry)
      const items = content?.items || [];
      for (const item of items) {
        const result = item?.item?.itemContent?.tweet_results?.result;
        if (result) {
          const tweet = parseTweetResult(result);
          if (tweet) tweets.push(tweet);
        }
      }
    }
  }

  return tweets;
}

export class TwitterClient {
  private headers: Record<string, string>;

  constructor() {
    this.headers = buildHeaders(config.twitter_ct0, config.twitter_auth_token);
  }

  async searchTweets(query: string, count: number = 20): Promise<TwitterTweet[]> {
    const variables = {
      count,
      rawQuery: query,
      querySource: 'typed_query',
      product: 'Top',
    };

    try {
      const url = buildGqlUrl('SearchTimeline', variables, DEFAULT_FEATURES);
      const data = await apiGet(url, this.headers);
      const instructions =
        data?.data?.search_by_raw_query?.search_timeline?.timeline?.instructions || [];
      return extractTweetsFromInstructions(instructions);
    } catch (err) {
      console.error('[ERROR] searchTweets:', err);
      return [];
    }
  }

  async fetchUserTweets(screenName: string, count: number = 10): Promise<TwitterTweet[]> {
    try {
      // First get user ID
      const user = await this.fetchUser(screenName);
      if (!user) return [];

      const variables = {
        userId: user.id,
        count,
        withQuickPromoteEligibilityTweetFields: true,
        withVoice: true,
        withV2Timeline: true,
      };

      const url = buildGqlUrl('UserTweets', variables, DEFAULT_FEATURES);
      const data = await apiGet(url, this.headers);
      const instructions =
        data?.data?.user?.result?.timeline_v2?.timeline?.instructions || [];
      return extractTweetsFromInstructions(instructions);
    } catch (err) {
      console.error('[ERROR] fetchUserTweets:', err);
      return [];
    }
  }

  async fetchUser(screenName: string): Promise<TwitterUser | null> {
    const variables = {
      screen_name: screenName,
      withSafetyModeUserFields: true,
    };
    const features = {
      hidden_profile_subscriptions_enabled: true,
      responsive_web_graphql_exclude_directive_enabled: true,
      verified_phone_label_enabled: false,
      subscriptions_verification_info_is_identity_verified_enabled: true,
      highlights_tweets_tab_ui_enabled: true,
      creator_subscriptions_tweet_preview_api_enabled: true,
      responsive_web_graphql_skip_user_profile_image_extensions_enabled: false,
      responsive_web_graphql_timeline_navigation_enabled: true,
    };

    try {
      const url = buildGqlUrl('UserByScreenName', variables, features);
      const data = await apiGet(url, this.headers);
      const result = data?.data?.user?.result;
      if (!result) return null;

      const legacy = result.legacy || {};
      return {
        id: result.rest_id || '',
        screenName: legacy.screen_name || screenName,
        name: legacy.name || '',
        bio: legacy.description || '',
        followersCount: legacy.followers_count || 0,
        verified: !!(result.is_blue_verified || legacy.verified),
      };
    } catch (err) {
      console.error('[ERROR] fetchUser:', err);
      return null;
    }
  }

  async postReply(tweetId: string, text: string): Promise<boolean> {
    const queryId = QUERY_IDS.CreateTweet;
    const url = `https://x.com/i/api/graphql/${queryId}/CreateTweet`;
    const body = {
      variables: {
        tweet_text: text,
        reply: {
          in_reply_to_tweet_id: tweetId,
          exclude_reply_user_ids: [],
        },
        media: { media_entities: [], possibly_sensitive: false },
        semantic_annotation_ids: [],
        dark_request: false,
      },
      queryId,
      features: DEFAULT_FEATURES,
    };

    try {
      const data = await apiPost(url, this.headers, body);
      const result = data?.data?.create_tweet?.tweet_results?.result;
      return !!result?.rest_id;
    } catch (err) {
      console.error('[ERROR] postReply:', err);
      return false;
    }
  }

  async checkAuth(): Promise<boolean> {
    try {
      const url = 'https://x.com/i/api/1.1/account/multi/list.json';
      const data = await apiGet(url, this.headers);
      return !!(data?.users?.length || (Array.isArray(data) && data.length));
    } catch {
      return false;
    }
  }
}

export const twitterClient = new TwitterClient();
