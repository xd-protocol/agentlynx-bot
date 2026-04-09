-- monitored_keywords
create table if not exists monitored_keywords (
  id uuid primary key default gen_random_uuid(),
  keyword text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- monitored_accounts
create table if not exists monitored_accounts (
  id uuid primary key default gen_random_uuid(),
  username text not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- account_cache
create table if not exists account_cache (
  username text primary key,
  account_type text not null,
  bio text,
  followers integer,
  classified_at timestamptz not null default now()
);

-- tweets
create table if not exists tweets (
  id uuid primary key default gen_random_uuid(),
  tweet_id text not null unique,
  author_username text not null,
  author_bio text,
  content text not null,
  thread_context text,
  relevance_score text,
  source_type text not null,
  source_value text not null,
  fetched_at timestamptz not null default now()
);

-- replies
create table if not exists replies (
  id uuid primary key default gen_random_uuid(),
  tweet_id text not null references tweets(tweet_id),
  draft_text text not null,
  final_text text,
  status text not null default 'pending',
  reviewed_at timestamptz,
  posted_at timestamptz,
  created_at timestamptz not null default now()
);

-- indexes
create index if not exists idx_tweets_tweet_id on tweets(tweet_id);
create index if not exists idx_replies_status on replies(status);
create index if not exists idx_replies_posted_at on replies(posted_at);
