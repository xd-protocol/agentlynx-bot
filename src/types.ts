export interface FetchedTweet {
  tweet_id: string;
  content: string;
  author_username: string;
  author_bio: string;
  thread_context: string | null;
  source_type: 'keyword' | 'account';
  source_value: string;
  fetched_at: string;
  metrics: Record<string, unknown>;
}

export type ReplyStatus = 'pending' | 'posted' | 'failed' | 'rejected' | 'notified';
export type AccountType = 'individual' | 'organization';
export type TweetType = 'agent_highlight' | 'anomaly' | 'comparison';

export interface Tweet {
  tweet_id: string;
  content: string;
  author_username: string;
  author_bio: string;
  thread_context: string | null;
  source_type: string;
  source_value: string;
  fetched_at: string;
}

export interface AccountCache {
  username: string;
  account_type: AccountType;
  bio: string;
  followers: number;
  classified_at?: string;
}

export interface Reply {
  id: string;
  tweet_id: string;
  draft_text: string;
  final_text: string | null;
  status: ReplyStatus;
  source_type?: string;
  reviewed_at: string | null;
  posted_at: string | null;
  created_at: string;
}
