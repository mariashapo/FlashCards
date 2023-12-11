/* These queries are stored in the Supabase database and are accessed in app.py through the SupabaseClient object.
For example, using supabase.rpc("get_random_words_for_same_owner", {"exclude_word_id": word_id})
The queries are included here for reference.
*/


CREATE OR REPLACE FUNCTION get_random_words_for_same_owner(exclude_word_id bigint)
RETURNS TABLE(word2 character varying) AS $$
DECLARE
    owner_of_word bigint;
BEGIN
    -- Find the owner_id of the topic related to the exclude_word_id
    SELECT t.owner_id INTO owner_of_word FROM "Flashcards" f
    JOIN "Topics" t ON f.topic_id = t.id
    WHERE f.id = exclude_word_id;

    -- Fetch three random word ids that have the same owner and are not the excluded word
    RETURN QUERY 
    SELECT f.word2 FROM "Flashcards" f
    JOIN "Topics" t ON f.topic_id = t.id
    WHERE t.owner_id = owner_of_word AND f.id != exclude_word_id
    ORDER BY RANDOM()
    LIMIT 3;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_random_word_for_topic(topic_id_ bigint)
RETURNS TABLE(word_id bigint, word1 character varying, word2 character varying) AS $$
BEGIN
    -- Fetch one random word that has the specified topic_id
    RETURN QUERY 
    SELECT f.id, f.word1, f.word2 FROM "Flashcards" f
    WHERE f.topic_id = topic_id_ AND learned = false
    ORDER BY RANDOM()
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION max_id()
RETURNS integer AS $$
DECLARE
  max_id_value integer;
BEGIN
  SELECT MAX(id) INTO max_id_value FROM "Topics";
  RETURN COALESCE(max_id_value, 0);
END;
$$ LANGUAGE plpgsql;