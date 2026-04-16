import { createClient, SupabaseClient } from "@supabase/supabase-js";

// Lazy singleton — defers createClient() until first property access so that
// Next.js static page-data collection at build time never sees missing env vars.
let _client: SupabaseClient | null = null;

function getClient(): SupabaseClient {
  if (!_client) {
    _client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    );
  }
  return _client;
}

export const supabase = new Proxy({} as SupabaseClient, {
  get(_target, prop: string) {
    return getClient()[prop as keyof SupabaseClient];
  },
});
