 Proposed Plan


  # Plan: Convert Chatbot to Local RAG

  ## Summary

  Replace the current “Gemini extracts dish name + fuzzy CSV lookup” mechanic with a local RAG pipeline using TF-IDF
  retrieval over recipes and products, then use Gemini only to generate a grounded answer from retrieved context. Preserve
  the existing /chatbot/get-response/ endpoint and current widget behavior, including "ok" to add ingredients/products to
  cart.

  ## Key Changes

  - Add scikit-learn to requirements.txt for TfidfVectorizer and cosine retrieval.
  - Add a new RAG utility module, e.g. chatbot/utils/rag_engine.py, with:
      - Recipe index built from data/recipes.csv using Title, Cleaned_Ingredients/Ingredients, and Instructions.
      - Product index built from active/in-stock Product rows using title, description, category/vendor if available.
      - Lazy in-memory indexes per Django process; no vector DB or persisted index in v1.
  - Retrieval behavior:
      - Query retrieves top 5 recipe candidates and top 10 product candidates.
      - If top recipe score is too low, return a “not enough information” response instead of hallucinating.
      - “Another dish” retrieves alternatives while excluding recipes already suggested in the current Django session.
  - Gemini behavior:
      - Prompt Gemini with only retrieved recipe/product context.
      - Instruct it to answer using retrieved context only, keep recipe title, ingredients, and instructions clear, and ask
        whether to add matching products to cart.
      - If Gemini/API key fails, fall back to deterministic template output from the top retrieved recipe.
  - Cart behavior:
      - After a recipe answer, store pending_ingredients, selected recipe metadata, and matched product IDs in Django
        session.
      - On "ok", add matched products to request.session["cart_data_obj"].
      - If some ingredients have no matching product, tell the user which ingredients were not added.
  - Frontend/session behavior:
      - Update templates/partials/chatbot_widget.html to send a persistent session_id via localStorage, matching the
        standalone chat page.
      - Keep response JSON compatible: { "reply": "...", "session_id": "..." }.

  ## Implementation Details

  - Keep existing endpoint name and route: POST /chatbot/get-response/.
  - Replace the main branch inside get_chatbot_response() with:
      - Parse message/session.
      - Handle "ok" cart confirmation first.
      - Detect alternative-intent messages.
      - Call RAG retrieval.
      - Generate grounded answer.
      - Save session state for follow-up/cart.
  - Keep old data_loader.py functions temporarily if other code uses them, but route the chatbot endpoint through the new
    RAG engine.
  - Use product retrieval for cart matching instead of only fuzzywuzzy.extractOne, but keep fuzzy matching as fallback if
    product TF-IDF score is low.
  - Do not add database migrations for v1.

  ## Test Plan
      - Recipe retrieval returns relevant recipes for queries like bread, chicken, mac and cheese, and ingredient-style
        prompts.
      - Alternative retrieval excludes the previous recipe.
      - Product retrieval maps common ingredients to available products when matching products exist.
      - Low-confidence queries return a safe “not found” response.
  - Endpoint tests:
      - POST /chatbot/get-response/ returns recipe answer with session_id.
      - Follow-up "another dish" returns a different recipe.
      - Follow-up "ok" adds matched products to cart_data_obj.
      - Gemini unavailable still returns deterministic recipe output.
  - Manual tests:
      - Floating widget on homepage works.
      - Standalone /chatbot/ page works.
      - Cart count updates after "ok" and cart page shows added products.

  ## Assumptions

  - Use local TF-IDF RAG for v1, not Gemini embeddings or FAISS/Chroma.
  - Index both recipes and products.
  - Gemini should only generate grounded answers from retrieved context.
  - No new public API route is needed.
  - No persistent vector index is needed until performance becomes a problem.