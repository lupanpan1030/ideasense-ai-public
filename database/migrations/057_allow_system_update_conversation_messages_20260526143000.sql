-- 057) Allow system-owned assistant message replacement after streaming compose.
--
-- The chat API now inserts a fallback assistant message before SSE streaming
-- starts, then replaces that same assistant message if the composed output
-- completes successfully. Keep the update scope limited to non-user messages.

DROP POLICY IF EXISTS conversation_messages_system_update
    ON conversation_messages;

CREATE POLICY conversation_messages_system_update
    ON conversation_messages
    FOR UPDATE USING (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
        AND role <> 'user'
    )
    WITH CHECK (
        app_actor_type() = 'system'
        AND org_id = app_org_id()
        AND role <> 'user'
    );
