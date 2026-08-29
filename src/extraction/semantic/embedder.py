from sentence_transformers import SentenceTransformer


class SemanticEmbedder:
    """Generate semantic embeddings using a local Sentence Transformer."""

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
    ):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(
        self,
        texts: str | list[str],
    ):
        return self.model.encode(
            texts,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )