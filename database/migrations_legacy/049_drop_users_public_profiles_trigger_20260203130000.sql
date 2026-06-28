-- 049) Drop users_public_profiles sync trigger (handled in app logic)
DROP TRIGGER IF EXISTS users_public_profiles_sync ON users;
