import re
from urllib.parse import unquote

import numpy as np

from .constants import model


def cosine_similarity(A, B):
    return float((np.dot(A, B) / (np.linalg.norm(A) * np.linalg.norm(B))))


def retrieve_top_n_content_pieces(
    user_input, queryset, n=5, content_type=None, platform="web"
):
    if not model:
        return []

    # similar_embeddings = [{'faq_name':, 'faq_content':, 'embedding':}, ...] # We need to filter by content type and then retrieve their embeddings
    # Generate embedding for user text
    user_embedding = model.encode([user_input])

    documents_retrieved = []
    for page in queryset:
        try:
            page_plat_embedding = page.embedding[platform]["values"]
        except (KeyError, TypeError):
            continue  # The page doesn't have embedding for this platform
        similarity_score = cosine_similarity(
            user_embedding[0].tolist(), page_plat_embedding
        )  # Replace with your cosine similarity calculation
        documents_retrieved.append((page.pk, page.title, page.body, similarity_score))
    documents_retrieved = sorted(documents_retrieved, key=lambda x: x[3], reverse=True)
    content_retrieved = [doc[0] for doc in documents_retrieved[0:n]]
    return content_retrieved


def _generate_regex_dashed_url(n_min_dashed_words_url):
    """
    Generate regex to parse dashed words from URL

    Parameters
    ----------
    n_min_dashed_words_url : int
        The number of words that must be separated by dashes in a URL, to treat the
        text as an actual relevant content summary

        For example, many websites have "breaking-news" in the URL, but we
        don't care to extract this as a content summary
    """
    word_and_dash = "[a-z0-9]+-"
    regexp = (
        r"\/(" + (n_min_dashed_words_url - 1) * word_and_dash + r"["
        r"a-z0-9-]*)(?:\/|\.|$)"
    )
    return regexp


def preprocess_content_for_embedding(content):
    content = unquote(
        content
    )  # Replace %xx escapes with their single-character equivalent.
    urls = re.findall(r"((?:https?:\/\/|www)(?:[^ ]+))", content)  # Find URLs
    for (
        url
    ) in (
        urls
    ):  # Replace URL portions with n_words_min or more words that are separated by dashes
        extract = re.findall(_generate_regex_dashed_url(2), url)
        extract = " ".join(extract)
        content = content.replace(url, extract)
    content = (
        "".join(content.split("*", 2)[2:])
        .replace("\n\n", " ")
        .replace("\n", " ")
        .replace("  ", " ")
        .replace("*", "")
    )  # Remove content piece title
    if len(content) < 2:
        return content
    if content[0] == " ":  # Remove space trailing content title
        content = content[1:]
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # Chinese characters
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u200d"
        "\u2640-\u2642"
        "]+",
        flags=re.UNICODE,
    )
    content = emoji_pattern.sub(r"", content)  # Remove emojis
    return content
