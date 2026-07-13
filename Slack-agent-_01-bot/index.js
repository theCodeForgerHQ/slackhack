import dotenv from 'dotenv';

dotenv.config();

function required(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const config = {
  slack: {
    botToken: required('SLACK_BOT_TOKEN'),
    signingSecret: required('SLACK_SIGNING_SECRET'),
    appToken: process.env.SLACK_APP_TOKEN || null,
    socketMode: process.env.SLACK_SOCKET_MODE === 'true',
    port: parseInt(process.env.PORT || '3000', 10),
  },
  supabase: {
    url: process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL,
    anonKey: process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY,
  },
  ai: {
    provider: process.env.AI_PROVIDER || 'openai',
    apiKey: process.env.AI_API_KEY || null,
    model: process.env.AI_MODEL || 'gpt-4o',
    maxSearchResults: parseInt(process.env.RTS_MAX_RESULTS || '10', 10),
  },
  rts: {
    channelTypes: process.env.RTS_CHANNEL_TYPES || 'public_channel,private_channel',
    contentTypes: process.env.RTS_CONTENT_TYPES || 'messages,files',
  },
};
